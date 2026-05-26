from __future__ import annotations

import inspect
from typing import Any

import pytest
import typer

from gitversioned.__main__ import app, main, run_cli
from tests.conftest import GitRepoHelper


@pytest.mark.smoke
def test_app() -> None:
    """Validate the `app` param type, value, and signature."""
    assert isinstance(app, typer.Typer)
    assert app.info.help == (
        "Opinionated PEP 440 Python versioning for Git repos and submodules."
    )


class TestMain:
    """Integration test suite for the main entry point function."""

    @pytest.mark.sanity
    def test_signature(self) -> None:
        """Validate the signature of the main function."""
        signature = inspect.signature(main)
        assert not signature.parameters
        assert signature.return_annotation == "None"

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "cli_args",
        [
            ["--package-name", "test_pkg"],
            ["--help"],
        ],
    )
    def test_invocation(
        self, cli_args: list[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Validate the main function invokes the app."""
        monkeypatch.setattr("sys.argv", ["gitversioned"] + cli_args)
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0


class TestRunCli:
    """Integration test suite for the run_cli command."""

    @pytest.mark.sanity
    def test_signature(self) -> None:
        """Validate the signature of the run_cli function."""
        signature = inspect.signature(run_cli)
        assert "output" in signature.parameters
        assert signature.return_annotation is inspect.Signature.empty

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("kwargs", "commit_messages", "tags", "expected_substring"),
        [
            (
                {"pattern_release": "template", "package_name": "test_pkg"},
                ["Initial commit"],
                [],
                "0.1.0",
            ),
            (
                {
                    "pattern_release": "template",
                    "release_branch_pattern": "main",
                    "package_name": "test_pkg",
                },
                ["Initial commit"],
                [],
                "0.1.0",
            ),
            (
                {"pattern_release": "template", "package_name": "test_pkg"},
                ["Initial commit"],
                ["v1.0.0"],
                "1.0.0",
            ),
            (
                {"version_type": "release", "package_name": "test_pkg"},
                ["Initial commit"],
                ["v1.0.0"],
                "1.0.0",
            ),
        ],
    )
    def test_invocation(
        self,
        temp_git_repo: GitRepoHelper,
        kwargs: dict[str, Any],
        commit_messages: list[str],
        tags: list[str],
        expected_substring: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Validate the CLI execution logic runs end-to-end properly."""
        for message in commit_messages:
            temp_git_repo.commit(message)
        for tag_name in tags:
            temp_git_repo.tag(tag_name)

        monkeypatch.chdir(temp_git_repo.path)
        kwargs["project_root"] = temp_git_repo.path
        if "src_root" not in kwargs:
            kwargs["src_root"] = temp_git_repo.path

        # run_cli should succeed
        run_cli(**kwargs)

        # In integration, we know that gitversioned writes to version.py by default
        version_file = temp_git_repo.path / "version.py"
        assert version_file.exists()
        content = version_file.read_text()
        assert expected_substring in content

    @pytest.mark.regression
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"version_type": "invalid"},
        ],
    )
    def test_invalid(
        self,
        temp_git_repo: GitRepoHelper,
        kwargs: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Validate the CLI properly exits on invalid settings or errors."""
        monkeypatch.chdir(temp_git_repo.path)
        kwargs["project_root"] = temp_git_repo.path
        with pytest.raises(SystemExit) as exc_info:
            run_cli(**kwargs)

        assert exc_info.value.code == 1
