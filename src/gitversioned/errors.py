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
Errors raised by gitversioned, each mapped to a CLI exit code.

Exit codes: 1 for a failed check or nothing to release, 2 for bad usage or
configuration, 3 for a problem with the environment such as a shallow clone.
"""

from __future__ import annotations

__all__ = [
    "CheckFailedError",
    "ConfigError",
    "EnvironmentProblemError",
    "GitVersionedError",
    "NothingToReleaseError",
]


class GitVersionedError(Exception):
    """
    Base class for every error gitversioned raises on purpose.

    :cvar exit_code: Process exit code the CLI uses for this error.
    """

    exit_code: int = 1


class CheckFailedError(GitVersionedError):
    """A validation failed: a title, a commit, a tag or the repository setup."""

    exit_code = 1


class NothingToReleaseError(GitVersionedError):
    """No commit since the last release justifies a new one."""

    exit_code = 1


class ConfigError(GitVersionedError):
    """The configuration or the command line is invalid."""

    exit_code = 2


class EnvironmentProblemError(GitVersionedError):
    """The environment cannot give a trustworthy answer (no git, shallow clone)."""

    exit_code = 3
