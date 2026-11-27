# Copyright 2026 markurtz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
The release flow: plan, write, pull request and tag.

A plan is computed first and changes nothing. The three stages build on it:
writing edits the changelog and the committed targets, the pull request stage
commits those edits to the release branch and opens or updates the pull request,
and the tag stage tags the merged release commit.

Example:
::
    from gitversioned.config import load_config
    from gitversioned.release import plan_release

    plan = plan_release(load_config(), use_github=False)
    print(plan.version.pep440(), plan.tag)
    print(plan.section)
"""

from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass, field, replace
from pathlib import Path

from loguru import logger

from gitversioned import forges, git
from gitversioned.changelog import (
    MIGRATIONS,
    Entry,
    Style,
    carried_entries,
    entries_from_commits,
    insert_section,
    read_section,
    render_section,
)
from gitversioned.changes import change_commits
from gitversioned.checks import check_tag
from gitversioned.commits import (
    BumpPlan,
    env_bump,
    level_text,
    next_version,
    parse_subject,
)
from gitversioned.config import Config
from gitversioned.errors import (
    CheckFailedError,
    ConfigError,
    EnvironmentProblemError,
    NothingToReleaseError,
)
from gitversioned.forges import PullRequest
from gitversioned.model import Version
from gitversioned.publish import Published, publish, semver_breaks
from gitversioned.resolve import (
    Resolved,
    match_tag,
    own_tag_folders,
    release_tags,
    resolve,
    tag_name,
)
from gitversioned.targets import Change, discover, stamp

__all__ = [
    "RELEASE_BRANCH",
    "RELEASE_LABEL",
    "ReleasePlan",
    "changelog_path",
    "forge_release",
    "maintenance_branch",
    "open_release_pr",
    "package_context",
    "plan_release",
    "publish_release",
    "tag_release",
    "write_release",
]

RELEASE_BRANCH = "release/next"
RELEASE_LABEL = "release"
RC_LABEL = "release:rc"
_BUMP_LABELS = {
    "release:major": "major",
    "release:minor": "minor",
    "release:patch": "patch",
}
_RANK = {"patch": 1, "minor": 2, "major": 3}


@dataclass
class ReleasePlan:
    """
    Everything a release would do.

    :param version: Version to release.
    :param previous: Version of the latest release tag, if any.
    :param tag: Tag the release gets.
    :param level: Bump level and where it came from, for the report.
    :param section: Rendered changelog section.
    :param files: Paths the release changes, relative to the project root.
    :param entries: Changelog entries.
    :param bump: What the commits asked for.
    :param package: Package being released, when not the repository.
    :param title: Title of the release commit and pull request.
    :param branch: Release branch name.
    :param base: Branch the release pull request merges into.
    :param consumed: Change files the release takes in and deletes.
    """

    version: Version
    previous: Version | None
    tag: str
    level: str
    section: str
    files: list[str]
    entries: list[Entry] = field(default_factory=list)
    bump: BumpPlan = field(default_factory=lambda: BumpPlan(None, ()))
    package: str | None = None
    title: str = ""
    branch: str = RELEASE_BRANCH
    base: str = "main"
    consumed: list[str] = field(default_factory=list)


def package_context(config: Config, package: str | None) -> tuple[str, str | None]:
    """
    Work out the tag template and commit scope for the repository or a package.

    :param config: The loaded configuration.
    :param package: Package name from ``[packages]``, or ``None``.
    :return: The tag template and the folder whose commits count.
    :raises ConfigError: If the package is unknown.
    """
    if package is None:
        return config.tag, None
    if package not in config.packages:
        raise ConfigError(
            f"unknown package {package!r}. Packages: "
            f"{', '.join(config.packages) or 'none configured'}."
        )
    item = config.packages[package]
    if item.tag is None:
        return config.tag, None
    return item.tag, item.path


def changelog_path(config: Config, package: str | None) -> str | None:
    """
    Name the changelog a release of the repository or a package edits.

    :param config: The loaded configuration.
    :param package: Package with its own tag, or ``None`` for the repository.
    :return: The path relative to the project root, or ``None`` when it is off.
    """
    if config.changelog is False:
        return None
    if package is not None and config.packages[package].tag:
        return f"{config.packages[package].path.rstrip('/')}/CHANGELOG.md"
    return str(config.changelog)


def _require_own_tag(config: Config, package: str | None) -> None:
    """Refuse to release a package that follows the repository version."""
    if package is None:
        return
    package_context(config, package)
    if config.packages[package].tag is None:
        raise ConfigError(
            f"package {package!r} has no `tag` of its own, so it is released with "
            "the repository. Run the release without -p, or give the package a "
            "`tag` such as "
            f'"{package}-v{{version}}".'
        )


def _require_repo(config: Config) -> git.Repo:
    """Open the repository or fail with an environment error."""
    repo = git.Repo.open(config.root)
    if repo is None or repo.head() is None:
        raise EnvironmentProblemError("a release needs a git repository with commits.")
    return repo


def _pull_requests(
    forge: forges.Forge | None, commits: list[git.Commit]
) -> dict[int, PullRequest]:
    """Read the pull requests behind squash commits, when the forge is reachable."""
    requests: dict[int, PullRequest] = {}
    if forge is None or not forge.available():
        return requests
    for commit in commits:
        parsed = parse_subject(commit.subject)
        number = parsed.pr if parsed else None
        if number is None or number in requests:
            continue
        found = forge.pull_request(number)
        if found is not None:
            requests[number] = found
    return requests


def _label_bump(
    commits: list[git.Commit], requests: dict[int, PullRequest]
) -> str | None:
    """Return the highest bump level asked for by pull request labels."""
    best: str | None = None
    for commit in commits:
        parsed = parse_subject(commit.subject)
        request = requests.get(parsed.pr) if parsed and parsed.pr else None
        for label in request.labels if request else ():
            level = _BUMP_LABELS.get(label)
            if level and (best is None or _RANK[level] > _RANK[best]):
                best = level
    return best


def _overrides(
    version: str | None,
    bump: str | None,
    labelled: str | None,
) -> tuple[str | None, str | None, str]:
    """
    Settle which override applies.

    :return: The explicit version or level, the bump level and where the choice
        came from, in the order VERSION, ``--bump``, environment, label, commits.
    """
    if version is not None:
        return version, bump, "VERSION"
    if bump is not None:
        return None, bump, "--bump"
    from_env = env_bump()
    if from_env:
        return from_env, None, "GITVERSIONED__BUMP"
    if labelled:
        return None, labelled, "label"
    return None, None, "commits"


def _level_text(  # noqa: PLR0913
    resolved: Resolved,
    plan: BumpPlan,
    *,
    explicit: str | None,
    bump: str | None,
    source: str,
    why: str = "commits",
) -> str:
    """Describe how the release level was chosen, for the plan report."""
    level = bump or (explicit if explicit in _RANK else None)
    if explicit and explicit not in _RANK:
        text = f"set by {source}"
    elif level:
        text = f"{level}, from {source}"
    elif resolved.base is None:
        text = "first release"
    elif resolved.base.pre is not None:
        text = f"final of {resolved.base.pep440()}"
    else:
        named = level_text(plan.level or "patch", resolved.base, shift=plan.shift)
        text = f"{named}, from {why}"
    if resolved.base is not None:
        text += f", from {resolved.base.pep440()}"
    return text


def _release_files(config: Config, package: str | None) -> list[str]:
    """List the files a release changes, relative to the project root."""
    files: list[str] = []
    changelog = changelog_path(config, package)
    if changelog:
        files.append(changelog)
    root = config.root.resolve()
    files += [
        item.path.resolve().relative_to(root).as_posix()
        for item in discover(config, package=package)
        if item.commit
    ]
    return files


_RANGE_RE = re.compile(r"^(?:.*/)?v?(?P<major>\d+)\.(?:(?P<minor>\d+)\.)?x$")


def maintenance_branch(config: Config, branch: str | None) -> bool:
    """
    :return: True when a branch is one of the ``branches`` maintenance branches.
    """
    return bool(branch) and any(
        fnmatch.fnmatchcase(branch or "", pattern) for pattern in config.branches
    )


def _current_branch(repo: git.Repo) -> str | None:
    """The branch being released, also on a detached CI checkout."""
    return (
        repo.branch()
        or os.environ.get("GITHUB_HEAD_REF")
        or os.environ.get("GITHUB_REF_NAME")
        or os.environ.get("CI_COMMIT_REF_NAME")
        or None
    )


def _check_line(branch: str, target: Version) -> None:
    """Keep a release on an ``N.x`` or ``N.M.x`` branch inside its line."""
    match = _RANGE_RE.match(branch)
    if match is None:
        return
    major = int(match["major"])
    minor = int(match["minor"]) if match["minor"] is not None else None
    if target.major != major or (minor is not None and target.minor != minor):
        line = f"{major}.{minor}" if minor is not None else f"{major}"
        raise CheckFailedError(
            f"{target.pep440()} is outside the {line}.x line that {branch!r} "
            "maintains. Release a smaller change, or release from the main branch."
        )


def _semver_plan(
    config: Config, plan: BumpPlan, base: Version | None, baseline: str | None
) -> tuple[BumpPlan, bool]:
    """Raise the commit level to major when cargo semver-checks finds a break."""
    if not config.semver_checks or baseline is None or base is None:
        return plan, False
    if plan.level == "major" or not semver_breaks(config, baseline):
        return plan, False
    return replace(plan, level="major"), True


def _post_version(finals: dict[str, Version], last_final: str | None) -> str:
    """The next post release of the latest final release."""
    if last_final is None:
        raise CheckFailedError("a post release needs an earlier final release.")
    latest = finals[last_final]
    return latest.with_parts(post=(latest.post or 0) + 1).pep440()


def plan_release(  # noqa: PLR0913, PLR0914
    config: Config,
    *,
    version: str | None = None,
    bump: str | None = None,
    pre: str | None = None,
    package: str | None = None,
    use_github: bool = True,
    post: bool = False,
) -> ReleasePlan:
    """
    Compute what a release would do, changing nothing.

    :param config: The loaded configuration.
    :param version: Version to release exactly.
    :param bump: Level that replaces the one chosen from commits.
    :param pre: Make the release a pre-release of this kind.
    :param package: Package to release instead of the repository.
    :param use_github: Read pull request titles, bodies and labels from the
        forge when it is reachable.
    :param post: Release the next post release of the latest final release.
    :return: The plan.
    :raises NothingToReleaseError: If nothing releasable happened since the last
        release and no override is given.
    :raises CheckFailedError: If the chosen version is not newer than the last
        release, or leaves the line a maintenance branch keeps.
    """
    repo = _require_repo(config)
    _require_own_tag(config, package)
    template, scope = package_context(config, package)
    resolved = resolve(config, tag_template=template, path_scope=scope)
    forge = forges.current(config)

    merged = repo.tags_merged()
    tags = release_tags(template, list(merged))
    finals = {name: found for name, found in tags.items() if found.is_final}
    last_final = (
        max(finals, key=lambda name: finals[name].sort_key()) if finals else None
    )
    scope_path = (config.root / scope) if scope else None
    excluded = [] if scope_path else own_tag_folders(config)
    since_final = repo.commits(
        merged[last_final] if last_final else None, path=scope_path, exclude=excluded
    )
    changes = change_commits(config, scope)
    requests = _pull_requests(forge if use_github else None, since_final)
    if post:
        version = _post_version(finals, last_final)
    # Labels on every pull request since the last final release count, so a
    # final release after a candidate still sees them.
    explicit, chosen, source = _overrides(
        version, bump, _label_bump(since_final, requests)
    )
    if post:
        source = "--post"
    bump_plan, broke = _semver_plan(config, resolved.plan, resolved.base, resolved.tag)
    target = next_version(
        resolved.base,
        resolved.known,
        bump_plan,
        fallback=Version.parse(config.fallback),
        explicit=explicit,
        bump=chosen,
        pre=pre,
    )
    if resolved.base is not None and target.sort_key() <= resolved.base.sort_key():
        raise CheckFailedError(
            f"{target.pep440()} is not newer than {resolved.tag} "
            f"({resolved.base.pep440()})."
        )
    branch = _current_branch(repo)
    maintained = maintenance_branch(config, branch) and branch != config.branch
    if maintained and branch:
        _check_line(branch, target)
    style = replace(Style.from_config(config), pr_path=forge.pr_path)
    entries = _merge_entries(
        carried_entries(
            _changelog_text(config, package), target, (*style.kinds, MIGRATIONS)
        ),
        entries_from_commits(changes + since_final, requests, style),
    )
    day = git.build_time().strftime("%Y-%m-%d")
    name = tag_name(template, target)
    prefix = f"release({package})" if package else "release"
    why = "cargo semver-checks" if broke else "commits"
    level = _level_text(
        resolved, bump_plan, explicit=explicit, bump=chosen, source=source, why=why
    )
    release_branch = f"{RELEASE_BRANCH}-{package}" if package else RELEASE_BRANCH
    if maintained and branch:
        release_branch += "-" + re.sub(r"[^A-Za-z0-9._-]+", "-", branch)
    consumed = [commit.path for commit in changes if commit.path]
    return ReleasePlan(
        version=target,
        previous=resolved.base,
        tag=name,
        level=level,
        section=render_section(
            target,
            entries,
            day=day,
            repo_url=forge.web,
            style=style,
            tag=name,
            previous=resolved.tag,
        ),
        files=_release_files(config, package) + consumed,
        entries=entries,
        bump=bump_plan,
        package=package,
        title=f"{prefix}: {name}",
        branch=release_branch,
        base=branch if maintained and branch else config.branch,
        consumed=consumed,
    )


def _changelog_text(config: Config, package: str | None) -> str:
    """Read the changelog a release would edit, or an empty string."""
    changelog = changelog_path(config, package)
    path = config.root / changelog if changelog else None
    return path.read_text(encoding="utf-8") if path and path.is_file() else ""


def _merge_entries(carried: list[Entry], derived: list[Entry]) -> list[Entry]:
    """Put carried entries first and drop derived ones already carried."""
    seen = {(entry.kind, entry.scope, entry.text) for entry in carried}
    return carried + [
        entry for entry in derived if (entry.kind, entry.scope, entry.text) not in seen
    ]


def write_release(config: Config, plan: ReleasePlan) -> list[str]:
    """
    Apply a plan to the working tree: changelog, committed targets and the
    change files it took in, which are deleted.

    :param config: The loaded configuration.
    :param plan: The plan to apply.
    :return: Paths that changed, relative to the project root.
    """
    changed: list[str] = []
    changelog = changelog_path(config, plan.package)
    if changelog:
        path = config.root / changelog
        old = path.read_text(encoding="utf-8") if path.is_file() else ""
        new = insert_section(old, plan.version, plan.section)
        if new != old:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8", newline="") as handle:
                handle.write(new)
            changed.append(changelog)
    resolved = Resolved(
        version=plan.version, type="release", source="release", tag=plan.tag
    )
    changes: list[Change] = stamp(
        config, resolved, package=plan.package, committed_only=True
    )
    changed += [change.path for change in changes if change.written]
    for relative in plan.consumed:
        path = config.root / relative
        if path.is_file():
            path.unlink()
            changed.append(relative)
    return changed


def _identity(repo: git.Repo) -> list[str]:
    """Return ``-c`` options giving git an author when none is configured."""
    if repo.git("config", "user.email", check=False):
        return []
    return [
        "-c",
        "user.name=github-actions[bot]",
        "-c",
        "user.email=41898282+github-actions[bot]@users.noreply.github.com",
    ]


def open_release_pr(
    config: Config,
    *,
    version: str | None = None,
    bump: str | None = None,
    pre: str | None = None,
    package: str | None = None,
    post: bool = False,
) -> tuple[ReleasePlan, PullRequest, bool]:
    """
    Open the release pull request, or update the one already open.

    The release branch is rebuilt from the current commit every time, so the pull
    request always holds exactly one commit on top of the release branch's base.
    On a maintenance branch from ``branches`` the pull request merges into that
    branch, from ``release/next-<branch>``.

    :param config: The loaded configuration.
    :param version: Version to release exactly.
    :param bump: Level that replaces the one chosen from commits.
    :param pre: Make the release a pre-release of this kind.
    :param package: Package to release instead of the repository.
    :param post: Release the next post release of the latest final release.
    :return: The plan, the pull request and whether it was newly opened.
    :raises CheckFailedError: If the working tree has uncommitted changes or
        the command runs on a branch other than the release branch.
    :raises NothingToReleaseError: If ``HEAD`` is a merged release commit whose
        tag does not exist yet, so the release is still waiting for its tag.
    """
    repo = _require_repo(config)
    forge = forges.current(config)
    forge.require("release --pr")
    if repo.dirty_paths():
        raise CheckFailedError(
            "the working tree has uncommitted changes; commit or stash them first."
        )
    current = repo.branch()
    if (
        current is not None
        and current != config.branch
        and not maintenance_branch(config, current)
    ):
        allowed = ", ".join(repr(name) for name in [config.branch, *config.branches])
        raise CheckFailedError(
            f"release --pr runs on {allowed}, not {current!r}: the release "
            "would carry this branch's unmerged commits."
        )
    _require_own_tag(config, package)
    pending = _released_tag(repo, package)
    if pending is not None and pending not in repo.all_tags():
        raise NothingToReleaseError(
            f"HEAD is the merged release commit for {pending}, which is not tagged "
            "yet. Run release --tag first."
        )
    plan = plan_release(
        config, version=version, bump=bump, pre=pre, package=package, post=post
    )
    existing = forge.find_open(plan.branch)
    if pre is None and existing is not None and RC_LABEL in existing.labels:
        plan = plan_release(
            config, version=version, bump=bump, pre="rc", package=package, post=post
        )

    start = current or repo.head() or "HEAD"
    repo.git("checkout", "-q", "-B", plan.branch)
    try:
        changed = write_release(config, plan)
        root_in_repo = config.root.resolve().relative_to(repo.top).as_posix()
        paths = [
            path if root_in_repo == "." else f"{root_in_repo}/{path}"
            for path in changed
        ]
        if paths:
            repo.git("add", "-A", "--", *paths)
        repo.git(*_identity(repo), "commit", "-q", "--allow-empty", "-m", plan.title)
        repo.git("push", "-q", "--force", "origin", plan.branch)
    except BaseException:
        # Leave no release edits behind on the branch the command started from.
        repo.git("reset", "-q", "--hard", check=False)
        raise
    finally:
        repo.git("checkout", "-q", start, check=False)

    body = (
        f"{plan.section}\n---\n"
        f"Merging this pull request releases `{plan.tag}`. "
        f"Add the `{RC_LABEL}` label to make it a release candidate.\n"
    )
    if existing is None:
        request = forge.create(
            head=plan.branch,
            base=plan.base,
            title=plan.title,
            body=body,
            label=RELEASE_LABEL,
        )
        return plan, request, True
    forge.update(existing.number, title=plan.title, body=body)
    return plan, existing, False


_RELEASE_SUBJECT = re.compile(r"^release(?:\((?P<package>[^)]+)\))?: (?P<tag>\S+)")


def _released_tag(repo: git.Repo, package: str | None) -> str | None:
    """Read the tag named by the release commit at ``HEAD``, if it is one."""
    subjects = [repo.git("log", "-1", "--format=%s", "HEAD", check=False) or ""]
    second = repo.git("log", "-1", "--format=%s", "HEAD^2", check=False)
    if second:
        subjects.append(second)
    for subject in subjects:
        match = _RELEASE_SUBJECT.match(subject)
        if match and (match["package"] or None) == package:
            return match["tag"]
    return None


def tag_release(
    config: Config,
    *,
    version: str | None = None,
    package: str | None = None,
    push: bool = True,
) -> tuple[str, str, bool]:
    """
    Tag the release commit and push the tag.

    Without a version, ``HEAD`` must be the merged release commit, whose subject
    names the tag. With a version, ``HEAD`` is tagged by hand after the same
    checks.

    :param config: The loaded configuration.
    :param version: Version to tag by hand.
    :param package: Package to tag instead of the repository.
    :param push: Push the tag to ``origin`` when that remote exists.
    :return: The tag name, the tagged commit and whether the tag was pushed.
    :raises CheckFailedError: If there is nothing to tag or the tag is not newer
        than the last release.
    """
    repo = _require_repo(config)
    _require_own_tag(config, package)
    template, _scope = package_context(config, package)
    if version is not None:
        name = tag_name(template, Version.parse(version))
    else:
        found = _released_tag(repo, package)
        if found is None:
            raise CheckFailedError(
                "nothing to tag: HEAD is not a merged release pull request. "
                "Pass a VERSION to tag by hand."
            )
        name = found
    target = match_tag(template, name)
    if target is None:
        raise CheckFailedError(
            f"{name!r} does not follow the tag template {template!r}."
        )
    if name in repo.all_tags():
        raise CheckFailedError(f"tag {name} already exists.")
    # The same checks as `check --tag`: newer than every release, and the
    # changelog holds the section the tag releases.
    changelog = changelog_path(config, package)
    for finding in check_tag(config, name, template=template, changelog=changelog):
        if finding.status == "fail":
            raise CheckFailedError(finding.message)
    sha = repo.head() or ""
    if config.annotated:
        message = (
            read_section(config.root / changelog, target) if changelog else None
        ) or name
        repo.git(
            *_identity(repo), "tag", "-a", name, "-m", message, "--cleanup=verbatim"
        )
    else:
        repo.git("tag", name)
    pushed = False
    if push and repo.git("remote", "get-url", "origin", check=False):
        repo.git("push", "-q", "origin", f"refs/tags/{name}")
        pushed = True
    else:
        logger.info("no origin remote; tag {} was created locally only", name)
    return name, sha, pushed


def _tag_at_head(
    config: Config, repo: git.Repo, package: str | None
) -> tuple[str, Version]:
    """Find the release tag that points at ``HEAD``."""
    template, _scope = package_context(config, package)
    output = repo.git("tag", "--points-at", "HEAD", check=False)
    names: list[str] = output.split() if output else []
    found = release_tags(template, names)
    if not found:
        raise CheckFailedError(
            "HEAD has no release tag. Publish from the tagged release commit, "
            "or run release --tag first."
        )
    name = max(found, key=lambda tag: found[tag].sort_key())
    return name, found[name]


def forge_release(
    config: Config,
    *,
    package: str | None = None,
    files: list[Path] | None = None,
) -> str | None:
    """
    Create the forge release for the tag at ``HEAD``, with its changelog section.

    It is skipped, with a warning, when ``forge_release`` is off or the forge
    cannot be reached, so tagging never fails for want of a token.

    :param config: The loaded configuration.
    :param package: Package whose tag to release, or ``None``.
    :param files: Files to attach (GitHub only).
    :return: The release's address, or ``None`` when none was created.
    """
    if not config.forge_release:
        return None
    forge = forges.current(config)
    if not forge.available():
        logger.warning(
            "no {} release created for the tag: it needs {}",
            {"github": "GitHub", "gitlab": "GitLab", "gitea": "Gitea"}[forge.name],
            forge.cli,
        )
        return None
    repo = _require_repo(config)
    name, version = _tag_at_head(config, repo, package)
    changelog = changelog_path(config, package)
    section = read_section(config.root / changelog, version) if changelog else None
    notes = section.split("\n", 1)[1].strip() if section and "\n" in section else ""
    return forge.create_release(
        tag=name,
        notes=notes or name,
        prerelease=not version.is_final,
        files=files or [],
    )


def publish_release(
    config: Config,
    *,
    package: str | None = None,
    dry_run: bool = False,
) -> tuple[str, Published]:
    """
    Publish the release tagged at ``HEAD`` to its package registries.

    :param config: The loaded configuration.
    :param package: Package to publish instead of the repository.
    :param dry_run: Run each tool's dry run instead of uploading.
    :return: The tag and what ran.
    :raises CheckFailedError: If ``HEAD`` is not a tagged release or a tool fails.
    """
    repo = _require_repo(config)
    _require_own_tag(config, package)
    name, version = _tag_at_head(config, repo, package)
    done = publish(
        config, package=package, prerelease=not version.is_final, dry_run=dry_run
    )
    return name, done
