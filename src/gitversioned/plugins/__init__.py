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
Build backend integrations: Hatchling, setuptools and Maturin.

Each integration resolves the version once and writes the generated
``version.py``, so a build needs no gitversioned settings at all.
"""

from __future__ import annotations

from pathlib import Path

from gitversioned.config import load_config
from gitversioned.resolve import Resolved, resolve
from gitversioned.targets import Change, stamp

__all__ = ["resolve_for_build"]


def resolve_for_build(
    root: Path | str, *, write: bool = True
) -> tuple[Resolved, list[Change]]:
    """
    Resolve the version for a build and write the generated module.

    :param root: Project folder being built.
    :param write: Write the generated ``version.py`` when the project has one.
    :return: The resolved version and the files written.
    """
    config = load_config(Path(root))
    resolved = resolve(config)
    changes: list[Change] = []
    if write:
        changes = [
            change
            for change in stamp(config, resolved, generated_only=True)
            if change.written or not change.diff
        ]
    return resolved, changes
