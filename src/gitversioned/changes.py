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
Change files: changelog entries written by hand, one file each, before release.

A change file lives in the ``changes`` folder (``.changes/`` by default) and
holds a short front matter block and the entry text::

    ---
    type: feat
    scope: cli
    ---
    Add `--explain`, which shows why a version was chosen.

``type`` is a commit type, so the bump rules and changelog sections apply as
they do to commits. ``bump`` (``major``, ``minor``, ``patch`` or ``none``)
replaces the level the type gives, ``breaking: true`` marks a breaking change
and ``package`` names a package from ``[packages]``. A release takes every
change file into its changelog section and deletes it.

Example:
::
    from gitversioned.changes import read_changes
    from gitversioned.config import load_config

    for change in read_changes(load_config()):
        print(change.path, change.subject)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from gitversioned.errors import ConfigError
from gitversioned.git import Commit, build_time

if TYPE_CHECKING:
    from gitversioned.config import Config

__all__ = ["Change", "change_commits", "read_changes", "write_change"]

_FRONT_RE = re.compile(r"\A---[ \t]*\n(?P<front>.*?)\n---[ \t]*\n(?P<body>.*)\Z", re.S)
_KEYS = ("type", "scope", "bump", "breaking", "package")
_BUMPS = ("major", "minor", "patch", "none")


@dataclass(frozen=True)
class Change:
    """
    One change file.

    :param path: Path relative to the project root.
    :param type: Commit type.
    :param scope: Scope, if any.
    :param text: The entry text.
    :param bump: Level that replaces the type's, if given.
    :param breaking: True for a breaking change.
    :param package: Package the change belongs to, if any.
    """

    path: str
    type: str
    scope: str | None
    text: str
    bump: str | None = None
    breaking: bool = False
    package: str | None = None

    @property
    def subject(self) -> str:
        """
        :return: The change as a Conventional Commit subject.
        """
        scope = f"({self.scope})" if self.scope else ""
        mark = "!" if self.breaking else ""
        return f"{self.type}{scope}{mark}: {self.text}"


def _parse(path: Path, relative: str) -> Change:
    """Read one change file."""
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = _FRONT_RE.match(text)
    if match is None:
        raise ConfigError(
            f"{relative}: a change file starts with a --- block holding `type`."
        )
    data: dict[str, str] = {}
    for line in match["front"].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        key = key.strip()
        if not sep or key not in _KEYS:
            raise ConfigError(
                f"{relative}: unknown line {line.strip()!r}. Keys: {', '.join(_KEYS)}."
            )
        data[key] = value.split(" #", 1)[0].strip().strip("\"'")
    body = " ".join(match["body"].split())
    if not data.get("type"):
        raise ConfigError(f"{relative}: `type` is required, such as type: feat.")
    if not body:
        raise ConfigError(f"{relative}: the entry text after the --- block is empty.")
    bump = data.get("bump") or None
    if bump is not None and bump not in _BUMPS:
        raise ConfigError(f"{relative}: bump must be one of {', '.join(_BUMPS)}.")
    return Change(
        path=relative,
        type=data["type"].lower(),
        scope=data.get("scope") or None,
        text=body,
        bump=bump,
        breaking=data.get("breaking", "").lower() in ("true", "yes", "1"),
        package=data.get("package") or None,
    )


def read_changes(config: Config, package: str | None = None) -> list[Change]:
    """
    Read the change files that belong to the repository or one package.

    :param config: The loaded configuration.
    :param package: Package with its own tag, or ``None`` for the repository.
    :return: Changes in file name order.
    :raises ConfigError: If a change file is malformed or names an unknown
        package.
    """
    folder = config.root / config.changes
    if not folder.is_dir():
        return []
    found: list[Change] = []
    for path in sorted(folder.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        change = _parse(path, path.relative_to(config.root).as_posix())
        if change.package is not None and change.package not in config.packages:
            raise ConfigError(
                f"{change.path}: unknown package {change.package!r}. Packages: "
                f"{', '.join(config.packages) or 'none configured'}."
            )
        own = (
            change.package
            if change.package and config.packages[change.package].tag
            else None
        )
        if own == package:
            found.append(change)
    return found


def change_commits(config: Config, path_scope: str | None = None) -> list[Commit]:
    """
    Turn change files into commit-like entries for the bump rules and changelog.

    :param config: The loaded configuration.
    :param path_scope: Folder of the package being versioned, if any.
    :return: One entry per change file.
    """
    package = next(
        (
            name
            for name, item in config.packages.items()
            if path_scope and item.tag and item.path.strip("/") == path_scope.strip("/")
        ),
        None,
    )
    return [
        Commit(sha="", subject=change.subject, level=change.bump, path=change.path)
        for change in read_changes(config, package)
    ]


def write_change(  # noqa: PLR0913
    config: Config,
    *,
    type_: str,
    text: str,
    scope: str | None = None,
    breaking: bool = False,
    bump: str | None = None,
    package: str | None = None,
) -> Path:
    """
    Write a new change file.

    :param config: The loaded configuration.
    :param type_: Commit type.
    :param text: Entry text.
    :param scope: Scope, if any.
    :param breaking: Mark the change as breaking.
    :param bump: Level that replaces the type's.
    :param package: Package the change belongs to.
    :return: The new file.
    """
    folder = config.root / config.changes
    folder.mkdir(parents=True, exist_ok=True)
    words = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-").split("-")
    slug = ""
    for word in words:
        if slug and len(slug) + len(word) >= 40:  # noqa: PLR2004
            break
        slug = f"{slug}-{word}" if slug else word
    slug = slug[:40] or "change"
    stem = f"{build_time().strftime('%Y%m%d')}-{slug}"
    path = folder / f"{stem}.md"
    number = 2
    while path.exists():
        path = folder / f"{stem}-{number}.md"
        number += 1
    lines = ["---", f"type: {type_}"]
    lines += [f"scope: {scope}"] if scope else []
    lines += ["breaking: true"] if breaking else []
    lines += [f"bump: {bump}"] if bump else []
    lines += [f"package: {package}"] if package else []
    lines += ["---", text.strip(), ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
