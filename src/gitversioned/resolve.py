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
Resolution of the version of the current checkout.

Sources are tried in a fixed order: a pinned version, git tags, the ``git archive``
export file, source distribution metadata and finally the fallback. A missing or
untrustworthy answer warns on a developer machine and fails in CI.

Example:
::
    from gitversioned.config import load_config
    from gitversioned.resolve import resolve

    resolved = resolve(load_config())
    print(resolved.version.pep440(), resolved.type, resolved.source)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, cast

from loguru import logger

from gitversioned import git
from gitversioned.changes import change_commits
from gitversioned.commits import BumpPlan, next_version, plan_bump
from gitversioned.config import Config
from gitversioned.errors import (
    ConfigError,
    EnvironmentProblemError,
    NothingToReleaseError,
)
from gitversioned.model import Version

__all__ = [
    "BuildType",
    "Resolved",
    "env_build_type",
    "match_tag",
    "own_tag_folders",
    "release_tags",
    "resolve",
    "tag_name",
]

BuildType = Literal["release", "dev", "nightly"]
_BUILD_TYPES: Annotated[tuple[str, ...], "Values of GITVERSIONED__TYPE"] = (
    "release",
    "dev",
    "nightly",
)


def env_build_type() -> BuildType | None:
    """
    Read the ``GITVERSIONED__TYPE`` override, which build plugins honour too.

    :return: ``release``, ``dev`` or ``nightly``, or ``None`` when unset.
    :raises ConfigError: When the variable holds another value.
    """
    value = os.environ.get("GITVERSIONED__TYPE", "").strip().lower()
    if not value:
        return None
    if value not in _BUILD_TYPES:
        raise ConfigError(
            f"GITVERSIONED__TYPE must be release, dev or nightly, not {value!r}."
        )
    return cast("BuildType", value)


_SHORT_SHA = 7


@dataclass
class Resolved:
    """
    A resolved version and how it was reached.

    :param version: The version of this checkout.
    :param type: ``release``, ``dev`` or ``nightly``.
    :param source: Where the base came from: ``pin``, ``tag``, ``archive``,
        ``sdist`` or ``fallback``.
    :param tag: The release tag the version is based on, if any.
    :param base: The version that tag carries.
    :param distance: Commits since the tag.
    :param sha: Commit hash of the checkout.
    :param date: Commit date of the checkout.
    :param dirty: Tracked paths with uncommitted changes that count.
    :param known: Every release version tagged and reachable.
    :param plan: What the commits since the tag ask for.
    :param notes: Lines for ``--explain``.
    :param warnings: Problems that did not stop resolution.
    :param branch: Branch checked out, if any.
    """

    version: Version
    type: BuildType
    source: str
    tag: str | None = None
    base: Version | None = None
    distance: int = 0
    sha: str | None = None
    date: datetime | None = None
    dirty: list[str] = field(default_factory=list)
    known: list[Version] = field(default_factory=list)
    plan: BumpPlan = field(default_factory=lambda: BumpPlan(None, ()))
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    branch: str | None = None

    @property
    def short_sha(self) -> str | None:
        """
        Shorten the commit hash for the local part of a version.

        Python packaging tools read an all-digit local part as a number and drop
        its leading zeros, so a hash that would be shortened to such a value is
        lengthened until it holds a letter.

        :return: At least the first seven characters of the commit hash.
        """
        if not self.sha:
            return None
        length = _SHORT_SHA
        while (
            length < len(self.sha)
            and self.sha[:length].isdigit()
            and self.sha.startswith("0")
        ):
            length += 1
        return self.sha[:length]


def tag_name(template: str, version: Version) -> str:
    """
    Build a tag name from a template.

    :param template: Tag template containing ``{version}``.
    :param version: Version to name; spelled as SemVer (a post release keeps
        ``.postN``).
    :return: The tag name.
    """
    return template.replace("{version}", version.tag_spelling())


def match_tag(template: str, name: str) -> Version | None:
    """
    Read the version out of a tag name that follows a template.

    Both pre-release spellings are accepted, so ``v1.3.0-rc.1`` and ``v1.3.0rc1``
    give the same version.

    :param template: Tag template containing ``{version}``.
    :param name: Tag name to test.
    :return: The version, or ``None`` when the tag does not follow the template.
    """
    prefix, _, suffix = template.partition("{version}")
    if not name.startswith(prefix) or not name.endswith(suffix):
        return None
    body = name[len(prefix) : len(name) - len(suffix) if suffix else None]
    if not body or not body[0].isdigit():
        return None
    version = Version.try_parse(body)
    if version is None or version.dev is not None or version.local:
        return None
    return version


_VERSION_LIKE_RE = re.compile(r"\d+\.\d+\.\d+")


def release_tags(template: str, names: list[str]) -> dict[str, Version]:
    """
    Keep the tag names that are release tags for a template.

    :param template: Tag template containing ``{version}``.
    :param names: Tag names to filter.
    :return: Tag name to version.
    """
    found: dict[str, Version] = {}
    for name in names:
        version = match_tag(template, name)
        if version is not None:
            found[name] = version
    return found


def own_tag_folders(config: Config) -> list[Path]:
    """
    List the folders of packages that carry their own tags.

    Commits that only touch these folders belong to the package's releases, not
    to the repository's.

    :param config: The loaded configuration.
    :return: Absolute package folders.
    """
    return [
        (config.root / item.path).resolve()
        for item in config.packages.values()
        if item.tag
    ]


def _problem(message: str, warnings: list[str]) -> None:
    """Fail in CI, warn elsewhere."""
    if git.is_ci():
        raise EnvironmentProblemError(message)
    logger.warning(message)
    warnings.append(message)


def _shape(
    config: Config,
    resolved: Resolved,
    build_type: BuildType,
    base_is_release: bool,
) -> Version:
    """Turn the base into a development or nightly version."""
    base = resolved.base or Version.parse(config.fallback)
    rule = config.nightly if build_type == "nightly" else config.dev
    if not base_is_release:
        target = base.release
    elif base.pre is not None:
        target = _next_pre(base, resolved.known)
    elif rule == "next":
        try:
            target = next_version(base, resolved.known, resolved.plan, fallback=base)
        except NothingToReleaseError:
            target = base.bump("patch")
    else:
        target = base.bump(rule)
    stamp = resolved.date if config.date == "commit" and resolved.date else None
    stamp = stamp or git.build_time()
    number = int(stamp.strftime("%Y%m%d"))
    template = config.formats.get(build_type)  # type: ignore[call-overload]
    if template:
        return _formatted(
            template,
            resolved,
            target=target,
            base=base,
            number=number,
            build_type=build_type,
        )
    if build_type == "nightly":
        return target.with_parts(pre=target.pre, dev=number, nightly=True)
    local: str | None = None
    if config.local:
        parts = [
            part
            for part in (resolved.short_sha, "dirty" if resolved.dirty else None)
            if part
        ]
        local = ".".join(parts) or None
    return target.with_parts(pre=target.pre, dev=number, local=local)


def _formatted(  # noqa: PLR0913
    template: str,
    resolved: Resolved,
    *,
    target: Version,
    base: Version,
    number: int,
    build_type: str,
) -> Version:
    """Render a ``formats`` template and read it back as a version."""
    fields = {
        "next": target.pep440(),
        "base": base.pep440(),
        "distance": resolved.distance,
        "date": number,
        "sha": resolved.short_sha or "0",
        "branch": re.sub(r"[^0-9A-Za-z]+", ".", resolved.branch or "detached").strip(
            "."
        ),
    }
    try:
        text = template.format(**fields)
    except (KeyError, IndexError, ValueError) as error:
        raise ConfigError(
            f"formats.{build_type} {template!r} has an unknown placeholder: {error}. "
            f"Use {', '.join('{' + name + '}' for name in fields)}."
        ) from error
    version = Version.try_parse(text)
    if version is None:
        raise ConfigError(
            f"formats.{build_type} gave {text!r}, which is not a PEP 440 version."
        )
    if build_type == "nightly" and version.dev is not None:
        version = version.with_parts(
            pre=version.pre,
            dev=version.dev,
            local=version.local,
            nightly=True,
            post=version.post,
        )
    return version


def _next_pre(base: Version, known: list[Version]) -> Version:
    """
    Return the pre-release after a pre-release base, for builds past its tag.

    A build after ``v1.3.0-rc.1`` must sort above it, so it is based on ``rc2``
    (or the next free number when later candidates are already tagged).

    :param base: The pre-release the build follows.
    :param known: Every tagged version.
    :return: The next pre-release of the same kind.
    """
    kind, number = base.pre or ("rc", 0)
    taken = [
        version.pre[1]
        for version in known
        if version.pre is not None
        and version.pre[0] == kind
        and version.release == base.release
    ]
    return base.release.with_parts(pre=(kind, max([number, *taken]) + 1))


def resolve(
    config: Config,
    *,
    pin: str | None = None,
    build_type: BuildType | None = None,
    tag_template: str | None = None,
    path_scope: str | None = None,
) -> Resolved:
    """
    Resolve the version of the current checkout.

    :param config: The loaded configuration.
    :param pin: A version to use as is, skipping git.
    :param build_type: Force ``release``, ``dev`` or ``nightly``; by default
        ``GITVERSIONED__TYPE``, else a clean tagged ``HEAD`` is a release and
        anything else a development build.
    :param tag_template: Tag template to use instead of the configured one, for a
        package with its own tags.
    :param path_scope: Folder, relative to the project root, whose commits count;
        used for a package with its own tags.
    :return: The resolved version and how it was reached.
    :raises EnvironmentProblemError: In CI, when no trustworthy version exists.
    """
    build_type = build_type or env_build_type()
    template = tag_template or config.tag
    source, note = "pin", ""
    pinned = pin
    if pinned is None and config.version != "auto":
        found = _source_version(config)
        if found is not None:
            pinned, source, note = found
    if pinned:
        version = Version.parse(pinned)
        kind: BuildType = "release"
        if version.dev is not None:
            kind = "nightly" if version.nightly else "dev"
        return Resolved(
            version=version,
            type=kind,
            source=source,
            notes=[note or f"pinned to {pinned}"],
        )

    warnings: list[str] = []
    fallback = Version.parse(config.fallback)
    repo = git.Repo.open(config.root)
    if repo is not None and repo.head() is None:
        repo = None
    if (
        repo is not None
        and (config.root / "PKG-INFO").is_file()
        and not repo.tracks(config.root)
    ):
        # An unpacked source distribution inside some other repository: the
        # surrounding history says nothing about this package.
        repo = None
    if repo is None:
        resolved = _resolve_without_git(
            config, template, build_type, fallback, warnings
        )
    else:
        resolved = _resolve_with_git(
            config,
            repo=repo,
            template=template,
            build_type=build_type,
            path_scope=path_scope,
            fallback=fallback,
            warnings=warnings,
        )
    logger.info(
        "version {} ({}, from {}); tag {}, {} commit{} since{}",
        resolved.version.pep440(),
        resolved.type,
        resolved.source,
        resolved.tag or "none",
        resolved.distance,
        "" if resolved.distance == 1 else "s",
        f", dirty: {', '.join(resolved.dirty)}" if resolved.dirty else "",
    )
    return resolved


_SOURCE_VERSION_RE = re.compile(
    r"(?<![\d.])\d+\.\d+\.\d+(?:[-.]?(?:rc|alpha|beta|a|b)[-.]?\d+)?(?:\.post\d+)?"
)


def _source_version(config: Config) -> tuple[str, str, str] | None:
    """
    Read the version from the ``version`` setting's source.

    :return: The version text, the source name and a note, or ``None`` when a
        ``branch`` or ``commit`` source names no version, so tags decide.
    :raises ConfigError: If a file or function source gives no version.
    """
    setting = config.version
    if Version.try_parse(setting) is not None:
        return setting, "pin", f"pinned to {setting}"
    if setting in ("branch", "commit"):
        repo = git.Repo.open(config.root)
        if setting == "branch":
            text = (
                (repo.branch() if repo else None)
                or os.environ.get("GITHUB_HEAD_REF", "")
                or os.environ.get("GITHUB_REF_NAME", "")
            )
        else:
            text = (
                repo.git("log", "-1", "--format=%s", check=False) if repo else ""
            ) or ""
        found = _SOURCE_VERSION_RE.search(text or "")
        if found is None:
            logger.info(f"the {setting} {text!r} names no version; using tags")
            return None
        return found[0], setting, f"version {found[0]} from the {setting} {text!r}"
    if setting.startswith("file:"):
        name = setting[len("file:") :]
        path = config.root / name
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as error:
            raise ConfigError(f"cannot read version file {name}: {error}") from error
        found = _SOURCE_VERSION_RE.search(content)
        if found is None:
            raise ConfigError(f"version file {name} holds no X.Y.Z version.")
        return found[0], "file", f"version {found[0]} from {name}"
    return _function_version(config, setting[len("python:") :])


def _function_version(config: Config, spec: str) -> tuple[str, str, str]:
    """Call a ``module:function`` from the project and read its version."""
    import importlib  # noqa: PLC0415
    import sys  # noqa: PLC0415

    module_name, _, function_name = spec.partition(":")
    root = str(config.root.resolve())
    added = root not in sys.path
    if added:
        sys.path.insert(0, root)
    try:
        # The project's own config names this module, the way setuptools' attr: does.
        # nosemgrep: non-literal-import
        module = importlib.import_module(module_name)
        value = getattr(module, function_name)()
    except Exception as error:  # noqa: BLE001
        raise ConfigError(f"version function {spec} failed: {error}") from error
    finally:
        if added:
            sys.path.remove(root)
    text = str(value).strip()
    if Version.try_parse(text) is None:
        raise ConfigError(f"version function {spec} returned {text!r}, not a version.")
    return text, "function", f"version {text} from {spec}()"


def _resolve_with_git(  # noqa: PLR0913
    config: Config,
    *,
    repo: git.Repo,
    template: str,
    build_type: BuildType | None,
    path_scope: str | None,
    fallback: Version,
    warnings: list[str],
) -> Resolved:
    """Resolve from the release tags reachable from ``HEAD``."""
    merged = repo.tags_merged()
    tags = release_tags(template, list(merged))
    resolved = Resolved(
        version=fallback,
        type="dev",
        source="tag" if tags else "fallback",
        sha=repo.head(),
        date=repo.head_date(),
        known=list(release_tags(template, repo.all_tags()).values()),
        warnings=warnings,
        branch=repo.branch(),
    )
    scope = (config.root / path_scope) if path_scope else None
    excluded = [] if scope else own_tag_folders(config)
    since: str | None = None
    if tags:
        best = max(tags, key=lambda name: tags[name].sort_key())
        resolved.tag = best
        resolved.base = tags[best]
        since = merged[best]
        resolved.notes.append(f"base {tags[best].pep440()} from tag {best}")
    elif repo.is_shallow():
        _problem(
            "shallow clone with no release tags reachable, so the version cannot "
            "be trusted. Fetch full history (fetch-depth: 0 on actions/checkout).",
            warnings,
        )
    else:
        message = (
            f"no release tags match {template!r}; using fallback {fallback.pep440()}."
        )
        logger.info(message)
        resolved.notes.append(message)
        # Version-like tags in another spelling are a misconfigured template, not
        # a new repository: say so rather than silently using the fallback.
        lookalikes = sorted(name for name in merged if _VERSION_LIKE_RE.search(name))
        if lookalikes:
            many = len(lookalikes) > 1
            noun = "tags" if many else "tag"
            verb = (
                "look like versions but do" if many else "looks like a version but does"
            )
            warning = (
                f"{noun} {', '.join(lookalikes[:3])} {verb}"
                f" not match the tag template {template!r}; using fallback "
                f"{fallback.pep440()}. Set `tag` to match them."
            )
            logger.warning(warning)
            warnings.append(warning)
    commits = repo.commits(since, path=scope, exclude=excluded)
    resolved.distance = len(commits)
    try:
        changes = change_commits(config, path_scope)
    except ConfigError as error:
        # A broken change file fails `check` and `release`, never a build.
        logger.warning("ignoring change files: {}", error)
        changes = []
    resolved.plan = plan_bump(commits + changes, config.levels, shift=config.zero_shift)

    resolved.dirty = _counted_dirty(config, repo)
    at_tag = resolved.base is not None and resolved.distance == 0 and not resolved.dirty
    kind: BuildType = build_type or ("release" if at_tag else "dev")
    resolved.type = kind
    if kind != "release":
        resolved.version = _shape(config, resolved, kind, base_is_release=bool(tags))
    elif at_tag and resolved.base is not None:
        resolved.version = resolved.base
    else:
        try:
            resolved.version = next_version(
                resolved.base, resolved.known, resolved.plan, fallback=fallback
            )
        except NothingToReleaseError:
            resolved.version = (resolved.base or fallback).release
    return resolved


def _counted_dirty(config: Config, repo: git.Repo) -> list[str]:
    """Return the dirty paths that are not just gitversioned's own stamping."""
    dirty = repo.dirty_paths()
    if not dirty:
        return []
    from gitversioned.targets import all_targets, only_version_changed  # noqa: PLC0415

    try:
        known = all_targets(config)
    except ConfigError:
        known = []
    return [
        path
        for path in dirty
        if not only_version_changed(config, repo, path, known=known)
    ]


def _resolve_without_git(
    config: Config,
    template: str,
    build_type: BuildType | None,
    fallback: Version,
    warnings: list[str],
) -> Resolved:
    """Resolve from the archive file, sdist metadata or the fallback."""
    archive = git.read_archive(config.root)
    if archive is not None:
        tags = release_tags(template, list(archive.tags))
        resolved = Resolved(
            version=fallback,
            type="dev",
            source="archive",
            sha=archive.sha,
            date=archive.date,
            distance=archive.distance,
            warnings=warnings,
        )
        if tags:
            best = max(tags, key=lambda name: tags[name].sort_key())
            resolved.tag = best
            resolved.base = tags[best]
            resolved.known = list(tags.values())
            resolved.notes.append(
                f"base {tags[best].pep440()} from {git.ARCHIVE_FILE} ({best})"
            )
        at_tag = resolved.base is not None and resolved.distance == 0
        kind = build_type or ("release" if at_tag else "dev")
        resolved.type = kind
        if kind == "release" and resolved.base is not None:
            resolved.version = resolved.base
        else:
            if kind == "release":
                kind = resolved.type = "dev"
            resolved.version = _shape(
                config, resolved, kind, base_is_release=bool(tags)
            )
        return resolved

    sdist = git.read_sdist_version(config.root)
    if sdist and Version.try_parse(sdist) is not None:
        version = Version.parse(sdist)
        kind = (
            "release"
            if version.dev is None
            else ("nightly" if version.nightly else "dev")
        )
        return Resolved(
            version=version,
            type=kind,
            source="sdist",
            notes=[f"version {sdist} from PKG-INFO"],
            warnings=warnings,
        )

    _problem(
        "no git repository, archive file or package metadata found, so the "
        f"version cannot be resolved; using fallback {fallback.pep440()}. "
        "Set GITVERSIONED__VERSION to pin one.",
        warnings,
    )
    resolved = Resolved(
        version=fallback, type="dev", source="fallback", warnings=warnings
    )
    resolved.version = _shape(config, resolved, "dev", base_is_release=False)
    return resolved
