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
Logging setup: the standard library logger on standard error for the CLI.

As a library gitversioned logs to the ``gitversioned`` logger and adds no
handler of its own, so it stays silent until the application configures logging.

Example:
::
    from gitversioned.logging import configure_logging

    configure_logging(verbosity=1)
"""

from __future__ import annotations

import logging
import sys
from typing import Annotated

__all__ = ["LOGGER_NAME", "configure_logging", "logger"]

LOGGER_NAME: Annotated[str, "Name of the logger every module writes to"] = (
    "gitversioned"
)
logger: Annotated[logging.Logger, "The package logger"] = logging.getLogger(LOGGER_NAME)
logger.addHandler(logging.NullHandler())

_LEVELS = {-1: logging.ERROR, 0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}


def configure_logging(verbosity: int = 0) -> None:
    """
    Send gitversioned's log output to standard error at the chosen level.

    :param verbosity: ``-1`` for errors only, ``0`` for warnings, ``1`` for
        information, ``2`` or more for debug output.
    """
    level = _LEVELS[max(-1, min(2, verbosity))]
    for handler in list(logger.handlers):
        if not isinstance(handler, logging.NullHandler):
            logger.removeHandler(handler)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)-7s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
