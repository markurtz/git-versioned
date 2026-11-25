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
Hatchling integration: a version source and a build hook.

Example:
::
    [build-system]
    requires = ["hatchling", "gitversioned>=0.4"]
    build-backend = "hatchling.build"

    [tool.hatch.version]
    source = "gitversioned"

    [tool.hatch.build.hooks.gitversioned]
"""

from __future__ import annotations

from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.plugin import hookimpl
from hatchling.version.source.plugin.interface import VersionSourceInterface

from gitversioned.plugins import resolve_for_build

__all__ = [
    "GitVersionedBuildHook",
    "GitVersionedVersionSource",
    "hatch_register_build_hook",
    "hatch_register_version_source",
]


class GitVersionedVersionSource(VersionSourceInterface):
    """Give Hatchling the version resolved from git and write ``version.py``."""

    PLUGIN_NAME = "gitversioned"

    def get_version_data(self) -> dict[str, Any]:
        """
        :return: The version in PEP 440 form under the ``version`` key.
        """
        resolved, _changes = resolve_for_build(self.root)
        return {"version": resolved.version.pep440()}

    def set_version(self, version: str, version_data: dict[str, Any]) -> None:
        """Refuse to set a version, since tags are the only source of truth."""
        raise NotImplementedError(
            "gitversioned reads versions from git tags; create a tag instead."
        )


class GitVersionedBuildHook(BuildHookInterface):
    """Ship the generated ``version.py`` even when git ignores it."""

    PLUGIN_NAME = "gitversioned"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """
        Write the generated module and add it to the build as an artifact.

        :param version: Build version label passed by Hatchling.
        :param build_data: Mutable build data; ``artifacts`` is extended.
        """
        _resolved, changes = resolve_for_build(self.root)
        artifacts = build_data.setdefault("artifacts", [])
        for change in changes:
            if change.path not in artifacts:
                artifacts.append(change.path)


@hookimpl
def hatch_register_version_source() -> type[VersionSourceInterface]:
    """Register the version source with Hatchling."""
    return GitVersionedVersionSource


@hookimpl
def hatch_register_build_hook() -> type[BuildHookInterface]:
    """Register the build hook with Hatchling."""
    return GitVersionedBuildHook
