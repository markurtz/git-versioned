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
Custom Zensical macros for markdown document processing.

This module defines hooks to dynamically modify documentation pages
during Zensical builds, such as conditionally embedding files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

__all__: Annotated[
    list[str],
    "The list of public symbols exported by this module.",
] = [
    "define_env",
]


def define_env(env: Any) -> None:
    """
    Register custom macros in the documentation environment.

    This function hooks into Zensical's build cycle to register dynamic markdown
    macros, enabling conditional file inclusion and API documentation linking.

    Example:
        >>> class MockEnv:
        ...     def macro(self, func): return func
        >>> define_env(MockEnv())

    :param env: The documentation environment instance used to register macros.
    :return: None
    """

    @env.macro
    def include_file_or_placeholder(file_path: str, placeholder: str) -> str:
        target_path = Path(file_path)
        if target_path.exists():
            return target_path.read_text(encoding="utf-8")
        return placeholder
