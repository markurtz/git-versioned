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
Setuptools integration, active only for projects that ask for it.

A project opts in by listing ``gitversioned`` in ``build-system.requires`` or by
passing ``gitversioned=True`` to ``setup()``.

Example:
::
    [build-system]
    requires = ["setuptools>=64", "gitversioned>=0.4"]
    build-backend = "setuptools.build_meta"

    [project]
    name = "acme"
    dynamic = ["version"]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from gitversioned.plugins import resolve_for_build

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

__all__ = ["finalize_distribution_options", "setup_keyword"]


def _opted_in(root: Path) -> bool:
    """Tell whether the project lists gitversioned as a build requirement."""
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return False
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return False
    requires = data.get("build-system", {}).get("requires", [])
    return any(re.match(r"^gitversioned\b", str(item).strip()) for item in requires)


def _apply(dist: Any) -> None:
    """Set the distribution version from git."""
    resolved, _changes = resolve_for_build(Path.cwd())
    dist.metadata.version = resolved.version.pep440()


def setup_keyword(dist: Any, keyword: str, value: Any) -> None:
    """
    Handle ``setup(gitversioned=True)``.

    :param dist: The setuptools distribution.
    :param keyword: The keyword name.
    :param value: Truthy to turn the integration on.
    """
    if value:
        _apply(dist)


def finalize_distribution_options(dist: Any) -> None:
    """
    Set the version for projects that list gitversioned as a build requirement.

    :param dist: The setuptools distribution.
    """
    if dist.metadata.version not in (None, "0.0.0"):
        return
    if _opted_in(Path.cwd()):
        _apply(dist)
