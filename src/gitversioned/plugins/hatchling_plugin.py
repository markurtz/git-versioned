"""
Hatchling version source plugin for GitVersioned.

This module provides the Hatchling plugin interface to dynamically resolve project
versions from Git state. It bridges Hatch's versioning configuration with GitVersioned's
core version resolution and file generation engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from hatchling.metadata.core import ProjectMetadata
from hatchling.plugin import hookimpl
from hatchling.version.source.plugin.interface import VersionSourceInterface
from loguru import logger

from gitversioned.logging import LoggingSettings, configure_logger
from gitversioned.settings import Settings
from gitversioned.utils import BuildEnvironment, GitRepository
from gitversioned.versioning import resolve_and_generate_version

__all__ = [
    "GitVersionedVersionSource",
    "hatch_register_version_source",
]


class GitVersionedVersionSource(VersionSourceInterface):
    """
    Hatchling version source interface for GitVersioned.

    This class provides the implementation for the Hatchling version source plugin
    interface, allowing projects using Hatchling to dynamically resolve their versions
    via GitVersioned. It handles version resolution, manual version setting, and project
    metadata extraction.

    .. code-block:: python

        source = GitVersionedVersionSource(root_dir, config)
        version_data = source.get_version_data()

    :cvar PLUGIN_NAME: The registered name of the plugin within the Hatchling ecosystem
    """

    PLUGIN_NAME: ClassVar[str] = "gitversioned"  # type: ignore[misc]

    def get_version_data(self) -> dict[str, str]:
        """
        Computes the project version from Git state.

        Resolves the version using the Git repository, build environment, and combined
        configuration context, optionally generating a version file if configured.

        .. code-block:: python

            data = source.get_version_data()
            version = data["version"]

        :return: A dictionary containing the resolved version string under
            the 'version' key
        :raises ValueError: If the version resolution process fails
        """
        configure_logger(LoggingSettings(enabled=True))
        logger.debug("GitVersionedVersionSource.get_version_data called")

        config = Settings(**self.get_settings_kwargs())
        repo = GitRepository(config.project_root)
        build_env = BuildEnvironment(project_root=config.project_root)
        version, output_path = resolve_and_generate_version(
            settings=config,
            repository=repo,
            environment=build_env,
        )

        logger.info(
            f"gitversioned computed version {version} and wrote it to {output_path}"
        )

        return {"version": str(version)}

    def set_version(
        self,
        version: str,
        version_data: dict[str, Any],  # noqa: ARG002
    ) -> None:
        """
        Handler for manual version setting via the Hatch CLI.

        This method updates the configured version source file with the explicitly
        provided version, making it the new persistent version source.

        .. code-block:: python

            source.set_version("1.2.3", {})

        :param version: The raw version string passed by the user
        :param version_data: Additional version data context from Hatchling
        """
        _ = (version_data,)  # to avoid lint errors for unused parameters
        logger.debug(
            f"GitVersionedVersionSource.set_version called with version='{version}'"
        )

        config = Settings(**self.get_settings_kwargs())
        if config.version_source_file:
            version_source_path = config.project_root / config.version_source_file
            version_source_path.write_text(f"version={version}\n", encoding="utf-8")

            logger.info(f"gitversioned set version {version} in {version_source_path}")
        else:
            logger.warning("version_source_file is not set; skipping manual update")

    def get_settings_kwargs(self) -> dict[str, Any]:
        """
        Extracts and prepares the configuration settings for GitVersioned.

        Gathers the project root, package name, source root, and plugin configuration
        from the Hatchling environment to construct the GitVersioned settings.

        .. code-block:: python

            kwargs = source.get_settings_kwargs()
            settings = Settings(**kwargs)

        :return: A dictionary of keyword arguments for configuring GitVersioned
        """
        project_root = self.get_project_root()
        package_name = self.get_package_name()
        src_root = self.get_src_root()

        kwargs = {
            "package_name": package_name,
            "project_root": project_root,
            "src_root": src_root,
            "build_is_editable": False,
        }
        kwargs.update(self.config)

        return kwargs

    def get_project_root(self) -> Path:
        """
        Resolves the absolute path to the project root directory.

        .. code-block:: python

            root = source.get_project_root()

        :return: The resolved absolute path to the project root
        """
        return Path(self.root).resolve()

    def get_package_name(self) -> str:
        """
        Retrieves the normalized package name from project metadata.

        Extracts the project name from the Hatchling metadata and normalizes it
        by replacing hyphens with underscores.

        .. code-block:: python

            name = source.get_package_name()

        :return: The normalized package name
        """
        root = self.get_project_root()
        metadata: Any = ProjectMetadata(str(root), None)
        return metadata.name.replace("-", "_")

    def get_src_root(self) -> Path:
        """
        Determines the source root directory for the project.

        Resolves the source directory by checking explicit plugin configuration,
        Hatchling build targets, or falling back to standard repository layouts
        like 'src/package_name' or 'package_name'.

        .. code-block:: python

            src_root = source.get_src_root()

        :return: The resolved path to the source root directory
        """
        root = self.get_project_root()

        if "project_root" in self.config:
            return Path(root) / str(self.config["project_root"])

        metadata: Any = ProjectMetadata(str(root), None)
        hatch_config = (
            metadata.config.get("tool", {})
            .get("hatch", {})
            .get("build", {})
            .get("targets", {})
            .get("wheel", {})
        )

        packages = hatch_config.get("packages", None)
        if packages and isinstance(packages, list):
            return root / packages[0]

        sources = hatch_config.get("sources", None)
        if sources and isinstance(sources, dict):
            return root / list(sources.keys())[0]

        package_name = self.get_package_name()

        src_path = root / "src" / package_name
        if src_path.exists():
            return src_path

        pkg_path = root / package_name
        if pkg_path.exists():
            return pkg_path

        return root


@hookimpl
def hatch_register_version_source() -> type[VersionSourceInterface]:
    """
    Register the GitVersioned source plugin with Hatchling.

    Provides the entry point for Hatchling to discover and load the
    GitVersionedVersionSource plugin implementation.

    .. code-block:: python

        plugin_class = hatch_register_version_source()

    :return: The class representing the plugin interface
    """
    return GitVersionedVersionSource
