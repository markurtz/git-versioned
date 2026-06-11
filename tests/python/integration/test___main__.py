from __future__ import annotations

import inspect
import json
import os as os_mod
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from gitversioned.__main__ import (
    _cli_execution_context,
    _parse_cli_args,
    app,
    calculate,
    format_cmd,
    main,
    write,
)
from tests.conftest import GitRepoHelper

# Module level constants to avoid magic strings and numbers
TEST_PACKAGE_NAME = "test_pkg"
DEFAULT_VERSION = "0.1.0"
INITIAL_COMMIT_MSG = "Initial commit"
VERSION_SHORT_FLAG = "-v"
VERSION_LONG_FLAG = "--version"
HELP_LONG_FLAG = "--help"
CALCULATE_COMMAND = "calculate"
FORMAT_COMMAND = "format"
WRITE_COMMAND = "write"


@pytest.mark.smoke
def test_app() -> None:
    """Validate that the typer app is properly initialized with correct description."""
    assert isinstance(app, typer.Typer)
    assert app.info.help == (
        "Opinionated PEP 440 Python versioning for Git repos and submodules."
    )


class TestCLIEntrypoint:
    """Integration test suite for global options and entrypoint routing."""

    @pytest.mark.smoke
    def test_cli_version(self) -> None:
        """Validate running the CLI with --version flag."""
        runner = CliRunner()
        result = runner.invoke(app, [VERSION_LONG_FLAG])
        assert result.exit_code == 0
        assert "gitversioned v" in result.stdout

    @pytest.mark.smoke
    def test_cli_version_short(self) -> None:
        """Validate running the CLI with -v flag."""
        runner = CliRunner()
        result = runner.invoke(app, [VERSION_SHORT_FLAG])
        assert result.exit_code == 0
        assert "gitversioned v" in result.stdout

    @pytest.mark.sanity
    def test_cli_help(self) -> None:
        """Validate running the CLI with --help flag."""
        runner = CliRunner()
        result = runner.invoke(app, [HELP_LONG_FLAG])
        assert result.exit_code == 0
        assert "Opinionated PEP 440 Python versioning" in result.stdout

    @pytest.mark.regression
    def test_cli_invalid_arg(self) -> None:
        """Validate running the CLI with an invalid argument."""
        runner = CliRunner()
        result = runner.invoke(app, ["--invalid-argument-option"])
        assert result.exit_code != 0

    @pytest.mark.smoke
    def test_cli_subprocess_run(self) -> None:
        """Validate running python -m gitversioned via subprocess."""
        env_vars = os_mod.environ.copy()
        env_vars["PYTHONPATH"] = "src"
        result = subprocess.run(
            [sys.executable, "-m", "gitversioned", VERSION_LONG_FLAG],
            capture_output=True,
            text=True,
            env=env_vars,
            check=False,
        )
        assert result.returncode == 0
        assert "gitversioned v" in result.stdout


class TestMain:
    """Integration test suite for the main entry point function."""

    @pytest.mark.sanity
    def test_signature(self) -> None:
        """Validate the signature of the main function."""
        sig = inspect.signature(main)
        assert not sig.parameters
        assert sig.return_annotation == "None"

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "cli_args",
        [
            [CALCULATE_COMMAND, "--package-name", TEST_PACKAGE_NAME],
            [HELP_LONG_FLAG],
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

    @pytest.mark.sanity
    def test_default_subcommand(
        self,
        monkeypatch: pytest.MonkeyPatch,
        temp_git_repo: GitRepoHelper,
    ) -> None:
        """Validate CLI prints help and exits when no arguments are provided."""
        temp_git_repo.commit(INITIAL_COMMIT_MSG)
        monkeypatch.chdir(temp_git_repo.path)
        monkeypatch.setattr("sys.argv", ["gitversioned"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0


class TestSubcommandsIntegration:
    """Integration tests for CLI subcommands, overrides, and errors."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("state", "args_list", "expected_version"),
        [
            ("clean", ["--auto-increment", "none"], "0.1.0"),
            ("tagged", ["--auto-increment", "none"], "1.0.0"),
            (
                "tagged_plus_commit",
                ["--version-type", "dev", "--auto-increment", "none"],
                "1.0.0.dev",
            ),
            (
                "tagged",
                ["--explicit-version", "2.3.4", "--auto-increment", "none"],
                "2.3.4",
            ),
            # Test default auto-increment behavior
            ("clean", [], "0.1.1.dev"),
            ("tagged_plus_commit", ["--version-type", "dev"], "1.0.1.dev"),
        ],
    )
    def test_calculate_happy(
        self,
        temp_git_repo: GitRepoHelper,
        monkeypatch: pytest.MonkeyPatch,
        state: str,
        args_list: list[str],
        expected_version: str,
    ) -> None:
        """Validate calculate subcommand stdout across repo states."""
        helper = temp_git_repo.setup_state(state)
        monkeypatch.chdir(helper.path)
        runner = CliRunner()
        cmd_args = [
            CALCULATE_COMMAND,
            "--project-root",
            str(helper.path),
            "--src-root",
            str(helper.path),
        ] + args_list
        result = runner.invoke(app, cmd_args)
        assert result.exit_code == 0
        assert expected_version in result.stdout

    @pytest.mark.smoke
    def test_format_happy(
        self,
        temp_git_repo: GitRepoHelper,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Validate format subcommand outputs correct template strings."""
        helper = temp_git_repo.setup_state("tagged")
        monkeypatch.chdir(helper.path)
        runner = CliRunner()
        strategy = {
            "release": {
                "type": "template_str",
                "content": "FORMATTED_VERSION={version}",
            }
        }
        cmd_args = [
            FORMAT_COMMAND,
            "--project-root",
            str(helper.path),
            "--src-root",
            str(helper.path),
            "--version-type",
            "release",
            "--output-strategies",
            json.dumps(strategy),
        ]
        result = runner.invoke(app, cmd_args)
        assert result.exit_code == 0
        assert result.stdout == "FORMATTED_VERSION=1.0.0"

    @pytest.mark.smoke
    def test_write_template_str(
        self,
        temp_git_repo: GitRepoHelper,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Validate write subcommand writes correct template string to output file."""
        helper = temp_git_repo.setup_state("tagged")
        monkeypatch.chdir(helper.path)
        runner = CliRunner()
        strategy = {
            "release": {
                "type": "template_str",
                "content": "__version__ = '{version}'",
            }
        }
        output_file = "test_version_file.py"
        cmd_args = [
            WRITE_COMMAND,
            "--project-root",
            str(helper.path),
            "--src-root",
            str(helper.path),
            "--output",
            output_file,
            "--version-type",
            "release",
            "--output-strategies",
            json.dumps(strategy),
        ]
        result = runner.invoke(app, cmd_args)
        assert result.exit_code == 0
        expected_path = helper.path / output_file
        assert f"Version successfully written to {expected_path}" in result.stdout
        assert expected_path.exists()
        assert expected_path.read_text(encoding="utf-8") == "__version__ = '1.0.0'"

    @pytest.mark.regression
    def test_write_regex_cargo(
        self,
        temp_git_repo: GitRepoHelper,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Validate write subcommand with regex replacement strategy on Cargo.toml."""
        helper = temp_git_repo.setup_state("tagged")
        cargo_content = '[package]\nname = "test_cargo"\nversion = "0.0.0"\n'
        cargo_file = helper.path / "Cargo.toml"
        cargo_file.write_text(cargo_content, encoding="utf-8")

        monkeypatch.chdir(helper.path)
        runner = CliRunner()
        strategy = {
            "type": "regex",
            "pattern": (
                r"(?s)(\[(?:workspace\.)?package\].*?^version\s*=\s*)"
                r"([\"'])(?P<version>.*?)\2"
            ),
        }
        cmd_args = [
            WRITE_COMMAND,
            "--project-root",
            str(helper.path),
            "--src-root",
            str(helper.path),
            "--output",
            "Cargo.toml",
            "--version-type",
            "release",
            "--output-strategies",
            json.dumps(strategy),
        ]
        result = runner.invoke(app, cmd_args)
        assert result.exit_code == 0
        assert cargo_file.exists()
        updated_content = cargo_file.read_text(encoding="utf-8")
        assert 'version = "1.0.0"' in updated_content

    @pytest.mark.regression
    def test_invalid_arguments(
        self,
        temp_git_repo: GitRepoHelper,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Validate that invalid subcommand arguments cause non-zero exit code."""
        helper = temp_git_repo.setup_state("clean")
        monkeypatch.chdir(helper.path)
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                CALCULATE_COMMAND,
                "--project-root",
                str(helper.path),
                "--version-type",
                "invalid_version_type_here",
            ],
        )
        assert result.exit_code != 0

    @pytest.mark.regression
    def test_cli_error_handling(self, caplog: pytest.LogCaptureFixture) -> None:
        """Validate unexpected errors are caught, logged, and exit with code 1."""
        with patch(
            "gitversioned.__main__.resolve_version",
            side_effect=RuntimeError("Unexpected test failure"),
        ):
            runner = CliRunner()
            result = runner.invoke(app, [CALCULATE_COMMAND])
            assert result.exit_code == 1
            assert any(
                "Failed to execute gitversioned CLI calculate" in record.message
                for record in caplog.records
            )

    @pytest.mark.regression
    def test_parse_cli_args_deserialization(self, tmp_path: Path) -> None:
        """Validate that list/dict CLI arguments are deserialized from JSON strings."""
        # Valid JSON list for source_type
        args_valid_list = {
            "source_type": '["tag", "branch"]',
            "project_root": str(tmp_path),
        }
        settings_list = _parse_cli_args(args_valid_list)
        assert settings_list.source_type == ["tag", "branch"]

        # Valid JSON dict for output_strategies
        strategy_json = (
            '{"release": {"type": "template_str", "content": "VER={version}"}}'
        )
        args_valid_dict = {
            "output_strategies": strategy_json,
            "project_root": str(tmp_path),
        }
        settings_dict = _parse_cli_args(args_valid_dict)
        assert isinstance(settings_dict.output_strategies, dict)
        assert settings_dict.output_strategies["release"].type == "template_str"

        # Malformed JSON dictionary starting/ending with brace should be caught,
        # suppressed, and kept as a raw string (which is standard string type).
        args_malformed = {
            "version": "{malformed_json}",
            "project_root": str(tmp_path),
        }
        settings_malformed = _parse_cli_args(args_malformed)
        assert settings_malformed.version == "{malformed_json}"

    @pytest.mark.sanity
    def test_cli_signature_construction(self) -> None:
        """Validate that CLI signatures are dynamically constructed from settings."""
        sig_calc = inspect.signature(calculate)
        assert "package_name" in sig_calc.parameters
        assert "output" not in sig_calc.parameters
        assert "output_strategies" not in sig_calc.parameters

        sig_form = inspect.signature(format_cmd)
        assert "package_name" in sig_form.parameters
        assert "output" not in sig_form.parameters
        assert "output_strategies" in sig_form.parameters

        sig_write = inspect.signature(write)
        assert "package_name" in sig_write.parameters
        assert "output" in sig_write.parameters
        assert "output_strategies" in sig_write.parameters

    @pytest.mark.regression
    def test_cli_exception_propagation(self) -> None:
        """Validate typer.Exit and typer.Abort propagate directly."""
        with (
            pytest.raises(typer.Exit) as exc_info,
            _cli_execution_context("test", {}),
        ):
            raise typer.Exit(code=42)
        assert exc_info.value.exit_code == 42

        with (
            pytest.raises(typer.Abort),
            _cli_execution_context("test", {}),
        ):
            raise typer.Abort
