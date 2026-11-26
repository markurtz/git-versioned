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
Changelog sections: entries by kind or by scope, rendered and inserted in place.

Kinds follow Keep a Changelog, and ``changelog_sections`` renames them per
commit type or hides a type. The default ``kind`` layout lists kinds with the
scope in bold; the ``scope`` layout gives each scope a heading with its kinds
below. Breaking changes with a ``BREAKING CHANGE:`` footer are also listed
under Migrations. Maintenance commits are hidden unless they are breaking; a
``## Changelog`` block in a pull request body replaces the entry derived from
its title. ``changelog_template`` replaces the whole section layout.

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
import string
from dataclasses import dataclass, field
from pathlib import Path

from gitversioned.commits import NO_RELEASE_TYPES, ParsedCommit, parse_subject
from gitversioned.errors import ConfigError
from gitversioned.git import Commit
from gitversioned.github import PullRequest
from gitversioned.model import Version

__all__ = [
    "KINDS",
    "MIGRATIONS",
    "Entry",
    "Style",
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
MIGRATIONS = "Migrations"
_FOOTER_RE = re.compile(
    r"^BREAKING[ -]CHANGE:\s*(?P<text>.+?)(?=\n\s*\n|\n[\w-]+: |\Z)", re.M | re.S
)
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


@dataclass(frozen=True)
class Style:
    """
    How sections are laid out, from the changelog settings.

    :param layout: ``kind`` or ``scope``.
    :param sections: Heading per commit type; ``False`` hides the type.
    :param template: A ``string.Template`` for the whole section, or ``None``.
    :param pr_path: Path segment of a pull request's web address on the forge.
    """

    layout: str = "kind"
    sections: dict[str, str | bool] = field(default_factory=dict)
    template: str | None = None
    pr_path: str = "pull"

    @property
    def kinds(self) -> tuple[str, ...]:
        """
        :return: Every heading entries go under, in order.
        """
        extra = [
            name
            for name in self.sections.values()
            if isinstance(name, str) and name not in KINDS
        ]
        return (*KINDS, *dict.fromkeys(extra))

    def kind_of(self, commit_type: str) -> str | None:
        """
        :return: The heading for a commit type, or ``None`` when it is hidden.
        """
        chosen = self.sections.get(commit_type)
        if chosen is False:
            return None
        if isinstance(chosen, str):
            return chosen
        if commit_type in NO_RELEASE_TYPES:
            return None
        return _TYPE_KIND.get(commit_type, "Changed")

    @classmethod
    def from_config(cls, config: object) -> Style:
        """
        :return: The style a configuration asks for.
        :raises ConfigError: If the template file cannot be read.
        """
        template = getattr(config, "changelog_template", None)
        text = None
        if template:
            path = getattr(config, "root", Path.cwd()) / template
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as error:
                raise ConfigError(
                    f"cannot read changelog_template {template}: {error}"
                ) from error
        return cls(
            layout=getattr(config, "changelog_layout", "kind"),
            sections=dict(getattr(config, "changelog_sections", {}) or {}),
            template=text,
        )


def _from_block(
    body: str,
    default_kind: str,
    scope: str | None,
    pr: int | None,
    kinds: tuple[str, ...] = KINDS,
) -> list[Entry]:
    """Read the entries of a ``## Changelog`` block in a pull request body."""
    match = _BLOCK_RE.search(body.replace("\r\n", "\n"))
    if match is None:
        return []
    entries: list[Entry] = []
    kind = default_kind
    for line in match["body"].splitlines():
        heading = re.match(r"^#{3,4}\s+(?P<kind>\w[\w ]*?)\s*$", line.strip())
        if heading:
            name = _known_kind(heading["kind"], kinds)
            kind = name or kind
            continue
        bullet = re.match(r"^\s*[-*]\s+(?P<text>.+)$", line)
        if bullet:
            entries.append(Entry(kind, scope, bullet["text"].strip(), pr))
    return entries


def _known_kind(name: str, kinds: tuple[str, ...]) -> str | None:
    """Match a heading to a known kind, ignoring case."""
    return next(
        (kind for kind in (*kinds, MIGRATIONS) if kind.lower() == name.lower()), None
    )


def _migration(body: str) -> str | None:
    """Read the text of a ``BREAKING CHANGE:`` footer."""
    found = _FOOTER_RE.search(body.replace("\r\n", "\n"))
    return " ".join(found["text"].split()) if found else None


def _lookup(
    commit: Commit, known: dict[int, PullRequest]
) -> tuple[ParsedCommit | None, int | None, PullRequest | None]:
    """Parse a commit, preferring its pull request's title when there is one."""
    parsed = parse_subject(commit.subject, commit.body, commit.sha)
    number = parsed.pr if parsed else None
    if number is None:
        suffix = re.search(r"\([#!](\d+)\)\s*$", commit.subject)
        number = int(suffix.group(1)) if suffix else None
    request = known.get(number) if number is not None else None
    if request is not None:
        retitled = parse_subject(request.title, request.body)
        if retitled is not None:
            parsed = retitled
    return parsed, number, request


def _kind_for(style: Style, parsed: ParsedCommit) -> str | None:
    """The heading of a parsed commit; hidden types still show when breaking."""
    kind = style.kind_of(parsed.type)
    if kind is None and parsed.breaking:
        return _TYPE_KIND.get(parsed.type, "Changed")
    return kind


def entries_from_commits(
    commits: list[Commit],
    pull_requests: dict[int, PullRequest] | None = None,
    style: Style | None = None,
) -> list[Entry]:
    """
    Turn commits into changelog entries.

    A pull request title replaces its squash commit subject, and a
    ``## Changelog`` block in the pull request body replaces both.

    :param commits: Commits since the previous release, newest first.
    :param pull_requests: Pull requests by number, when the forge was reachable.
    :param style: Section headings per type; the defaults when ``None``.
    :return: Entries in commit order, oldest first, with hidden types left out.
    """
    style = style or Style()
    known = pull_requests or {}
    entries: list[Entry] = []
    for commit in reversed(commits):
        parsed, number, request = _lookup(commit, known)
        kind = _kind_for(style, parsed) if parsed else None
        if parsed is None or kind is None:
            continue
        migration = _migration(request.body if request else commit.body)
        if migration:
            entries.append(Entry(MIGRATIONS, parsed.scope, migration, number))
        if request is not None:
            block = _from_block(request.body, kind, parsed.scope, number, style.kinds)
            if block:
                entries.extend(block)
                continue
        entries.append(
            Entry(kind, parsed.scope, parsed.subject, number, parsed.breaking)
        )
    return entries


_Links = tuple[str | None, str]


def _bullet(entry: Entry, links: _Links, *, scope: bool = True) -> str:
    """Render one entry; ``links`` is the pull request address base and sign."""
    text = entry.text
    if entry.breaking:
        text = f"**Breaking:** {text}"
    if scope and entry.scope:
        text = f"**{entry.scope}**: {text}"
    if entry.pr is not None:
        base, sign = links
        link = f"[{sign}{entry.pr}]({base}/{entry.pr})" if base else f"{sign}{entry.pr}"
        text += f" ({link})"
    return f"- {text}"


def _by_kind(
    entries: list[Entry],
    kinds: tuple[str, ...],
    level: str,
    links: _Links,
    *,
    scope: bool,
) -> list[str]:
    """Render entries grouped under kind headings."""
    lines: list[str] = []
    for kind in kinds:
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
        lines += [f"{level} {kind}", ""]
        lines += [_bullet(entry, links, scope=scope) for entry in chosen]
        lines.append("")
    return lines


def _body(entries: list[Entry], style: Style, links: _Links) -> list[str]:
    """Render the entries of a section, without the heading or migrations."""
    changes = [entry for entry in entries if entry.kind != MIGRATIONS]
    kinds = (
        *style.kinds,
        *dict.fromkeys(e.kind for e in changes if e.kind not in style.kinds),
    )
    if style.layout != "scope":
        return _by_kind(changes, kinds, "###", links, scope=True)
    lines: list[str] = []
    scopes = sorted({entry.scope for entry in changes if entry.scope})
    for name in [*scopes, None]:
        group = [entry for entry in changes if entry.scope == name]
        if group:
            lines += [f"### {name or 'General'}", ""]
            lines += _by_kind(group, kinds, "####", links, scope=False)
    return lines


def _migrations(entries: list[Entry], links: _Links) -> list[str]:
    """Render the Migrations list."""
    chosen = [entry for entry in entries if entry.kind == MIGRATIONS]
    if not chosen:
        return []
    return [f"### {MIGRATIONS}", "", *(_bullet(e, links) for e in chosen), ""]


def render_section(  # noqa: PLR0913
    version: Version,
    entries: list[Entry],
    *,
    day: str,
    repo_url: str | None = None,
    style: Style | None = None,
    tag: str | None = None,
    previous: str | None = None,
) -> str:
    """
    Render one release section.

    :param version: Version being released.
    :param entries: Entries to list.
    :param day: Release date as ``YYYY-MM-DD``.
    :param repo_url: Repository web address, used to link pull requests.
    :param style: Layout, headings and template; the defaults when ``None``.
    :param tag: Tag of the release, for a template's ``$tag``.
    :param previous: Tag of the previous release, for ``$previous`` and
        ``$compare``.
    :return: Markdown ending in a newline.
    """
    style = style or Style()
    sign = "!" if "merge_requests" in style.pr_path else "#"
    links = (f"{repo_url}/{style.pr_path}" if repo_url else None, sign)
    body = _body(entries, style, links)
    migrations = _migrations(entries, links)
    if style.template is not None:
        compare = (
            f"{repo_url}/{'-/' if style.pr_path.startswith('-/') else ''}"
            f"compare/{previous}...{tag}"
            if repo_url and previous and tag
            else ""
        )
        values = {
            "version": version.semver(),
            "pep440": version.pep440(),
            "tag": tag or "",
            "date": day,
            "previous": previous or "",
            "compare": compare,
            "entries": "\n".join(body).strip() or "No notable changes.",
            "migrations": "\n".join(migrations).strip(),
        }
        try:
            text = string.Template(style.template).substitute(values)
        except (KeyError, ValueError) as error:
            raise ConfigError(
                f"changelog_template uses an unknown placeholder {error}. "
                f"Placeholders: {', '.join('$' + key for key in values)}."
            ) from error
        if not text.lstrip().startswith(f"## [{version.semver()}]"):
            raise ConfigError(
                "changelog_template must start with `## [$version]`, so releases "
                "can find and replace their sections."
            )
        return re.sub(r"\n{3,}", "\n\n", text.strip()) + "\n"
    lines = [f"## [{version.semver()}] - {day}", "", *body, *migrations]
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


def carried_entries(
    text: str, version: Version, kinds: tuple[str, ...] = KINDS
) -> list[Entry]:
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
            entries.extend(_parse_entries(body, kinds))
    return entries


def _parse_entries(body: str, kinds: tuple[str, ...] = KINDS) -> list[Entry]:
    """Read the bullets of a rendered section back into entries."""
    entries: list[Entry] = []
    kind = "Changed"
    heading_scope: str | None = None
    for line in body.splitlines():
        heading = re.match(
            r"^(?P<level>#{3,4})\s+(?P<name>[\w-][\w -]*?)\s*$", line.strip()
        )
        if heading:
            name = heading["name"]
            known = _known_kind(name, kinds)
            if known:
                kind = known
                if heading["level"] == "###":
                    heading_scope = None
            elif name != "General":
                heading_scope = name
            else:
                heading_scope = None
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
