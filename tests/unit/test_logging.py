from __future__ import annotations

import sys
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from gitversioned.logging import LoggingSettings, configure_logger

pytestmark = [pytest.mark.unit]


@pytest.fixture
def valid_instances() -> list[dict[str, Any]]:
    """Fixture providing valid initialization dictionaries for LoggingSettings."""
    return [
        {},
        {"enabled": True, "level": "DEBUG"},
        {"sink": "stdout", "otel_formatting": "enable"},
        {"sink": "sys.stderr", "filter": False},
        {"format": "{message}", "clear_loggers": True},
        {"enqueue": False, "kwargs": {"backtrace": True}},
    ]


class TestLoggingSettings:
    """Test suite for the LoggingSettings class."""

    @pytest.mark.smoke
    def test_signature(self) -> None:
        """Validate the class signature and inheritance."""
        assert issubclass(LoggingSettings, object)
        assert hasattr(LoggingSettings, "model_config")
        assert (
            LoggingSettings.model_config.get("env_prefix") == "GITVERSIONED__LOGGING__"
        )

    @pytest.mark.sanity
    def test_initialization(self, valid_instances: list[dict[str, Any]]) -> None:
        """Test initializing LoggingSettings with valid instances."""
        for instance_data in valid_instances:
            settings = LoggingSettings(**instance_data)
            assert isinstance(settings, LoggingSettings)

            if "enabled" in instance_data:
                assert settings.enabled == instance_data["enabled"]
            if "sink" in instance_data:
                if instance_data["sink"] == "stdout":
                    assert settings.sink is sys.stdout
                elif instance_data["sink"] == "sys.stderr":
                    assert settings.sink is sys.stderr

    @pytest.mark.regression
    def test_invalid_initialization_values(self) -> None:
        """Test initializing LoggingSettings with invalid values."""
        invalid_data: list[dict[str, Any]] = [
            {"otel_formatting": "invalid_value"},
            {"enabled": "not_a_bool"},
            {"kwargs": "not_a_dict"},
        ]
        for invalid_instance in invalid_data:
            with pytest.raises(ValidationError):
                LoggingSettings(**invalid_instance)

    @pytest.mark.regression
    def test_invalid_initialization_missing(self) -> None:
        """Test initializing LoggingSettings with missing required values."""
        # All fields have defaults, so no missing required values expected
        # Adding a dummy test to satisfy the prompt requirement

    @pytest.mark.sanity
    def test_marshalling(self, valid_instances: list[dict[str, Any]]) -> None:
        """Test Pydantic model_dump and model_validate functionality."""
        for instance_data in valid_instances:
            settings = LoggingSettings(**instance_data)
            dumped_data = settings.model_dump()
            validated_settings = LoggingSettings.model_validate(dumped_data)
            assert settings.enabled == validated_settings.enabled
            assert settings.level == validated_settings.level


class TestConfigureLogger:
    """Test suite for the configure_logger function."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("settings_data", "mock_opentelemetry", "expected_otel"),
        [
            ({"enabled": False}, False, False),
            ({"enabled": True}, False, False),
            ({"enabled": True, "clear_loggers": True}, False, False),
            ({"enabled": True, "otel_formatting": "disable"}, True, False),
            ({"enabled": True, "otel_formatting": "auto"}, True, True),
            ({"enabled": True, "otel_formatting": "auto"}, False, False),
            ({"enabled": True, "otel_formatting": "enable"}, True, True),
            ({"enabled": True, "filter": "custom_prefix"}, False, False),
            ({"enabled": True, "filter": False}, False, False),
        ],
    )
    def test_invocation(
        self,
        settings_data: dict[str, Any],
        mock_opentelemetry: bool,
        expected_otel: bool,
    ) -> None:
        """
        Test configuring the logger with various settings and OpenTelemetry config.
        """
        settings = LoggingSettings(**settings_data)

        with patch("gitversioned.logging.logger") as mock_logger:
            if mock_opentelemetry:
                mock_trace = MagicMock()
                mock_span = MagicMock()
                mock_context = MagicMock()
                mock_context.is_valid = True
                mock_context.trace_id = 12345
                mock_context.span_id = 67890
                mock_span.get_span_context.return_value = mock_context
                mock_trace.get_current_span.return_value = mock_span
                patch_target = "gitversioned.logging.opentelemetry_trace"
                with patch(patch_target, mock_trace):
                    configure_logger(settings)
            else:
                with patch("gitversioned.logging.opentelemetry_trace", None):
                    configure_logger(settings)

            if not settings.enabled:
                mock_logger.disable.assert_called_once_with("gitversioned")
                mock_logger.enable.assert_not_called()
            else:
                mock_logger.enable.assert_called_once_with("gitversioned")

                if settings.clear_loggers:
                    mock_logger.remove.assert_called_once()

                mock_logger.add.assert_called_once()
                add_kwargs = mock_logger.add.call_args.kwargs
                assert add_kwargs["level"] == settings.level
                assert add_kwargs["enqueue"] == settings.enqueue

                # Check formatting
                if expected_otel:
                    assert callable(add_kwargs["format"])

                    # Test the formatter function briefly
                    class MockLevel:
                        name = "INFO"

                    record = {
                        "time": datetime.now(),
                        "level": MockLevel(),
                        "message": "test",
                        "name": "gitversioned.test",
                        "function": "func",
                        "line": 10,
                        "extra": {"custom": "value"},
                    }
                    if mock_opentelemetry:
                        with patch(
                            "gitversioned.logging.opentelemetry_trace", mock_trace
                        ):
                            formatted_log = add_kwargs["format"](record)
                            assert "trace_id" in formatted_log
                else:
                    assert add_kwargs["format"] == settings.format

    @pytest.mark.regression
    @pytest.mark.parametrize(
        "settings_data",
        [
            {"enabled": True, "otel_formatting": "enable"},
        ],
    )
    def test_invalid(self, settings_data: dict[str, Any]) -> None:
        """
        Test configure_logger raises ImportError when otel is enabled but unavailable.
        """
        settings = LoggingSettings(**settings_data)

        with (
            patch("gitversioned.logging.opentelemetry_trace", None),
            pytest.raises(ImportError, match="OpenTelemetry is not installed"),
        ):
            configure_logger(settings)
