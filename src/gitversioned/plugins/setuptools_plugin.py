"""
Setuptools build integration plugin for GitVersioned.

This module implements the integration layer between GitVersioned and the
Setuptools build system. It exposes hook entry points that Setuptools calls
during distribution configuration, allowing packaging configuration to
dynamically query and apply resolved Git-based versions.

The plugin functions by registering setup keyword arguments and finalizer
hooks. It extracts the package distribution options, resolves project
context, extracts any pre-existing or environment-specified versions,
executes the Git versioning resolution, and updates the distribution
metadata version dynamically. If configured, it also injects the generated
version file into the distribution's package_data or py_modules.
"""

from __future__ import annotations

import email
import os
from distutils.errors import DistutilsSetupError
from pathlib import Path
from typing import Any, cast

from packaging.utils import canonicalize_name
from setuptools import Distribution

from gitversioned.logging import LoggingSettings, autolog, configure_logger, logger
from gitversioned.settings import Settings
from gitversioned.utils import BuildEnvironment, GitRepository
from gitversioned.versioning import resolve_version_output_to_stream

__all__ = ["finalize_distribution_options", "setup_keywords"]

# Constants for internal validation
_INVALID_VERSIONS: set[str] = {"None", "0.0.0", "UNKNOWN"}


def setup_keywords(distribution: Distribution, attribute: str, value: Any) -> None:
    """
    Validate and store the GitVersioned configuration dictionary.

    Registers the `gitversioned` configuration dictionary on the distribution object.
    This configuration is subsequently retrieved during option finalization to customize
    the version resolution process.

    .. code-block:: python

        # Example usage inside setup.py:
        setup(
            gitversioned={
                "version_source_file": "version.txt",
                "source_type": ["tag", "file"],
            },
        )

    :param distribution: The Setuptools distribution object being configured.
    :param attribute: The name of the setup keyword (must be "gitversioned").
    :param value: The configuration settings dictionary provided in the setup call.
    :raises DistutilsSetupError: If the keyword attribute is invalid or the
        value is not a dict.
    """
    configure_logger(LoggingSettings(enabled=True))
    logger.debug(f"setup_keywords called with attribute='{attribute}'")

    if attribute != "gitversioned":
        logger.error(f"Unknown keyword argument: {attribute}")
        raise DistutilsSetupError(f"Unknown keyword argument: {attribute}")

    if not isinstance(value, dict):
        logger.error("gitversioned keyword argument must be a dict")
        raise DistutilsSetupError("gitversioned must be a dict")

    cast("Any", distribution).gitversioned_config = value


def finalize_distribution_options(distribution: Distribution) -> None:
    """
    Compute the package version and update the distribution metadata.

    This is the primary entry point triggered during the Setuptools distribution
    finalization lifecycle. It resolves the package name, extracts any established or
    environment-provided version, reads configuration overrides, calculates the dynamic
    version using Git metadata, and applies the version to the distribution metadata.
    If a version file is generated, it is automatically injected into the distribution's
    package data or module list.

    .. code-block:: python

        # Hook is registered as a Setuptools entry point:
        # entry_point = "gitversioned.plugins.setuptools_plugin"
        # func = "finalize_distribution_options"

    :param distribution: The Setuptools distribution object to finalize.
    :raises DistutilsSetupError: If the package name is unresolved or if version
        resolution encounters an unexpected failure.
    """
    configure_logger(LoggingSettings(enabled=True))
    logger.debug("Finalizing distribution options for GitVersioned.")

    project_root, source_root, package_name = _resolve_project_context(distribution)
    if not package_name:
        raise DistutilsSetupError("Could not determine package name.")

    # Check for an established version to avoid redundant Git resolution
    established_version = _extract_established_version(distribution, project_root)

    resolved = os.environ.get("GITVERSIONED_RESOLVED_VERSION")
    if resolved and not established_version:
        established_version = resolved

    config_overrides = getattr(distribution, "gitversioned_config", {})

    try:
        kwargs: Any = {
            "package_name": package_name,
            "project_root": project_root,
            "src_root": source_root,
            "build_is_editable": getattr(distribution, "editable", False),
        }
        kwargs.update(config_overrides)
        settings = Settings(**kwargs)

        if established_version:
            logger.info(f"Using established version: {established_version}")
            version_string = established_version
            output_path = _find_existing_version_file(settings)
        else:
            repository = GitRepository(settings.project_root)
            environment = BuildEnvironment(project_root=settings.project_root)
            output_path, _, version, _, _ = resolve_version_output_to_stream(
                settings=settings, repository=repository, environment=environment
            )
            version_string = str(version)

        # Update distribution metadata
        if hasattr(distribution, "metadata"):
            distribution.metadata.version = version_string

        if output_path and isinstance(output_path, Path):
            _inject_output_into_distribution(
                distribution=distribution,
                output_path=output_path,
                source_root=source_root,
                package_name=package_name,
            )

    except Exception as error:
        if isinstance(error, DistutilsSetupError):
            raise
        logger.exception("Unexpected failure during version resolution")
        raise DistutilsSetupError(f"Failed to resolve version: {error}") from error


@autolog
def _extract_established_version(
    distribution: Distribution, project_root: Path
) -> str | None:
    # Check metadata, distribution, and PKG-INFO for an existing valid version.
    candidates = [
        getattr(distribution.metadata, "version", None),
        getattr(distribution, "version", None),
    ]

    pkg_info_path = project_root / "PKG-INFO"
    if pkg_info_path.is_file():
        try:
            with pkg_info_path.open(encoding="utf-8") as file_handle:
                message = email.message_from_file(file_handle)
                candidates.append(message.get("Version"))
        except (OSError, ValueError) as error:
            logger.warning(f"Failed to read PKG-INFO: {error}")

    for version in candidates:
        if (
            isinstance(version, str)
            and version.strip()
            and version not in _INVALID_VERSIONS
        ):
            return version.strip()
    return None


@autolog
def _find_existing_version_file(settings: Settings) -> Path | None:
    # Locate the existing version file if resolution is skipped.
    if not settings.output:
        return None
    output_path = Path(settings.output)
    if not output_path.is_absolute():
        output_path = settings.src_root / output_path
    return output_path if output_path.exists() else None


@autolog
def _resolve_project_context(
    distribution: Distribution,
) -> tuple[Path, Path, str | None]:
    # Determines project root, source root, and package name via waterfall logic.
    project_root = Path(getattr(distribution, "src_root", None) or Path.cwd())
    package_name = None

    # Priority 1: Direct metadata
    name_raw = getattr(distribution.metadata, "name", None)
    if not name_raw or name_raw == "UNKNOWN":
        name_raw = distribution.get_name()

    if name_raw and name_raw != "UNKNOWN":
        package_name = canonicalize_name(name_raw).replace("-", "_")

    # Priority 2: Packages list
    if not package_name:
        packages = getattr(distribution, "packages", None)
        if packages and isinstance(packages, (list, tuple)):
            package_name = packages[0]

    # Resolve source root and fallback if name is still missing
    if package_name:
        source_root = _get_source_root(project_root, distribution, package_name)
    else:
        probe = _probe_filesystem_context(project_root)
        source_root, package_name = probe if probe else (project_root, None)

    return project_root, source_root, package_name


def _get_source_root(
    project_root: Path, distribution: Distribution, package_name: str
) -> Path:
    # Maps the package name to its source directory using package_dir configuration.
    package_dir = getattr(distribution, "package_dir", None) or {}

    relative_source = package_dir.get(package_name)
    if relative_source is None and "_" in package_name:
        relative_source = package_dir.get(package_name.replace("_", "-"))

    if relative_source is None:
        relative_source = package_dir.get("", "")

    base_path = project_root / relative_source
    return (
        base_path / package_name if (base_path / package_name).is_dir() else base_path
    )


def _probe_filesystem_context(project_root: Path) -> tuple[Path, str] | None:
    # Probes the filesystem for a package directory containing an __init__.py.
    for search_path in (project_root / "src", project_root):
        if not search_path.is_dir():
            continue
        for item in search_path.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                return item, item.name
    return None


@autolog
def _inject_output_into_distribution(
    distribution: Distribution,
    output_path: Path,
    source_root: Path,
    package_name: str,
) -> None:
    # Registers the generated file in the distribution's package_data or py_modules.
    # Attempt 1: Package data (internal file)
    package_folder = (
        source_root if source_root.name == package_name else source_root / package_name
    )
    try:
        relative_output = str(output_path.relative_to(package_folder))
        current_packages = getattr(distribution, "packages", None)
        if current_packages is None:
            distribution.packages = [package_name]
        elif package_name not in current_packages:
            distribution.packages = list(current_packages) + [package_name]

        if getattr(distribution, "package_data", None) is None:
            distribution.package_data = {}
        distribution.package_data.setdefault(package_name, []).append(relative_output)
        return
    except ValueError:
        pass

    # Attempt 2: Flat module
    try:
        relative_module = str(output_path.relative_to(source_root))
        if "/" not in relative_module and output_path.suffix == ".py":
            modules = getattr(distribution, "py_modules", []) or []
            if output_path.stem not in modules:
                modules.append(output_path.stem)
            distribution.py_modules = modules
            return
    except ValueError:
        pass

    logger.warning(f"Version file {output_path} is outside source root {source_root}")
