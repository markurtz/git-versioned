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
Versions from git tags for Python, Rust and npm projects in one repository.

gitversioned resolves the version of a checkout from its release tags, stamps it
into every manifest with scoped text edits, validates Conventional Commit titles
and drives a reviewed release: changelog, release pull request and tag.

Example:
::
    from gitversioned import get_version, load_config, resolve

    print(get_version())
    resolved = resolve(load_config())
    print(resolved.version.semver(), resolved.type)
"""

from __future__ import annotations

from pathlib import Path

from gitversioned.config import Config, load_config
from gitversioned.errors import (
    CheckFailedError,
    ConfigError,
    EnvironmentProblemError,
    GitVersionedError,
    NothingToReleaseError,
)
from gitversioned.model import Version
from gitversioned.release import ReleasePlan, plan_release
from gitversioned.resolve import Resolved, resolve
from gitversioned.targets import stamp

__all__ = [
    "CheckFailedError",
    "Config",
    "ConfigError",
    "EnvironmentProblemError",
    "GitVersionedError",
    "NothingToReleaseError",
    "ReleasePlan",
    "Resolved",
    "Version",
    "__version__",
    "get_version",
    "load_config",
    "plan_release",
    "resolve",
    "stamp",
]

__version__ = "0.4.0"


def get_version(root: Path | str | None = None, *, standard: str = "pep440") -> str:
    """
    Resolve the version of a project as text.

    :param root: Project folder; defaults to the current one.
    :param standard: ``pep440`` or ``semver``.
    :return: The version of the checkout.
    """
    config = load_config(Path(root) if root is not None else None)
    return resolve(config).version.render(standard)  # type: ignore[arg-type]
