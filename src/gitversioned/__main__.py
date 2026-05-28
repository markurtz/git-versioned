"""
CLI entry point for GitVersioned version resolution.

This module provides a standalone command-line interface for GitVersioned,
allowing developers and CI/CD pipelines to calculate versions, format output
strategies, and write version metadata to disk. It handles dynamic CLI parsing
by inspecting the Pydantic configuration schemas and maps subcommands directly
to version resolution workflows.

The main interface is the Typer application `app`, which exposes three primary
commands: `calculate`, `format`, and `write`. These commands dynamically adjust
their accepted parameters based on the `Settings` model fields, allowing
command-line overrides of any project-level configuration options.
"""

from __future__ import annotations

import contextlib
import inspect
import json
import sys
import typing
from typing import Annotated, Any

import typer
from loguru import logger
from pydantic_core import PydanticUndefined

from gitversioned import __version__
from gitversioned.logging import LoggingSettings, configure_logger
from gitversioned.settings import Settings
from gitversioned.utils import BuildEnvironment, GitRepository
from gitversioned.versioning import (
    resolve_version,
    resolve_version_output,
    resolve_version_output_to_stream,
)

__all__ = [
    "app",
    "calculate",
    "format_cmd",
    "main",
    "main_callback",
    "overrides_app",
    "write",
]

app: Annotated[
    typer.Typer,
    (
        "The Typer application instance serving as the primary command-line "
        "entry point. Manages global options, subcommand routing, and "
        "auto-generates help text."
    ),
] = typer.Typer(
    add_completion=False,
    help="Opinionated PEP 440 Python versioning for Git repos and submodules.",
)

overrides_app: Annotated[
    typer.Typer,
    (
        "The Typer application instance serving as the overrides subcommand group. "
        "Allows running commands under a specific overrides context."
    ),
] = typer.Typer(
    add_completion=False,
    help="Run commands under a specific overrides context.",
)


def main() -> None:
    """
    Run the Typer command-line application.

    .. code-block:: python

        from gitversioned.__main__ import main
        main()

    :returns: None.
    """
    app()


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = None,
) -> None:
    """
    Handle global command-line options and subcommand routing.

    :param ctx: Context object representing the current Typer execution flow.
    :param version: Flag to display the GitVersioned version and exit.
    :returns: None.
    :raises typer.Exit: When displaying version or printing help.
    """
    if version:
        typer.echo(f"gitversioned v{__version__}")
        raise typer.Exit
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit


@overrides_app.callback(invoke_without_command=True)
def overrides_callback(
    ctx: typer.Context,
    overrides: Annotated[
        str,
        typer.Argument(
            help="The overrides name context to use.",
        ),
    ],
) -> None:
    """
    Handle overrides subcommand routing and capture overrides argument.
    """
    ctx.obj = overrides
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit


@app.command(name="calculate")
def calculate(**kwargs: Any) -> None:
    """
    Resolve and output only the PEP 440 version string.

    This command runs version resolution and prints the final calculated version
    string directly to stdout. It excludes output target and strategy settings.

    :param kwargs: Dynamic CLI override arguments mapping to Settings schema fields.
    :returns: None.
    """
    _run_calculate(kwargs)


@app.command(name="format")
def format_cmd(**kwargs: Any) -> None:
    """
    Resolve the version and output the formatted strategy templates.

    This command prints the rendered content from the configured version output
    strategies to stdout. It excludes final file write targets from the options.

    :param kwargs: Dynamic CLI override arguments mapping to Settings schema fields.
    :returns: None.
    """
    _run_format(kwargs)


@app.command(name="write")
def write(**kwargs: Any) -> None:
    """
    Resolve the version and write output files.

    This command writes the rendered version templates to the configured file
    paths and prints a confirmation of the successfully written path to stdout.

    :param kwargs: Dynamic CLI override arguments mapping to Settings schema fields.
    :returns: None.
    """
    _run_write(kwargs)


@overrides_app.command(name="calculate")
def overrides_calculate(ctx: typer.Context, **kwargs: Any) -> None:
    """
    Resolve and output only the PEP 440 version string for overrides.
    """
    _run_calculate(kwargs, overrides=ctx.obj)


@overrides_app.command(name="format")
def overrides_format(ctx: typer.Context, **kwargs: Any) -> None:
    """
    Resolve the version and output formatted strategy templates for overrides.
    """
    _run_format(kwargs, overrides=ctx.obj)


@overrides_app.command(name="write")
def overrides_write(ctx: typer.Context, **kwargs: Any) -> None:
    """
    Resolve the version and write output files for overrides.
    """
    _run_write(kwargs, overrides=ctx.obj)


def _run_calculate(kwargs: dict[str, Any], overrides: str | None = None) -> None:
    """
    Internal execution helper for the calculate subcommand.
    """
    with _cli_execution_context("calculate", kwargs, overrides=overrides) as (
        settings,
        repository,
        environment,
    ):
        version, _, _ = resolve_version(
            settings=settings,
            repository=repository,
            environment=environment,
        )
        typer.echo(str(version))


def _run_format(kwargs: dict[str, Any], overrides: str | None = None) -> None:
    """
    Internal execution helper for the format subcommand.
    """
    with _cli_execution_context("format", kwargs, overrides=overrides) as (
        settings,
        repository,
        environment,
    ):
        content, _, _, _ = resolve_version_output(
            settings=settings,
            repository=repository,
            environment=environment,
        )
        typer.echo(content, nl=False)


def _run_write(kwargs: dict[str, Any], overrides: str | None = None) -> None:
    """
    Internal execution helper for the write subcommand.
    """
    with _cli_execution_context("write", kwargs, overrides=overrides) as (
        settings,
        repository,
        environment,
    ):
        output_path, _, version, _, _ = resolve_version_output_to_stream(
            settings=settings,
            repository=repository,
            environment=environment,
        )

        logger.info(f"Successfully resolved version: {version}")
        if output_path:
            typer.echo(f"Version successfully written to {output_path}")


def _parse_cli_args(kwargs: dict[str, Any], overrides: str | None = None) -> Settings:
    """
    Filter out None values and deserialize JSON strings for list/dict/model fields.
    """
    cli_args = {key: value for key, value in kwargs.items() if value is not None}
    for field, value in cli_args.items():
        if isinstance(value, str):
            stripped = value.strip()
            if (stripped.startswith("[") and stripped.endswith("]")) or (
                stripped.startswith("{") and stripped.endswith("}")
            ):
                with contextlib.suppress(Exception):
                    cli_args[field] = json.loads(stripped)
    if overrides:
        root_settings = Settings()
        override_settings = root_settings.get_overridden_settings(overrides)
        data = override_settings.model_dump()
        data.pop("overrides", None)
        data.update(cli_args)
        return Settings(**data)
    return Settings(**typing.cast("Any", cli_args))


@contextlib.contextmanager
def _cli_execution_context(
    command_name: str,
    kwargs: dict[str, Any],
    overrides: str | None = None,
) -> typing.Iterator[tuple[Settings, GitRepository, BuildEnvironment]]:
    """
    Provide a unified execution context for CLI subcommands.

    Parses configuration, configures logging (ensuring stdout logger sinks are routed
    to stderr to prevent interference with command output), initializes repo and build
    environments, and handles all standard or unexpected errors/exits consistently.

    :param command_name: The name of the subcommand (for logging/errors).
    :param kwargs: Raw CLI argument dictionary matching Settings schema.
    :param overrides: Optional overrides context name.
    :yields: A tuple of (Settings, GitRepository, BuildEnvironment) instances.
    """
    try:
        settings = _parse_cli_args(kwargs, overrides=overrides)

        logging_settings = LoggingSettings()
        if logging_settings.sink is sys.stdout:
            logging_settings.sink = sys.stderr
        configure_logger(logging_settings)
        logger.debug(f"Starting gitversioned CLI {command_name}...")

        repository = GitRepository(settings.project_root)
        environment = BuildEnvironment(project_root=settings.project_root)
        yield settings, repository, environment

    except (typer.Exit, typer.Abort) as exit_exc:
        raise exit_exc
    except Exception as error:
        with contextlib.suppress(Exception):
            configure_logger(LoggingSettings(enabled=True, sink=sys.stderr))
        logger.exception(f"Failed to execute gitversioned CLI {command_name}")
        raise SystemExit(1) from error


def _build_cli_signature(
    exclude_fields: set[str] | None = None,
    include_ctx: bool = False,
) -> inspect.Signature:
    """
    Dynamically build a CLI signature from the Settings model fields.
    """
    exclude = exclude_fields or set()
    parameters = []
    if include_ctx:
        parameters.append(
            inspect.Parameter(
                "ctx",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=typer.Context,
            )
        )
    for name, field in Settings.model_fields.items():
        if name in exclude:
            continue

        # Use None as default so kwargs only contains explicitly provided arguments.
        # This prevents Typer from overriding environment variables or config files
        # with Pydantic default values.
        default_val_repr: bool | str = False
        if field.default not in (..., PydanticUndefined, None):
            default_val_repr = (
                field.default if isinstance(field.default, bool) else str(field.default)
            )

        flag_name = f"--{name.replace('_', '-')}"
        if name == "version":
            flag_name = "--explicit-version"

        typer_option = typer.Option(
            None,
            flag_name,
            help=field.description,
            show_default=default_val_repr,
        )
        annotation = field.annotation
        if "dict" in str(annotation).lower():
            annotation = str

        parameters.append(
            inspect.Parameter(
                name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=typer_option,
                annotation=annotation,
            )
        )

    return inspect.Signature(parameters)


# Add the overrides application to the main app instance
app.add_typer(overrides_app, name="overrides")


# Patch signatures dynamically to expose Settings fields as CLI parameters to Typer.
typing.cast("Any", calculate).__signature__ = _build_cli_signature(
    exclude_fields={"output", "output_strategies"}
)
typing.cast("Any", format_cmd).__signature__ = _build_cli_signature(
    exclude_fields={"output"}
)
typing.cast("Any", write).__signature__ = _build_cli_signature()

typing.cast("Any", overrides_calculate).__signature__ = _build_cli_signature(
    exclude_fields={"output", "output_strategies"},
    include_ctx=True,
)
typing.cast("Any", overrides_format).__signature__ = _build_cli_signature(
    exclude_fields={"output"},
    include_ctx=True,
)
typing.cast("Any", overrides_write).__signature__ = _build_cli_signature(
    include_ctx=True,
)


if __name__ == "__main__":
    main()
