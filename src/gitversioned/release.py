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

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from gitversioned import git, github
from gitversioned.changelog import (
    Entry,
    entries_from_commits,
    insert_section,
    read_section,
    render_section,
)
from gitversioned.commits import BumpPlan, env_bump, next_version, parse_subject
from gitversioned.config import Config
from gitversioned.errors import (
    CheckFailedError,
    ConfigError,
    EnvironmentProblemError,
)
from gitversioned.logging import logger
from gitversioned.model import Version
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
    "open_release_pr",
    "package_context",
    "plan_release",
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


def _changelog_path(config: Config, package: str | None) -> str | None:
    """Return the changelog path, relative to the project root."""
    if config.changelog is False:
        return None
    if package is not None and config.packages[package].tag:
        return f"{config.packages[package].path.rstrip('/')}/CHANGELOG.md"
    return str(config.changelog)


def _require_repo(config: Config) -> git.Repo:
    """Open the repository or fail with an environment error."""
    repo = git.Repo.open(config.root)
    if repo is None or repo.head() is None:
        raise EnvironmentProblemError("a release needs a git repository with commits.")
    return repo


def _pull_requests(
    config: Config, commits: list[git.Commit], use_github: bool
) -> dict[int, github.PullRequest]:
    """Read the pull requests behind squash commits, when GitHub is reachable."""
    requests: dict[int, github.PullRequest] = {}
    if not use_github or not github.available(config.root):
        return requests
    for commit in commits:
        parsed = parse_subject(commit.subject)
        number = parsed.pr if parsed else None
        if number is None or number in requests:
            continue
        found = github.pull_request(config.root, number)
        if found is not None:
            requests[number] = found
    return requests


def _label_bump(
    commits: list[git.Commit], requests: dict[int, github.PullRequest]
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


def _level_text(
    resolved: Resolved, explicit: str | None, bump: str | None, source: str
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
        text = f"{resolved.plan.level}, from commits"
    if resolved.base is not None:
        text += f", from {resolved.base.pep440()}"
    return text


def _release_files(config: Config, package: str | None) -> list[str]:
    """List the files a release changes, relative to the project root."""
    files: list[str] = []
    changelog = _changelog_path(config, package)
    if changelog:
        files.append(changelog)
    root = config.root.resolve()
    files += [
        item.path.resolve().relative_to(root).as_posix()
        for item in discover(config, package=package)
        if item.commit
    ]
    return files


def plan_release(  # noqa: PLR0913
    config: Config,
    *,
    version: str | None = None,
    bump: str | None = None,
    pre: str | None = None,
    package: str | None = None,
    use_github: bool = True,
) -> ReleasePlan:
    """
    Compute what a release would do, changing nothing.

    :param config: The loaded configuration.
    :param version: Version to release exactly.
    :param bump: Level that replaces the one chosen from commits.
    :param pre: Make the release a pre-release of this kind.
    :param package: Package to release instead of the repository.
    :param use_github: Read pull request titles, bodies and labels through ``gh``
        when it is available.
    :return: The plan.
    :raises NothingToReleaseError: If nothing releasable happened since the last
        release and no override is given.
    :raises CheckFailedError: If the chosen version is not newer than the last
        release.
    """
    repo = _require_repo(config)
    template, scope = package_context(config, package)
    resolved = resolve(config, tag_template=template, path_scope=scope)

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
    since_tag = repo.commits(
        merged[resolved.tag] if resolved.tag else None,
        path=scope_path,
        exclude=excluded,
    )
    requests = _pull_requests(config, since_final, use_github)
    explicit, chosen, source = _overrides(
        version, bump, _label_bump(since_tag, requests)
    )
    target = next_version(
        resolved.base,
        resolved.known,
        resolved.plan,
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
    entries = entries_from_commits(since_final, requests)
    day = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    name = tag_name(template, target)
    prefix = f"release({package})" if package else "release"
    return ReleasePlan(
        version=target,
        previous=resolved.base,
        tag=name,
        level=_level_text(resolved, explicit, chosen, source),
        section=render_section(
            target, entries, day=day, repo_url=github.repo_url(repo)
        ),
        files=_release_files(config, package),
        entries=entries,
        bump=resolved.plan,
        package=package,
        title=f"{prefix}: {name}",
        branch=f"{RELEASE_BRANCH}-{package}" if package else RELEASE_BRANCH,
    )


def write_release(config: Config, plan: ReleasePlan) -> list[str]:
    """
    Apply a plan to the working tree: changelog and committed targets.

    :param config: The loaded configuration.
    :param plan: The plan to apply.
    :return: Paths that changed, relative to the project root.
    """
    changed: list[str] = []
    changelog = _changelog_path(config, plan.package)
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
) -> tuple[ReleasePlan, github.PullRequest, bool]:
    """
    Open the release pull request, or update the one already open.

    The release branch is rebuilt from the current commit every time, so the pull
    request always holds exactly one commit on top of the release branch's base.

    :param config: The loaded configuration.
    :param version: Version to release exactly.
    :param bump: Level that replaces the one chosen from commits.
    :param pre: Make the release a pre-release of this kind.
    :param package: Package to release instead of the repository.
    :return: The plan, the pull request and whether it was newly opened.
    :raises CheckFailedError: If the working tree has uncommitted changes.
    """
    repo = _require_repo(config)
    if not github.available(config.root):
        raise EnvironmentProblemError(
            "release --pr needs the GitHub CLI `gh`, signed in (set GH_TOKEN in CI)."
        )
    if repo.dirty_paths():
        raise CheckFailedError(
            "the working tree has uncommitted changes; commit or stash them first."
        )
    branch = f"{RELEASE_BRANCH}-{package}" if package else RELEASE_BRANCH
    existing = github.find_open_pull_request(config.root, branch)
    if pre is None and existing is not None and RC_LABEL in existing.labels:
        pre = "rc"
    plan = plan_release(config, version=version, bump=bump, pre=pre, package=package)

    start = repo.branch() or repo.head() or "HEAD"
    repo.git("checkout", "-q", "-B", plan.branch)
    try:
        changed = write_release(config, plan)
        root_in_repo = config.root.resolve().relative_to(repo.top).as_posix()
        paths = [
            path if root_in_repo == "." else f"{root_in_repo}/{path}"
            for path in changed
        ]
        if paths:
            repo.git("add", "--", *paths)
        repo.git(*_identity(repo), "commit", "-q", "--allow-empty", "-m", plan.title)
        repo.git("push", "-q", "--force", "origin", plan.branch)
    finally:
        repo.git("checkout", "-q", start, check=False)

    body = (
        f"{plan.section}\n---\n"
        f"Merging this pull request releases `{plan.tag}`. "
        f"Add the `{RC_LABEL}` label to make it a release candidate.\n"
    )
    if existing is None:
        request = github.create_pull_request(
            config.root,
            head=plan.branch,
            base=config.branch,
            title=plan.title,
            body=body,
            label=RELEASE_LABEL,
        )
        return plan, request, True
    github.update_pull_request(
        config.root, existing.number, title=plan.title, body=body
    )
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
    existing = release_tags(template, repo.all_tags())
    if existing:
        latest = max(existing, key=lambda tag: existing[tag].sort_key())
        if target.sort_key() <= existing[latest].sort_key():
            raise CheckFailedError(f"{target.pep440()} is not newer than {latest}.")
    sha = repo.head() or ""
    if config.annotated:
        changelog = _changelog_path(config, package)
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
        logger.info("no origin remote; tag %s was created locally only", name)
    return name, sha, pushed
