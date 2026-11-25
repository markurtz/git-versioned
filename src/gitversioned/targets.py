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
The files gitversioned stamps: discovery, scoped edits and the generated module.

Every target except the generated ``version.py`` is changed by replacing only the
version value in place. Discovery finds the usual manifests; listed targets add
files it cannot know about.

Example:
::
    from gitversioned.config import load_config
    from gitversioned.resolve import resolve
    from gitversioned.targets import stamp

    config = load_config()
    for change in stamp(config, resolve(config), dry_run=True):
        print(change.path, change.new)
"""

from __future__ import annotations

import difflib
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from gitversioned import git
from gitversioned.config import Config, TargetConfig
from gitversioned.editors import json_span, toml_span, toml_table_spans, yaml_span
from gitversioned.errors import ConfigError
from gitversioned.model import Standard
from gitversioned.resolve import Resolved

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

__all__ = [
    "Change",
    "Span",
    "Target",
    "discover",
    "only_version_changed",
    "render_version_module",
    "stamp",
]

_SKIP_DIRS = {
    "node_modules",
    "target",
    ".venv",
    "venv",
    "dist",
    "build",
    ".git",
    "site",
}
_DOCKER_LABEL = re.compile(
    r"""org\.opencontainers\.image\.version\s*=\s*(?P<q>["']?)(?P<value>[^"'\s\\]+)(?P=q)"""
)
_CARGO_DEP_TABLE = re.compile(r"(^|\.)(dev-|build-)?dependencies$")
_INLINE_VERSION = re.compile(r"""\bversion\s*=\s*(?P<q>["'])(?P<value>[^"']*)(?P=q)""")
_INLINE_PATH = re.compile(r"\bpath\s*=")
_LOCK_ENTRY = re.compile(
    r'\[\[package\]\]\s*\nname = "(?P<name>[^"]+)"\s*\nversion = "(?P<value>[^"]+)"'
)


@dataclass(frozen=True)
class Span:
    """
    One value to replace inside a file.

    :param kind: ``version`` for a version, ``req`` for a dependency requirement
        whose operator is kept, ``date`` for a release date.
    :param start: First character of the value.
    :param end: One past the last character.
    """

    kind: str
    start: int
    end: int


@dataclass
class Target:
    """
    A file that carries the version.

    :param path: Absolute path of the file.
    :param kind: Handler name such as ``cargo``, ``npm`` or ``python``.
    :param standard: Spelling the file expects.
    :param commit: Whether the release pull request commits the file.
    :param locate: Finds the values to replace in the file's text.
    :param generated: True when the whole file is written from the template.
    """

    path: Path
    kind: str
    standard: Standard
    commit: bool
    locate: Callable[[str], list[Span]] = field(default=lambda text: [], repr=False)
    generated: bool = False

    def current(self, text: str) -> str | None:
        """
        Read the version the file holds now.

        :param text: File content.
        :return: The first version value found, or ``None``.
        """
        for span in self.locate(text):
            if span.kind == "version":
                return text[span.start : span.end]
        return None

    def apply(self, text: str, values: dict[str, str]) -> str:
        """
        Replace each located value, leaving the rest of the text untouched.

        :param text: File content.
        :param values: Replacement per span kind.
        :return: The new content.
        """
        for span in sorted(
            self.locate(text), key=lambda item: item.start, reverse=True
        ):
            new = values.get(span.kind)
            if new is None:
                continue
            if span.kind == "req":
                operator = re.match(r"^[\^~=<>\s]*", text[span.start : span.end])
                new = (operator.group(0) if operator else "") + new
            text = text[: span.start] + new + text[span.end :]
        return text


@dataclass(frozen=True)
class Change:
    """
    The result of stamping one target.

    :param path: Path relative to the project root.
    :param old: Version the file held, when it had one.
    :param new: Version written.
    :param diff: Unified diff of the edit; empty when nothing changed.
    :param commit: Whether the release pull request commits the file.
    :param written: True when the file was changed on disk.
    """

    path: str
    old: str | None
    new: str
    diff: str
    commit: bool
    written: bool


def _spans(kind: str, *found: tuple[int, int] | None) -> list[Span]:
    """Wrap raw spans, dropping the ones that were not found."""
    return [Span(kind, span[0], span[1]) for span in found if span is not None]


def _cargo_locate(text: str) -> list[Span]:
    """Locate the package version and the versions of path dependencies."""
    spans = _spans(
        "version",
        toml_span(text, ["package", "version"]),
        toml_span(text, ["workspace", "package", "version"]),
    )
    for name, start, end in toml_table_spans(text):
        parent, _, leaf = name.rpartition(".")
        if _CARGO_DEP_TABLE.search(name):
            offset = start
            for line in text[start:end].splitlines(keepends=True):
                match = _INLINE_VERSION.search(line)
                if match and _INLINE_PATH.search(line):
                    spans.append(
                        Span(
                            "req",
                            offset + match.start("value"),
                            offset + match.end("value"),
                        )
                    )
                offset += len(line)
        elif leaf and _CARGO_DEP_TABLE.search(parent):
            body = text[start:end]
            match = re.search(
                r"""(?m)^\s*version\s*=\s*(["'])(?P<value>[^"']*)\1""", body
            )
            if match and re.search(r"(?m)^\s*path\s*=", body):
                spans.append(
                    Span(
                        "req", start + match.start("value"), start + match.end("value")
                    )
                )
    return spans


def _lock_locate(names: set[str]) -> Callable[[str], list[Span]]:
    """Build a locator for the lock entries of the workspace's own crates."""

    def locate(text: str) -> list[Span]:
        return [
            Span("version", match.start("value"), match.end("value"))
            for match in _LOCK_ENTRY.finditer(text)
            if match["name"] in names
        ]

    return locate


def _keyed_locate(path: Path, key: str) -> Callable[[str], list[Span]]:
    """Build a locator for a dotted key in a TOML, JSON or YAML file."""
    parts = key.split(".")
    suffix = path.suffix.lower()
    if suffix == ".toml":
        return lambda text: _spans("version", toml_span(text, parts))
    if suffix == ".json":
        return lambda text: _spans("version", json_span(text, parts))
    if suffix in (".yaml", ".yml", ".cff"):
        return lambda text: _spans("version", yaml_span(text, parts))
    raise ConfigError(
        f"target {path.name}: `key` works for .toml, .json, .yaml and .yml files. "
        "Use `pattern` for other files."
    )


def _pattern_locate(path: Path, pattern: str) -> Callable[[str], list[Span]]:
    """Build a locator from a regular expression with a ``version`` group."""
    try:
        compiled = re.compile(pattern, re.MULTILINE)
    except re.error as error:
        raise ConfigError(f"target {path.name}: invalid pattern: {error}") from error
    if "version" not in compiled.groupindex:
        raise ConfigError(f"target {path.name}: pattern needs a (?P<version>...) group")
    return lambda text: [
        Span("version", match.start("version"), match.end("version"))
        for match in compiled.finditer(text)
    ]


def _by_name(path: Path) -> Target | None:
    """Build the target for a file recognised by its name."""
    name = path.name
    if name == "pyproject.toml":
        return Target(
            path,
            "pyproject",
            "pep440",
            True,
            lambda text: _spans("version", toml_span(text, ["project", "version"])),
        )
    if name == "Cargo.toml":
        return Target(path, "cargo", "semver", True, _cargo_locate)
    if name == "package.json":
        return Target(
            path,
            "npm",
            "semver",
            True,
            lambda text: _spans("version", json_span(text, ["version"])),
        )
    if name == "tauri.conf.json":
        return Target(
            path,
            "tauri",
            "semver",
            True,
            lambda text: (
                _spans("version", json_span(text, ["version"]))
                or _spans("version", json_span(text, ["package", "version"]))
            ),
        )
    if name == "Chart.yaml":
        return Target(
            path,
            "helm",
            "semver",
            True,
            lambda text: _spans(
                "version", yaml_span(text, ["version"]), yaml_span(text, ["appVersion"])
            ),
        )
    if name == "CITATION.cff":
        return Target(
            path,
            "citation",
            "semver",
            True,
            lambda text: (
                _spans("version", yaml_span(text, ["version"]))
                + _spans("date", yaml_span(text, ["date-released"]))
            ),
        )
    if (
        name == "Dockerfile"
        or name.startswith("Dockerfile.")
        or name.endswith(".Dockerfile")
    ):
        return Target(
            path,
            "dockerfile",
            "semver",
            True,
            lambda text: [
                Span("version", match.start("value"), match.end("value"))
                for match in _DOCKER_LABEL.finditer(text)
            ],
        )
    return None


def _python_module(pyproject: Path) -> Path | None:
    """Return where the generated ``version.py`` goes for a dynamic project."""
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    project = data.get("project", {})
    build = data.get("build-system", {})
    uses_plugin = str(build.get("build-backend", "")).startswith("gitversioned") or any(
        re.match(r"^gitversioned\b", str(item).strip())
        for item in build.get("requires", [])
    )
    if not uses_plugin:
        return None
    if "version" not in project.get("dynamic", []) or not project.get("name"):
        return None
    package = re.sub(r"[-.]+", "_", str(project["name"])).lower()
    for base in (
        pyproject.parent / "src",
        pyproject.parent,
        pyproject.parent / "python",
    ):
        if (base / package).is_dir():
            return base / package / "version.py"
    return None


def _listed(config: Config, entry: TargetConfig) -> Target:
    """Build the target for a ``[[targets]]`` entry."""
    path = (config.root / entry.path).resolve()
    if entry.pattern:
        target = Target(
            path, "pattern", "semver", True, _pattern_locate(path, entry.pattern)
        )
    elif entry.key:
        target = Target(path, "key", "semver", True, _keyed_locate(path, entry.key))
    else:
        named = _by_name(path)
        if named is None:
            raise ConfigError(
                f"target {entry.path}: unknown file type. Add `key` or `pattern`."
            )
        target = named
    if path.suffix == ".py" or path.name == "pyproject.toml":
        target.standard = "pep440"
    if entry.commit is not None:
        target.commit = entry.commit
    return target


def _candidates(config: Config, base: Path) -> list[Path]:
    """List the files discovery should look at under a folder."""
    repo = git.Repo.open(config.root)
    if repo is not None:
        files = [repo.top / name for name in repo.tracked_files()]
    else:
        files = [path for path in base.rglob("*") if path.is_file()]
    found: list[Path] = []
    for path in files:
        try:
            relative = path.resolve().relative_to(base.resolve())
        except ValueError:
            continue
        if _SKIP_DIRS.intersection(relative.parts[:-1]):
            continue
        found.append(base / relative)
    return sorted(found)


def discover(config: Config, *, package: str | None = None) -> list[Target]:
    """
    Find every target of the project or of one package.

    Folders of packages that carry their own tag are left out of the repository's
    targets, and are the only folders searched when that package is asked for.

    :param config: The loaded configuration.
    :param package: Name of a package from ``[packages]`` to limit the search to.
    :return: The targets, discovered ones first, listed ones after.
    :raises ConfigError: If the package is unknown or a listed target is invalid.
    """
    root = config.root.resolve()
    if package is not None:
        if package not in config.packages:
            raise ConfigError(
                f"unknown package {package!r}. Packages: "
                f"{', '.join(config.packages) or 'none configured'}."
            )
        base = (root / config.packages[package].path).resolve()
        excluded: list[Path] = []
    else:
        base = root
        excluded = [
            (root / item.path).resolve()
            for item in config.packages.values()
            if item.tag
        ]

    def allowed(path: Path) -> bool:
        resolved = path.resolve()
        if any(resolved == folder or folder in resolved.parents for folder in excluded):
            return False
        return resolved == base or base in resolved.parents

    targets: list[Target] = []
    crate_names: set[str] = set()
    lock_dirs: list[Path] = []
    for path in _candidates(config, base):
        if not allowed(path):
            continue
        if path.name == "Cargo.toml":
            text = path.read_text(encoding="utf-8")
            name_span = toml_span(text, ["package", "name"])
            if name_span:
                crate_names.add(text[name_span[0] : name_span[1]])
            if (path.parent / "Cargo.lock").is_file():
                lock_dirs.append(path.parent)
        if path.name == "pyproject.toml":
            module = _python_module(path)
            if module is not None:
                targets.append(
                    Target(module, "python", "pep440", False, generated=True)
                )
        root_only = path.name == "CITATION.cff" or "Dockerfile" in path.name
        if root_only and path.parent.resolve() != base:
            continue
        target = _by_name(path)
        if target is None:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if target.current(text) is not None:
            targets.append(target)
    if crate_names and any(target.kind == "cargo" for target in targets):
        targets.extend(
            Target(
                folder / "Cargo.lock",
                "cargo-lock",
                "semver",
                True,
                _lock_locate(crate_names),
            )
            for folder in lock_dirs
        )
    seen = {target.path.resolve() for target in targets}
    for entry in config.targets:
        listed = _listed(config, entry)
        if not allowed(listed.path):
            continue
        if listed.path.resolve() in seen:
            targets = [
                item for item in targets if item.path.resolve() != listed.path.resolve()
            ]
        seen.add(listed.path.resolve())
        targets.append(listed)
    return targets


def render_version_module(resolved: Resolved) -> str:
    """
    Render the generated ``version.py`` for a resolved version.

    The module carries the version and git metadata only, so two builds of the
    same commit produce the same file.

    :param resolved: The resolved version.
    :return: Python source.
    """
    version = resolved.version
    parts: list[object] = [version.major, version.minor, version.patch]
    if version.pre is not None:
        parts.append(f"{version.pre[0]}{version.pre[1]}")
    if version.dev is not None:
        parts.append(f"dev{version.dev}")
    if version.local:
        parts.append(version.local)
    date = resolved.date.isoformat() if resolved.date else None
    return (
        '"""Version information generated by gitversioned. Do not edit or commit."""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "__all__ = [\n"
        '    "__commit__",\n'
        '    "__commit_date__",\n'
        '    "__distance__",\n'
        '    "__tag__",\n'
        '    "__version__",\n'
        '    "__version_semver__",\n'
        '    "__version_tuple__",\n'
        '    "version",\n'
        '    "version_tuple",\n'
        "]\n"
        "\n"
        f"__version__ = version = {version.pep440()!r}\n"
        f"__version_semver__ = {version.semver()!r}\n"
        f"__version_tuple__ = version_tuple = {tuple(parts)!r}\n"
        f"__tag__ = {resolved.tag!r}\n"
        f"__distance__ = {resolved.distance!r}\n"
        f"__commit__ = {resolved.sha!r}\n"
        f"__commit_date__ = {date!r}\n"
    ).replace("'", '"')


def _values(target: Target, resolved: Resolved) -> dict[str, str]:
    """Build the replacement values for a target."""
    rendered = resolved.version.render(target.standard)
    values = {"version": rendered, "req": rendered}
    if resolved.type == "release":
        day = datetime.now(tz=timezone.utc)
        values["date"] = day.strftime("%Y-%m-%d")
    return values


def stamp(
    config: Config,
    resolved: Resolved,
    *,
    dry_run: bool = False,
    package: str | None = None,
    committed_only: bool = False,
    generated_only: bool = False,
) -> list[Change]:
    """
    Write the resolved version into every target.

    :param config: The loaded configuration.
    :param resolved: The version to write.
    :param dry_run: Compute the changes and diffs without touching any file.
    :param package: Limit the work to one package from ``[packages]``.
    :param committed_only: Skip targets the release pull request does not commit.
    :param generated_only: Write only the generated ``version.py`` files, as a
        build backend does.
    :return: One change per target, in discovery order.
    """
    changes: list[Change] = []
    for target in discover(config, package=package):
        if committed_only and not target.commit:
            continue
        if generated_only and not target.generated:
            continue
        relative = _relative(target.path, config.root)
        rendered = resolved.version.render(target.standard)
        old_text = _read_exact(target.path) if target.path.is_file() else ""
        if target.generated:
            old = _generated_version(old_text)
            new_text = render_version_module(resolved)
        else:
            old = target.current(old_text)
            new_text = target.apply(old_text, _values(target, resolved))
        diff = "".join(
            difflib.unified_diff(
                old_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                f"a/{relative}",
                f"b/{relative}",
            )
        )
        changed = new_text != old_text
        if changed and not dry_run:
            target.path.parent.mkdir(parents=True, exist_ok=True)
            with target.path.open("w", encoding="utf-8", newline="") as handle:
                handle.write(new_text)
        changes.append(
            Change(
                relative, old, rendered, diff, target.commit, changed and not dry_run
            )
        )
    return changes


def _read_exact(path: Path) -> str:
    """Read a file without translating its line endings."""
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


def _generated_version(text: str) -> str | None:
    """Read the version out of a generated module."""
    match = re.search(
        r"""(?m)^__version__\s*=\s*(?:version\s*=\s*)?["']([^"']+)["']""", text
    )
    return match.group(1) if match else None


def _relative(path: Path, root: Path) -> str:
    """Express a path relative to the project root when it is inside it."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def only_version_changed(config: Config, repo: git.Repo, path: str) -> bool:
    """
    Tell whether a dirty file differs from ``HEAD`` only by stamped values.

    This is what keeps a build from making its own tree dirty: a manifest whose
    only change is the version gitversioned wrote does not count.

    :param config: The loaded configuration.
    :param repo: The repository.
    :param path: Dirty path relative to the repository root.
    :return: True when the change is only gitversioned's own stamping.
    """
    absolute = (repo.top / path).resolve()
    try:
        targets = discover(config)
        for name in config.packages:
            targets += discover(config, package=name)
    except ConfigError:
        return False
    for target in targets:
        if target.path.resolve() != absolute:
            continue
        if target.generated:
            return True
        head = repo.show(path)
        try:
            work = absolute.read_text(encoding="utf-8")
        except OSError:
            return False
        if head is None:
            return False
        head_spans = sorted(target.locate(head), key=lambda item: item.start)
        work_spans = sorted(target.locate(work), key=lambda item: item.start)
        if len(head_spans) != len(work_spans) or not head_spans:
            return False
        rebuilt = head
        for head_span, work_span in reversed(list(zip(head_spans, work_spans, strict=False))):
            rebuilt = (
                rebuilt[: head_span.start]
                + work[work_span.start : work_span.end]
                + rebuilt[head_span.end :]
            )
        return rebuilt.replace("\r\n", "\n").rstrip("\n") == work.replace(
            "\r\n", "\n"
        ).rstrip("\n")
    return False
