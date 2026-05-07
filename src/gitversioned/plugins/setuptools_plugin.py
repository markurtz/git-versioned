"""
Setuptools integration for GitVersioned.

This module provides entry points for Setuptools to automatically compute and
inject versions resolved from Git metadata into package distribution objects.
It enables seamless versioning by hooking into the Setuptools lifecycle to
resolve versions before metadata is finalized.
"""

from __future__ import annotations

from distutils.errors import DistutilsSetupError
from pathlib import Path
from typing import Any

from packaging.utils import canonicalize_name
from setuptools import Distribution

from gitversioned.logging import configure_logger, logger
from gitversioned.settings import Settings
from gitversioned.utils import BuildEnvironment, GitRepository
from gitversioned.versioning import resolve_and_generate_version

__all__ = ["finalize_distribution_options", "setup_keywords"]


def setup_keywords(distribution: Distribution, attribute: str, value: Any) -> None:
    """
    Validates and stores the GitVersioned configuration dictionary.

    This function acts as a Setuptools keyword entry point, capturing the
    configuration passed via the ``gitversioned`` argument in ``setup()``.

    :param distribution: The Setuptools distribution object.
    :param attribute: The keyword attribute name (expected to be "gitversioned").
    :param value: The configuration dictionary provided by the user.
    :raises DistutilsSetupError: If the attribute is invalid or value is not a dict.
    """
    logger.debug(f"setup_keywords called with attribute='{attribute}', value='{value}'")

    if attribute != "gitversioned":
        logger.error(f"Unknown keyword argument passed to setup_keywords: {attribute}")
        raise DistutilsSetupError(f"Unknown keyword argument: {attribute}")

    if not isinstance(value, dict):
        logger.error("gitversioned keyword argument must be a dict")
        raise DistutilsSetupError("gitversioned must be a dict")

    distribution.gitversioned_config = value
    logger.debug("Successfully injected gitversioned config into distribution.")


def finalize_distribution_options(distribution: Distribution) -> None:
    """
    Computes the package version and updates the distribution metadata.

    This function triggers the core versioning engine. It resolves the package
    context, initializes settings, and generates the version. If a version file
    is generated, it ensures the file is registered in the distribution's
    package data or module list.

    :param distribution: The Setuptools distribution object being finalized.
    :raises DistutilsSetupError: If version resolution fails or the package name
        cannot be determined.
    """
    configure_logger()
    logger.debug("finalize_distribution_options called for setuptools plugin")

    project_root, source_root, package_name = _resolve_project_context(distribution)

    if not package_name or package_name == "UNKNOWN":
        raise DistutilsSetupError("Could not determine package name.")

    resolution_kwargs: dict[str, Any] = {
        "package_name": package_name,
        "project_root": project_root,
        "src_root": source_root,
        "build_is_editable": getattr(distribution, "editable", False),
    }

    current_version = getattr(distribution, "version", None)
    if isinstance(current_version, str) and current_version not in (None, "0.0.0"):
        resolution_kwargs["version"] = current_version

    resolution_kwargs.update(getattr(distribution, "gitversioned_config", {}))

    try:
        settings = Settings(**resolution_kwargs)
        repository = GitRepository(settings.project_root)
        environment = BuildEnvironment(project_root=settings.project_root)

        version, output_path = resolve_and_generate_version(
            settings=settings, repository=repository, environment=environment
        )

        version_string = str(version)
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
        logger.exception("Failed to resolve version for setuptools plugin")
        raise DistutilsSetupError(f"Failed to resolve version: {error}") from error

    logger.info(f"git-versioned set version to {version}, saved in {output_path}")


def _resolve_project_context(
    distribution: Distribution,
) -> tuple[Path, Path, str | None]:
    """
    Consolidated discovery of project root, source root, and package name.
    """
    project_root = Path(getattr(distribution, "src_root", None) or Path.cwd())

    package_name = _get_package_name(distribution)
    source_root = _get_source_root(project_root, distribution, package_name)

    # If metadata resolution fails, attempt filesystem discovery
    if not package_name:
        probe = _probe_filesystem_context(project_root)
        if probe:
            source_root, package_name = probe

    return project_root, source_root, package_name


def _get_package_name(distribution: Distribution) -> str | None:
    """
    Resolves the package name from distribution attributes or metadata.
    """
    packages = getattr(distribution, "packages", None)
    if isinstance(packages, (list, tuple)) and packages:
        return packages[0]

    name = None
    # Check metadata attributes, allowing fallback if "UNKNOWN"
    for candidate in (distribution.metadata.name, distribution.get_name()):
        if not candidate:
            continue
        if candidate == "UNKNOWN":
            name = "UNKNOWN"
            continue
        return canonicalize_name(candidate).replace("-", "_")
    return name


def _get_source_root(
    project_root: Path, distribution: Distribution, package_name: str | None
) -> Path:
    """
    Determines the source root based on package_dir mapping.
    """
    package_dir = getattr(distribution, "package_dir", None) or {}
    rel_src = package_dir.get("", "")

    if package_name and package_name != "UNKNOWN":
        possible_keys = {package_name, package_name.replace("_", "-")}
        for key in possible_keys:
            if key in package_dir:
                rel_src = package_dir[key]
                break

    return project_root / rel_src


def _probe_filesystem_context(project_root: Path) -> tuple[Path, str] | None:
    """
    Searches for valid package directories containing an __init__.py.
    """
    for search_path in (project_root / "src", project_root):
        if not search_path.exists():
            continue
        valid_packages = [
            item.name
            for item in search_path.iterdir()
            if item.is_dir() and (item / "__init__.py").exists()
        ]
        if valid_packages:
            return search_path, valid_packages[0]
    return None


def _inject_output_into_distribution(
    distribution: Distribution,
    output_path: Path,
    source_root: Path,
    package_name: str,
) -> None:
    """
    Registers the generated version file into the distribution metadata.
    """
    # Attempt 1: File is inside the specific package directory
    package_folder = source_root / package_name
    try:
        relative_output = str(output_path.relative_to(package_folder))

        packages = getattr(distribution, "packages", None)
        if packages is None:
            distribution.packages = [package_name]
        elif package_name not in packages:
            distribution.packages = list(packages) + [package_name]

        distribution.package_data.setdefault(package_name, []).append(relative_output)
        return
    except ValueError:
        pass

    # Attempt 2: File is a top-level module (flat layout)
    try:
        relative_module = str(output_path.relative_to(source_root))
        if "/" not in relative_module and output_path.suffix == ".py":
            modules = getattr(distribution, "py_modules", None)
            if modules is None:
                distribution.py_modules = []

            module_name = output_path.stem
            if module_name not in distribution.py_modules:
                distribution.py_modules.append(module_name)
            return
    except ValueError:
        pass

    logger.warning(
        f"Version file {output_path} is outside of source root {source_root}"
    )
