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
Logging setup: loguru on standard error, sized by the ``-v`` and ``-q`` flags.

Example:
::
    from gitversioned.logging import configure_logging

    configure_logging(verbosity=1)
"""

from __future__ import annotations

import sys

from loguru import logger

__all__ = ["configure_logging"]

_LEVELS = {-1: "ERROR", 0: "WARNING", 1: "INFO", 2: "DEBUG"}


def configure_logging(verbosity: int = 0) -> None:
    """
    Send gitversioned's log output to standard error at the chosen level.

    :param verbosity: ``-1`` for errors only, ``0`` for warnings, ``1`` for
        information, ``2`` or more for debug output.
    """
    level = _LEVELS[max(-1, min(2, verbosity))]
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format="<level>{level: <7}</level> {message}",
        colorize=None,
    )
