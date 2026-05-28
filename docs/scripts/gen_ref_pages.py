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

"""Generate Python API reference pages dynamically in the docs directory."""

from __future__ import annotations

import shutil
from pathlib import Path

src = Path("src")
ref_dir = Path("docs/reference/python_api")

# Clean existing reference dir to prevent stale/deleted modules from lingering
if ref_dir.exists():
    shutil.rmtree(ref_dir)
ref_dir.mkdir(parents=True, exist_ok=True)

for path in sorted(src.rglob("*.py")):
    module_path = path.relative_to(src).with_suffix("")
    parts = list(module_path.parts)

    # Exclude __main__ command line entry points or non-public modules
    if parts[-1] == "__main__":
        continue

    is_index = False
    if parts[-1] == "__init__":
        parts.pop()
        is_index = True

    if not parts:
        continue

    import_str = ".".join(parts)

    # Strip the root package name to keep the navigation clean
    doc_parts = parts[1:]

    if is_index:
        doc_path = ref_dir.joinpath(*doc_parts, "index.md")
    else:
        doc_path = ref_dir.joinpath(*doc_parts).with_suffix(".md")

    # Ensure parent directories exist
    doc_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate the file with mkdocstrings directive
    with doc_path.open("w", encoding="utf-8") as f:
        f.write(f"# {import_str}\n\n")
        f.write(f"::: {import_str}\n")
