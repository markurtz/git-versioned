"""
Configure logging infrastructure and provide utilities for GitVersioned.

This module initializes the global logger with custom configurations such as
log levels, target sinks, and thread-safe queues. It also provides automatic
function execution logging and integrates with OpenTelemetry trace contexts
for structured JSON output.
"""

from __future__ import annotations

import contextlib
import functools
import json
import sys
import traceback
from collections.abc import Callable
from typing import Any, ClassVar, Literal, TypeVar, cast, overload

from loguru import logger
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from gitversioned.compat import opentelemetry_trace

__all__ = ["LoggingSettings", "autolog", "configure_logger", "logger"]

_LOG_ENTRY_FORMAT: str = "Calling function '{name}' with args={args}, kwargs={kwargs}"
_LOG_EXIT_FORMAT: str = "Function '{name}' returned: {result}"
_LOG_EXCEPTION_FORMAT: str = "Exception occurred in function '{name}': {exception}"

_FuncT = TypeVar("_FuncT", bound=Callable[..., Any])

_state: dict[str, int | None] = {"handler_id": None}


class LoggingSettings(BaseSettings):
    """
    Settings for configuring the loguru logging infrastructure.

    This Pydantic settings class loads variables prefixed with
    GITVERSIONED__LOGGING__ to manage log levels, destination sinks, thread
    queues, and OpenTelemetry format options.

    Example:
        >>> from gitversioned.logging import LoggingSettings, configure_logger
        >>> settings = LoggingSettings(level="DEBUG")
        >>> configure_logger(settings)

    model_config : ClassVar[SettingsConfigDict]
        Configuration dictionary dictating environment variable prefixes and
        nested delimiters.
    """

    enabled: bool = Field(
        default=False,
        description="Enables logging output across the gitversioned package.",
    )
    clear_loggers: bool = Field(
        default=False,
        description="Removes all existing active logger sinks prior to configuration.",
    )
    sink: str | Any = Field(
        default=sys.stdout,
        description=(
            "Specifies the output target (e.g. stdout, stderr, or a file path) "
            "for log messages."
        ),
    )
    level: str = Field(
        default="WARNING",
        description="Sets the minimum severity level for logged messages.",
    )
    otel_formatting: Literal["auto", "enable", "disable"] = Field(
        default="auto",
        description="Enables JSON formatting compliant with OpenTelemetry.",
    )
    format: str | Callable[..., Any] | None = Field(
        default="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>\n",
        description="Defines the standard text format template for emitted log lines.",
    )
    filter: Any = Field(
        default=True,
        description="Specifies a filter function or package prefix string.",
    )
    enqueue: bool = Field(
        default=True,
        description="Enables asynchronous, thread-safe message queueing.",
    )
    kwargs: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra arguments passed directly to loguru's add handler.",
    )

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="GITVERSIONED__LOGGING__",
        env_nested_delimiter="__",
    )

    @field_validator("sink", mode="before")
    @classmethod
    def _parse_sink(cls, value: Any) -> Any:
        # Convert string aliases for standard output/error streams to stream objects.
        if isinstance(value, str):
            mapping = {
                "stdout": sys.stdout,
                "sys.stdout": sys.stdout,
                "stderr": sys.stderr,
                "sys.stderr": sys.stderr,
            }
            return mapping.get(value.lower(), value)
        return value


def configure_logger(settings: LoggingSettings | None = None) -> None:
    """
    Configure the global loguru logger handler.

    Example:
        >>> configure_logger(LoggingSettings(level="WARNING"))

    :param settings: Logging configurations, defaults to None (loads from environment).
    :type settings: LoggingSettings | None
    :return: None
    :raises ImportError: Raised if OpenTelemetry formatting is enabled but
                         the package is not installed.
    """
    settings = settings or LoggingSettings()

    if not settings.enabled:
        logger.disable("gitversioned")
        return

    logger.enable("gitversioned")

    if settings.clear_loggers:
        logger.remove()
        _state["handler_id"] = None
    elif isinstance(_state["handler_id"], int):
        with contextlib.suppress(ValueError):
            logger.remove(_state["handler_id"])
        _state["handler_id"] = None

    use_otel = settings.otel_formatting == "enable" or (
        settings.otel_formatting == "auto" and opentelemetry_trace is not None
    )
    if settings.otel_formatting == "enable" and opentelemetry_trace is None:
        raise ImportError(
            "OpenTelemetry is not installed but 'otel_formatting' was set to 'enable'."
        )

    log_format = _otel_formatter if use_otel else settings.format
    filter_val = "gitversioned" if settings.filter is True else settings.filter

    if isinstance(filter_val, (list, tuple, str)):
        prefixes = (
            tuple(filter_val)
            if isinstance(filter_val, (list, tuple))
            else (filter_val,)
        )

        def final_filter(record: dict[str, Any]) -> bool:
            return bool(record["name"] and record["name"].startswith(prefixes))

    else:
        final_filter = None if filter_val is False else filter_val

    _state["handler_id"] = logger.add(
        cast("Any", settings.sink),
        level=settings.level,
        filter=cast("Any", final_filter),
        format=cast("Any", log_format),
        enqueue=settings.enqueue,
        **settings.kwargs,
    )


@overload
def autolog(func: _FuncT) -> _FuncT: ...


@overload
def autolog(
    func: None = None,
    *,
    exception_log_level: str | None = "ERROR",
) -> Callable[[_FuncT], _FuncT]: ...


def autolog(
    func: _FuncT | None = None,
    *,
    exception_log_level: str | None = "ERROR",
) -> _FuncT | Callable[[_FuncT], _FuncT]:
    """
    Decorate a function to log call inputs, outputs, and any raised exceptions.

    Examples:
        Use as a direct decorator:

        >>> @autolog
        ... def add(a: int, b: int) -> int:
        ...     return a + b

        Use as a decorator factory call with defaults:

        >>> @autolog()
        ... def sub(a: int, b: int) -> int:
        ...     return a - b

        Use with a custom exception log level:

        >>> @autolog(exception_log_level="WARNING")
        ... def divide(a: int, b: int) -> float:
        ...     return a / b

    :param func: Target function to wrap, defaults to None.
    :type func: Callable | None
    :param exception_log_level: Log level for exception reporting,
                                defaults to "ERROR".
    :type exception_log_level: str | None
    :return: The decorated wrapper or a decorator factory function.
    :rtype: Callable
    """

    def decorator(func_to_wrap: _FuncT) -> _FuncT:
        @functools.wraps(func_to_wrap)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_name = getattr(func_to_wrap, "__qualname__", "function")
            logger.debug(
                _LOG_ENTRY_FORMAT.format(name=func_name, args=args, kwargs=kwargs)
            )
            try:
                result = func_to_wrap(*args, **kwargs)
            except Exception as error:
                if exception_log_level == "ERROR":
                    logger.opt(exception=error).error(
                        _LOG_EXCEPTION_FORMAT.format(name=func_name, exception=error),
                    )
                elif exception_log_level is not None:
                    logger.log(
                        exception_log_level,
                        _LOG_EXCEPTION_FORMAT.format(name=func_name, exception=error),
                    )
                raise error
            else:
                logger.debug(_LOG_EXIT_FORMAT.format(name=func_name, result=result))
                return result

        return cast("_FuncT", wrapper)

    if func is None:
        return decorator
    return decorator(func)


def _otel_formatter(record: dict[str, Any]) -> str:
    # Format the log record as an OpenTelemetry compliant JSON string.
    trace_id = span_id = trace_flags = None

    if opentelemetry_trace:
        span = opentelemetry_trace.get_current_span()
        context = span.get_span_context()
        if context.is_valid:
            trace_id = format(context.trace_id, "032x")
            span_id = format(context.span_id, "016x")
            trace_flags = format(context.trace_flags, "02x")

    log_record = {
        "timestamp": record["time"].isoformat(),
        "severity_text": record["level"].name,
        "body": record["message"],
        "resource": {"service.name": "gitversioned"},
        "attributes": {
            "module": record["name"],
            "function": record["function"],
            "line": record["line"],
            "process_id": record["process"].id,
            **record["extra"],
        },
    }

    if record.get("exception"):
        exception = record["exception"]
        log_record["attributes"]["exception.type"] = exception.type.__name__
        log_record["attributes"]["exception.message"] = str(exception.value)
        log_record["attributes"]["exception.stacktrace"] = "".join(
            traceback.format_exception(
                exception.type, exception.value, exception.traceback
            )
        )

    if trace_id:
        log_record.update(
            {
                "trace_id": trace_id,
                "span_id": span_id,
                "trace_flags": trace_flags,
            }
        )

    # Escape braces so loguru doesn't interpret the JSON string as a format string
    # Escape '<' and '>' to prevent loguru from interpreting them as color markup tags
    return (
        json.dumps(log_record)
        .replace("{", "{{")
        .replace("}", "}}")
        .replace("<", "\\<")
        .replace(">", "\\>")
    ) + "\n"
