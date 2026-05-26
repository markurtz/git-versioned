from __future__ import annotations

import subprocess
import sys

import pytest

from tests.conftest import GitRepoHelper


class TestMain:
    """Test suite for the main function."""

    @pytest.mark.parametrize(
        "cli_args",
        [
            ["--package-name", "test_pkg"],
            ["--pattern-release", "template", "--package-name", "test_pkg"],
            ["--version-type", "release", "--package-name", "test_pkg"],
        ],
    )
    @pytest.mark.sanity
    def test_invocation(
        self, temp_git_repo: GitRepoHelper, cli_args: list[str]
    ) -> None:
        """Test main invocation directly via subprocess."""
        temp_git_repo.commit("Initial commit")
        temp_git_repo.tag("v2.0.0")

        cmd = [
            sys.executable,
            "-m",
            "gitversioned",
            "--project-root",
            str(temp_git_repo.path),
        ]
        cmd.extend(cli_args)

        result = subprocess.run(
            cmd, cwd=temp_git_repo.path, capture_output=True, text=True, check=False
        )
        assert result.returncode == 0

        # Verify that the version file was created
        version_file = temp_git_repo.path / "version.py"
        assert version_file.exists()
        assert "2.0.0" in version_file.read_text(encoding="utf-8")
