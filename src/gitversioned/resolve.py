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

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from gitversioned import git
from gitversioned.commits import BumpPlan, next_version, plan_bump
from gitversioned.config import Config
from gitversioned.errors import EnvironmentProblemError, NothingToReleaseError
from gitversioned.logging import logger
from gitversioned.model import Version

__all__ = [
    "BuildType",
    "Resolved",
    "match_tag",
    "own_tag_folders",
    "release_tags",
    "resolve",
    "tag_name",
]

BuildType = Literal["release", "dev", "nightly"]


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
    :param version: Version to name; spelled as SemVer.
    :return: The tag name.
    """
    return template.replace("{version}", version.semver())


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
    if not base_is_release or base.pre is not None:
        target = base.release
    elif rule == "next":
        try:
            target = next_version(base, resolved.known, resolved.plan, fallback=base)
        except NothingToReleaseError:
            target = base.bump("patch")
    else:
        target = base.bump(rule)
    stamp = resolved.date if config.date == "commit" and resolved.date else None
    stamp = stamp or datetime.now(tz=timezone.utc)
    number = int(stamp.strftime("%Y%m%d"))
    if build_type == "nightly":
        return target.with_parts(dev=number, nightly=True)
    local: str | None = None
    if config.local:
        parts = [
            part
            for part in (resolved.short_sha, "dirty" if resolved.dirty else None)
            if part
        ]
        local = ".".join(parts) or None
    return target.with_parts(dev=number, local=local)


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
    :param build_type: Force ``release``, ``dev`` or ``nightly``; by default a
        clean tagged ``HEAD`` is a release and anything else a development build.
    :param tag_template: Tag template to use instead of the configured one, for a
        package with its own tags.
    :param path_scope: Folder, relative to the project root, whose commits count;
        used for a package with its own tags.
    :return: The resolved version and how it was reached.
    :raises EnvironmentProblemError: In CI, when no trustworthy version exists.
    """
    template = tag_template or config.tag
    pinned = pin or (config.version if config.version != "auto" else None)
    if pinned:
        version = Version.parse(pinned)
        kind: BuildType = "release"
        if version.dev is not None:
            kind = "nightly" if version.nightly else "dev"
        return Resolved(
            version=version, type=kind, source="pin", notes=[f"pinned to {pinned}"]
        )

    warnings: list[str] = []
    fallback = Version.parse(config.fallback)
    repo = git.Repo.open(config.root)
    if repo is not None and repo.head() is None:
        repo = None
    if repo is None:
        return _resolve_without_git(config, template, build_type, fallback, warnings)

    return _resolve_with_git(
        config,
        repo=repo,
        template=template,
        build_type=build_type,
        path_scope=path_scope,
        fallback=fallback,
        warnings=warnings,
    )


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
    commits = repo.commits(since, path=scope, exclude=excluded)
    resolved.distance = len(commits)
    resolved.plan = plan_bump(commits)

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
    from gitversioned.targets import only_version_changed  # noqa: PLC0415

    return [path for path in dirty if not only_version_changed(config, repo, path)]


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
