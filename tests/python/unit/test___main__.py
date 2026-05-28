from __future__ import annotations

import inspect
import runpy
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import typer

from gitversioned import __version__
from gitversioned.__main__ import app, calculate, format_cmd, main, main_callback, write


@pytest.mark.smoke
def test_app() -> None:
    """Validate the `app` param type, value, and registered subcommands."""
    assert isinstance(app, typer.Typer)
    assert (
        app.info.help
        == "Opinionated PEP 440 Python versioning for Git repos and submodules."
    )
    callbacks = {cmd.callback for cmd in app.registered_commands}
    assert callbacks == {calculate, format_cmd, write}


class TestMain:
    """Test suite for the main entry point and global callback."""

    @pytest.mark.sanity
    def test_signature(self) -> None:
        """Validate the signature of the main function."""
        signature = inspect.signature(main)
        assert not signature.parameters
        assert signature.return_annotation == "None"

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "initial_args",
        [
            [],
            ["calculate"],
            ["--version"],
            ["-v"],
            ["--help"],
        ],
    )
    def test_invocation(
        self,
        initial_args: list[str],
    ) -> None:
        """Validate the main function executes app."""
        with (
            patch("sys.argv", ["gitversioned"] + initial_args),
            patch("gitversioned.__main__.app") as mock_app,
        ):
            main()
            mock_app.assert_called_once_with()
            assert sys.argv[1:] == initial_args


class TestMainCallback:
    """Unit tests for the main CLI callback function."""

    @pytest.mark.sanity
    def test_signature(self) -> None:
        """Validate main_callback signature."""
        signature = inspect.signature(main_callback)
        assert "ctx" in signature.parameters
        assert "version" in signature.parameters

    @pytest.mark.smoke
    def test_invocation_smoke(self) -> None:
        """Validate version flag outputs version and exits."""
        mock_ctx = MagicMock()
        with patch("typer.echo") as mock_echo:
            with pytest.raises(typer.Exit):
                main_callback(ctx=mock_ctx, version=True)
            mock_echo.assert_called_once_with(f"gitversioned v{__version__}")

    @pytest.mark.sanity
    def test_invocation_sanity(self) -> None:
        """Validate invoked_subcommand is None displays help and exits."""
        mock_ctx = MagicMock()
        mock_ctx.invoked_subcommand = None
        mock_ctx.get_help.return_value = "Mock help text"
        with patch("typer.echo") as mock_echo:
            with pytest.raises(typer.Exit):
                main_callback(ctx=mock_ctx, version=False)
            mock_ctx.get_help.assert_called_once()
            mock_echo.assert_called_once_with("Mock help text")

    @pytest.mark.regression
    def test_invocation_regression(self) -> None:
        """Validate invoked_subcommand is set runs cleanly without exit."""
        mock_ctx = MagicMock()
        mock_ctx.invoked_subcommand = "calculate"
        with patch("typer.echo") as mock_echo:
            main_callback(ctx=mock_ctx, version=False)
            mock_echo.assert_not_called()


class TestCalculate:
    """Unit tests for the calculate subcommand."""

    @pytest.mark.sanity
    def test_signature(self) -> None:
        """Validate calculate signature excludes output and strategies."""
        signature = inspect.signature(calculate)
        assert "project_root" in signature.parameters
        assert "output" not in signature.parameters
        assert "output_strategies" not in signature.parameters
        assert signature.parameters["version"].annotation is not dict
        assert (
            "--explicit-version" in signature.parameters["version"].default.param_decls
        )

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("kwargs_payload", "expected_called_args"),
        [
            (
                {"package_name": "test_pkg", "project_root": "/mock/root"},
                {"package_name": "test_pkg", "project_root": "/mock/root"},
            ),
            (
                {
                    "package_name": "test_pkg",
                    "output_strategies": '["a", "b"]',
                    "project_root": "/mock/root",
                },
                {
                    "package_name": "test_pkg",
                    "output_strategies": ["a", "b"],
                    "project_root": "/mock/root",
                },
            ),
            (
                {
                    "package_name": "test_pkg",
                    "regex_version": '{"a": "b"}',
                    "project_root": "/mock/root",
                },
                {
                    "package_name": "test_pkg",
                    "regex_version": {"a": "b"},
                    "project_root": "/mock/root",
                },
            ),
            (
                {
                    "package_name": "test_pkg",
                    "regex_version": "{invalid_json",
                    "project_root": "/mock/root",
                },
                {
                    "package_name": "test_pkg",
                    "regex_version": "{invalid_json",
                    "project_root": "/mock/root",
                },
            ),
        ],
    )
    def test_invocation(
        self,
        kwargs_payload: dict[str, Any],
        expected_called_args: dict[str, Any],
    ) -> None:
        """Validate standard calculate call path parses JSON and prints version."""
        with (
            patch("gitversioned.__main__.configure_logger") as mock_logger,
            patch("gitversioned.__main__.Settings") as mock_settings,
            patch("gitversioned.__main__.GitRepository") as mock_repo,
            patch("gitversioned.__main__.BuildEnvironment") as mock_env,
            patch("gitversioned.__main__.resolve_version") as mock_resolve,
            patch("typer.echo") as mock_echo,
        ):
            mock_settings_instance = MagicMock()
            mock_settings_instance.project_root = "/mock/root"
            mock_settings.return_value = mock_settings_instance
            mock_resolve.return_value = ("1.2.3", "release", "ref")

            calculate(**kwargs_payload)

            mock_logger.assert_called_once()
            mock_settings.assert_called_once_with(**expected_called_args)
            mock_resolve.assert_called_once_with(
                settings=mock_settings_instance,
                repository=mock_repo.return_value,
                environment=mock_env.return_value,
            )
            mock_echo.assert_called_once_with("1.2.3")

    @pytest.mark.regression
    @pytest.mark.parametrize(
        ("raised_exception", "expected_exit"),
        [
            (typer.Exit(0), typer.Exit),
            (typer.Abort(), typer.Abort),
            (ValueError("Generic failure"), SystemExit),
        ],
    )
    def test_invalid(
        self,
        raised_exception: Exception,
        expected_exit: type[Exception],
    ) -> None:
        """Validate error handling behavior inside calculate context."""
        with (
            patch("gitversioned.__main__.configure_logger"),
            patch("gitversioned.__main__.Settings") as mock_settings,
            patch("gitversioned.__main__.GitRepository"),
            patch("gitversioned.__main__.BuildEnvironment"),
            patch("gitversioned.__main__.resolve_version") as mock_resolve,
        ):
            mock_settings_instance = MagicMock()
            mock_settings_instance.project_root = "/mock/root"
            mock_settings.return_value = mock_settings_instance
            mock_resolve.side_effect = raised_exception

            with pytest.raises(expected_exit) as exc_info:
                calculate(package_name="test_pkg")
            if expected_exit is SystemExit:
                assert exc_info.value.code == 1

    @pytest.mark.regression
    def test_logging_sink_routing(self) -> None:
        """Validate calculate routes stdout log sink to stderr."""
        with (
            patch("gitversioned.__main__.configure_logger") as mock_logger,
            patch("gitversioned.__main__.Settings") as mock_settings,
            patch("gitversioned.__main__.GitRepository"),
            patch("gitversioned.__main__.BuildEnvironment"),
            patch(
                "gitversioned.__main__.resolve_version",
                return_value=("1.0.0", "rel", "ref"),
            ),
            patch("typer.echo"),
        ):
            mock_settings_instance = MagicMock()
            mock_settings_instance.project_root = "/mock/root"
            mock_settings.return_value = mock_settings_instance

            with patch(
                "gitversioned.__main__.LoggingSettings"
            ) as mock_logging_settings:
                mock_log_settings_instance = MagicMock()
                mock_log_settings_instance.sink = sys.stdout
                mock_logging_settings.return_value = mock_log_settings_instance

                calculate()

                assert mock_log_settings_instance.sink is sys.stderr
                mock_logger.assert_called_once_with(mock_log_settings_instance)


class TestFormatCmd:
    """Unit tests for the format subcommand."""

    @pytest.mark.sanity
    def test_signature(self) -> None:
        """Validate format dynamic signature excludes output but allows strategies."""
        signature = inspect.signature(format_cmd)
        assert "project_root" in signature.parameters
        assert "output_strategies" in signature.parameters
        assert "output" not in signature.parameters

    @pytest.mark.smoke
    def test_invocation(self) -> None:
        """Validate standard format call path prints template result."""
        with (
            patch("gitversioned.__main__.configure_logger") as mock_logger,
            patch("gitversioned.__main__.Settings") as mock_settings,
            patch("gitversioned.__main__.GitRepository") as mock_repo,
            patch("gitversioned.__main__.BuildEnvironment") as mock_env,
            patch("gitversioned.__main__.resolve_version_output") as mock_resolve,
            patch("typer.echo") as mock_echo,
        ):
            mock_settings_instance = MagicMock()
            mock_settings_instance.project_root = "/mock/root"
            mock_settings.return_value = mock_settings_instance
            mock_resolve.return_value = (
                "formatted-content",
                "1.2.3",
                "release",
                "ref",
            )

            format_cmd(package_name="test_pkg")

            mock_logger.assert_called_once()
            mock_settings.assert_called_once_with(package_name="test_pkg")
            mock_resolve.assert_called_once_with(
                settings=mock_settings_instance,
                repository=mock_repo.return_value,
                environment=mock_env.return_value,
            )
            mock_echo.assert_called_once_with("formatted-content", nl=False)

    @pytest.mark.regression
    @pytest.mark.parametrize(
        ("raised_exception", "expected_exit"),
        [
            (typer.Exit(0), typer.Exit),
            (typer.Abort(), typer.Abort),
            (ValueError("Generic failure"), SystemExit),
        ],
    )
    def test_invalid(
        self,
        raised_exception: Exception,
        expected_exit: type[Exception],
    ) -> None:
        """Validate error handling behavior inside format context."""
        with (
            patch("gitversioned.__main__.configure_logger"),
            patch("gitversioned.__main__.Settings") as mock_settings,
            patch("gitversioned.__main__.GitRepository"),
            patch("gitversioned.__main__.BuildEnvironment"),
            patch("gitversioned.__main__.resolve_version_output") as mock_resolve,
        ):
            mock_settings_instance = MagicMock()
            mock_settings_instance.project_root = "/mock/root"
            mock_settings.return_value = mock_settings_instance
            mock_resolve.side_effect = raised_exception

            with pytest.raises(expected_exit) as exc_info:
                format_cmd(package_name="test_pkg")
            if expected_exit is SystemExit:
                assert exc_info.value.code == 1


class TestWrite:
    """Unit tests for the write subcommand."""

    @pytest.mark.sanity
    def test_signature(self) -> None:
        """Validate write dynamic signature allows output and strategies."""
        signature = inspect.signature(write)
        assert "project_root" in signature.parameters
        assert "output" in signature.parameters
        assert "output_strategies" in signature.parameters

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "returned_output_path",
        [
            "/mock/root/version.py",
            None,
        ],
    )
    def test_invocation(self, returned_output_path: str | None) -> None:
        """Validate standard write call path writes file.

        Also prints location if present.
        """
        with (
            patch("gitversioned.__main__.configure_logger") as mock_logger,
            patch("gitversioned.__main__.Settings") as mock_settings,
            patch("gitversioned.__main__.GitRepository") as mock_repo,
            patch("gitversioned.__main__.BuildEnvironment") as mock_env,
            patch(
                "gitversioned.__main__.resolve_version_output_to_stream"
            ) as mock_resolve,
            patch("typer.echo") as mock_echo,
        ):
            mock_settings_instance = MagicMock()
            mock_settings_instance.project_root = "/mock/root"
            mock_settings.return_value = mock_settings_instance
            mock_resolve.return_value = (
                returned_output_path,
                "content",
                "1.2.3",
                "release",
                "ref",
            )

            write(package_name="test_pkg")

            mock_logger.assert_called_once()
            mock_settings.assert_called_once_with(package_name="test_pkg")
            mock_resolve.assert_called_once_with(
                settings=mock_settings_instance,
                repository=mock_repo.return_value,
                environment=mock_env.return_value,
            )
            if returned_output_path:
                mock_echo.assert_called_once_with(
                    f"Version successfully written to {returned_output_path}"
                )
            else:
                mock_echo.assert_not_called()

    @pytest.mark.regression
    @pytest.mark.parametrize(
        ("raised_exception", "expected_exit"),
        [
            (typer.Exit(0), typer.Exit),
            (typer.Abort(), typer.Abort),
            (ValueError("Generic failure"), SystemExit),
        ],
    )
    def test_invalid(
        self,
        raised_exception: Exception,
        expected_exit: type[Exception],
    ) -> None:
        """Validate error handling behavior inside write context."""
        with (
            patch("gitversioned.__main__.configure_logger"),
            patch("gitversioned.__main__.Settings") as mock_settings,
            patch("gitversioned.__main__.GitRepository"),
            patch("gitversioned.__main__.BuildEnvironment"),
            patch(
                "gitversioned.__main__.resolve_version_output_to_stream"
            ) as mock_resolve,
        ):
            mock_settings_instance = MagicMock()
            mock_settings_instance.project_root = "/mock/root"
            mock_settings.return_value = mock_settings_instance
            mock_resolve.side_effect = raised_exception

            with pytest.raises(expected_exit) as exc_info:
                write(package_name="test_pkg")
            if expected_exit is SystemExit:
                assert exc_info.value.code == 1


class TestRunAsMain:
    """Test suite for direct execution of the __main__ module."""

    @pytest.mark.regression
    def test_run_as_main(self) -> None:
        """Validate the execution flow when the module is run as __main__."""
        with (
            patch("typer.Typer") as mock_typer_class,
            patch("gitversioned.__main__.__name__", "__main__"),
        ):
            runpy.run_module("gitversioned.__main__", run_name="__main__")
            mock_typer_class.assert_called()
            mock_typer_class.return_value.assert_called()
