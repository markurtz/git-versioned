"""
Git repository utility module.

This module provides a robust interface for interacting with Git repositories.
It uses a combination of subprocess calls and Pydantic models to safely and
efficiently retrieve and represent Git metadata such as commits, tags, and branches.

.. code-block:: python

    from gitversioned.utils.git import GitRepository

    repo = GitRepository()
    if repo.is_available:
        print(repo.current_branch.branch_name)
"""

from __future__ import annotations

import re
import shlex
import subprocess
import sys
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, Field, model_validator

from gitversioned.logging import logger

__all__ = [
    "GitReference",
    "GitRepository",
    "NotAGitRepositoryError",
]


class NotAGitRepositoryError(Exception):
    """
    Raised when the directory is not a valid Git repository.

    This exception is raised when Git operations are attempted on a directory that
    is not part of a valid Git work tree.
    """


class GitReference(BaseModel):
    """
    Pydantic model representing a Git reference (commit, tag, or branch).

    Provides the foundational metadata fields for Git objects and includes
    optional fields for specific types like author information for commits,
    or names for tags and branches.

    .. code-block:: python

        def print_metadata(metadata: GitReference):
            print(f"SHA: {metadata.short_sha}, HEAD: {metadata.is_head_commit}")
    """

    VERSION_PATTERN: ClassVar[str] = (
        r"^(?:releases?/)?v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$"
    )

    commit_sha: str = Field(
        description="The full, un-abbreviated SHA hash of the commit.",
        default="",
    )
    short_sha: str = Field(
        description="The abbreviated SHA hash of the commit for display purposes.",
        default="",
    )
    timestamp: datetime = Field(
        description="The creation or commit timestamp of the Git object.",
        default=datetime.min,
    )
    distance_from_head: int = Field(
        description="The number of commits between this object and the current HEAD.",
        default=sys.maxsize,
    )
    is_head_commit: bool = Field(
        description="Indicates whether this object represents the current HEAD commit.",
        default=False,
    )
    total_commits: int = Field(
        description="Total number of commits in the repository.",
        default=0,
    )
    author_name: str = Field(
        description="The name of the author who created the commit.", default=""
    )
    author_email: str = Field(
        description="The email address of the author who created the commit.",
        default="",
    )
    commit_message: str = Field(
        description="The full message associated with the commit.", default=""
    )
    tag_name: str = Field(description="The name of the Git tag.", default="")
    branch_name: str = Field(description="The name of the Git branch.", default="")
    is_current_branch: bool = Field(
        description="Indicates whether this branch is currently checked out.",
        default=False,
    )

    def __str__(self) -> str:
        if self.tag_name:
            return f"{self.tag_name} -> {self.short_sha} ({self.timestamp.isoformat()})"
        if self.branch_name:
            marker = "*" if self.is_current_branch else " "
            return (
                f"{marker} {self.branch_name} -> {self.short_sha} "
                f"({self.timestamp.isoformat()})"
            )
        if self.commit_message:
            return (
                f"{self.short_sha} {self.commit_message} - {self.author_name} "
                f"({self.timestamp.isoformat()})"
            )
        return f"{self.short_sha} ({self.timestamp.isoformat()})"

    @model_validator(mode="before")
    @classmethod
    def parse_git_references(cls, data: Any) -> Any:
        """
        Extracts branch and tag metadata from the 'refs' input string.

        Logic identifies the current branch via 'HEAD ->' and extracts
        the most recent semantic version tag using VERSION_PATTERN.
        """
        if not isinstance(data, dict) or not data.get("refs"):
            return data

        reference_string = data["refs"]
        reference_parts = [part.strip() for part in reference_string.split(",")]
        found_tags = []

        for part in reference_parts:
            # Detect current branch from 'HEAD -> branch_name'
            if "HEAD ->" in part:
                data["branch_name"] = part.replace("HEAD ->", "").strip()
                data["is_current_branch"] = True

            # Detect tags and validate against version regex
            elif "tag:" in part:
                tag_content = part.replace("tag:", "").strip()
                # finditer used to ensure matching against the provided pattern
                if any(re.finditer(cls.VERSION_PATTERN, tag_content)):
                    found_tags.append(tag_content)

            # Fallback for plain branch names if HEAD was not explicitly indicated
            elif not data.get("branch_name") and not part.startswith("tag:"):
                data["branch_name"] = part

        # The first tag in the ref list is considered the closest/most recent
        if found_tags and not data.get("tag_name"):
            data["tag_name"] = found_tags[0]

        return data


class GitRepository:
    """
    Refined interface for Git operations using Pydantic and safe execution.

    Provides properties and methods to query a Git repository's status, branches, tags,
    and commits. It encapsulates subprocess calls to Git and returns typed
    Pydantic models.

    .. code-block:: python

        repo = GitRepository()
        if repo.is_available:
            print(repo.last_tag.tag_name if repo.last_tag else "No tags found")
    """

    def __init__(
        self,
        repository_path: Path | str | None = None,
    ) -> None:
        """
        Initializes the GitRepository instance.

        :param repository_path: The base path to the Git repository.
            Defaults to the current working directory.
        """
        self.base_path = Path(repository_path or Path.cwd()).resolve()

    def __str__(self) -> str:
        """Return a concise string representation."""
        if not self.is_available:
            return f"GitRepository({self.base_path}) - Unavailable"

        status = "*" if self.is_dirty else ""
        head = self.head_name or "detached"

        current = self.current_commit
        tag = self.last_tag
        branch = self.current_branch

        return (
            f"GitRepository(path={self.base_path!r}, is_available={self.is_available}, "
            f"commit_count={self.commit_count}, is_dirty={self.is_dirty}, "
            f"dirty_files={self.dirty_files}, "
            f"current_commit={current.short_sha if current else None}, "
            f"last_tag={tag.tag_name if tag else None}, "
            f"current_branch={branch.branch_name if branch else None}"
            f") - {head}{status}"
        )

    def __repr__(self) -> str:
        """Return a detailed string representation."""
        return f"GitRepository(base_path={self.base_path!r})"

    @property
    def is_available(self) -> bool:
        """
        Checks if the path is inside a valid git work tree.

        :return: True if the base path is a valid Git repository work tree,
            False otherwise.
        """
        return self._execute_command(["rev-parse", "--is-inside-work-tree"]) == "true"

    @property
    def root_directory(self) -> Path:
        """
        Gets the root directory of the Git repository.

        :return: The absolute path to the root directory of the Git repository.
        :raises NotAGitRepositoryError: If the repository is not valid.
        """
        self._ensure_valid_repository()
        return Path(self._execute_command(["rev-parse", "--show-toplevel"]))

    @property
    def repository_name(self) -> str:
        """
        Gets the name of the Git repository.

        Extracts the repository name from the remote origin URL if available; otherwise,
        falls back to the name of the root directory.

        :return: The string name of the Git repository.
        """
        if remote_url := self.remote_origin_url:
            name = remote_url.split("/")[-1]
            return name[:-4] if name.endswith(".git") else name
        return self.root_directory.name

    @property
    def remote_origin_url(self) -> str:
        """
        Gets the remote origin URL.

        :return: The URL of the remote origin, or an empty string if not configured.
        """
        return self._execute_command(["config", "--get", "remote.origin.url"])

    @property
    def commit_count(self) -> int:
        """
        Gets the total number of commits in the repository.

        :return: The total number of commits.
        """
        if not self.is_available:
            return 0
        try:
            return int(self._execute_command(["rev-list", "--count", "HEAD"]) or 0)
        except ValueError:
            return 0

    @property
    def is_dirty(self) -> bool:
        """
        Checks if the repository has uncommitted changes.

        :return: True if there are uncommitted changes, False otherwise.
        """
        return bool(self.dirty_files)

    @property
    def dirty_files(self) -> list[str]:
        """
        Gets a list of modified files.

        :return: A list of file paths that have uncommitted changes.
        """
        output = self._execute_command(["status", "--porcelain"])
        return [line[3:] for line in output.splitlines() if line]

    @property
    def current_commit(self) -> GitReference | None:
        """
        Gets the most recent commit.

        :return: The most recent GitReference object, or None if no commits exist.
        """
        return next(self.commits, None)

    @property
    def last_tag(self) -> GitReference | None:
        """
        Gets the most recent tag.

        :return: The most recent GitReference object, or None if no tags exist.
        """
        return next(self.tags, None)

    @property
    def current_branch(self) -> GitReference | None:
        """
        Gets the currently checked-out branch.

        :return: The GitReference object representing the current branch,
            or None if detached.
        """
        return next(
            (branch for branch in self.branches if branch.is_current_branch),
            None,
        )

    @property
    def head_name(self) -> str:
        """
        Gets the branch name or short sha of HEAD.

        :return: The current branch name, or the short SHA if in a detached HEAD state.
        """
        if branch := self.current_branch:
            return branch.branch_name
        if current := self.current_commit:
            return current.short_sha
        return ""

    @property
    def commits(self) -> Iterator[GitReference]:
        """
        Yields all commits in the repository.

        :return: An iterator of GitReference objects.
        :raises NotAGitRepositoryError: If the repository is not valid.
        """
        self._ensure_valid_repository()
        total_commits = self.commit_count
        format_string = "%H|%h|%cI|%an|%ae|%s|%D"
        lines = self._stream_command(["log", f"--format={format_string}"])

        for index, line in enumerate(lines):
            parts = line.split("|", 6)
            if len(parts) == 7:  # noqa: PLR2004
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
        """
        Yields all tags in the repository.

        :return: An iterator of GitReference objects.
        :raises NotAGitRepositoryError: If the repository is not valid.
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
        """
        Yields all branches in the repository.

        :return: An iterator of GitReference objects.
        :raises NotAGitRepositoryError: If the repository is not valid.
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

    def _stream_command(self, arguments: list[str]) -> Iterator[str]:
        """Executes a git command and streams output line by line."""
        full_command = ["git", *arguments]
        try:
            with subprocess.Popen(  # noqa: S603
                full_command, cwd=self.base_path, stdout=subprocess.PIPE, text=True
            ) as process:
                if process.stdout:
                    for line in process.stdout:
                        if clean_line := line.strip():
                            yield clean_line
        except (subprocess.CalledProcessError, FileNotFoundError, OSError) as error:
            logger.debug(f"Command '{shlex.join(full_command)}' failed: {error}")

    def _execute_command(self, arguments: list[str]) -> str:
        """Executes a git command with standardized error handling."""
        full_command = ["git", *arguments]
        try:
            return subprocess.run(  # noqa: S603
                full_command,
                cwd=self.base_path,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError, OSError) as error:
            logger.debug(f"Command '{shlex.join(full_command)}' failed: {error}")
            return ""

    def _ensure_valid_repository(self) -> None:
        """Raises an error if the directory is not a Git repository."""
        if not self.is_available:
            raise NotAGitRepositoryError(
                f"Path '{self.base_path}' is not a Git repository."
            )
