"""Add the Apache 2.0 license header to Python files that lack it."""

from __future__ import annotations

import sys
from pathlib import Path

HEADER = """# Copyright 2026 markurtz
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


def main() -> None:
    """Prepend the header to every Python file under the given folders."""
    for folder in sys.argv[1:] or ["src", "tests", "examples", "scripts"]:
        for path in Path(folder).rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "Licensed under the Apache License" not in text[:400]:
                path.write_text(HEADER + text, encoding="utf-8")
                print(f"header added: {path}")


if __name__ == "__main__":
    main()
