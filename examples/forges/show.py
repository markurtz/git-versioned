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
Print what the stand-in forges recorded: pull requests and releases.

Usage: ``python show.py github|gitlab|gitea``. The state files are named by
``FAKE_GH_STATE``, ``FAKE_GITLAB_STATE`` and ``FAKE_GITEA_STATE``; against a
real forge, look at its web pages instead.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

VARIABLES = {
    "github": "FAKE_GH_STATE",
    "gitlab": "FAKE_GITLAB_STATE",
    "gitea": "FAKE_GITEA_STATE",
}


def _branch(value: object) -> str:
    return value["ref"] if isinstance(value, dict) else str(value)


def main() -> int:
    """Print the pull requests and releases of one forge."""
    forge = sys.argv[1]
    state = json.loads(Path(os.environ[VARIABLES[forge]]).read_text(encoding="utf-8"))
    for number, pull in state.get("pulls", {}).items():
        head = _branch(pull.get("head") or pull.get("source_branch"))
        base = _branch(pull.get("base") or pull.get("target_branch"))
        labels = [
            label if isinstance(label, str) else label["name"]
            for label in pull.get("labels", [])
        ]
        print(f"pull {number}  {head} -> {base}  {pull['title']}  {labels}")
    for tag, release in state.get("releases", {}).items():
        notes = (
            release.get("notes") or release.get("description") or release.get("body")
        )
        first = next(line for line in notes.splitlines() if line.startswith("- "))
        print(f"release {tag}  {first}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
