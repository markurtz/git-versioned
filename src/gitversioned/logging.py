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

gitversioned is silent when used as a library: importing it disables its
loguru logger, as loguru advises for libraries. The command line turns it on
with :func:`configure_logging`, and the build plugins with
:func:`configure_build_logging`, which shows warnings only. Call
``logger.enable("gitversioned")`` to see its messages in your own handlers.

Example:
::
    from gitversioned.logging import configure_logging

    configure_logging(verbosity=1)
"""

from __future__ import annotations

import contextlib
import sys
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from loguru import Message

__all__ = ["configure_build_logging", "configure_logging"]

_LEVELS = {-1: "ERROR", 0: "WARNING", 1: "INFO", 2: "DEBUG"}


def configure_logging(verbosity: int = 0) -> None:
    """
    Send gitversioned's log output to standard error at the chosen level.

    :param verbosity: ``-1`` for errors only, ``0`` for warnings, ``1`` for
        information, ``2`` or more for debug output.
    """
    level = _LEVELS[max(-1, min(2, verbosity))]
    logger.enable("gitversioned")
    logger.remove()
    logger.add(
        # Look up the stream on every message, so a replaced stderr (a test
        # runner, a build frontend) never receives writes after it is closed.
        _to_stderr,
        level=level,
        format="<level>{level: <7}</level> {message}",
        colorize=False,
    )


_build_handler: list[int] = []


def configure_build_logging() -> None:
    """
    Show gitversioned's warnings during a package build, once per process.

    Only loguru's default handler is replaced, so a build that set up its own
    handlers keeps them.
    """
    if _build_handler:
        return
    logger.enable("gitversioned")
    with contextlib.suppress(ValueError):
        logger.remove(0)
    _build_handler.append(
        logger.add(
            _to_stderr,
            level="WARNING",
            filter="gitversioned",
            format="<level>{level: <7}</level> {message}",
            colorize=False,
        )
    )


def _to_stderr(message: Message) -> None:
    """Write one formatted log message to the current standard error."""
    sys.stderr.write(message)
