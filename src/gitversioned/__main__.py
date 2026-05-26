"""
CLI entry point for GitVersioned.

This module provides the standalone CLI for GitVersioned, allowing users to run
version resolution outside of the build backend context, for instance, in pre-commit
hooks or before a Cargo build.

Example:
    ::

        python -m gitversioned --output-format=cargo
        gitversioned --output-format=cargo
"""

from __future__ import annotations

import contextlib
import inspect
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
from gitversioned.versioning import resolve_and_generate_version

__all__ = ["app", "main", "run_cli"]

app: Annotated[
    typer.Typer,
    "The Typer application instance for the gitversioned CLI.",
] = typer.Typer(
    add_completion=False,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    help="Opinionated PEP 440 Python versioning for Git repos and submodules.",
)


@app.callback(invoke_without_command=True)
def main_callback(
    version: bool | None = typer.Option(
        None,
        "--version",
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    """
    Opinionated PEP 440 Python versioning for Git repos and submodules.
    """
    if version:
        typer.echo(f"gitversioned v{__version__}")
        raise typer.Exit


@app.command()
def run_cli(**kwargs: Any) -> None:
    """
    Main entry point for the gitversioned CLI.

    Initializes configuration from pyproject.toml, setup.cfg, environment variables,
    and CLI arguments. It then resolves the version, generates the version.py file,
    and optionally executes file injections.

    Example:
        ::

            run_cli(output_format="cargo")

    :param kwargs: CLI arguments passed dynamically from the Typer signature.
    :raises SystemExit: If version resolution or file injection fails.
    """
    try:
        # Filter out None values so Pydantic uses its native priority system
        cli_args = {key: value for key, value in kwargs.items() if value is not None}
        settings = Settings(**typing.cast("Any", cli_args))

        # Redirect log output to stderr if output is stdout
        logging_sink = sys.stderr if settings.output == "sys.stdout" else sys.stdout
        configure_logger(LoggingSettings(enabled=True, sink=logging_sink))
        logger.debug("Starting gitversioned CLI...")

        repository = GitRepository(settings.project_root)
        environment = BuildEnvironment(project_root=settings.project_root)

        version, output_path = resolve_and_generate_version(
            settings=settings,
            repository=repository,
            environment=environment,
        )

        logger.info(f"Successfully resolved version: {version}")
        if output_path:
            logger.info(f"Version file written to: {output_path}")

    except Exception as error:
        with contextlib.suppress(Exception):
            configure_logger(LoggingSettings(enabled=True, sink=sys.stderr))
        logger.exception("Failed to execute gitversioned CLI")
        raise SystemExit(1) from error


def main() -> None:
    """
    Invokes the Typer app.
    """
    # If no subcommand is specified, and --version / --help are not present,
    # default to the "run-cli" command.
    args = sys.argv[1:]
    subcommands = ["run-cli"]
    has_subcommand = any(arg in subcommands for arg in args)
    has_global = any(arg in ["--version", "-v", "--help", "-h"] for arg in args)

    if not has_subcommand and not has_global:
        sys.argv.insert(1, "run-cli")

    app()


def _build_cli_signature() -> inspect.Signature:
    """Dynamically builds a CLI signature from the Settings model fields."""
    parameters = []
    for name, field in Settings.model_fields.items():
        # Use None as default so kwargs only contains explicitly provided arguments.
        # This prevents Typer from overriding environment variables or config files
        # with Pydantic default values.
        default_val_repr: bool | str = False
        if field.default not in (..., PydanticUndefined, None):
            if isinstance(field.default, bool):
                default_val_repr = field.default
            else:
                default_val_repr = str(field.default)

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


# Patch the function signature dynamically to expose Settings fields as
# CLI parameters to Typer. This prevents duplicating Settings fields in the
# CLI parameters while ensuring --help and CLI argument parsing work correctly.
setattr(run_cli, "__signature__", _build_cli_signature())  # noqa: B010


if __name__ == "__main__":
    main()
