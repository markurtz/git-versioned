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
#
# Unless otherwise noted, all files in this directory and its subdirectories
# are licensed under the Apache License, Version 2.0.

"""
Opinionated PEP 440 Python versioning for Git repos and submodules.

Provides an automated, deterministic system for generating rich version information from
Git repository metadata. It enforces CI/User authority and creates version files with
deep metadata for auditability, integrating natively with Hatch and Setuptools.

Example:
::
    from gitversioned import Settings, resolve_version
    from gitversioned.utils import BuildEnvironment, GitRepository

    version, _, ref = resolve_version(
        Settings(), GitRepository(), BuildEnvironment()
    )
    print("Current version:", version)
"""

from __future__ import annotations

from .logging import LoggingSettings, configure_logger
from .settings import Settings
from .utils import BuildEnvironment, GitRepository
from .versioning import (
    resolve_version,
    resolve_version_output,
    resolve_version_output_to_stream,
)

__all__ = [
    "BuildEnvironment",
    "GitRepository",
    "LoggingSettings",
    "Settings",
    "__version__",
    "configure_logger",
    "resolve_version",
    "resolve_version_output",
    "resolve_version_output_to_stream",
]

__version__ = "0.3.1.dev25+652050a"

configure_logger()
