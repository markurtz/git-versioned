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
The optional ``init`` step: the archive file and build backend wiring.

Every edit appends to a file or creates a new one; nothing existing is rewritten.

Example:
::
    from gitversioned.config import load_config
    from gitversioned.scaffold import scaffold

    for action, path, detail in scaffold(load_config()):
        print(action, path, detail)
"""

from __future__ import annotations

from gitversioned import git
from gitversioned.config import Config

__all__ = ["ARCHIVE_TEMPLATE", "scaffold"]

ARCHIVE_TEMPLATE = (
    "node: $Format:%H$\n"
    "node-date: $Format:%cI$\n"
    "describe-name: $Format:%(describe:tags=true,match=*[0-9]*)$\n"
    "ref-names: $Format:%D$\n"
)
_ATTRIBUTE_LINE = f"{git.ARCHIVE_FILE}  export-subst\n"


def _append(path, text: str) -> None:  # noqa: ANN001
    """Append text to a file, adding a newline first when the file lacks one."""
    old = path.read_text(encoding="utf-8") if path.is_file() else ""
    joiner = "" if not old or old.endswith("\n") else "\n"
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(old + joiner + text)


def scaffold(config: Config) -> list[tuple[str, str, str]]:
    """
    Set up the files a repository needs for versions to survive without git.

    :param config: The loaded configuration.
    :return: One ``(action, path, detail)`` row per step, where the action is
        ``wrote``, ``edit`` or ``ok``.
    """
    actions: list[tuple[str, str, str]] = []
    root = config.root
    archive = root / git.ARCHIVE_FILE
    if archive.is_file():
        actions.append(("ok", git.ARCHIVE_FILE, "already present"))
    else:
        archive.write_text(ARCHIVE_TEMPLATE, encoding="utf-8")
        actions.append(("wrote", git.ARCHIVE_FILE, ""))
    attributes = root / ".gitattributes"
    current = attributes.read_text(encoding="utf-8") if attributes.is_file() else ""
    if git.ARCHIVE_FILE in current and "export-subst" in current:
        actions.append(("ok", ".gitattributes", "already marks the archive file"))
    else:
        _append(attributes, _ATTRIBUTE_LINE)
        actions.append(("edit", ".gitattributes", f"+ {_ATTRIBUTE_LINE.strip()}"))
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8")
        if (
            "hatchling" in text
            and "[tool.hatch.version]" not in text
            and "dynamic" in text
        ):
            _append(pyproject, '\n[tool.hatch.version]\nsource = "gitversioned"\n')
            actions.append(
                (
                    "edit",
                    "pyproject.toml",
                    '+ [tool.hatch.version] source = "gitversioned"',
                )
            )
    return actions
