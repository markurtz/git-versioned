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
Conventional Commit parsing and the rules that choose the next version.

The rules are fixed: a breaking change raises major, ``feat`` raises minor, any
other change raises patch, and ``chore``, ``ci``, ``test`` and ``release`` commits
alone do not justify a release. Below 1.0 every level shifts down by one.

Example:
::
    from gitversioned.commits import parse_subject, level_of

    parsed = parse_subject("feat(cli)!: drop the old commands (#12)")
    assert parsed is not None and parsed.breaking and parsed.pr == 12
    assert level_of(parsed) == "major"
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from gitversioned.errors import ConfigError, NothingToReleaseError
from gitversioned.git import Commit
from gitversioned.model import Level, PreKind, Version

__all__ = [
    "NO_RELEASE_TYPES",
    "BumpPlan",
    "ParsedCommit",
    "env_bump",
    "level_of",
    "next_version",
    "parse_subject",
    "plan_bump",
]

NO_RELEASE_TYPES: frozenset[str] = frozenset({"chore", "ci", "test", "release"})
_LEVEL_RANK: dict[str, int] = {"patch": 1, "minor": 2, "major": 3}

_SUBJECT_RE = re.compile(
    r"^(?P<type>[A-Za-z][A-Za-z0-9-]*)"
    r"(?:\((?P<scope>[^()\r\n]+)\))?"
    r"(?P<breaking>!)?: (?P<subject>\S.*)$"
)
_PR_RE = re.compile(r"\s*\(#(?P<pr>\d+)\)\s*$")
_BREAKING_RE = re.compile(r"^BREAKING[ -]CHANGE: ", re.MULTILINE)
_MERGE_RE = re.compile(r"^Merge (branch|pull request|remote-tracking branch|tag) ")


@dataclass(frozen=True)
class ParsedCommit:
    """
    A commit subject split into its Conventional Commit parts.

    :param type: Commit type in lower case, such as ``feat``.
    :param scope: Scope in parentheses, when present.
    :param breaking: True for a ``!`` marker or a ``BREAKING CHANGE:`` footer.
    :param subject: Description after the colon, without the pull request suffix.
    :param pr: Pull request number from a ``(#N)`` suffix, when present.
    :param sha: Commit hash, when the subject came from a commit.
    """

    type: str
    scope: str | None
    breaking: bool
    subject: str
    pr: int | None = None
    sha: str | None = None


@dataclass(frozen=True)
class BumpPlan:
    """
    The level a set of commits asks for and the reason per commit.

    :param level: The highest level found, or ``None`` when nothing is releasable.
    :param reasons: Each commit with the level it contributes.
    """

    level: Level | None
    reasons: tuple[tuple[Level | None, Commit], ...]


def parse_subject(
    subject: str, body: str = "", sha: str | None = None
) -> ParsedCommit | None:
    """
    Parse a commit subject or pull request title.

    :param subject: First line of the message.
    :param body: Rest of the message, searched for a breaking-change footer.
    :param sha: Commit hash to carry along.
    :return: The parsed parts, or ``None`` when the subject is not conventional.
    """
    match = _SUBJECT_RE.match(subject.strip())
    if match is None:
        return None
    text = match["subject"]
    pr: int | None = None
    pr_match = _PR_RE.search(text)
    if pr_match:
        pr = int(pr_match["pr"])
        text = text[: pr_match.start()]
    return ParsedCommit(
        type=match["type"].lower(),
        scope=match["scope"].strip() if match["scope"] else None,
        breaking=bool(match["breaking"]) or bool(_BREAKING_RE.search(body)),
        subject=text.strip(),
        pr=pr,
        sha=sha,
    )


def level_of(parsed: ParsedCommit | None, subject: str = "") -> Level | None:
    """
    Decide the level one commit asks for.

    :param parsed: The parsed commit, or ``None`` for an unconventional subject.
    :param subject: The raw subject, used to skip merge commits.
    :return: ``major``, ``minor``, ``patch`` or ``None`` for no release.
    """
    if parsed is None:
        return None if _MERGE_RE.match(subject) else "patch"
    if parsed.breaking:
        return "major"
    if parsed.type == "feat":
        return "minor"
    if parsed.type in NO_RELEASE_TYPES:
        return None
    return "patch"


def plan_bump(commits: list[Commit]) -> BumpPlan:
    """
    Find the highest level a list of commits asks for.

    :param commits: Commits since the last release.
    :return: The level and the per-commit reasons.
    """
    reasons: list[tuple[Level | None, Commit]] = []
    best: Level | None = None
    for commit in commits:
        level = level_of(parse_subject(commit.subject, commit.body), commit.subject)
        reasons.append((level, commit))
        if level is not None and (
            best is None or _LEVEL_RANK[level] > _LEVEL_RANK[best]
        ):
            best = level
    return BumpPlan(level=best, reasons=tuple(reasons))


def _shift(level: Level, current: Version) -> Level:
    """Shift a commit-derived level down by one for a version below 1.0."""
    if current.major > 0:
        return level
    return {"major": "minor", "minor": "patch", "patch": "patch"}[level]  # type: ignore[return-value]


def env_bump() -> str | None:
    """
    :return: The ``GITVERSIONED__BUMP`` override, a level or a version, if set.
    """
    return os.environ.get("GITVERSIONED__BUMP", "").strip() or None


def next_version(
    current: Version | None,
    known: list[Version],
    plan: BumpPlan,
    *,
    fallback: Version,
    explicit: str | None = None,
    bump: str | None = None,
    pre: PreKind | None = None,
) -> Version:
    """
    Choose the next release version.

    Overrides win in this order: an explicit version, an explicit level, then the
    commits. A pre-release numbers itself after the existing tags of its kind.

    :param current: The latest released version, or ``None`` before the first tag.
    :param known: Every version already tagged, used to number pre-releases.
    :param plan: What the commits ask for.
    :param fallback: First version of a repository with no tags.
    :param explicit: A version to release exactly, or a level name.
    :param bump: A level that replaces the one chosen from commits.
    :param pre: Make the result a pre-release of this kind.
    :return: The version to release.
    :raises NothingToReleaseError: If no override is given and no commit is
        releasable.
    :raises ConfigError: If an override is neither a level nor a version.
    """
    if explicit and explicit not in _LEVEL_RANK:
        target = Version.parse(explicit)
        if pre is None:
            return target
        target = target.release
    else:
        level_name = explicit or bump
        if level_name is not None and level_name not in _LEVEL_RANK:
            raise ConfigError(
                f"not a bump level: {level_name!r}. Use major, minor or patch."
            )
        if current is None:
            target = fallback.release
        elif current.pre is not None and level_name is None:
            target = current.release
        elif level_name is not None:
            target = current.release.bump(level_name)  # type: ignore[arg-type]
        elif plan.level is None:
            raise NothingToReleaseError("Nothing to release: no releasable commits.")
        else:
            target = current.bump(_shift(plan.level, current))
    if pre is None:
        return target
    numbers = [
        version.pre[1]
        for version in known
        if version.pre is not None
        and version.dev is None
        and version.pre[0] == pre
        and version.release == target
    ]
    return target.with_parts(pre=(pre, max(numbers, default=0) + 1))
