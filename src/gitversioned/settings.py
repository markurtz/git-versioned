"""
Configuration management settings for GitVersioned.

This module resolves and manages configuration parameters loaded from CLI arguments,
environment variables, and files like ``pyproject.toml`` or ``setup.cfg``.
"""

from __future__ import annotations

import configparser
import contextlib
import functools
import re
from pathlib import Path
from typing import Annotated, Any, Literal, cast

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import (
    BaseSettings,
    CliSettingsSource,
    PydanticBaseSettingsSource,
    PyprojectTomlConfigSettingsSource,
    SettingsConfigDict,
)

from gitversioned.compat import tomllib
from gitversioned.logging import autolog
from gitversioned.utils import EnsureList, EnsurePath

__all__ = [
    "IncrementLevel",
    "OutputStrategy",
    "RegexStrategy",
    "Settings",
    "SetupCfgSettingsSource",
    "TemplatePathStrategy",
    "TemplateStrStrategy",
    "VersionStandard",
    "VersionType",
]

VersionType = Annotated[
    Literal["auto", "release", "dev", "pre", "alpha", "nightly", "post"],
    "The type of version format to generate, driving version string construction.",
]
VersionStandard = Annotated[
    Literal["pep440", "semver2"],
    "The standard format used to normalize version strings.",
]
IncrementLevel = Annotated[
    Literal["major", "minor", "micro", "patch", "bug"],
    "The target segment level of the version to auto-increment.",
]


class TemplatePathStrategy(BaseModel):
    """
    Output strategy using a template file path.

    Resolves version files by reading a template file containing placeholder variables,
    replacing them with resolved version metadata, and writing to the output path.

    Example:
        ::

            strategy = TemplatePathStrategy(path=Path("templates/release.py.template"))
    """

    type: Literal["template_path"] = Field(
        default="template_path",
        description=(
            "Discriminator type field identifying the template path "
            "resolution strategy."
        ),
    )
    path: Path = Field(
        description=(
            "The file path containing the template text to format with "
            "version metadata."
        )
    )


class TemplateStrStrategy(BaseModel):
    """
    Output strategy using a raw template string.

    Formats the target version file utilizing an inline template string pattern
    defined directly in the configuration, rather than reading from a file.

    Example:
        ::

            strategy = TemplateStrStrategy(content="__version__ = '{version}'")
    """

    type: Literal["template_str"] = Field(
        default="template_str",
        description=(
            "Discriminator type field identifying the template string "
            "resolution strategy."
        ),
    )
    content: str = Field(
        description="The inline template string used to format the version file output."
    )


class RegexStrategy(BaseModel):
    """
    Output strategy using regex version replacement.

    Updates the version string inline in an existing file by searching for a match with
    a regex pattern and replacing the target named 'version' group.

    Example:
        ::

            strategy = RegexStrategy(pattern=r'version = "(?P<version>.*?)"')
    """

    type: Literal["regex"] = Field(
        default="regex",
        description=(
            "Discriminator type field identifying the regex-based replacement strategy."
        ),
    )
    pattern: str = Field(
        description=(
            "The regular expression containing a (?P<version>...) named group to "
            "locate and replace within the target file."
        )
    )


OutputStrategy = Annotated[
    TemplatePathStrategy | TemplateStrStrategy | RegexStrategy,
    (
        "The active output strategy configuration used to format and "
        "generate target version files."
    ),
    Field(
        discriminator="type",
        description=(
            "The active output strategy configuration used to format and "
            "generate target version files."
        ),
    ),
]


@autolog
def _detect_package_name(project_root: Path) -> str:
    # Detect package name from various config files or folder name.
    pyproject_path = project_root / "pyproject.toml"
    if pyproject_path.exists() and tomllib is not None:
        try:
            with pyproject_path.open("rb") as toml_file:
                data = tomllib.load(toml_file)
                name = data.get("project", {}).get("name")
                if name:
                    return str(name).replace("-", "_")
        except (OSError, ValueError):
            with contextlib.suppress(OSError, ValueError):
                content = pyproject_path.read_text(encoding="utf-8")
                match = re.search(r'(?m)^name\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    return match.group(1).replace("-", "_")

    setup_cfg_path = project_root / "setup.cfg"
    if setup_cfg_path.exists():
        with contextlib.suppress(OSError, configparser.Error):
            config = configparser.ConfigParser()
            config.read(setup_cfg_path)
            name = config.get("metadata", "name", fallback=None)
            if name:
                return name.replace("-", "_")

    return project_root.name.replace("-", "_")


@autolog
def _resolve_src_root(project_root: Path, package_name: str) -> Path:
    # Resolve src_root directory from project_root and package_name.
    src_pkg = project_root / "src" / package_name
    pkg_dir = project_root / package_name
    if src_pkg.exists() and src_pkg.is_dir():
        return src_pkg
    if pkg_dir.exists() and pkg_dir.is_dir():
        return pkg_dir
    return project_root


class SetupCfgSettingsSource(PydanticBaseSettingsSource):
    """
    Settings source for loading configurations from setup.cfg files.

    Extracts configuration parameters nested under the 'tool:gitversioned'
    sections of a project's setup.cfg file. Integrates as a custom source in
    the Pydantic settings management pipeline.

    Example:
        ::

            source = SetupCfgSettingsSource(Settings, project_root=Path.cwd())
            config = source()

    :ivar project_root: The root directory containing the setup.cfg file.
    """

    def __init__(self, settings_cls: type[BaseSettings], project_root: Path) -> None:
        """
        Initialize the setup.cfg settings source.

        :param settings_cls: The Settings class being configured.
        :param project_root: The root directory containing setup.cfg.
        """
        super().__init__(settings_cls)
        self.project_root = project_root

    def __call__(self) -> dict[str, Any]:
        """
        Retrieve loaded settings from setup.cfg.

        :return: Loaded configuration settings dict.
        """
        return self._config

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        """
        Get value for a configuration field from setup.cfg.

        :param field: The Pydantic Field object.
        :param field_name: The name of the field to fetch.
        :return: A tuple containing the field's value, name, and if it was found.
        :raises KeyError: If the field is not present in the settings source.
        """
        _ = (field,)  # Allow unused variable to satisfy lint/format
        config = self._config
        if field_name in config:
            return config[field_name], field_name, False
        raise KeyError(field_name)

    @functools.cached_property
    def _config(self) -> dict[str, Any]:
        # Load and parse configuration from setup.cfg and cache the result.
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
    Unified configuration settings for GitVersioned.

    Manages settings loaded from environment variables, configuration files (such as
    pyproject.toml or setup.cfg), CLI flags, and constructor inputs. Governs how
    the dynamic version parser resolves git refs, matches tags, and generates target
    version files.

    Example:
        ::

            settings = Settings(package_name="my_package")
            src_path = settings.resolve_path_from_src("my_package/__init__.py")

    :cvar model_config: Custom configuration dictionary settings for Pydantic.
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

    # Project Configuration
    package_name: str = Field(
        default="auto",
        description=(
            "The package name being versioned. "
            "Enables automatic package name detection when set to 'auto'."
        ),
    )
    project_root: EnsurePath = Field(
        default_factory=Path.cwd,
        description="The absolute path to the root directory of the project.",
    )
    src_root: EnsurePath = Field(
        default_factory=Path.cwd,
        description=(
            "The path to the source root directory. "
            "Enables automatic source directory fallback detection "
            "when set to 'auto'."
        ),
    )
    build_is_editable: bool = Field(
        default=False,
        description=(
            "Flag indicating whether the package is built as an editable installation."
        ),
    )

    # Version Source Configuration
    version: str = Field(
        default="auto",
        description=(
            "Explicit version override string. "
            "Enables dynamic version resolution from git/files "
            "when set to 'auto'."
        ),
    )
    source_type: Annotated[list[str], EnsureList()] = Field(
        default_factory=lambda: ["auto"],
        description="Priority order of sources to query for version information.",
    )
    version_source_file: str | None = Field(
        default="version.txt",
        description=(
            "Path to a file containing the version string. Set to None to disable."
        ),
    )
    version_source_archive: str | None = Field(
        default=".git_archival.txt",
        description=(
            "Path to a git-archive export info file used when "
            "Git is unavailable. Set to None to disable."
        ),
    )
    version_source_function: str | None = Field(
        default=None,
        description=(
            "A string pointing to a module and function (e.g. 'module:func') "
            "to resolve the version. Set to None to disable."
        ),
    )
    regex_version: Annotated[list[str], EnsureList()] = Field(
        default_factory=lambda: [
            r"^(?:releases?/)?v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$"
        ],
        description=(
            "Regular expression patterns to parse and validate "
            "the explicit version string."
        ),
    )
    regex_tag: Annotated[list[str], EnsureList()] = Field(
        default_factory=lambda: [
            r"^(?:releases?/)?v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$"
        ],
        description=(
            "Regular expression patterns to extract semantic versioning from Git tags."
        ),
    )
    regex_branch: Annotated[list[str], EnsureList()] = Field(
        default_factory=lambda: [
            r"^(?:releases?/)?v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
        ],
        description=(
            "Regular expression patterns to extract semantic "
            "versioning from the current Git branch name."
        ),
    )
    regex_commit: Annotated[list[str], EnsureList()] = Field(
        default_factory=lambda: [
            r"(?i)^(?:release\s+|bump(?:\s+\w+)*\s+)?"
            r"v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
        ],
        description=(
            "Regular expression patterns to extract semantic "
            "versioning from Git commit messages."
        ),
    )
    regex_file: Annotated[list[str], EnsureList()] = Field(
        default_factory=lambda: [
            r"(?i)(?:version|__version__)\s*[:=]\s*['\"]?"
            r"(v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?:[a-zA-Z0-9.\-+]+)?)"
            r"['\"]?"
        ],
        description=(
            "Regular expression patterns to parse version strings "
            "from version source files."
        ),
    )
    regex_archive: Annotated[list[str], EnsureList()] = Field(
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
            "Regular expression patterns to parse Git metadata "
            "from git-archive export files."
        ),
    )

    # Generated Version Configuration
    version_type: VersionType = Field(
        default="auto",
        description=(
            "The type of version format to generate (e.g. 'release', 'dev', or 'auto')."
        ),
    )
    version_standard: VersionStandard = Field(
        default="pep440",
        description=(
            "The standard formatting layout (PEP 440 or SemVer 2) "
            "to use for version normalization."
        ),
    )
    auto_increment: (
        dict[
            Literal["release", "dev", "pre", "alpha", "nightly", "post"],
            IncrementLevel,
        ]
        | None
    ) = Field(
        default=None,
        description=(
            "Target increment mapping to apply when ahead of the latest release tag."
        ),
    )
    format_main: str = Field(
        default="{version.major}.{version.minor}.{version.micro}",
        description="Format string for the main semantic version segment.",
    )
    format_dev: str = Field(
        default="dev{ref.timestamp:%Y%m%d}+{ref.short_sha}",
        description="Format string for development builds.",
    )
    format_pre: str = Field(
        default="a{ref.timestamp:%Y%m%d}",
        description="Format string for pre-release or alpha builds.",
    )
    format_post: str = Field(
        default="post{ref.distance_from_head}",
        description="Format string for post-release builds.",
    )
    dirty_ignore: Annotated[list[str], EnsureList()] = Field(
        default_factory=lambda: ["target", "build", "dist"],
        description=(
            "List of file paths and directories to ignore when "
            "checking if the repository is dirty."
        ),
    )

    # Generated Version Outputs Configuration
    output: str = Field(
        default="version.py",
        description="The target output path to write the generated version file.",
    )
    output_strategies: dict[str, OutputStrategy] | OutputStrategy = Field(
        default_factory=lambda: cast(
            "dict[str, OutputStrategy]",
            {
                "release": TemplatePathStrategy(
                    path=Path(__file__).parent / "templates" / "release.py.template",
                ),
                "dev": TemplatePathStrategy(
                    path=Path(__file__).parent / "templates" / "dev.py.template",
                ),
            },
        ),
        description="Output strategies for formatting the version file.",
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
        """
        Customize configuration sources and priority for loading settings.

        This method overrides the default pydantic-settings loaders to resolve
        values in the following order: constructor kwargs, setup.cfg,
        pyproject.toml, dotenv files, environment variables, and CLI arguments.

        :param settings_cls: The BaseSettings subclass being initialized.
        :param init_settings: Source loading constructor keyword arguments.
        :param env_settings: Source loading environment variables.
        :param dotenv_settings: Source loading .env files.
        :param file_secret_settings: Source loading file secrets.
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

    def __str__(self) -> str:
        """
        Return a concise string representation of the settings.

        :return: Concise string representation.
        """
        return (
            f"{self.__class__.__name__}("
            f"package_name={self.package_name!r}, "
            f"version={self.version!r}, "
            f"version_type={self.version_type!r}, "
            f"project_root={self.project_root!r}, "
            f"src_root={self.src_root!r}, "
            f"source_type={self.source_type!r}, "
            f"auto_increment={self.auto_increment!r}, "
            f"output={self.output!r}, "
            f"dirty_ignore={self.dirty_ignore!r}"
            f")"
        )

    def __repr__(self) -> str:
        """
        Return a detailed string representation of the settings.

        :return: Detailed string representation of settings.
        """
        return (
            f"{self.__class__.__name__}("
            f"package_name={self.package_name!r}, "
            f"project_root={self.project_root!r}, "
            f"src_root={self.src_root!r}, "
            f"build_is_editable={self.build_is_editable!r}, "
            f"version={self.version!r}, "
            f"source_type={self.source_type!r}, "
            f"version_source_file={self.version_source_file!r}, "
            f"version_source_archive={self.version_source_archive!r}, "
            f"version_source_function={self.version_source_function!r}, "
            f"regex_version={self.regex_version!r}, "
            f"regex_tag={self.regex_tag!r}, "
            f"regex_branch={self.regex_branch!r}, "
            f"regex_commit={self.regex_commit!r}, "
            f"regex_file={self.regex_file!r}, "
            f"regex_archive={self.regex_archive!r}, "
            f"version_type={self.version_type!r}, "
            f"version_standard={self.version_standard!r}, "
            f"auto_increment={self.auto_increment!r}, "
            f"format_main={self.format_main!r}, "
            f"format_dev={self.format_dev!r}, "
            f"format_pre={self.format_pre!r}, "
            f"format_post={self.format_post!r}, "
            f"dirty_ignore={self.dirty_ignore!r}, "
            f"output={self.output!r}, "
            f"output_strategies={self.output_strategies!r}"
            f")"
        )

    @autolog
    def resolve_path_from_root(
        self, path: str | Path | None, enforce_existence: bool = True
    ) -> Path | None:
        """
        Resolve a path relative to the project root or source root.

        This method attempts to resolve the given path first from the project root,
        falling back to the source root if it is not found.

        Example:
            ::

                path = settings.resolve_path_from_root("version.txt")

        :param path: The path to resolve.
        :param enforce_existence: Whether to enforce that the path exists.
        :return: The resolved absolute Path if it exists (or if not enforcing
            existence), otherwise None.
        """
        if enforce_existence:
            return self.resolve_path_from_project(
                path, enforce_existence=True
            ) or self.resolve_path_from_src(path, enforce_existence=True)
        else:
            resolved = self.resolve_path_from_project(
                path, enforce_existence=True
            ) or self.resolve_path_from_src(path, enforce_existence=True)
            if resolved is not None:
                return resolved
            return self.resolve_path_from_project(path, enforce_existence=False)

    @autolog
    def resolve_path_from_project(
        self, path: str | Path | None, enforce_existence: bool = True
    ) -> Path | None:
        """
        Resolve a path relative to the project root directory.

        Example:
            ::

                path = settings.resolve_path_from_project("setup.cfg")

        :param path: The path to resolve.
        :param enforce_existence: Whether to enforce that the path exists.
        :return: The resolved absolute Path if it exists (or if not enforcing
            existence), otherwise None.
        """
        if not path:
            return None

        if isinstance(path, str):
            path = Path(path)
        if not path.is_absolute():
            path = self.project_root / path
        return path if (not enforce_existence or path.exists()) else None

    @autolog
    def resolve_path_from_src(
        self, path: str | Path | None, enforce_existence: bool = True
    ) -> Path | None:
        """
        Resolve a path relative to the source root directory.

        Example:
            ::

                path = settings.resolve_path_from_src("my_package/__init__.py")

        :param path: The path to resolve.
        :param enforce_existence: Whether to enforce that the path exists.
        :return: The resolved absolute Path if it exists (or if not enforcing
            existence), otherwise None.
        """
        if not path:
            return None

        if isinstance(path, str):
            path = Path(path)
        if not path.is_absolute():
            path = self.src_root / path
        return path if (not enforce_existence or path.exists()) else None

    @model_validator(mode="after")
    def _resolve_auto_fields(self) -> Settings:
        # Internal validator to resolve 'auto' fields after initialization.
        if self.package_name == "auto":
            new_pkg_name = _detect_package_name(self.project_root)
            if new_pkg_name != self.package_name:
                self.package_name = new_pkg_name

        if self.src_root == self.project_root:
            new_src_root = _resolve_src_root(self.project_root, self.package_name)
            if new_src_root != self.src_root:
                self.src_root = new_src_root

        return self
