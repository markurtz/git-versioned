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
Shared conftest configuration for examples tests.
"""

from __future__ import annotations

import os
from typing import Any

from loguru import logger


def pytest_configure(config: Any) -> None:
    """
    Configure environment variables and handlers before test suite runs.

    :param config: The pytest Config object.
    """
    _ = config
    os.environ.setdefault("GITVERSIONED__LOGGING__LEVEL", "ERROR")
    # Remove default loguru handler to prevent verbose debug logging to stderr
    logger.remove()
