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
#
# Unless otherwise noted, all files in this directory and its subdirectories
# are licensed under the Apache License, Version 2.0.

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import shutil
import subprocess
from collections.abc import Generator
from functools import wraps
from pathlib import Path

import pytest
from loguru import logger

__all__ = [
    "GitRepoHelper",
    "PropagateHandler",
    "async_timeout",
    "caplog_loguru",
    "e2e_git_repo",
    "temp_git_repo",
]


def pytest_configure(config: pytest.Config) -> None:
    """Apply TEST_FILTER env var and default log level for tests."""
    test_filter = os.environ.get("TEST_FILTER")
    if test_filter and not config.option.keyword:
        config.option.keyword = test_filter
    os.environ.setdefault("GITVERSIONED__LOGGING__LEVEL", "ERROR")


class PropagateHandler(logging.Handler):
    """
    Routes loguru logs to standard logging so that caplog can capture them.
    """

    def __init__(self, caplog_handler: logging.Handler) -> None:
        super().__init__()
        self.caplog_handler = caplog_handler

    def emit(self, record: logging.LogRecord) -> None:
        """Route loguru record to standard logging."""
        self.caplog_handler.handle(record)


@pytest.fixture(autouse=True)
def caplog_loguru(
    caplog: pytest.LogCaptureFixture,
) -> Generator[pytest.LogCaptureFixture, None, None]:
    """
    Hook loguru into pytest's caplog fixture.

    This ensures that assertions like `assert "foo" in caplog.text` work
    seamlessly with Loguru output.
    """
    from gitversioned.logging import _state  # noqa: PLC0415

    logger.remove()
    _state["handler_id"] = None
    logger.enable("gitversioned")

    logger.add(PropagateHandler(caplog.handler), format="{message}")
    yield caplog
    logger.remove()
    _state["handler_id"] = None
    logger.disable("gitversioned")


class GitRepoHelper:
    """Helper class to manage a temporary git repository for tests."""

    def __init__(self, path: Path, init: bool = True, initial_commit: bool = False):
        self.path = path
        if init:
            self._init_repo(initial_commit=initial_commit)

    def _init_repo(self, initial_commit: bool = True) -> None:
        """Initialize a git repository in the temporary path."""
        try:
            subprocess.check_call(
                ["git", "init", "-b", "main"],
                cwd=self.path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            subprocess.check_call(
                ["git", "init"],
                cwd=self.path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            with contextlib.suppress(subprocess.CalledProcessError):
                subprocess.check_call(
                    ["git", "checkout", "-b", "main"],
                    cwd=self.path,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

        subprocess.check_call(
            ["git", "config", "user.name", "Test User"],
            cwd=self.path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.check_call(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Create a dummy pyproject.toml for hatchling and maturin tests
        pyproject_path = self.path / "pyproject.toml"
        pyproject_path.write_text(
            '[project]\nname = "test_pkg"\ndynamic = ["version"]\n', encoding="utf-8"
        )
        if initial_commit:
            self.add("pyproject.toml")
            self.commit("Initial commit")

    def branch(self, name: str) -> None:
        """Create a branch in the repository."""
        subprocess.check_call(
            ["git", "checkout", "-b", name],
            cwd=self.path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def add(self, file: str) -> None:
        """Add a file to the repository."""
        subprocess.check_call(
            ["git", "add", file],
            cwd=self.path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    @property
    def short_sha(self) -> str:
        """Get the short SHA of the current commit."""
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=self.path,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()

    def commit(self, message: str, empty: bool = True) -> None:
        """Create a commit in the repository."""
        cmd = ["git", "commit", "-m", message]
        if empty:
            cmd.append("--allow-empty")
        subprocess.check_call(
            cmd,
            cwd=self.path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def tag(
        self, name: str, annotated: bool = False, message: str | None = None
    ) -> None:
        """Create a tag in the repository."""
        cmd = ["git", "tag"]
        if annotated:
            cmd.extend(["-a", name, "-m", message or f"Tag {name}"])
        else:
            cmd.append(name)
        subprocess.check_call(
            cmd,
            cwd=self.path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def dirty(self, filename: str = "dirty.txt") -> None:
        """Make the working directory dirty by creating an untracked file."""
        file_path = self.path / filename
        file_path.write_text("dirty")

    def checkout_detached(self) -> None:
        """Checkout a detached HEAD state."""
        # Get the current commit hash
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=self.path,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        subprocess.check_call(
            ["git", "checkout", commit_hash],
            cwd=self.path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def shallow_clone(self, target_path: Path) -> GitRepoHelper:
        """Create a shallow clone of the repository."""
        subprocess.check_call(
            ["git", "clone", "--depth", "1", f"file://{self.path}", str(target_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Re-configure user so commits can be made in the clone if needed
        subprocess.check_call(
            ["git", "config", "user.name", "Test User"],
            cwd=target_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.check_call(
            ["git", "config", "user.email", "test@example.com"],
            cwd=target_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        pyproject_path = self.path / "pyproject.toml"
        if pyproject_path.exists():
            shutil.copy2(pyproject_path, target_path / "pyproject.toml")
        return GitRepoHelper(target_path, init=False)

    def remove_git_dir(self) -> None:
        """Remove the .git directory to simulate a downloaded source archive."""
        git_dir = self.path / ".git"
        if git_dir.exists():
            shutil.rmtree(git_dir)

    def setup_state(self, state: str) -> GitRepoHelper:
        """Set up the repository to a specific state and return the GitRepoHelper."""
        if state != "clean":
            self.commit("First commit")

        if state in {
            "lightweight_tag",
            "tagged",
            "tagged_dirty",
            "detached",
            "shallow",
            "tagged_plus_commit",
            "annotated_tag",
        }:
            annotated = state == "annotated_tag"
            self.tag("v1.0.0", annotated=annotated)

        if state == "tagged_plus_commit":
            self.commit("Second commit")

        if state in {"dirty", "tagged_dirty"}:
            self.dirty()

        if state == "detached":
            self.checkout_detached()

        if state == "shallow":
            clone_path = self.path.with_name(self.path.name + "_shallow")
            return self.shallow_clone(clone_path)

        if state == "no_git":
            self.remove_git_dir()

        return self


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> GitRepoHelper:
    """Yield a temporary git repository helper."""
    return GitRepoHelper(tmp_path)


@pytest.fixture
def e2e_git_repo(temp_git_repo: GitRepoHelper) -> GitRepoHelper:
    """Yield a temporary git repo helper configured for E2E tests."""
    return temp_git_repo


def async_timeout(delay):
    def decorator(func):
        @wraps(func)
        async def new_func(*args, **kwargs):
            return await asyncio.wait_for(func(*args, **kwargs), timeout=delay)

        return new_func

    return decorator
