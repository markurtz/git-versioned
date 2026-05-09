"""
Utility components and helpers for the gitversioned package.

Provides foundational utilities such as Git repository abstractions, environment
metadata gathering, and Pydantic type coercions. Designed for consistent, typed,
and testable interfaces across the core application logic.

Example:
    .. code-block:: python

        from gitversioned.utils import BuildEnvironment, GitRepository

        repo = GitRepository(".")
        env = BuildEnvironment()
"""

from __future__ import annotations

from .environment import BuildEnvironment, get_ci_info, get_user
from .git import Branch, Commit, GitRepository, NotAGitRepositoryError, Tag
from .pydantic import (
    EnsureBool,
    EnsureList,
    EnsurePath,
    coerce_bool,
    coerce_list,
    coerce_path,
)

__all__ = [
    "Branch",
    "BuildEnvironment",
    "Commit",
    "EnsureBool",
    "EnsureList",
    "EnsurePath",
    "GitRepository",
    "NotAGitRepositoryError",
    "Tag",
    "coerce_bool",
    "coerce_list",
    "coerce_path",
    "get_ci_info",
    "get_user",
]
