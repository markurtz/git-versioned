"""Git repository utility module.

This module exposes a Pydantic-based interface to extract Git repository
metadata (commits, tags, and branches) via command-line subprocesses.

Example
-------
.. code-block:: python

    from gitversioned.utils.git import GitRepository

    repo = GitRepository()
    if repo.is_available:
        print(repo.current_branch.branch_name)
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from gitversioned.logging import logger

__all__ = [
    "GitReference",
    "GitRepository",
    "NotAGitRepositoryError",
]

_EXPECTED_LOG_PARTS_COUNT = 7


class NotAGitRepositoryError(Exception):
    """Exception raised when a directory is not a valid Git repository.

    This error is raised when Git operations are performed on a directory
    that is not inside a valid Git work tree.

    Example
    -------
    .. code-block:: python

        try:
            root = GitRepository("/tmp").root_directory
        except NotAGitRepositoryError:
            pass
    """


class GitReference(BaseModel):
    """Pydantic model representing a Git reference (commit, tag, or branch).

    Provides the core metadata fields representing a Git reference in a repository
    with details for tag, branch, or commit types.

    Example
    -------
    .. code-block:: python

        from gitversioned.utils.git import GitReference

        ref = GitReference(short_sha="a1b2c3d", distance_from_head=0)
        print(ref.short_sha)
    """

    commit_sha: str = Field(
        description="Full Git commit SHA-1 hash to identify the object.",
        default="",
    )
    short_sha: str = Field(
        description="Abbreviated Git commit SHA hash for short display.",
        default="",
    )
    timestamp: datetime = Field(
        description="Creation or commit timestamp of the Git object.",
        default=datetime.min,
    )
    distance_from_head: int = Field(
        description="Commit distance from the current HEAD.",
        default=sys.maxsize,
    )
    is_head_commit: bool = Field(
        description="True if this is the HEAD commit.",
        default=False,
    )
    total_commits: int = Field(
        description="Total commit count of the repository.",
        default=0,
    )
    author_name: str = Field(description="Name of the commit author.", default="")
    author_email: str = Field(
        description="Email of the commit author.",
        default="",
    )
    commit_message: str = Field(
        description="Full commit message body and subject.", default=""
    )
    tag_name: str = Field(description="Name of the Git tag.", default="")
    branch_name: str = Field(description="Name of the Git branch.", default="")
    is_current_branch: bool = Field(
        description="True if the branch is currently checked out.",
        default=False,
    )

    @model_validator(mode="before")
    @classmethod
    def parse_git_references(cls, data: Any) -> Any:
        """Extract branch and tag metadata from input dictionary ref strings.

        This validator parses command output references to identify current
        branches and tags.

        :param data: The input dictionary or raw data to validate.
        :return: The parsed and normalized dictionary.
        """
        if not isinstance(data, dict):
            return data

        if "ref_names" in data:
            data["refs"] = data["ref_names"]

        if "refs" not in data:
            return data

        reference_string = data["refs"]
        reference_parts = [part.strip() for part in reference_string.split(",")]
        found_tags = []

        for part in reference_parts:
            # Detect current branch from 'HEAD -> branch_name'
            if "HEAD ->" in part:
                data["branch_name"] = part.replace("HEAD ->", "").strip()
                data["is_current_branch"] = True

            # Detect tags
            elif "tag:" in part:
                tag_content = part.replace("tag:", "").strip()
                found_tags.append(tag_content)

            # Fallback for plain branch names if HEAD was not explicitly indicated
            elif not data.get("branch_name") and not part.startswith("tag:"):
                data["branch_name"] = part

        # The first tag in the ref list is considered the closest/most recent
        if found_tags and not data.get("tag_name"):
            data["tag_name"] = found_tags[0]

        return data

    def __str__(self) -> str:
        time_str = self.timestamp.isoformat()
        if self.tag_name:
            return f"{self.tag_name} -> {self.short_sha} ({time_str})"
        if self.branch_name:
            marker = "*" if self.is_current_branch else " "
            return f"{marker} {self.branch_name} -> {self.short_sha} ({time_str})"
        if self.commit_message:
            return (
                f"{self.short_sha} {self.commit_message} - {self.author_name} "
                f"({time_str})"
            )
        return f"{self.short_sha} ({time_str})"


class GitRepository:
    """Interface for querying Git repository status and references.

    Provides properties and methods to interact with a Git repository using typed
    Pydantic models for commits, tags, and branches.

    Example
    -------
    .. code-block:: python

        from gitversioned.utils.git import GitRepository

        repo = GitRepository()
        if repo.is_available:
            print(repo.head_name)
    """

    def __init__(
        self,
        repository_path: Path | str | None = None,
    ) -> None:
        """Initialize the GitRepository instance.

        :param repository_path: Base directory of the repository,
            defaults to Path.cwd().
        """
        self.base_path = Path(repository_path or Path.cwd()).resolve()

    def __str__(self) -> str:
        """Return a concise string representation."""
        if not self.is_available:
            return f"GitRepository({self.base_path}) - Unavailable"

        dirty_files = self.dirty_files
        current = self.current_commit
        tag = self.last_tag
        branch = self.current_branch

        head = "detached"
        if branch:
            head = branch.branch_name
        elif current:
            head = current.short_sha

        return (
            f"GitRepository(path={self.base_path!r}, is_available=True, "
            f"commit_count={self.commit_count}, is_dirty={bool(dirty_files)}, "
            f"dirty_files={dirty_files}, "
            f"current_commit={current.short_sha if current else None}, "
            f"last_tag={tag.tag_name if tag else None}, "
            f"current_branch={branch.branch_name if branch else None}"
            f") - {head}{'*' if dirty_files else ''}"
        )

    def __repr__(self) -> str:
        """Return a detailed string representation."""
        return f"GitRepository(base_path={self.base_path!r})"

    @property
    def is_available(self) -> bool:
        """Check if the base path is within a valid Git work tree.

        :return: True if the repository path is a valid Git work tree, False otherwise.
        """
        return self._execute_command(["rev-parse", "--is-inside-work-tree"]) == "true"

    @property
    def root_directory(self) -> Path:
        """Get the root directory of the Git repository.

        :return: Absolute path to the Git repository root.
        :raises NotAGitRepositoryError: If the path is not a valid Git repository.
        """
        self._ensure_valid_repository()
        return Path(self._execute_command(["rev-parse", "--show-toplevel"]))

    @property
    def repository_name(self) -> str:
        """Get the name of the Git repository.

        Attempts to parse the name from the remote origin URL, falling back
        to the root directory name.

        :return: The repository name.
        """
        if remote_url := self.remote_origin_url:
            name = remote_url.split("/")[-1]
            return name[:-4] if name.endswith(".git") else name
        return self.root_directory.name

    @property
    def remote_origin_url(self) -> str:
        """Get the remote origin URL.

        :return: Remote origin URL, or empty string if not set.
        """
        return self._execute_command(["config", "--get", "remote.origin.url"])

    @property
    def commit_count(self) -> int:
        """Get the total commit count on the current branch.

        :return: Total number of commits, or 0 if unavailable.
        """
        if not self.is_available:
            return 0
        try:
            return int(self._execute_command(["rev-list", "--count", "HEAD"]) or 0)
        except ValueError:
            return 0

    @property
    def is_dirty(self) -> bool:
        """Check if the repository has uncommitted modifications.

        :return: True if dirty changes exist, False otherwise.
        """
        return bool(self.dirty_files)

    @property
    def dirty_files(self) -> list[Path]:
        """Get a list of all modified and untracked file paths.

        :return: List of paths with uncommitted changes.
        """
        output = self._execute_command(["status", "--porcelain"])
        dirty = []
        for line in output.splitlines():
            if line:
                path = line[3:]
                if " -> " in path:
                    path = path.split(" -> ")[-1]
                dirty.append((self.base_path / path).resolve())
        return dirty

    @property
    def current_commit(self) -> GitReference | None:
        """Get the most recent commit.

        :return: Most recent commit reference, or None if empty.
        """
        return next(self.commits, None)

    @property
    def current_commit_or_fallback(self) -> GitReference:
        """Get the most recent commit or a generated fallback reference.

        :return: Current commit reference, or a dummy reference if unavailable.
        """
        return (
            self.current_commit
            if self.is_available and self.current_commit
            else GitReference(
                timestamp=datetime.now(timezone.utc),
                distance_from_head=0,
                is_head_commit=True,
            )
        )

    @property
    def last_tag(self) -> GitReference | None:
        """Get the most recent tag.

        :return: Most recent tag reference, or None if no tags exist.
        """
        return next(self.tags, None)

    @property
    def current_branch(self) -> GitReference | None:
        """Get the currently checked-out branch.

        :return: Current branch reference, or None if in detached HEAD.
        """
        return next(
            (branch for branch in self.branches if branch.is_current_branch),
            None,
        )

    @property
    def head_name(self) -> str:
        """Get the branch name or the short commit SHA of HEAD.

        :return: Current branch name, or short SHA if detached.
        """
        if branch := self.current_branch:
            return branch.branch_name
        if current := self.current_commit:
            return current.short_sha
        return ""

    @property
    def commits(self) -> Iterator[GitReference]:
        """Yield all commits in the repository history.

        :return: Iterator of commit reference objects.
        :raises NotAGitRepositoryError: If the path is not a valid Git repository.
        """
        self._ensure_valid_repository()
        total_commits = self.commit_count
        format_string = "%H|%h|%cI|%an|%ae|%s|%D"
        lines = self._stream_command(["log", f"--format={format_string}"])

        for index, line in enumerate(lines):
            parts = line.split("|", 6)
            if len(parts) == _EXPECTED_LOG_PARTS_COUNT:
                tag_name = ""
                branch_name = ""
                is_current_branch = False

                refs = parts[6].split(", ") if parts[6] else []
                for ref in refs:
                    if ref.startswith("tag: "):
                        tag_name = ref[5:]
                    elif "->" in ref:
                        branch_name = ref.split(" -> ")[1]
                        is_current_branch = True
                    elif (
                        ref
                        and not ref.startswith("origin/")
                        and ref != "HEAD"
                        and not branch_name
                    ):
                        branch_name = ref

                yield GitReference(
                    commit_sha=parts[0],
                    short_sha=parts[1],
                    timestamp=datetime.fromisoformat(parts[2].replace("Z", "+00:00")),
                    author_name=parts[3],
                    author_email=parts[4],
                    commit_message=parts[5],
                    tag_name=tag_name,
                    branch_name=branch_name,
                    is_current_branch=is_current_branch,
                    distance_from_head=index,
                    is_head_commit=(index == 0),
                    total_commits=total_commits,
                )

    @property
    def tags(self) -> Iterator[GitReference]:
        """Yield all tags in the repository sorted by creation date.

        :return: Iterator of tag reference objects.
        :raises NotAGitRepositoryError: If the path is not a valid Git repository.
        """
        self._ensure_valid_repository()
        current = self.current_commit
        head_sha = current.commit_sha if current else ""
        total_commits = self.commit_count
        format_string = "%(refname:short)|%(creatordate:iso-strict)|%(objectname)"

        lines = self._stream_command(
            [
                "for-each-ref",
                "--sort=-creatordate",
                f"--format={format_string}",
                "refs/tags/",
            ]
        )

        for line in lines:
            name, date_str, sha = line.split("|")
            distance_str = self._execute_command(
                ["rev-list", "--count", f"{sha}..HEAD"]
            )
            yield GitReference(
                tag_name=name,
                commit_sha=sha,
                short_sha=sha[:7],
                timestamp=datetime.fromisoformat(date_str.replace("Z", "+00:00")),
                distance_from_head=int(distance_str or 0),
                is_head_commit=(sha == head_sha),
                total_commits=total_commits,
            )

    @property
    def branches(self) -> Iterator[GitReference]:
        """Yield all branches in the repository.

        :return: Iterator of branch reference objects.
        :raises NotAGitRepositoryError: If the path is not a valid Git repository.
        """
        self._ensure_valid_repository()
        current = self.current_commit
        head_sha = current.commit_sha if current else ""
        total_commits = self.commit_count
        format_string = (
            "%(refname:short)|%(objectname)|%(HEAD)|%(committerdate:iso-strict)"
        )

        lines = self._stream_command(
            [
                "for-each-ref",
                f"--format={format_string}",
                "refs/heads/",
                "refs/remotes/",
            ]
        )

        for line in lines:
            name, sha, current_marker, date_str = line.split("|")
            yield GitReference(
                branch_name=name,
                commit_sha=sha,
                short_sha=sha[:7],
                timestamp=datetime.fromisoformat(date_str.replace("Z", "+00:00")),
                distance_from_head=0,
                is_head_commit=(sha == head_sha),
                is_current_branch=(current_marker == "*"),
                total_commits=total_commits,
            )

    def filtered_dirty_files(
        self, ignore_paths: list[Path] | None = None, fail_on_unavailable: bool = False
    ) -> list[str]:
        """Filter modified files excluding the specified ignore paths.

        Example
        -------
        .. code-block:: python

            dirty = repo.filtered_dirty_files(ignore_paths=[Path("tmp")])

        :param ignore_paths: List of file/directory paths to exclude from results.
        :param fail_on_unavailable: If True, raise exception if Git is missing.
        :return: List of filtered dirty file paths as strings.
        :raises NotAGitRepositoryError: If repository is missing and
            fail_on_unavailable is True.
        """
        if not self.is_available:
            if fail_on_unavailable:
                raise NotAGitRepositoryError(
                    f"Path '{self.base_path}' is not a Git repository."
                )
            return []

        unfiltered_files = []
        ignore_paths_abs = [
            path.resolve() if path.is_absolute() else (self.base_path / path).resolve()
            for path in ignore_paths or []
        ]

        for dirty_file in self.dirty_files:
            if not any(
                dirty_file == ignored or ignored in dirty_file.parents
                for ignored in ignore_paths_abs
            ):
                unfiltered_files.append(str(dirty_file))

        return unfiltered_files

    def _stream_command(self, arguments: list[str]) -> Iterator[str]:
        # Stream the output of a Git command line by line.
        full_command = ["git", *arguments]
        try:
            with subprocess.Popen(  # noqa: S603
                full_command,
                cwd=self.base_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            ) as process:
                if process.stdout:
                    for line in process.stdout:
                        if clean_line := line.strip():
                            yield clean_line
        except (subprocess.CalledProcessError, FileNotFoundError, OSError) as error:
            logger.debug(f"Command '{shlex.join(full_command)}' failed: {error}")

    def _execute_command(self, arguments: list[str]) -> str:
        # Execute a Git command and return stdout as a stripped string.
        full_command = ["git", *arguments]
        try:
            return subprocess.run(  # noqa: S603
                full_command,
                cwd=self.base_path,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.rstrip()
        except (subprocess.CalledProcessError, FileNotFoundError, OSError) as error:
            logger.debug(f"Command '{shlex.join(full_command)}' failed: {error}")
            return ""

    def _ensure_valid_repository(self) -> None:
        # Ensure the repository is available, raising NotAGitRepositoryError if not.
        if not self.is_available:
            raise NotAGitRepositoryError(
                f"Path '{self.base_path}' is not a Git repository."
            )
