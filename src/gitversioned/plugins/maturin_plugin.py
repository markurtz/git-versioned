"""
Maturin build backend wrapper for GitVersioned.

This module implements PEP 517 and PEP 660 build backend hooks
to integrate dynamic version resolution into Rust-based Python
packages. When a build frontend (such as pip or build) invokes
this backend, the wrapper calculates the project version using
Git repository metadata and configuration, updates Cargo.toml
if necessary, and then invokes the corresponding Maturin
backend hook to compile and package the project.

The main interfaces correspond to PEP 517/660 hooks, which
automatically locate, configure, and invoke the underlying
maturin implementation while transparently managing the logging
setup and build environment configuration.
"""

from __future__ import annotations

import email
import os
import types
from typing import Any

from packaging.version import Version as PackagingVersion

from gitversioned.compat import maturin, tomllib
from gitversioned.logging import LoggingSettings, configure_logger, logger
from gitversioned.settings import Settings
from gitversioned.utils import BuildEnvironment, GitRepository
from gitversioned.versioning import resolve_version_output_to_stream

__all__ = [
    "build_editable",
    "build_sdist",
    "build_wheel",
    "get_requires_for_build_editable",
    "get_requires_for_build_sdist",
    "get_requires_for_build_wheel",
    "prepare_metadata_for_build_editable",
    "prepare_metadata_for_build_wheel",
]


def build_editable(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    """
    Build an editable wheel, delegating to maturin.

    .. code-block:: python

        from gitversioned.plugins import maturin_plugin

        path = maturin_plugin.build_editable("dist/")

    :param wheel_directory: Directory where the editable wheel
        should be written.
    :param config_settings: Configuration options passed by the
        build frontend.
    :param metadata_directory: Optional directory containing
        pre-built metadata.
    :returns: The filename of the built editable wheel.
    :raises ImportError: If the maturin package is not installed.
    """
    return _get_maturin().build_editable(
        wheel_directory,
        config_settings=config_settings,
        metadata_directory=metadata_directory,
    )


def build_sdist(
    sdist_directory: str,
    config_settings: dict[str, Any] | None = None,
) -> str:
    """
    Build a source distribution (sdist), delegating packaging to maturin.

    .. code-block:: python

        from gitversioned.plugins import maturin_plugin

        path = maturin_plugin.build_sdist("dist/")

    :param sdist_directory: Directory where the constructed sdist
        should be written.
    :param config_settings: Configuration options passed by the
        build frontend.
    :returns: The filename of the built sdist.
    :raises ImportError: If the maturin package is not installed.
    """
    return _get_maturin().build_sdist(
        sdist_directory,
        config_settings=config_settings,
    )


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    """
    Build a wheel, delegating compilation and packaging to maturin.

    .. code-block:: python

        from gitversioned.plugins import maturin_plugin

        path = maturin_plugin.build_wheel("dist/")

    :param wheel_directory: Directory where the constructed wheel
        should be written.
    :param config_settings: Configuration options passed by the
        build frontend.
    :param metadata_directory: Optional directory containing
        pre-built metadata.
    :returns: The filename of the built wheel.
    :raises ImportError: If the maturin package is not installed.
    """
    return _get_maturin().build_wheel(
        wheel_directory,
        config_settings=config_settings,
        metadata_directory=metadata_directory,
    )


def get_requires_for_build_editable(
    config_settings: dict[str, Any] | None = None,
) -> list[str]:
    """
    Get additional packages required to build an editable wheel.

    .. code-block:: python

        from gitversioned.plugins import maturin_plugin

        reqs = maturin_plugin.get_requires_for_build_editable()

    :param config_settings: Configuration options passed by the
        build frontend.
    :returns: A list of dependency specification strings.
    :raises ImportError: If the maturin package is not installed.
    """
    return _get_maturin().get_requires_for_build_editable(
        config_settings=config_settings
    )


def get_requires_for_build_sdist(
    config_settings: dict[str, Any] | None = None,
) -> list[str]:
    """
    Get additional packages required to build a source distribution (sdist).

    .. code-block:: python

        from gitversioned.plugins import maturin_plugin

        reqs = maturin_plugin.get_requires_for_build_sdist()

    :param config_settings: Configuration options passed by the
        build frontend.
    :returns: A list of dependency specification strings.
    :raises ImportError: If the maturin package is not installed.
    """
    return _get_maturin().get_requires_for_build_sdist(config_settings=config_settings)


def get_requires_for_build_wheel(
    config_settings: dict[str, Any] | None = None,
) -> list[str]:
    """
    Get additional packages required to build a wheel.

    .. code-block:: python

        from gitversioned.plugins import maturin_plugin

        reqs = maturin_plugin.get_requires_for_build_wheel()

    :param config_settings: Configuration options passed by the
        build frontend.
    :returns: A list of dependency specification strings.
    :raises ImportError: If the maturin package is not installed.
    """
    return _get_maturin().get_requires_for_build_wheel(config_settings=config_settings)


def prepare_metadata_for_build_editable(
    metadata_directory: str,
    config_settings: dict[str, Any] | None = None,
) -> str:
    """
    Prepare the dist-info metadata directory for an editable wheel build.

    .. code-block:: python

        from gitversioned.plugins import maturin_plugin

        path = maturin_plugin.prepare_metadata_for_build_editable("metadata/")

    :param metadata_directory: Directory where the metadata should
        be written.
    :param config_settings: Configuration options passed by the
        build frontend.
    :returns: The basename of the metadata directory.
    :raises ImportError: If the maturin package is not installed.
    """
    return _get_maturin().prepare_metadata_for_build_editable(
        metadata_directory,
        config_settings=config_settings,
    )


def prepare_metadata_for_build_wheel(
    metadata_directory: str,
    config_settings: dict[str, Any] | None = None,
) -> str:
    """
    Prepare the dist-info metadata directory for a wheel build.

    .. code-block:: python

        from gitversioned.plugins import maturin_plugin

        path = maturin_plugin.prepare_metadata_for_build_wheel("metadata/")

    :param metadata_directory: Directory where the metadata should
        be written.
    :param config_settings: Configuration options passed by the
        build frontend.
    :returns: The basename of the metadata directory.
    :raises ImportError: If the maturin package is not installed.
    """
    return _get_maturin().prepare_metadata_for_build_wheel(
        metadata_directory,
        config_settings=config_settings,
    )


_logging_configured: bool = False


def _get_maturin() -> types.ModuleType:
    # Check for maturin availability, prepare version, and return maturin module.
    if maturin is None:
        raise ImportError(
            "The 'maturin' package must be installed to use the maturin plugin backend."
        )

    global _logging_configured  # noqa: PLW0603
    if not _logging_configured:
        configure_logger(LoggingSettings(enabled=True))
        _logging_configured = True

    logger.debug("Maturin plugin: resolving dynamic version...")
    settings = Settings()

    # Verify that version is listed in dynamic fields of pyproject.toml
    pyproject_path = settings.project_root / "pyproject.toml"
    if pyproject_path.is_file() and tomllib is not None:
        with pyproject_path.open("rb") as toml_file:
            pyproject_data = tomllib.load(toml_file)
            if "version" not in pyproject_data.get("project", {}).get("dynamic", []):
                raise ValueError(
                    "Maturin plugin requires 'version' to be listed in "
                    "[project] dynamic fields, but it was not found."
                )

    if resolved := os.environ.get("GITVERSIONED_RESOLVED_VERSION"):
        PackagingVersion(resolved)
        settings.version = resolved
        settings.version_type = "release"
    else:
        pkg_info_path = settings.project_root / "PKG-INFO"
        if pkg_info_path.is_file():
            try:
                with pkg_info_path.open(encoding="utf-8") as file_handle:
                    message = email.message_from_file(file_handle)
                    if (
                        (candidate := message.get("Version"))
                        and (stripped := candidate.strip())
                        and stripped not in ("None", "0.0.0", "UNKNOWN")
                    ):
                        settings.version = stripped
                        settings.version_type = "release"
            except (OSError, ValueError) as error:
                logger.warning(f"Failed to read PKG-INFO: {error}")

    cargo_toml = settings.project_root / "Cargo.toml"
    if cargo_toml.exists() and cargo_toml.is_file() and not settings.overrides:
        settings.overrides = {
            "cargo": {
                "output": "Cargo.toml",
                "version_standard": "semver2",
                "output_strategies": {
                    "type": "regex",
                    "pattern": (
                        r"(?ms)^\[package\].*?^"
                        r"(\s*version\s*=\s*)([\'\"])(?P<version>[^\'\"]+)\2"
                    ),
                },
            }
        }

    repository = GitRepository(settings.project_root)
    environment = BuildEnvironment(project_root=settings.project_root)
    result = resolve_version_output_to_stream(
        settings=settings,
        repository=repository,
        environment=environment,
    )
    output_path = result[0]
    version = result[2]
    logger.info(f"Maturin plugin resolved version: {version} (wrote to: {output_path})")

    return maturin
