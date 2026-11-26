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
Every read gitversioned makes from git, plus the no-git fallbacks.

All calls go through :func:`run`, which never invokes a shell. Tag lookups peel
annotated tags to their commit, and dirty paths are reported from the repository
root so a project in a subfolder sees the same paths git does.

Example:
::
    from pathlib import Path

    from gitversioned import git

    repo = git.Repo.open(Path.cwd())
    if repo is not None:
        print(repo.head(), repo.tags_merged())
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

__all__ = [
    "ArchiveInfo",
    "Commit",
    "Repo",
    "build_time",
    "is_ci",
    "read_archive",
    "read_sdist_version",
    "run",
]

ARCHIVE_FILE = ".git_archival.txt"
_FIELD_SEP = "\x1f"
_RECORD_SEP = "\x1e"
_STATUS_PREFIX = 3
_DESCRIBE_RE = re.compile(r"^(?P<tag>.+)-(?P<distance>\d+)-g(?P<sha>[0-9a-f]+)$")


def is_ci() -> bool:
    """
    :return: True when a CI system is detected through the ``CI`` variable.
    """
    return os.environ.get("CI", "").strip().lower() not in ("", "0", "false", "no")


def build_time() -> datetime:
    """
    The time of this build, for build dates and release dates.

    ``SOURCE_DATE_EPOCH`` (https://reproducible-builds.org/specs/source-date-epoch/)
    fixes it, so a rebuild of the same source gives the same version and changelog.

    :return: The current time in UTC, or the time ``SOURCE_DATE_EPOCH`` names.
    """
    epoch = os.environ.get("SOURCE_DATE_EPOCH", "").strip()
    if epoch.isdigit():
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc)
    return datetime.now(tz=timezone.utc)


def run(args: list[str], cwd: Path, *, check: bool = True) -> str | None:
    """
    Run a git command and return its output.

    :param args: Arguments after ``git``.
    :param cwd: Folder to run in.
    :param check: When False, a failing command returns ``None`` instead of raising.
    :return: Standard output without the trailing newline, or ``None`` on failure
        when ``check`` is False.
    :raises subprocess.CalledProcessError: If the command fails and ``check`` is True.
    """
    logger.debug(f"git {' '.join(args)}")
    try:
        result = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        if check:
            raise
        return None
    if result.returncode != 0:
        return None
    return result.stdout.rstrip("\n")


@dataclass(frozen=True)
class Commit:
    """
    One commit as the changelog and the bump rules need it.

    :param sha: Full commit hash.
    :param subject: First line of the message.
    :param body: Rest of the message.
    """

    sha: str
    subject: str
    body: str = ""


@dataclass(frozen=True)
class ArchiveInfo:
    """
    What a ``git archive`` export file says about the exported commit.

    :param sha: Commit hash, when the file was expanded.
    :param tags: Tag names pointing at the commit or named by ``describe``.
    :param distance: Commits since the nearest tag.
    :param date: Commit date.
    """

    sha: str | None
    tags: tuple[str, ...]
    distance: int
    date: datetime | None


@dataclass(frozen=True)
class Repo:
    """
    A git repository seen from a project folder inside it.

    :param top: Repository root.
    :param cwd: Project folder the commands run from.
    """

    top: Path
    cwd: Path

    @classmethod
    def open(cls, cwd: Path) -> Repo | None:
        """
        Open the repository containing a folder.

        :param cwd: Any folder inside the work tree.
        :return: The repository, or ``None`` when git is missing or the folder is
            not in a work tree.
        """
        if not cwd.is_dir():
            return None
        top = run(["rev-parse", "--show-toplevel"], cwd, check=False)
        if not top:
            return None
        return cls(top=Path(top).resolve(), cwd=cwd.resolve())

    def git(self, *args: str, check: bool = True) -> str | None:
        """
        Run a git command from the repository root.

        :param args: Arguments after ``git``.
        :param check: When False, failure returns ``None``.
        :return: The command output.
        """
        return run(list(args), self.top, check=check)

    def head(self) -> str | None:
        """
        :return: The full hash of ``HEAD``, or ``None`` in a repository with no
            commits.
        """
        return self.git("rev-parse", "--verify", "-q", "HEAD", check=False) or None

    def head_date(self) -> datetime | None:
        """
        :return: The committer date of ``HEAD`` in UTC.
        """
        stamp = self.git("log", "-1", "--format=%ct", check=False)
        if not stamp:
            return None
        return datetime.fromtimestamp(int(stamp), tz=timezone.utc)

    def branch(self) -> str | None:
        """
        :return: The current branch name, or ``None`` on a detached ``HEAD``.
        """
        return self.git("symbolic-ref", "--short", "-q", "HEAD", check=False) or None

    def is_shallow(self) -> bool:
        """
        :return: True when history was cut by a shallow clone.
        """
        return self.git("rev-parse", "--is-shallow-repository", check=False) == "true"

    def tags_merged(self, ref: str = "HEAD") -> dict[str, str]:
        """
        List the tags reachable from a ref with the commit each one points at.

        Annotated tags are peeled, so the hash is always a commit.

        :param ref: Ref the tags must be reachable from.
        :return: Tag name to commit hash.
        """
        out = self.git(
            "for-each-ref",
            "--merged",
            ref,
            "--format=%(refname:short)%1f%(objectname)%1f%(*objectname)",
            "refs/tags",
            check=False,
        )
        tags: dict[str, str] = {}
        for line in (out or "").splitlines():
            name, obj, peeled = (line.split(_FIELD_SEP) + ["", ""])[:3]
            tags[name] = peeled or obj
        return tags

    def all_tags(self) -> list[str]:
        """
        :return: Every tag name in the repository.
        """
        out = self.git("tag", "--list", check=False)
        return out.splitlines() if out else []

    def distance(self, since: str | None, ref: str = "HEAD") -> int:
        """
        Count the commits on a ref after a starting point.

        :param since: Commit or tag to count from; ``None`` counts all history.
        :param ref: Ref to count to.
        :return: Number of commits.
        """
        spec = f"{since}..{ref}" if since else ref
        out = self.git("rev-list", "--count", spec, check=False)
        return int(out) if out and out.isdigit() else 0

    def commits(
        self,
        since: str | None,
        ref: str = "HEAD",
        path: Path | None = None,
        exclude: list[Path] | None = None,
    ) -> list[Commit]:
        """
        List the commits on a ref after a starting point, newest first.

        :param since: Commit or tag to start after; ``None`` lists all history.
        :param ref: Ref to list to.
        :param path: Only commits touching this folder, for a package.
        :param exclude: Folders whose commits do not count, for packages that
            carry their own tags.
        :return: The commits.
        """
        spec = f"{since}..{ref}" if since else ref
        args = ["log", f"--format=%H{_FIELD_SEP}%s{_FIELD_SEP}%b{_RECORD_SEP}", spec]
        if path is not None:
            args += ["--", str(path)]
        elif exclude:
            args += [
                "--",
                ".",
                *[f":(exclude){self.relative(item)}" for item in exclude],
            ]
        out = self.git(*args, check=False) or ""
        commits: list[Commit] = []
        for record in out.split(_RECORD_SEP):
            if not record.strip():
                continue
            sha, subject, body = (record.strip("\n").split(_FIELD_SEP) + ["", ""])[:3]
            commits.append(Commit(sha=sha, subject=subject, body=body.strip()))
        return commits

    def dirty_paths(self) -> list[str]:
        """
        List tracked files with uncommitted changes, relative to the repository root.

        Untracked files do not count, matching ``git describe --dirty``.

        :return: Paths with staged or unstaged changes.
        """
        out = self.git(
            "status", "--porcelain=v1", "--untracked-files=no", "-z", check=False
        )
        paths: list[str] = []
        entries = (out or "").split("\0")
        index = 0
        while index < len(entries):
            entry = entries[index]
            index += 1
            if len(entry) <= _STATUS_PREFIX:
                continue
            paths.append(entry[_STATUS_PREFIX:])
            if entry[0] in "RC":
                index += 1
        return paths

    def show(self, path: str, ref: str = "HEAD") -> str | None:
        """
        Read a file as committed.

        :param path: Path relative to the repository root.
        :param ref: Commit to read from.
        :return: The file text, or ``None`` when it does not exist there.
        """
        return self.git("show", f"{ref}:{path}", check=False)

    def tracked_files(self) -> list[str]:
        """
        :return: Tracked and untracked-but-not-ignored files, relative to the root.
        """
        out = self.git(
            "ls-files", "--cached", "--others", "--exclude-standard", check=False
        )
        return out.splitlines() if out else []

    def tracks(self, folder: Path) -> bool:
        """
        Tell whether git tracks anything in a folder.

        :param folder: Folder inside the work tree.
        :return: True when at least one tracked file lies in the folder.
        """
        out = self.git("ls-files", "--", self.relative(folder) or ".", check=False)
        return bool(out)

    def relative(self, path: Path) -> str:
        """
        Express a path relative to the repository root with forward slashes.

        :param path: Absolute path inside the work tree.
        :return: The relative path.
        """
        return path.resolve().relative_to(self.top).as_posix()


def read_archive(root: Path) -> ArchiveInfo | None:
    """
    Read a ``git archive`` export file in either supported layout.

    Both the setuptools-scm layout (``node``, ``node-date``, ``describe-name``,
    ``ref-names``) and the gitversioned layout (``commit_sha``, ``commit_date``,
    ``ref_names``) are accepted. A file that was never expanded is ignored.

    :param root: Folder holding ``.git_archival.txt``.
    :return: The archive details, or ``None`` when absent or unexpanded.
    """
    path = root / ARCHIVE_FILE
    if not path.is_file():
        return None
    fields: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip().lower().replace("_", "-")] = value.strip()
    values = {
        key: value
        for key, value in fields.items()
        if value and "$Format" not in value and not value.startswith("%")
    }
    if not values:
        return None
    sha = values.get("node") or values.get("commit-sha")
    tags, distance = _archive_tags(values)
    date: datetime | None = None
    raw_date = values.get("node-date") or values.get("commit-date")
    if raw_date:
        try:
            date = datetime.fromisoformat(raw_date).astimezone(timezone.utc)
        except ValueError:
            date = None
    if not sha and not tags:
        return None
    return ArchiveInfo(sha=sha, tags=tuple(tags), distance=distance, date=date)


def _archive_tags(values: dict[str, str]) -> tuple[list[str], int]:
    """Read the tag names and the distance from expanded archive fields."""
    tags: list[str] = []
    distance = 0
    describe = values.get("describe-name", "")
    match = _DESCRIBE_RE.match(describe)
    if match:
        tags.append(match["tag"])
        distance = int(match["distance"])
    elif describe:
        tags.append(describe)
    exact = [
        name.strip()[len("tag: ") :].strip()
        for name in values.get("ref-names", "").split(",")
        if name.strip().startswith("tag: ")
    ]
    if exact:
        distance = 0
    return list(dict.fromkeys(exact + tags)), distance


def read_sdist_version(root: Path) -> str | None:
    """
    Read the version recorded in an unpacked source distribution.

    :param root: Folder that may hold ``PKG-INFO``.
    :return: The ``Version`` field, or ``None``.
    """
    path = root / "PKG-INFO"
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("Version:"):
            return line.partition(":")[2].strip() or None
        if not line.strip():
            break
    return None
