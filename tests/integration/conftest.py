from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


class GitRepoHelper:
    """Helper class to manage a temporary git repository for integration tests."""

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


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> GitRepoHelper:
    """Yield a temporary git repository helper."""
    return GitRepoHelper(tmp_path)
