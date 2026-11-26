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

A repository keeps its settings in exactly one home. Unknown keys are errors,
and any root key can be overridden with ``GITVERSIONED__KEY`` in the
environment. Every key has a default, so most repositories set none.

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
from gitversioned.model import Version

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
LevelName = Literal["major", "minor", "patch", "none"]
Registry = Literal["pypi", "crates", "npm"]


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

    :param version: ``auto`` to resolve from git tags, a pinned version, or a
        source: ``branch`` or ``commit`` (the first ``X.Y.Z`` in the branch name
        or the ``HEAD`` subject), ``file:PATH`` or ``python:MODULE:FUNCTION``.
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
    :param scopes: Allowed scopes; an entry ending in ``.toml`` names a file whose
        table names are scopes.
    :param targets: Extra files to stamp.
    :param packages: Packages with their own folder and optional tag.
    :param formats: PEP 440 templates for ``dev`` and ``nightly`` versions, with
        ``{next}``, ``{base}``, ``{distance}``, ``{date}``, ``{sha}`` and
        ``{branch}`` placeholders.
    :param module_template: File holding a ``string.Template`` for the
        generated ``version.py``.
    :param levels: Bump level per commit type, replacing the defaults (``feat``
        minor, maintenance types none, others patch). Breaking changes are major.
    :param zero_shift: Below 1.0.0, shift every level down one.
    :param changelog_layout: ``kind`` (kinds, then scope in bold) or ``scope``
        (a heading per scope, then kinds).
    :param changelog_sections: Changelog heading per commit type; ``false``
        hides the type.
    :param changelog_template: File holding a ``string.Template`` for a release
        section.
    :param changes: Folder of change files, each one changelog entry.
    :param forge: ``auto``, ``github``, ``gitlab`` or ``gitea``.
    :param forge_release: Create a release on the forge, with the changelog section
        as notes, when ``release --tag`` pushes a tag. Off by default, since many
        release workflows already create one.
    :param branches: Maintenance branches (glob patterns) releases may also be
        cut from.
    :param exclude: Files discovery leaves alone (glob patterns).
    :param semver_checks: Raise the level when ``cargo semver-checks`` finds a
        breaking API change.
    :param publish: Registries ``release --publish`` uploads to; by default every
        one with a package.
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
    formats: dict[Literal["dev", "nightly"], str] = Field(default_factory=dict)
    module_template: str | None = None
    levels: dict[str, LevelName] = Field(default_factory=dict)
    zero_shift: bool = True
    changelog_layout: Literal["kind", "scope"] = "kind"
    changelog_sections: dict[str, str | Literal[False]] = Field(default_factory=dict)
    changelog_template: str | None = None
    changes: str = ".changes"
    forge: Literal["auto", "github", "gitlab", "gitea"] = "auto"
    forge_release: bool = False
    branches: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)
    semver_checks: bool = False
    publish: list[Registry] | None = None

    root: Path = Field(default_factory=Path.cwd, exclude=True)
    home: str = Field(default="defaults", exclude=True)
    keys_set: tuple[str, ...] = Field(default=(), exclude=True)

    @model_validator(mode="after")
    def _tag_template(self) -> Config:
        if "{version}" not in self.tag:
            raise ValueError("`tag` must contain {version}")
        source = self.version
        if not (
            source in ("auto", "branch", "commit")
            or source.startswith(("file:", "python:"))
            or _looks_like_version(source)
        ):
            raise ValueError(
                "`version` must be auto, branch, commit, file:PATH, "
                f"python:MODULE:FUNCTION or a version, not {source!r}"
            )
        if source.startswith("python:") and source.count(":") != 2:  # noqa: PLR2004
            raise ValueError(
                f"`version` {source!r} must name a function: python:MODULE:FUNCTION"
            )
        return self

    def allowed_scopes(self) -> list[str]:
        """
        Resolve the allowed scopes, reading any scopes file that is named.

        A scope ending in ``.toml`` is a file whose table names are scopes, so a
        list can mix a file with extra names. Package names are always allowed
        once any scope is restricted.

        :return: Scope names; an empty list allows any scope.
        :raises ConfigError: If a scopes file is missing or not valid TOML.
        """
        entries = [self.scopes] if isinstance(self.scopes, str) else self.scopes
        scopes: list[str] = []
        for entry in entries:
            names = self._scopes_file(entry) if entry.endswith(".toml") else [entry]
            scopes += [name for name in names if name not in scopes]
        if scopes:
            scopes += [name for name in self.packages if name not in scopes]
        return scopes

    def _scopes_file(self, name: str) -> list[str]:
        """Read the table names of one scopes file."""
        path = self.root / name
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as error:
            raise ConfigError(f"cannot read scopes file {path}: {error}") from error
        return [key for key, value in data.items() if isinstance(value, dict)]

    @classmethod
    def key_names(cls) -> list[str]:
        """
        :return: The names of the settings a home may hold.
        """
        return [name for name, field in cls.model_fields.items() if not field.exclude]


def _looks_like_version(text: str) -> bool:
    """Tell whether a `version` value is a literal version."""
    return Version.try_parse(text) is not None


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


_RETIRED: dict[str, str] = {
    "output": "version.py has one fixed home; list other files in [[targets]].",
    "output_strategies": "set `module_template` to shape version.py.",
    "overrides": "most files are discovered; list the rest in [[targets]].",
    "version_type": "pass --type, or set GITVERSIONED__TYPE.",
    "version_standard": "pass --standard; each file gets its own spelling.",
    "regex_tag": 'set `tag`, such as tag = "v{version}".',
    "auto_increment": "set `dev` and `nightly`.",
    "source_type": "set `version`: auto, branch, commit, file:PATH or python:M:F.",
    "dirty_ignore": "stamped files and build folders never count as dirty.",
    "logging": "use -v, -vv or -q.",
}
_RETIRED_PREFIXES: dict[str, str] = {
    "regex_": 'set `tag`, such as tag = "v{version}".',
    "format_": "set `formats = {dev = ..., nightly = ...}`.",
    "version_source_": "set `version`: auto, branch, commit, file:PATH or python:M:F.",
}


def _suggest(name: str, valid: list[str]) -> str:
    """Return a hint naming the nearest valid key, or the 0.3 key's replacement."""
    retired = _RETIRED.get(name) or next(
        (hint for prefix, hint in _RETIRED_PREFIXES.items() if name.startswith(prefix)),
        None,
    )
    if retired:
        return f" `{name}` was removed in 0.4: {retired}"
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
        if key in ("bump", "type"):
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
            (f"{'.'.join(str(part) for part in item['loc'])}: " if item["loc"] else "")
            + str(item["msg"]).removeprefix("Value error, ")
            for item in error.errors()
        )
        raise ConfigError(f"invalid config in {label}: {problems}") from error
    config.root = root
    config.home = label
    config.keys_set = tuple(keys_set)
    logger.info(f"settings from {label}: {', '.join(keys_set) or 'all defaults'}")
    return config
