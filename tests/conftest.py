from __future__ import annotations

import asyncio
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
    """Apply TEST_FILTER env var as a pytest keyword expression."""
    test_filter = os.environ.get("TEST_FILTER")
    if test_filter and not config.option.keyword:
        config.option.keyword = test_filter


class PropagateHandler(logging.Handler):
    """
    Routes loguru logs to standard logging so that caplog can capture them.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Route loguru record to standard logging."""
        logging.getLogger(record.name).handle(record)


@pytest.fixture(autouse=True)
def caplog_loguru(
    caplog: pytest.LogCaptureFixture,
) -> Generator[pytest.LogCaptureFixture, None, None]:
    """
    Hook loguru into pytest's caplog fixture.

    This ensures that assertions like `assert "foo" in caplog.text` work
    seamlessly with Loguru output.
    """
    handler_id = logger.add(PropagateHandler(), format="{message}")
    yield caplog
    logger.remove(handler_id)


class GitRepoHelper:
    """Helper class to manage a temporary git repository for tests."""

    def __init__(self, path: Path, init: bool = True):
        self.path = path
        if init:
            self._init_repo()

    def _init_repo(self) -> None:
        """Initialize a git repository in the temporary path."""
        subprocess.check_call(["git", "init"], cwd=self.path)
        subprocess.check_call(
            ["git", "config", "user.name", "Test User"], cwd=self.path
        )
        subprocess.check_call(
            ["git", "config", "user.email", "test@example.com"], cwd=self.path
        )
        # Create a dummy pyproject.toml for hatchling tests
        pyproject_path = self.path / "pyproject.toml"
        pyproject_path.write_text(
            '[project]\nname = "test_pkg"\nversion = "0.1.0"\n', encoding="utf-8"
        )

    def branch(self, name: str) -> None:
        """Create a branch in the repository."""
        subprocess.check_call(["git", "checkout", "-b", name], cwd=self.path)

    def add(self, file: str) -> None:
        """Add a file to the repository."""
        subprocess.check_call(["git", "add", file], cwd=self.path)

    @property
    def short_sha(self) -> str:
        """Get the short SHA of the current commit."""
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=self.path, text=True
        ).strip()

    def commit(self, message: str, empty: bool = True) -> None:
        """Create a commit in the repository."""
        cmd = ["git", "commit", "-m", message]
        if empty:
            cmd.append("--allow-empty")
        subprocess.check_call(cmd, cwd=self.path)

    def tag(
        self, name: str, annotated: bool = False, message: str | None = None
    ) -> None:
        """Create a tag in the repository."""
        cmd = ["git", "tag"]
        if annotated:
            cmd.extend(["-a", name, "-m", message or f"Tag {name}"])
        else:
            cmd.append(name)
        subprocess.check_call(cmd, cwd=self.path)

    def dirty(self, filename: str = "dirty.txt") -> None:
        """Make the working directory dirty by creating an untracked file."""
        file_path = self.path / filename
        file_path.write_text("dirty")

    def checkout_detached(self) -> None:
        """Checkout a detached HEAD state."""
        # Get the current commit hash
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=self.path, text=True
        ).strip()
        subprocess.check_call(["git", "checkout", commit_hash], cwd=self.path)

    def shallow_clone(self, target_path: Path) -> GitRepoHelper:
        """Create a shallow clone of the repository."""
        subprocess.check_call(
            ["git", "clone", "--depth", "1", f"file://{self.path}", str(target_path)]
        )
        # Re-configure user so commits can be made in the clone if needed
        subprocess.check_call(
            ["git", "config", "user.name", "Test User"], cwd=target_path
        )
        subprocess.check_call(
            ["git", "config", "user.email", "test@example.com"], cwd=target_path
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
