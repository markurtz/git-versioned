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
Changelog sections: entries by kind then scope, rendered and inserted in place.

The layout is fixed. Kinds follow Keep a Changelog; maintenance commits are
hidden unless they are breaking; a ``## Changelog`` block in a pull request body
replaces the entry derived from its title.

Example:
::
    from gitversioned.changelog import entries_from_commits, render_section
    from gitversioned.git import Commit
    from gitversioned.model import Version

    entries = entries_from_commits([Commit("abc", "feat(cli): add explain (#41)")])
    print(render_section(Version.parse("1.3.0"), entries, day="2026-11-25"))
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from gitversioned.commits import NO_RELEASE_TYPES, parse_subject
from gitversioned.git import Commit
from gitversioned.github import PullRequest
from gitversioned.model import Version

__all__ = [
    "KINDS",
    "Entry",
    "carried_entries",
    "entries_from_commits",
    "insert_section",
    "read_section",
    "render_section",
]

KINDS: tuple[str, ...] = (
    "Added",
    "Changed",
    "Deprecated",
    "Removed",
    "Fixed",
    "Security",
)
_TYPE_KIND: dict[str, str] = {
    "feat": "Added",
    "fix": "Fixed",
    "deprecate": "Deprecated",
    "security": "Security",
    "remove": "Removed",
}
_HEADER = (
    "# Changelog\n\n"
    "All notable changes to this project are documented in this file.\n"
    "The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) "
    "and the project follows [Semantic Versioning](https://semver.org/).\n\n"
)
_SECTION_RE = re.compile(r"(?m)^## \[?(?P<version>[^\]\s]+)\]?.*$")
_UNRELEASED = "unreleased"
_BULLET_RE = re.compile(
    r"^\s*[-*]\s+(?:\*\*(?P<scope>[^*:]+)\*\*:\s+)?(?P<breaking>\*\*Breaking:\*\*\s+)?"
    r"(?P<text>.+?)(?:\s+\((?:\[#(?P<link>\d+)\]\([^)]*\)|#(?P<pr>\d+))\))?\s*$"
)
_BLOCK_RE = re.compile(r"(?ims)^#{2,3}\s+changelog\s*$\n(?P<body>.*?)(?=^#{1,2}\s|\Z)")


@dataclass(frozen=True)
class Entry:
    """
    One line of a changelog section.

    :param kind: Keep a Changelog heading the entry goes under.
    :param scope: Scope shown in bold, when the change has one.
    :param text: What changed.
    :param pr: Pull request number, when known.
    :param breaking: True for a breaking change.
    """

    kind: str
    scope: str | None
    text: str
    pr: int | None = None
    breaking: bool = False


def _from_block(
    body: str, default_kind: str, scope: str | None, pr: int | None
) -> list[Entry]:
    """Read the entries of a ``## Changelog`` block in a pull request body."""
    match = _BLOCK_RE.search(body.replace("\r\n", "\n"))
    if match is None:
        return []
    entries: list[Entry] = []
    kind = default_kind
    for line in match["body"].splitlines():
        heading = re.match(r"^#{3,4}\s+(?P<kind>\w+)\s*$", line.strip())
        if heading:
            name = heading["kind"].capitalize()
            kind = name if name in KINDS else kind
            continue
        bullet = re.match(r"^\s*[-*]\s+(?P<text>.+)$", line)
        if bullet:
            entries.append(Entry(kind, scope, bullet["text"].strip(), pr))
    return entries


def entries_from_commits(
    commits: list[Commit], pull_requests: dict[int, PullRequest] | None = None
) -> list[Entry]:
    """
    Turn commits into changelog entries.

    A pull request title replaces its squash commit subject, and a
    ``## Changelog`` block in the pull request body replaces both.

    :param commits: Commits since the previous release, newest first.
    :param pull_requests: Pull requests by number, when GitHub was reachable.
    :return: Entries in commit order, oldest first, with hidden types left out.
    """
    known = pull_requests or {}
    entries: list[Entry] = []
    for commit in reversed(commits):
        parsed = parse_subject(commit.subject, commit.body, commit.sha)
        number = parsed.pr if parsed else None
        if number is None:
            suffix = re.search(r"\(#(\d+)\)\s*$", commit.subject)
            number = int(suffix.group(1)) if suffix else None
        request = known.get(number) if number is not None else None
        if request is not None:
            retitled = parse_subject(request.title, request.body)
            if retitled is not None:
                parsed = retitled
        if parsed is None:
            continue
        if parsed.type in NO_RELEASE_TYPES and not parsed.breaking:
            continue
        kind = _TYPE_KIND.get(parsed.type, "Changed")
        if request is not None:
            block = _from_block(request.body, kind, parsed.scope, number)
            if block:
                entries.extend(block)
                continue
        entries.append(
            Entry(kind, parsed.scope, parsed.subject, number, parsed.breaking)
        )
    return entries


def render_section(
    version: Version,
    entries: list[Entry],
    *,
    day: str,
    repo_url: str | None = None,
) -> str:
    """
    Render one release section.

    :param version: Version being released.
    :param entries: Entries to list.
    :param day: Release date as ``YYYY-MM-DD``.
    :param repo_url: Repository web address, used to link pull requests.
    :return: Markdown ending in a newline.
    """
    lines = [f"## [{version.semver()}] - {day}", ""]
    for kind in KINDS:
        chosen = [entry for entry in entries if entry.kind == kind]
        if not chosen:
            continue
        chosen.sort(
            key=lambda entry: (
                not entry.breaking,
                entry.scope is None,
                entry.scope or "",
            )
        )
        lines += [f"### {kind}", ""]
        for entry in chosen:
            text = entry.text
            if entry.breaking:
                text = f"**Breaking:** {text}"
            if entry.scope:
                text = f"**{entry.scope}**: {text}"
            if entry.pr is not None:
                link = (
                    f"[#{entry.pr}]({repo_url}/pull/{entry.pr})"
                    if repo_url
                    else f"#{entry.pr}"
                )
                text += f" ({link})"
            lines.append(f"- {text}")
        lines.append("")
    if not entries:
        lines += ["No notable changes.", ""]
    return "\n".join(lines)


def _sections(text: str) -> list[tuple[str, int, int]]:
    """List the release sections of a changelog with their spans."""
    matches = list(_SECTION_RE.finditer(text))
    sections: list[tuple[str, int, int]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match["version"], match.start(), end))
    return sections


def carried_entries(text: str, version: Version) -> list[Entry]:
    """
    Read the entries a new release section takes over from the changelog.

    Keep a Changelog collects upcoming changes under ``## [Unreleased]``; a
    release moves them into its own section. Sections of earlier pre-releases of
    the same release are folded in too, since :func:`insert_section` replaces them.
    Both nested layouts are read: ``### Added`` and ``### <scope>`` then
    ``#### Added``.

    :param text: Current changelog content.
    :param version: Version being released.
    :return: Entries in file order.
    """
    entries: list[Entry] = []
    for name, start, end in _sections(text):
        found = Version.try_parse(name)
        carried = name.lower() == _UNRELEASED or (
            found is not None
            and found.pre is not None
            and found.release == version.release
            and found != version
        )
        if carried:
            body = text[start:end].split("\n", 1)[1] if "\n" in text[start:end] else ""
            entries.extend(_parse_entries(body))
    return entries


def _parse_entries(body: str) -> list[Entry]:
    """Read the bullets of a rendered section back into entries."""
    entries: list[Entry] = []
    kind = "Changed"
    heading_scope: str | None = None
    for line in body.splitlines():
        heading = re.match(r"^#{3,4}\s+(?P<name>[\w-]+)\s*$", line.strip())
        if heading:
            name = heading["name"]
            if name.capitalize() in KINDS:
                kind = name.capitalize()
            else:
                heading_scope = name
            continue
        bullet = _BULLET_RE.match(line)
        if bullet:
            number = bullet["link"] or bullet["pr"]
            entries.append(
                Entry(
                    kind,
                    bullet["scope"] or heading_scope,
                    bullet["text"].strip(),
                    int(number) if number else None,
                    breaking=bool(bullet["breaking"]),
                )
            )
    return entries


def insert_section(text: str, version: Version, section: str) -> str:
    """
    Put a release section into a changelog, touching nothing else.

    A section for the same version is replaced, and pre-release sections of the
    same release are removed, so a release pull request can be rebuilt freely.

    :param text: Current changelog content; empty for a new file.
    :param version: Version of the section.
    :param section: Rendered section.
    :return: The new changelog content.
    """
    if not text.strip():
        text = _HEADER
    for name, start, end in reversed(_sections(text)):
        if name.lower() == _UNRELEASED:
            heading = text[start:end].split("\n", 1)[0]
            text = text[:start] + heading + "\n\n" + text[end:]
        found = Version.try_parse(name)
        if found is None:
            continue
        if found == version or (
            found.pre is not None and found.release == version.release
        ):
            text = text[:start] + text[end:]
    position = len(text)
    for name, start, _end in _sections(text):
        if Version.try_parse(name) is not None:
            position = start
            break
    before = text[:position]
    if before and not before.endswith("\n\n"):
        before = before.rstrip("\n") + "\n\n"
    after = text[position:]
    block = section.rstrip("\n") + "\n"
    return before + block + ("\n" + after if after else "")


def read_section(path: Path, version: Version) -> str | None:
    """
    Read the section of one version back out of a changelog file.

    :param path: Changelog file.
    :param version: Version to find.
    :return: The section text, or ``None``.
    """
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    for name, start, end in _sections(text):
        if Version.try_parse(name) == version:
            return text[start:end].strip() + "\n"
    return None
