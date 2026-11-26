# Copyright 2026 markurtz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
The configuration model, its homes and its environment overrides.

A repository keeps its settings in exactly one home. The model has twelve root
keys, four keys per target and two per package; unknown keys are errors, and any
root key can be overridden with ``GITVERSIONED__KEY`` in the environment.

Example:
::
    from pathlib import Path
    from gitversioned.config import load_config

    config = load_config(Path.cwd())
    print(config.home, config.tag, config.scopes)
"""

from __future__ import annotations

import configparser
import difflib
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, Literal

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from gitversioned import git
from gitversioned.errors import ConfigError

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

__all__ = [
    "DEFAULT_TYPES",
    "ENV_PREFIX",
    "Config",
    "PackageConfig",
    "TargetConfig",
    "find_homes",
    "find_root",
    "load_config",
]

ENV_PREFIX: Annotated[str, "Prefix of every environment override"] = "GITVERSIONED__"
DEFAULT_TYPES: Annotated[tuple[str, ...], "Commit types the template allows"] = (
    "feat",
    "fix",
    "perf",
    "refactor",
    "docs",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
    "deprecate",
    "release",
)

BumpBase = Literal["patch", "minor", "major", "next"]


class TargetConfig(BaseModel):
    """
    A file to stamp that discovery cannot find on its own.

    :param path: File to stamp, relative to the project root.
    :param key: Dotted path of the value in a TOML, JSON or YAML file.
    :param pattern: Regular expression with a ``version`` group, for any text file.
    :param commit: Whether the release pull request commits the file; the default
        depends on the kind of file.
    """

    model_config = ConfigDict(extra="forbid")

    path: str
    key: str | None = None
    pattern: str | None = None
    commit: bool | None = None

    @model_validator(mode="after")
    def _one_locator(self) -> TargetConfig:
        if self.key and self.pattern:
            raise ValueError("a target takes `key` or `pattern`, not both")
        return self


class PackageConfig(BaseModel):
    """
    A package with its own folder and, optionally, its own tag.

    :param path: Package folder, relative to the project root.
    :param tag: Tag template such as ``core-v{version}``; without it the package
        follows the repository version.
    """

    model_config = ConfigDict(extra="forbid")

    path: str
    tag: str | None = None

    @model_validator(mode="after")
    def _tag_template(self) -> PackageConfig:
        if self.tag is not None and "{version}" not in self.tag:
            raise ValueError("`tag` must contain {version}")
        return self


class Config(BaseModel):
    """
    Every setting gitversioned has.

    :param version: A pinned version, or ``auto`` to resolve from git.
    :param fallback: Base version when no tag exists yet.
    :param tag: Tag template; also how release tags are recognised.
    :param annotated: Create annotated tags carrying the changelog section.
    :param branch: Branch releases are cut from.
    :param dev: Base of a development build.
    :param nightly: Base of a nightly build.
    :param date: Date used in development and nightly versions.
    :param local: Add the commit hash to development builds.
    :param changelog: Changelog file, or ``False`` to turn it off.
    :param types: Allowed commit types.
    :param scopes: Allowed scopes, or a TOML file whose table names are the scopes.
    :param targets: Extra files to stamp.
    :param packages: Packages with their own folder and optional tag.
    :param root: Project root the paths are relative to.
    :param home: Where the settings were read from, for messages.
    """

    model_config = ConfigDict(extra="forbid")

    version: str = "auto"
    fallback: str = "0.1.0"
    tag: str = "v{version}"
    annotated: bool = False
    branch: str = "main"
    dev: BumpBase = "patch"
    nightly: BumpBase = "next"
    date: Literal["commit", "build"] = "commit"
    local: bool = True
    changelog: str | Literal[False] = "CHANGELOG.md"
    types: list[str] = Field(default_factory=lambda: list(DEFAULT_TYPES))
    scopes: list[str] | str = Field(default_factory=list)
    targets: list[TargetConfig] = Field(default_factory=list)
    packages: dict[str, PackageConfig] = Field(default_factory=dict)

    root: Path = Field(default_factory=Path.cwd, exclude=True)
    home: str = Field(default="defaults", exclude=True)
    keys_set: tuple[str, ...] = Field(default=(), exclude=True)

    @model_validator(mode="after")
    def _tag_template(self) -> Config:
        if "{version}" not in self.tag:
            raise ValueError("`tag` must contain {version}")
        return self

    def allowed_scopes(self) -> list[str]:
        """
        Resolve the allowed scopes, reading the scopes file when one is named.

        Package names are always allowed once any scope is restricted.

        :return: Scope names; an empty list allows any scope.
        :raises ConfigError: If the scopes file is missing or not valid TOML.
        """
        if isinstance(self.scopes, list):
            scopes = list(self.scopes)
        else:
            path = self.root / self.scopes
            try:
                data = tomllib.loads(path.read_text(encoding="utf-8"))
            except (OSError, tomllib.TOMLDecodeError) as error:
                raise ConfigError(f"cannot read scopes file {path}: {error}") from error
            scopes = [key for key, value in data.items() if isinstance(value, dict)]
        if scopes:
            scopes += [name for name in self.packages if name not in scopes]
        return scopes

    @classmethod
    def key_names(cls) -> list[str]:
        """
        :return: The names of the settings a home may hold.
        """
        return [name for name, field in cls.model_fields.items() if not field.exclude]


_HOME_ORDER = (
    ".config/gitversioned.toml",
    "gitversioned.toml",
    "pyproject.toml",
    "Cargo.toml",
    "package.json",
    "setup.cfg",
)


def _pyproject_table(path: Path, text: str) -> tuple[str, dict[str, Any]] | None:
    """Read ``[tool.gitversioned]`` from a pyproject file."""
    table = tomllib.loads(text).get("tool", {}).get("gitversioned")
    return (f"{path} [tool.gitversioned]", table) if table is not None else None


def _cargo_table(path: Path, text: str) -> tuple[str, dict[str, Any]] | None:
    """Read the gitversioned metadata table from a Cargo manifest."""
    data = tomllib.loads(text)
    for section in ("workspace", "package"):
        table = data.get(section, {}).get("metadata", {}).get("gitversioned")
        if table is not None:
            return f"{path} [{section}.metadata.gitversioned]", table
    return None


def _npm_table(path: Path, text: str) -> tuple[str, dict[str, Any]] | None:
    """Read the ``gitversioned`` key from a package.json file."""
    table = json.loads(text).get("gitversioned")
    return (f'{path} "gitversioned"', table) if table is not None else None


def _setup_cfg_table(path: Path, text: str) -> tuple[str, dict[str, Any]] | None:
    """Read ``[tool:gitversioned]`` from a setup.cfg file."""
    parser = configparser.ConfigParser()
    parser.read_string(text)
    if not parser.has_section("tool:gitversioned"):
        return None
    table = {key: _coerce(value) for key, value in parser["tool:gitversioned"].items()}
    return f"{path} [tool:gitversioned]", table


def _own_file_table(path: Path, text: str) -> tuple[str, dict[str, Any]] | None:
    """Read a gitversioned.toml file, which is settings from top to bottom."""
    return str(path), tomllib.loads(text)


_HOME_READERS: dict[str, Callable[[Path, str], tuple[str, dict[str, Any]] | None]] = {
    "gitversioned.toml": _own_file_table,
    "pyproject.toml": _pyproject_table,
    "Cargo.toml": _cargo_table,
    "package.json": _npm_table,
    "setup.cfg": _setup_cfg_table,
}


def _read_home(path: Path) -> tuple[str, dict[str, Any]] | None:
    """Return the label and settings table of a home file, if it holds one."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        return _HOME_READERS[path.name](path, text)
    except (tomllib.TOMLDecodeError, json.JSONDecodeError, configparser.Error) as error:
        raise ConfigError(f"cannot parse {path}: {error}") from error


def _coerce(value: str) -> Any:
    """Turn an environment or INI string into a typed value when it is JSON."""
    text = value.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def find_homes(root: Path) -> list[tuple[str, dict[str, Any]]]:
    """
    Find every config home in a folder that holds settings.

    :param root: Folder to look in.
    :return: A label and settings table per home, in priority order.
    """
    homes: list[tuple[str, dict[str, Any]]] = []
    for relative in _HOME_ORDER:
        path = root / relative
        found = _read_home(path)
        if found is not None:
            label, table = found
            homes.append((label.replace(str(path), relative, 1), table))
    return homes


def find_root(start: Path) -> Path:
    """
    Find the project root for a starting folder.

    The root is the nearest parent holding a config home or an unpacked source
    distribution (``PKG-INFO``), searching no higher than the repository root;
    failing that the repository root, then the start.

    :param start: Folder the command was started in.
    :return: The project root.
    """
    start = start.resolve()
    repo = git.Repo.open(start)
    top = repo.top if repo is not None else None
    current = start
    while True:
        if find_homes(current) or (current / "PKG-INFO").is_file():
            return current
        if current in (top, current.parent):
            break
        current = current.parent
    return top if top is not None and _inside(start, top) else start


def _inside(path: Path, parent: Path) -> bool:
    """Return whether a path is the parent or below it."""
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _suggest(name: str, valid: list[str]) -> str:
    """Return a hint naming the nearest valid key."""
    close = difflib.get_close_matches(name, valid, n=1)
    return f" Did you mean `{close[0]}`?" if close else ""


def load_config(
    start: Path | None = None, *, env: dict[str, str] | None = None
) -> Config:
    """
    Load the configuration for a project.

    :param start: Folder the command was started in; defaults to the current one.
    :param env: Environment to read overrides from; defaults to ``os.environ``.
    :return: The validated configuration.
    :raises ConfigError: For two homes, an unknown key or an invalid value.
    """
    environment = os.environ if env is None else env
    root = find_root(start or Path.cwd())
    homes = find_homes(root)
    if len(homes) > 1:
        names = " and ".join(label for label, _ in homes)
        raise ConfigError(
            f"settings found in two homes: {names}. Keep them in one file."
        )
    label, table = homes[0] if homes else ("defaults", {})
    if not isinstance(table, dict):
        raise ConfigError(f"{label} must be a table")
    data: dict[str, Any] = dict(table)
    valid = Config.key_names()
    for name in data:
        if name not in valid:
            raise ConfigError(
                f"unknown key `{name}` in {label}.{_suggest(name, valid)} "
                f"Valid keys: {', '.join(valid)}."
            )
    keys_set = sorted(data)
    for name, value in environment.items():
        if not name.startswith(ENV_PREFIX):
            continue
        key = name[len(ENV_PREFIX) :].lower()
        if key == "bump":
            continue
        if key not in valid:
            # The environment is shared with other tools and older gitversioned
            # releases, so a stale variable warns instead of stopping a build.
            logger.warning(
                "ignoring unknown environment override {}.{}",
                name,
                _suggest(key, valid),
            )
            continue
        data[key] = _coerce(value) if key not in ("version", "fallback") else value
        keys_set.append(f"{key} (env)")
    try:
        config = Config(**data)
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in item['loc']) or 'config'}: {item['msg']}"
            for item in error.errors()
        )
        raise ConfigError(f"invalid config in {label}: {problems}") from error
    config.root = root
    config.home = label
    config.keys_set = tuple(keys_set)
    return config
