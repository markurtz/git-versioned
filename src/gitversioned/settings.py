"""
Settings module for GitVersioned.

This module provides the primary configuration structure for resolving
version information from Git using Pydantic Settings. It aggregates configuration
from multiple sources, including config files (pyproject.toml, setup.cfg),
environment variables, and CLI arguments, and exposes a unified interface.

Example:
    ::

        settings = Settings(package_name="my_pkg")
        print(settings.format_main)
"""

from __future__ import annotations

import configparser
from pathlib import Path
from typing import Any, Literal

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    CliSettingsSource,
    PydanticBaseSettingsSource,
    PyprojectTomlConfigSettingsSource,
    SettingsConfigDict,
)

from gitversioned.utils import EnsureList, EnsurePath

__all__ = ["Settings"]


class SetupCfgSettingsSource(PydanticBaseSettingsSource):  # type: ignore[misc, abstract]
    """Custom settings source to load configuration from setup.cfg."""

    def __init__(self, settings_cls: type[BaseSettings], project_root: Path) -> None:
        super().__init__(settings_cls)
        self.project_root = project_root

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        _ = (field,)  # Allow unused variable to satisfy lint/format
        return self()[field_name], field_name, False

    def __call__(self) -> dict[str, Any]:
        path = self.project_root / "setup.cfg"
        if not path.exists():
            return {}

        config_parser = configparser.ConfigParser()
        config_parser.read(path)
        section = "tool:gitversioned"

        return dict(config_parser.items(section)) if section in config_parser else {}


class Settings(BaseSettings):
    """Configuration for GitVersioned, handling formatting, strictness, and outputs.

    This class aggregates and prioritizes configuration from multiple sources,
    providing a unified state for version resolution across the tool. It is built
    on top of pydantic-settings to allow validation and type coercion.

    Example:
        ::

            settings = Settings(package_name="my_pkg")
            print(settings.format_main)
    """

    model_config = SettingsConfigDict(
        arbitrary_types_allowed=True,
        extra="ignore",
        populate_by_name=True,
        validate_assignment=True,
        env_prefix="GITVERSIONED__",
        cli_prefix="gitversioned_",
        cli_parse_args=True,
        pyproject_toml_table_header=("tool", "gitversioned"),
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customizes the configuration sources and their priority.

        This method overrides the default pydantic-settings source priority to
        inject our custom `SetupCfgSettingsSource` and define the specific order
        of resolution.

        :param settings_cls: The settings class being instantiated.
        :param init_settings: The initial settings provided via kwargs.
        :param env_settings: Settings loaded from environment variables.
        :param dotenv_settings: Settings loaded from a .env file.
        :param file_secret_settings: Settings loaded from secret files.
        :return: A tuple of settings sources in priority order.
        """
        _ = (file_secret_settings,)  # Allow unused variable to satisfy lint/format
        input_args = init_settings()
        project_root = input_args.get("project_root") or Path.cwd()

        return (
            init_settings,
            SetupCfgSettingsSource(settings_cls, project_root=project_root),
            PyprojectTomlConfigSettingsSource(
                settings_cls, toml_file=project_root / "pyproject.toml"
            ),
            dotenv_settings,
            env_settings,
            CliSettingsSource(
                settings_cls,
                cli_ignore_unknown_args=True,
                cli_parse_args=True,
                cli_prefix=settings_cls.model_config.get("cli_prefix", ""),
            ),
        )

    # GitVersioned Configuration
    package_name: str = Field(
        description="The package name being versioned.",
    )
    version: str = Field(
        default="auto",
        description="Explicit version override. 'auto' enables dynamic resolution.",
    )
    project_root: EnsurePath = Field(
        default_factory=Path.cwd,
        description="The root directory of the project.",
    )
    src_root: EnsurePath = Field(
        default_factory=Path.cwd,
        description="The root directory of the project source code.",
    )
    build_is_editable: bool = Field(
        default=False,
        description="Flag indicating if the current build is an editable install.",
    )

    # Formatting properties
    format_main: str = Field(
        default="{version.major}.{version.minor}.{version.micro}",
        description="Format for main semantic versioning.",
    )
    format_dev: str = Field(
        default="dev{ref.timestamp:%Y%m%d}+{ref.short_sha}",
        description="Format for dev builds.",
    )
    format_pre: str = Field(
        default="a{ref.timestamp:%Y%m%d}",
        description="Format for pre/alpha builds.",
    )
    format_post: str = Field(
        default="post{ref.distance_from_head}",
        description="Format for post builds.",
    )

    # Sourcing properties
    regex_tag: EnsureList[str] = Field(
        default_factory=lambda: [  # type: ignore[arg-type]
            r"^(?:releases?/)?v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$"
        ],
        description="Regex used to find version tags and extract the version.",
    )
    regex_branch: EnsureList[str] = Field(
        default_factory=lambda: [  # type: ignore[arg-type]
            r"^(?:releases?/)?v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
        ],
        description="Regex used to extract version from the current branch.",
    )
    regex_commit: EnsureList[str] = Field(
        default_factory=lambda: [  # type: ignore[arg-type]
            r"(?i)^(?:release\s+|bump(?:\s+\w+)*\s+)?"
            r"v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
        ],
        description="Regex used to extract version from previous commits.",
    )
    regex_file: EnsureList[str] = Field(
        default_factory=lambda: [  # type: ignore[arg-type]
            r"(?i)(?:version|__version__)\s*[:=]\s*['\"]?"
            r"(v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?:[a-zA-Z0-9.\-]+)?)"
            r"['\"]?"
        ],
        description="Regex used to extract version from a file.",
    )
    version_source_file: str | None = Field(
        default="version.txt",
        description="File to pull version from if searching local sources.",
    )
    version_source_function: str | None = Field(
        default=None,
        description="Module and function to invoke for version string.",
    )
    source_type: EnsureList[str] = Field(
        default_factory=lambda: ["auto"],  # type: ignore[arg-type]
        description="Priority order of source types to extract the version from.",
    )

    # Creation & output properties
    auto_increment: (
        dict[
            Literal["release", "dev", "pre", "alpha", "nightly", "post"],
            Literal["major", "minor", "micro", "patch"],
        ]
        | None
    ) = Field(
        default=None,
        description=(
            "Target increment for specific version types when the repo is ahead of the "
            "last tag source."
        ),
    )
    version_type: Literal[
        "auto", "release", "dev", "pre", "alpha", "nightly", "post"
    ] = Field(
        default="auto",
        description="Type of version to create.",
    )
    output_file: str = Field(
        default="version.py",
        description="File path where the generated version string is written.",
    )
    template_release: str = Field(
        default_factory=(
            Path(__file__).parent / "templates" / "release.py.template"
        ).read_text,
        description="The ExStr template used for release builds.",
    )
    template_dev: str = Field(
        default_factory=(
            Path(__file__).parent / "templates" / "dev.py.template"
        ).read_text,
        description="The ExStr template used for dev builds.",
    )

    def __str__(self) -> str:
        """Return a concise string representation."""
        return (
            f"Settings(package_name={self.package_name!r}, version={self.version!r}, "
            f"version_type={self.version_type!r}, project_root={self.project_root!r}, "
            f"src_root={self.src_root!r}, source_type={self.source_type!r}, "
            f"auto_increment={self.auto_increment!r}, output_file={self.output_file!r})"
        )

    def __repr__(self) -> str:
        """Return a detailed string representation."""
        return (
            f"Settings("
            f"package_name={self.package_name!r}, version={self.version!r}, "
            f"project_root={self.project_root!r}, src_root={self.src_root!r}, "
            f"build_is_editable={self.build_is_editable!r}, "
            f"format_main={self.format_main!r}, format_dev={self.format_dev!r}, "
            f"format_pre={self.format_pre!r}, format_post={self.format_post!r}, "
            f"regex_tag={self.regex_tag!r}, regex_branch={self.regex_branch!r}, "
            f"regex_commit={self.regex_commit!r}, regex_file={self.regex_file!r}, "
            f"version_source_file={self.version_source_file!r}, "
            f"version_source_function={self.version_source_function!r}, "
            f"source_type={self.source_type!r}, "
            f"auto_increment={self.auto_increment!r}, "
            f"version_type={self.version_type!r}, output_file={self.output_file!r}, "
            f"template_release={self.template_release!r}, "
            f"template_dev={self.template_dev!r}"
            f")"
        )
