"""
Setuptools plugin integration for GitVersioned.

This module provides the entry points for setuptools to automatically compute
and inject the version resolved by GitVersioned into the package metadata.
It registers keywords and finalizes the distribution options by loading the
configuration and generating the version.

Example:
::
    from setuptools import Distribution
    from gitversioned.plugins.setuptools_plugin import finalize_distribution_options

    dist = Distribution({"name": "my-package", "gitversioned": {}})
    finalize_distribution_options(dist)
    print(dist.version)
"""

from __future__ import annotations

try:
    from setuptools.errors import SetupError as DistutilsSetupError
except ImportError:
    try:
        from distutils.errors import DistutilsSetupError
    except ImportError:
        DistutilsSetupError = Exception  # type: ignore

from pathlib import Path
from typing import Any

from packaging.utils import canonicalize_name
from setuptools import Distribution

from gitversioned.logging import configure_logger, logger
from gitversioned.settings import Settings
from gitversioned.utils import BuildEnvironment, GitRepository
from gitversioned.versioning import resolve_and_generate_version

__all__ = ["finalize_distribution_options", "setup_keywords"]


def _get_package_name(distribution: Distribution) -> str:
    name = distribution.metadata.name

    if not name or name == "UNKNOWN":
        name = distribution.get_name()

    if not name or name == "UNKNOWN":
        raise DistutilsSetupError("Could not determine package name.")

    return canonicalize_name(name)


def _get_project_paths(
    distribution: Distribution, package_name: str
) -> tuple[Path, Path]:
    project_root = Path(distribution.src_root) if distribution.src_root else Path.cwd()
    rel_src_root = ""
    package_dir = getattr(distribution, "package_dir", None) or {}
    if "" in package_dir:
        rel_src_root = package_dir[""]
    if package_name in package_dir:
        rel_src_root = package_dir[package_name]
    src_root = project_root / rel_src_root

    return project_root, src_root


def setup_keywords(distribution: Distribution, attr: str, value: Any) -> None:
    """
    Parse and inject the gitversioned keyword configuration into the distribution.

    This function is intended to be used as a setuptools ``setup_keywords`` entry point.
    It validates that the keyword argument is ``gitversioned`` and that its value is a
    dictionary before attaching it to the distribution for later processing.

    :param distribution: The setuptools distribution object.
    :param attr: The setup keyword attribute name.
    :param value: The configuration dictionary provided to the keyword.
    :return: None
    :raises DistutilsSetupError: If the attribute is not ``gitversioned`` or the
        value is not a dict.
    """
    if attr != "gitversioned":
        raise DistutilsSetupError(f"Unknown keyword argument: {attr}")

    if not isinstance(value, dict):
        raise DistutilsSetupError("gitversioned must be a dict")

    distribution.gitversioned_config = value


def finalize_distribution_options(distribution: Distribution) -> None:
    """
    Compute and inject the resolved version into the setuptools distribution.

    This function acts as a setuptools ``finalize_distribution_options`` entry point.
    It resolves the package name, extracts the base configuration from the distribution
    and environment, initializes the settings, and triggers version resolution.

    :param distribution: The setuptools distribution object being built.
    :return: None
    """
    configure_logger()

    version = getattr(distribution, "version", None)
    if version not in (None, "", "0.0.0"):
        logger.warning(
            "Version already set to non-default value; skipping.",
            extra={
                "plugin.name": "setuptools",
                "version.current": version,
                "event.type": "plugin.version_already_set",
            },
        )
        return

    is_editable = getattr(distribution, "editable", False)
    pkg_name = _get_package_name(distribution)
    project_root, src_root = _get_project_paths(distribution, pkg_name)
    kwargs = {
        "package_name": pkg_name,
        "project_root": project_root,
        "src_root": src_root,
        "build_is_editable": is_editable,
    }
    kwargs.update(getattr(distribution, "gitversioned_config", {}))
    config = Settings(**kwargs)  # type: ignore[arg-type]
    repo = GitRepository(config.project_root)
    build_env = BuildEnvironment(project_root=config.project_root)
    version, _ = resolve_and_generate_version(
        settings=config, repository=repo, environment=build_env
    )

    if hasattr(distribution, "metadata"):
        distribution.metadata.version = str(version)
    distribution.version = str(version)
    logger.info(
        "git-versioned set distribution version",
        extra={
            "plugin.name": "setuptools",
            "package.name": pkg_name,
            "version.computed": version,
            "event.type": "plugin.version_set",
        },
    )
