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
import contextlib
import re
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import Field, model_validator
from pydantic_settings import (
    BaseSettings,
    CliSettingsSource,
    PydanticBaseSettingsSource,
    PyprojectTomlConfigSettingsSource,
    SettingsConfigDict,
)

from gitversioned.compat import tomllib
from gitversioned.utils import EnsureList, EnsurePath

__all__ = ["Settings", "SetupCfgSettingsSource"]


class SetupCfgSettingsSource(PydanticBaseSettingsSource):
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
        base_section = "tool:gitversioned"

        result: dict[str, Any] = {}
        if base_section in config_parser:
            result.update(config_parser.items(base_section))

        prefix = f"{base_section}:"
        for section in config_parser.sections():
            if section.startswith(prefix):
                key = section[len(prefix) :]
                val = result.get(key, {})
                if not isinstance(val, dict):
                    val = {"_": val}

                val.update(config_parser.items(section))
                result[key] = val

        return result


class Settings(BaseSettings):
    """
    Configuration for GitVersioned, handling formatting, strictness, and outputs.

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
        default="auto",
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
    regex_version: EnsureList[str] = cast(
        "EnsureList[str]",
        Field(
            default_factory=lambda: [
                r"^(?:releases?/)?v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$"
            ],
            description="Regex used to extract version from explicit version strings.",
        ),
    )
    regex_tag: EnsureList[str] = cast(
        "EnsureList[str]",
        Field(
            default_factory=lambda: [
                r"^(?:releases?/)?v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$"
            ],
            description="Regex used to find version tags and extract the version.",
        ),
    )
    regex_branch: EnsureList[str] = cast(
        "EnsureList[str]",
        Field(
            default_factory=lambda: [
                r"^(?:releases?/)?v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
            ],
            description="Regex used to extract version from the current branch.",
        ),
    )
    regex_commit: EnsureList[str] = cast(
        "EnsureList[str]",
        Field(
            default_factory=lambda: [
                r"(?i)^(?:release\s+|bump(?:\s+\w+)*\s+)?"
                r"v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
            ],
            description="Regex used to extract version from previous commits.",
        ),
    )
    regex_file: EnsureList[str] = cast(
        "EnsureList[str]",
        Field(
            default_factory=lambda: [
                r"(?i)(?:version|__version__)\s*[:=]\s*['\"]?"
                r"(v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?:[a-zA-Z0-9.\-]+)?)"
                r"['\"]?"
            ],
            description="Regex used to extract version from a file.",
        ),
    )
    regex_archive: EnsureList[str] = cast(
        "EnsureList[str]",
        Field(
            default_factory=lambda: [
                r"(?sm)"
                r"(?=.*^commit_sha:\s*(?P<commit_sha>[^\n]*))"
                r"(?=.*^short_sha:\s*(?P<short_sha>[^\n]*))"
                r"(?=.*^timestamp:\s*(?P<timestamp>[^\n]*))"
                r"(?=.*^author_name:\s*(?P<author_name>[^\n]*))"
                r"(?=.*^author_email:\s*(?P<author_email>[^\n]*))"
                r"(?=.*^ref_names:\s*(?P<ref_names>[^\n]*))"
                r"(?=.*^ref_names:.*?(?:v)?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+))"
                r"(?=.*^distance_from_head:\s*(?P<distance_from_head>[^\n]*))"
                r"(?=.*^is_head_commit:\s*(?P<is_head_commit>[^\n]*))"
                r"(?=.*^total_commits:\s*(?P<total_commits>[^\n]*))"
                r"(?=.*^is_current_branch:\s*(?P<is_current_branch>[^\n]*))"
                r"(?=.*^commit_message:\n(?P<commit_message>.*))"
            ],
            description=(
                "Regex patterns used to extract versions/metadata from "
                "an archive export."
            ),
        ),
    )
    version_source_file: str | None = Field(
        default="version.txt",
        description="File to pull version from if searching local sources.",
    )
    version_source_archive: str | None = Field(
        default=".git_archival.txt",
        description="File to pull version from if executed from a git archive.",
    )
    version_source_function: str | None = Field(
        default=None,
        description="Module and function to resolve version and git reference.",
    )
    source_type: EnsureList[str] = cast(
        "EnsureList[str]",
        Field(
            default_factory=lambda: ["auto"],
            description="Priority order of source types to extract the version from.",
        ),
    )
    dirty_ignore: EnsureList[str] = Field(
        default_factory=list,
        description=(
            "List of file paths to ignore when checking if the repository is dirty."
        ),
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
    output: str = Field(
        default="version.py",
        description=(
            "Where the version string is written (file path, 'sys.stdout' for stdout)."
        ),
    )
    pattern_release: str = Field(
        default_factory=(
            Path(__file__).parent / "templates" / "release.py.template"
        ).read_text,
        description=(
            "Output representation for release builds. Supports default "
            "templates, aliases ('template', 'cargo', 'pyproject'), "
            "file paths, or custom string/regex."
        ),
    )
    pattern_dev: str = Field(
        default_factory=(
            Path(__file__).parent / "templates" / "dev.py.template"
        ).read_text,
        description=(
            "Output representation for dev builds. Supports default "
            "templates, aliases ('template', 'cargo', 'pyproject'), "
            "file paths, or custom string/regex."
        ),
    )
    build_backend: str | None = Field(
        default=None,
        validation_alias="GITVERSIONED_BUILD_BACKEND",
        description=(
            "Target build backend to delegate to (e.g. 'maturin' or "
            "'setuptools.build_meta')."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_keys(cls, data: Any) -> Any:
        """Normalize legacy/dashed keys to standard settings field names."""
        if isinstance(data, dict):
            # Normalize build-backend / build_backend
            if "build-backend" in data and "build_backend" not in data:
                data["build_backend"] = data.pop("build-backend")
            # Normalize output_file / output
            if "output_file" in data and "output" not in data:
                data["output"] = data.pop("output_file")
            if "output-file" in data and "output" not in data:
                data["output"] = data.pop("output-file")
            # Normalize template_release / pattern_release
            if "template_release" in data and "pattern_release" not in data:
                data["pattern_release"] = data.pop("template_release")
            if "template-release" in data and "pattern_release" not in data:
                data["pattern_release"] = data.pop("template-release")
            # Normalize template_dev / pattern_dev
            if "template_dev" in data and "pattern_dev" not in data:
                data["pattern_dev"] = data.pop("template_dev")
            if "template-dev" in data and "pattern_dev" not in data:
                data["pattern_dev"] = data.pop("template-dev")
        return data

    @model_validator(mode="after")
    def _resolve_auto_fields(self) -> Settings:
        """Resolve dynamic fields like package_name and src_root.

        This is performed when fields are configured to 'auto'.
        """
        if self.package_name == "auto":
            self.package_name = self._detect_package_name()

        # Resolve src_root if it is default (equal to project_root)
        if self.src_root == self.project_root:
            pkg_name = self.package_name
            src_pkg = self.project_root / "src" / pkg_name
            pkg_dir = self.project_root / pkg_name
            if src_pkg.exists() and src_pkg.is_dir():
                self.src_root = src_pkg
            elif pkg_dir.exists() and pkg_dir.is_dir():
                self.src_root = pkg_dir
        return self

    def _detect_package_name(self) -> str:
        """Detect package name from various config files or folder name."""
        # 1. Try to read from pyproject.toml
        pyproject_path = self.project_root / "pyproject.toml"
        if pyproject_path.exists() and tomllib is not None:
            try:
                with pyproject_path.open("rb") as f:
                    data = tomllib.load(f)
                    name = data.get("project", {}).get("name")
                    if name:
                        return str(name).replace("-", "_")
            except (OSError, ValueError):
                with contextlib.suppress(OSError, ValueError):
                    content = pyproject_path.read_text(encoding="utf-8")
                    match = re.search(r'(?m)^name\s*=\s*["\']([^"\']+)["\']', content)
                    if match:
                        return match.group(1).replace("-", "_")

        # 2. Try to read from setup.cfg
        setup_cfg_path = self.project_root / "setup.cfg"
        if setup_cfg_path.exists():
            with contextlib.suppress(OSError, configparser.Error):
                config = configparser.ConfigParser()
                config.read(setup_cfg_path)
                name = config.get("metadata", "name", fallback=None)
                if name:
                    return name.replace("-", "_")

        # 3. Fallback to project root directory name
        return self.project_root.name.replace("-", "_")

    def __str__(self) -> str:
        """Return a concise string representation."""
        return (
            f"Settings(package_name={self.package_name!r}, version={self.version!r}, "
            f"version_type={self.version_type!r}, project_root={self.project_root!r}, "
            f"src_root={self.src_root!r}, source_type={self.source_type!r}, "
            f"auto_increment={self.auto_increment!r}, output={self.output!r},"
            f" dirty_ignore={self.dirty_ignore!r})"
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
            f"source_type={self.source_type!r}, dirty_ignore={self.dirty_ignore!r}, "
            f"auto_increment={self.auto_increment!r}, "
            f"version_type={self.version_type!r}, output={self.output!r}, "
            f"pattern_release={self.pattern_release!r}, "
            f"pattern_dev={self.pattern_dev!r}, "
            f"build_backend={self.build_backend!r}"
            f")"
        )
