"""
Unit tests for the gitversioned CLI entry point.
"""

from __future__ import annotations

import inspect
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import typer

from gitversioned.__main__ import app, main, run_cli


@pytest.mark.smoke
def test_app() -> None:
    """Validate the `app` param type, value, and signature."""
    assert isinstance(app, typer.Typer)
    assert (
        app.info.help
        == "Opinionated PEP 440 Python versioning for Git repos and submodules."
    )
    assert len(app.registered_commands) == 1
    assert app.registered_commands[0].callback == run_cli


class TestMain:
    """Test suite for the main entry point function."""

    @pytest.mark.sanity
    def test_signature(self) -> None:
        """Validate the signature of the main function."""
        signature = inspect.signature(main)
        assert not signature.parameters
        assert signature.return_annotation == "None"

    @pytest.mark.smoke
    @pytest.mark.parametrize("mock_return", [None])
    def test_invocation(self, mock_return: Any) -> None:
        """Validate the main function invokes the app."""
        with patch("gitversioned.__main__.app") as mock_app:
            mock_app.return_value = mock_return
            main()
            mock_app.assert_called_once_with()


class TestRunCli:
    """Test suite for the run_cli command."""

    @pytest.mark.sanity
    def test_signature(self) -> None:
        """Validate the signature of the run_cli function."""
        signature = inspect.signature(run_cli)
        assert "output" in signature.parameters
        assert signature.return_annotation is inspect.Signature.empty

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("kwargs", "expected_version", "expected_path"),
        [
            ({"pattern_release": "cargo"}, "1.0.0", "/path/to/Cargo.toml"),
            ({}, "1.0.0", None),
        ],
    )
    def test_invocation(
        self,
        kwargs: dict[str, Any],
        expected_version: str,
        expected_path: str | None,
    ) -> None:
        """Validate the CLI execution logic under normal conditions."""
        with (
            patch("gitversioned.__main__.configure_logger") as mock_logger,
            patch("gitversioned.__main__.Settings") as mock_settings,
            patch("gitversioned.__main__.GitRepository") as mock_repo,
            patch("gitversioned.__main__.BuildEnvironment") as mock_env,
            patch("gitversioned.__main__.resolve_and_generate_version") as mock_resolve,
        ):
            mock_settings_instance = MagicMock()
            mock_settings_instance.project_root = "/mock/root"
            mock_settings.return_value = mock_settings_instance
            mock_resolve.return_value = (expected_version, expected_path)

            run_cli(**kwargs)

            mock_logger.assert_called_once()
            mock_settings.assert_called_once_with(**kwargs)
            mock_repo.assert_called_once_with("/mock/root")
            mock_env.assert_called_once_with(project_root="/mock/root")
            mock_resolve.assert_called_once_with(
                settings=mock_settings_instance,
                repository=mock_repo.return_value,
                environment=mock_env.return_value,
            )

    @pytest.mark.regression
    @pytest.mark.parametrize(
        "error_instance",
        [
            ValueError("Invalid configuration provided"),
            RuntimeError("Unexpected Git execution error"),
        ],
    )
    def test_invalid(self, error_instance: Exception) -> None:
        """Validate the CLI properly exits on errors."""
        with (
            patch("gitversioned.__main__.configure_logger"),
            patch("gitversioned.__main__.Settings", side_effect=error_instance),
        ):
            with pytest.raises(SystemExit) as exc_info:
                run_cli(output="invalid")

            assert exc_info.value.code == 1
