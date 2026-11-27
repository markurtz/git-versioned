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
Build backend integrations: Hatchling, setuptools and Maturin.

Each integration resolves the version once and writes the generated
``version.py``, so a build needs no gitversioned settings at all.
"""

from __future__ import annotations

import re
from pathlib import Path

from gitversioned.config import Config, load_config
from gitversioned.logging import configure_build_logging
from gitversioned.model import Version
from gitversioned.release import package_context
from gitversioned.resolve import Resolved, resolve
from gitversioned.targets import Change, python_module, render_version_module

__all__ = ["build_package", "resolve_for_build"]


def build_package(config: Config, build_root: Path) -> str | None:
    """
    Name the ``[packages]`` entry a build folder belongs to, if any.

    :param config: The loaded configuration.
    :param build_root: Folder being built.
    :return: The package name, or ``None`` for the repository itself.
    """
    for name, item in config.packages.items():
        folder = (config.root / item.path).resolve()
        if build_root == folder or folder in build_root.parents:
            return name
    return None


def resolve_for_build(
    root: Path | str, *, write: bool = True
) -> tuple[Resolved, list[Change]]:
    """
    Resolve the version for a build and write the generated module.

    The build folder may sit below the project root, as an extra package under
    ``packages/<name>/`` does: the version then follows that package's tags when
    it has its own, and only the build folder's own ``version.py`` is written.

    :param root: Project folder being built.
    :param write: Write the generated ``version.py`` when the project has one.
    :return: The resolved version and the files written, relative to ``root``.
    """
    configure_build_logging()
    build_root = Path(root).resolve()
    config = load_config(build_root)
    package = build_package(config, build_root)
    template, scope = package_context(config, package)
    resolved = resolve(config, tag_template=template, path_scope=scope)
    changes: list[Change] = []
    module = python_module(build_root / "pyproject.toml") if write else None
    if module is not None:
        text = render_version_module(resolved, config)
        old = module.read_text(encoding="utf-8") if module.is_file() else ""
        # An unpacked sdist ships the module written from git, with the tag and
        # commit that PKG-INFO lacks: keep it while it names the same version.
        if resolved.source == "sdist" and _module_version(old) == resolved.version:
            text = old
        if old != text:
            module.parent.mkdir(parents=True, exist_ok=True)
            with module.open("w", encoding="utf-8", newline="") as handle:
                handle.write(text)
        changes.append(
            Change(
                path=module.relative_to(build_root).as_posix(),
                old=None,
                new=resolved.version.pep440(),
                diff="" if old == text else "changed",
                commit=False,
                written=old != text,
            )
        )
    return resolved, changes


def _module_version(text: str) -> Version | None:
    """Read ``__version__`` back out of a generated module."""
    found = re.search(r'^__version__ = version = "(?P<version>[^"]+)"$', text, re.M)
    return Version.try_parse(found["version"]) if found else None
