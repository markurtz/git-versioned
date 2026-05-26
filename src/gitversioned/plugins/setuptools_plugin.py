"""
Setuptools integration for GitVersioned.

This module provides entry points for Setuptools to automatically compute and
inject versions resolved from Git metadata into package distribution objects.
"""

from __future__ import annotations

import email
from distutils.errors import DistutilsSetupError
from pathlib import Path
from typing import Any, cast

from loguru import logger
from packaging.utils import canonicalize_name
from setuptools import Distribution

from gitversioned.logging import LoggingSettings, configure_logger
from gitversioned.settings import Settings
from gitversioned.utils import BuildEnvironment, GitRepository
from gitversioned.versioning import resolve_and_generate_version

__all__ = ["finalize_distribution_options", "setup_keywords"]

# Constants for internal validation
INVALID_VERSIONS: set[str] = {"None", "0.0.0", "UNKNOWN"}


def setup_keywords(distribution: Distribution, attribute: str, value: Any) -> None:
    """
    Validates and stores the GitVersioned configuration dictionary.

    :param distribution: The Setuptools distribution object.
    :param attribute: The keyword attribute name.
    :param value: The configuration dictionary provided by the user.
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
    Computes the package version and updates the distribution metadata.

    This is the primary entry point triggered during the Setuptools lifecycle.
    """

    configure_logger(LoggingSettings(enabled=True))
    logger.debug("Finalizing distribution options for GitVersioned.")

    project_root, source_root, package_name = _resolve_project_context(distribution)
    if not package_name:
        raise DistutilsSetupError("Could not determine package name.")

    # Check for an established version to avoid redundant Git resolution
    established_version = _extract_established_version(distribution, project_root)
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
            version, output_path = resolve_and_generate_version(
                settings=settings, repository=repository, environment=environment
            )
            version_string = str(version)

        # Update distribution metadata
        if hasattr(distribution, "metadata"):
            distribution.metadata.version = version_string
        distribution.version = version_string

        if output_path:
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


def _extract_established_version(
    distribution: Distribution, project_root: Path
) -> str | None:
    """Check metadata, distribution, and PKG-INFO for an existing valid version."""
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
            and version not in INVALID_VERSIONS
        ):
            return version.strip()
    return None


def _find_existing_version_file(settings: Settings) -> Path | None:
    """Locate the existing version file if resolution is skipped."""
    if not settings.output or settings.output in ("sys.stdout", "sys.stderr"):
        return None
    path = Path(settings.output)
    output_path = path if path.is_absolute() else settings.src_root / path
    return output_path if output_path.exists() else None


def _resolve_project_context(
    distribution: Distribution,
) -> tuple[Path, Path, str | None]:
    """Determines project root, source root, and package name via waterfall logic."""
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
    """Maps the package name to its source directory using package_dir configuration."""
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
    """Probes the filesystem for a package directory containing an __init__.py."""
    for search_path in (project_root / "src", project_root):
        if not search_path.is_dir():
            continue
        for item in search_path.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                return item, item.name
    return None


def _inject_output_into_distribution(
    distribution: Distribution,
    output_path: Path,
    source_root: Path,
    package_name: str,
) -> None:
    """Registers the generated file in the distribution's package_data or py_modules."""
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
