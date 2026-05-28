"""Hatchling version source plugin for GitVersioned.

This module provides the Hatchling plugin interface for GitVersioned, allowing
Hatchling-based projects to resolve their dynamic package version directly from
the repository's Git history and environment state. It acts as a bridge between
Hatch's custom versioning hook framework and GitVersioned's core resolution and
generation logic.

The main plugin implementation is defined in the GitVersionedVersionSource
class, which is registered with Hatchling via the
hatch_register_version_source entry point.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from hatchling.metadata.core import ProjectMetadata
from hatchling.plugin import hookimpl
from hatchling.version.source.plugin.interface import VersionSourceInterface

from gitversioned.logging import LoggingSettings, autolog, configure_logger, logger
from gitversioned.settings import Settings
from gitversioned.utils import BuildEnvironment, GitRepository
from gitversioned.versioning import resolve_version_output_to_stream

__all__ = [
    "GitVersionedVersionSource",
    "hatch_register_version_source",
]


class GitVersionedVersionSource(VersionSourceInterface):
    """Hatchling version source interface for GitVersioned.

    This class implements the Hatchling VersionSourceInterface to resolve and
    manage project versions dynamically. It hooks into the Hatchling build
    lifecycle, retrieving version information from Git tags, commits, or
    environment variables and passing it to the package builder.

    By extending Hatchling's standard interface, it integrates directly with
    tools like Hatch build or Hatch publish, enabling zero-configuration
    version resolution for end users.

    .. code-block:: python

        from gitversioned.plugins.hatchling_plugin import GitVersionedVersionSource

        # Instantiate the plugin with project root and Hatch config
        source = GitVersionedVersionSource(root="/path/to/project", config={})
        version_info = source.get_version_data()

    :cvar PLUGIN_NAME: The registered name of this plugin within the Hatchling
        build system
    """

    PLUGIN_NAME: str = "gitversioned"

    def __init__(self, root: str, config: dict[str, Any]) -> None:
        """Initialize the GitVersioned version source plugin with project details.

        :param root: The project root directory path
        :param config: The plugin configuration dictionary from Hatchling
        """
        super().__init__(root, config)
        self._metadata: ProjectMetadata | None = None

    def get_version_data(self) -> dict[str, str]:
        """Compute the project version based on Git state and configuration.

        Resolves the version using the Git repository, build environment, and
        plugin configuration, and optionally writes the resolved version to a
        generated file if configured.

        .. code-block:: python

            version_data = source.get_version_data()
            version_str = version_data["version"]

        :returns: A dictionary containing the resolved version string mapped to
            the 'version' key
        :raises ValueError: If the version resolution process fails or cannot
            find a valid Git state
        """
        configure_logger(LoggingSettings(enabled=True))
        logger.debug("GitVersionedVersionSource.get_version_data called")

        resolved = os.environ.get("GITVERSIONED_RESOLVED_VERSION")
        if resolved:
            logger.info(f"Using resolved version from environment: {resolved}")
            return {"version": resolved}

        config = Settings(**self.get_settings_kwargs())
        repo = GitRepository(config.project_root)
        build_env = BuildEnvironment(project_root=config.project_root)
        output_path, _, version, _, _ = resolve_version_output_to_stream(
            settings=config,
            repository=repo,
            environment=build_env,
        )

        logger.info(
            f"gitversioned computed version {version} and wrote it to {output_path}"
        )

        return {"version": str(version)}

    def set_version(self, version: str, version_data: dict[str, Any]) -> None:
        """Set the project version manually, updating the version source file.

        This handler is invoked when writing a version via Hatch CLI (e.g.,
        `hatch version <version>`), persisting the version string to the
        configured file.

        .. code-block:: python

            source.set_version(version="1.2.3", version_data={})

        :param version: The raw version string to set
        :param version_data: Additional version context provided by Hatchling
        """
        logger.debug(
            "GitVersionedVersionSource.set_version called with "
            f"version='{version}', context={version_data}"
        )

        config = Settings(**self.get_settings_kwargs())
        if config.version_source_file:
            version_source_path = config.project_root / config.version_source_file
            version_source_path.write_text(f"version={version}\n", encoding="utf-8")

            logger.info(f"gitversioned set version {version} in {version_source_path}")
        else:
            logger.warning("version_source_file is not set; skipping manual update")

    @autolog
    def get_settings_kwargs(self) -> dict[str, Any]:
        """Extract and prepare the configuration dictionary for GitVersioned settings.

        Gathers the project metadata (root directory, package name, source root)
        and combines it with Hatch plugin-specific configurations to build
        keyword arguments.

        .. code-block:: python

            kwargs = source.get_settings_kwargs()

        :returns: A dictionary of configuration options compatible with
            GitVersioned settings
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

        plugin_config = self.config.copy()
        plugin_config.pop("project_root", None)
        plugin_config.pop("src_root", None)

        kwargs.update(plugin_config)

        return kwargs

    def get_project_root(self) -> Path:
        """Resolve the absolute path to the project root directory.

        .. code-block:: python

            root_path = source.get_project_root()

        :returns: The resolved absolute path to the project root
        """
        return Path(self.root).resolve()

    def get_package_name(self) -> str:
        """Retrieve and normalize the package name from project metadata.

        Extracts the project name from the Hatchling project configuration and replaces
        hyphens with underscores for Python package compatibility.

        .. code-block:: python

            pkg_name = source.get_package_name()

        :returns: The normalized Python package name
        """
        metadata = self._get_metadata()
        return metadata.name.replace("-", "_")

    def get_src_root(self) -> Path:
        """Determine the source root directory for the project.

        Resolves the directory containing the source package by checking the
        explicit src_root configuration, Hatchling build target package paths,
        or falling back to directory layout conventions.

        .. code-block:: python

            src_root = source.get_src_root()

        :returns: The resolved Path to the source root directory
        """
        root = self.get_project_root()

        if "src_root" in self.config:
            return Path(root) / str(self.config["src_root"])

        metadata = self._get_metadata()
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
            return root / str(list(sources.keys())[0])

        package_name = self.get_package_name()

        src_path = root / "src" / package_name
        if src_path.exists():
            return src_path

        pkg_path = root / package_name
        if pkg_path.exists():
            return pkg_path

        return root

    def _get_metadata(self) -> ProjectMetadata:
        if self._metadata is None:
            self._metadata = ProjectMetadata(str(self.get_project_root()), None)
        return self._metadata


@hookimpl
def hatch_register_version_source() -> type[VersionSourceInterface]:
    """Register the GitVersioned version source plugin with the Hatchling build system.

    Provides the entry point hook for Hatchling to locate and instantiate the custom
    GitVersionedVersionSource version source implementation.

    .. code-block:: python

        from gitversioned.plugins.hatchling_plugin import hatch_register_version_source

        plugin_type = hatch_register_version_source()

    :returns: The GitVersionedVersionSource class implementing VersionSourceInterface
    """
    return GitVersionedVersionSource
