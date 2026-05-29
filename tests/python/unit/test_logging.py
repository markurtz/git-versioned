from __future__ import annotations

import sys
from datetime import datetime
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError
from pydantic_settings import BaseSettings

from gitversioned.logging import (
    LoggingSettings,
    _state,
    autolog,
    configure_logger,
    logger,
)


@pytest.fixture(
    params=[
        {},
        {"enabled": True, "level": "DEBUG"},
        {"sink": "stdout", "otel_formatting": "enable"},
        {"sink": "sys.stderr", "filter": False},
        {"sink": "stderr"},
        {"sink": "sys.stdout"},
        {"sink": "logfile.log"},
        {"format": "{message}", "clear_loggers": True},
        {"enqueue": False, "kwargs": {"backtrace": True}},
    ]
)
def valid_instances(request: pytest.FixtureRequest) -> LoggingSettings:
    """Fixture providing instantiated valid variations of LoggingSettings."""
    return LoggingSettings(**request.param)


class TestLoggingSettings:
    """Test suite for the LoggingSettings class."""

    @pytest.mark.smoke
    def test_signature(self) -> None:
        """Validate class signature, inheritance, and attributes."""
        assert issubclass(LoggingSettings, BaseSettings)
        expected_fields = {
            "enabled",
            "clear_loggers",
            "sink",
            "level",
            "otel_formatting",
            "format",
            "filter",
            "enqueue",
            "kwargs",
        }
        assert expected_fields.issubset(LoggingSettings.model_fields.keys())
        assert hasattr(LoggingSettings, "model_config")
        assert (
            LoggingSettings.model_config.get("env_prefix") == "GITVERSIONED__LOGGING__"
        )

    @pytest.mark.sanity
    def test_initialization(self, valid_instances: LoggingSettings) -> None:
        """Test initializing LoggingSettings and verify state mappings."""
        assert isinstance(valid_instances, LoggingSettings)
        sink_val = valid_instances.sink
        if isinstance(sink_val, str):
            assert sink_val not in {"stdout", "sys.stdout", "stderr", "sys.stderr"}
        else:
            assert sink_val in {sys.stdout, sys.stderr}

    @pytest.mark.regression
    @pytest.mark.parametrize(
        "invalid_data",
        [
            {"otel_formatting": "invalid_value"},
            {"enabled": "not_a_bool"},
            {"kwargs": "not_a_dict"},
        ],
    )
    def test_invalid_initialization_values(self, invalid_data: dict[str, Any]) -> None:
        """Test initializing LoggingSettings with invalid values."""
        with pytest.raises(ValidationError):
            LoggingSettings(**invalid_data)

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test initializing LoggingSettings when arguments are missing."""
        monkeypatch.delenv("GITVERSIONED__LOGGING__LEVEL", raising=False)
        settings = LoggingSettings()
        assert settings.enabled is False
        assert settings.clear_loggers is False
        assert settings.sink is sys.stdout
        assert settings.level == "WARNING"
        assert settings.otel_formatting == "auto"
        assert settings.filter is True
        assert settings.enqueue is True
        assert settings.kwargs == {}
        assert isinstance(settings.format, str)
        assert "{message}" in settings.format

    @pytest.mark.sanity
    def test_marshalling(self, valid_instances: LoggingSettings) -> None:
        """Verify Pydantic model_dump and model_validate pipelines."""
        dumped_data = valid_instances.model_dump()
        validated_settings = LoggingSettings.model_validate(dumped_data)
        assert valid_instances.enabled == validated_settings.enabled
        assert valid_instances.level == validated_settings.level
        assert valid_instances.clear_loggers == validated_settings.clear_loggers
        assert valid_instances.otel_formatting == validated_settings.otel_formatting
        assert valid_instances.format == validated_settings.format
        assert valid_instances.enqueue == validated_settings.enqueue

    @pytest.mark.regression
    def test_env_loading(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify GITVERSIONED__LOGGING__ env variables override settings."""
        monkeypatch.setenv("GITVERSIONED__LOGGING__LEVEL", "WARNING")
        monkeypatch.setenv("GITVERSIONED__LOGGING__ENABLED", "true")
        monkeypatch.setenv("GITVERSIONED__LOGGING__CLEAR_LOGGERS", "true")
        settings = LoggingSettings()
        assert settings.level == "WARNING"
        assert settings.enabled is True
        assert settings.clear_loggers is True


class TestConfigureLogger:
    """Test suite for the configure_logger function."""

    @pytest.mark.smoke
    def test_invocation_defaults(self) -> None:
        """Verify configure_logger works with default arguments (None)."""
        with patch("gitversioned.logging.logger") as mock_logger:
            configure_logger(None)
            mock_logger.disable.assert_called_once_with("gitversioned")

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        "settings_dict",
        [
            {"enabled": False},
            {"enabled": True},
            {"enabled": True, "clear_loggers": True},
        ],
    )
    def test_invocation_enabled_disabled(self, settings_dict: dict[str, Any]) -> None:
        """Test configure_logger correctly enables, disables or clears loggers."""
        settings = LoggingSettings(**settings_dict)
        with patch("gitversioned.logging.logger") as mock_logger:
            configure_logger(settings)
            if not settings.enabled:
                mock_logger.disable.assert_called_once_with("gitversioned")
                mock_logger.enable.assert_not_called()
            else:
                mock_logger.enable.assert_called_once_with("gitversioned")
                if settings.clear_loggers:
                    mock_logger.remove.assert_called_once()

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("settings_dict", "expected_match", "expected_non_match"),
        [
            (
                {"enabled": True, "filter": "custom_prefix"},
                "custom_prefix.test",
                "other_scope",
            ),
            (
                {"enabled": True, "filter": ["prefix1", "prefix2"]},
                "prefix1.test",
                "other_scope",
            ),
            (
                {"enabled": True, "filter": ("prefix3", "prefix4")},
                "prefix3.test",
                "other_scope",
            ),
            ({"enabled": True, "filter": False}, None, None),
            (
                {
                    "enabled": True,
                    "filter": lambda record: record["name"] == "gitversioned",
                },
                "gitversioned",
                "other_scope",
            ),
        ],
    )
    def test_invocation_filters(
        self,
        settings_dict: dict[str, Any],
        expected_match: str | None,
        expected_non_match: str | None,
    ) -> None:
        """Test configure_logger correctly configures prefix or custom filters."""
        settings = LoggingSettings(**settings_dict)
        with patch("gitversioned.logging.logger") as mock_logger:
            configure_logger(settings)
            mock_logger.add.assert_called_once()
            add_kwargs = mock_logger.add.call_args.kwargs
            logger_filter = add_kwargs["filter"]

            if expected_match is not None:
                assert callable(logger_filter)
                assert logger_filter({"name": expected_match}) is True
                assert logger_filter({"name": expected_non_match}) is False
                assert logger_filter({"name": None}) is False
            elif settings.filter is False:
                assert logger_filter is None
            elif callable(settings.filter):
                assert logger_filter({"name": "gitversioned"}) is True

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("settings_dict", "mock_otel", "expect_otel"),
        [
            ({"enabled": True, "otel_formatting": "disable"}, True, False),
            ({"enabled": True, "otel_formatting": "auto"}, True, True),
            ({"enabled": True, "otel_formatting": "auto"}, False, False),
            ({"enabled": True, "otel_formatting": "enable"}, True, True),
        ],
    )
    def test_invocation_otel(
        self,
        settings_dict: dict[str, Any],
        mock_otel: bool,
        expect_otel: bool,
    ) -> None:
        """Test configure_logger correctly configures OpenTelemetry formatting."""
        settings = LoggingSettings(**settings_dict)

        with patch("gitversioned.logging.logger") as mock_logger:
            mock_logger.add.return_value = 42
            if mock_otel:
                mock_trace = MagicMock()
                mock_span = MagicMock()
                mock_context = MagicMock()
                mock_context.is_valid = True
                mock_context.trace_id = 12345
                mock_context.span_id = 67890
                mock_context.trace_flags = 1
                mock_span.get_span_context.return_value = mock_context
                mock_trace.get_current_span.return_value = mock_span
                patch_target = "gitversioned.logging.opentelemetry_trace"
                with patch(patch_target, mock_trace):
                    configure_logger(settings)
            else:
                with patch("gitversioned.logging.opentelemetry_trace", None):
                    configure_logger(settings)

            mock_logger.add.assert_called_once()
            add_kwargs = mock_logger.add.call_args.kwargs

            if expect_otel:
                assert callable(add_kwargs["format"])

                class MockLevel:
                    name = "INFO"

                class MockProcess:
                    id = 1234

                record_data: dict[str, Any] = {
                    "time": datetime.now(),
                    "level": MockLevel(),
                    "message": "test message {with} <brackets>",
                    "name": "gitversioned.test",
                    "function": "func",
                    "line": 10,
                    "extra": {"custom_key": "custom_val"},
                    "process": MockProcess(),
                }

                # Verify formatter output formatting with trace details
                if mock_otel:
                    with patch("gitversioned.logging.opentelemetry_trace", mock_trace):
                        formatted_log = add_kwargs["format"](record_data)
                        assert "trace_id" in formatted_log
                        assert "span_id" in formatted_log
                        assert "trace_flags" in formatted_log
                        assert "\\<brackets\\>" in formatted_log
                        assert "{{with}}" in formatted_log

                # Verify formatter output when trace context is invalid
                if mock_otel:
                    mock_context.is_valid = False
                    with patch("gitversioned.logging.opentelemetry_trace", mock_trace):
                        formatted_log = add_kwargs["format"](record_data)
                        assert "trace_id" not in formatted_log

                # Verify formatter output when record contains exception
                class MockExceptionInfo:
                    type = ValueError
                    value = ValueError("error message")
                    traceback = None

                record_data["exception"] = MockExceptionInfo()
                with patch("gitversioned.logging.opentelemetry_trace", mock_trace):
                    formatted_log = add_kwargs["format"](record_data)
                    assert "exception.type" in formatted_log
                    assert "exception.message" in formatted_log
            else:
                assert add_kwargs["format"] == settings.format

    @pytest.mark.regression
    def test_invocation_existing_handler(self) -> None:
        """Verify configure_logger removes the previously registered handler."""
        _state["handler_id"] = 9999
        settings = LoggingSettings(enabled=True)
        with patch("gitversioned.logging.logger") as mock_logger:
            mock_logger.add.return_value = 1234
            configure_logger(settings)
            mock_logger.remove.assert_called_once_with(9999)
            assert _state["handler_id"] == 1234

    @pytest.mark.regression
    def test_invalid(self) -> None:
        """Test configure_logger raises ImportError when OpenTelemetry is missing.

        This occurs when OTEL formatting is enabled but the library is not installed.
        """
        settings = LoggingSettings(enabled=True, otel_formatting="enable")

        with (
            patch("gitversioned.logging.opentelemetry_trace", None),
            pytest.raises(ImportError, match="OpenTelemetry is not installed"),
        ):
            configure_logger(settings)


class TestAutolog:
    """Test suite for the autolog decorator."""

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("use_factory", "exception_level", "should_fail"),
        [
            (False, "ERROR", False),
            (True, "ERROR", False),
            (False, "ERROR", True),
            (True, "ERROR", True),
            (True, None, True),
            (True, "WARNING", True),
        ],
    )
    def test_invocation(
        self,
        use_factory: bool,
        exception_level: str | None,
        should_fail: bool,
    ) -> None:
        """Test autolog decorator's core logging and wrapping functionality."""

        def target_func(first_arg: int, second_arg: str) -> str:
            if should_fail:
                raise ValueError("custom error")
            return f"{first_arg}-{second_arg}"

        if use_factory:
            decorator = autolog(exception_log_level=exception_level)
            wrapped = decorator(target_func)
        else:
            wrapped = autolog(target_func)

        with patch("gitversioned.logging.logger") as mock_logger:
            mock_opt_logger = MagicMock()
            mock_logger.opt.return_value = mock_opt_logger

            if should_fail:
                with pytest.raises(ValueError, match="custom error") as exc_info:
                    wrapped(42, "hello")

                # Verify entry log
                expected_msg = (
                    "Calling function "
                    "'TestAutolog.test_invocation.<locals>.target_func' "
                    "with args=(42, 'hello'), kwargs={}"
                )
                mock_logger.debug.assert_any_call(expected_msg)

                # Verify exception log
                if exception_level is not None or not use_factory:
                    expected_level = exception_level if use_factory else "ERROR"
                    if expected_level == "ERROR":
                        mock_logger.opt.assert_called_once_with(
                            exception=exc_info.value
                        )
                        mock_opt_logger.error.assert_called_once()
                        log_args = mock_opt_logger.error.call_args[0]
                        assert "Exception occurred in function" in log_args[0]
                    else:
                        mock_logger.opt.assert_not_called()
                        mock_logger.log.assert_called_once()
                        log_args = mock_logger.log.call_args[0]
                        assert log_args[0] == expected_level
                        assert "Exception occurred in function" in log_args[1]
                else:
                    mock_logger.opt.assert_not_called()
                    mock_logger.log.assert_not_called()
            else:
                result = wrapped(42, "hello")
                assert result == "42-hello"

                # Verify entry and exit debug logs
                assert mock_logger.debug.call_count == 2
                first_call_args = mock_logger.debug.call_args_list[0][0][0]
                assert "Calling function" in first_call_args
                assert "target_func" in first_call_args
                assert "42" in first_call_args
                assert "hello" in first_call_args

                second_call_args = mock_logger.debug.call_args_list[1][0][0]
                assert "returned" in second_call_args
                assert "42-hello" in second_call_args

    @pytest.mark.sanity
    def test_invalid(self) -> None:
        """Verify invalid autolog usage raising TypeError."""
        with pytest.raises(TypeError):
            cast("Any", autolog)(None, "WARNING")


@pytest.mark.smoke
def test_logger() -> None:
    """Validate that the public logger is configured correctly."""
    assert type(logger).__name__ == "Logger"
    logger.debug("Test public logger validation message")
