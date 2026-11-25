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

"""A stand-in for the GitHub CLI that keeps pull requests in a JSON file."""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

__all__ = ["install", "main", "read_state"]

_SCRIPT = """#!{python}
import sys
sys.path.insert(0, {root!r})
from tests.fake_gh import main
main()
"""


def install(folder: Path, state: Path, pulls: dict[str, dict] | None = None) -> Path:
    """
    Put a fake ``gh`` executable in a folder and seed its state.

    :param folder: Folder to add to ``PATH``.
    :param state: JSON file holding the pull requests.
    :param pulls: Pull requests by number to start with.
    :return: The folder, for prepending to ``PATH``.
    """
    folder.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({"pulls": pulls or {}, "calls": []}), encoding="utf-8")
    script = folder / "gh"
    root = str(Path(__file__).resolve().parents[1])
    script.write_text(
        _SCRIPT.format(python=sys.executable, root=root), encoding="utf-8"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return folder


def read_state(state: Path) -> dict:
    """Read the fake's state file."""
    return json.loads(state.read_text(encoding="utf-8"))


def _option(args: list[str], name: str) -> str | None:
    return args[args.index(name) + 1] if name in args else None


def main() -> None:
    """Handle the subset of ``gh`` commands gitversioned uses."""
    state_path = Path(os.environ["FAKE_GH_STATE"])
    state = json.loads(state_path.read_text(encoding="utf-8"))
    args = sys.argv[1:]
    state["calls"].append(args)
    pulls: dict[str, dict] = state["pulls"]
    out = ""
    code = 0
    if args[:2] == ["auth", "status"]:
        code = 1 if os.environ.get("FAKE_GH_SIGNED_OUT") else 0
    elif args[:2] == ["label", "create"]:
        pass
    elif args[:2] == ["pr", "view"]:
        found = pulls.get(args[2])
        if found is None:
            code = 1
        else:
            out = json.dumps(found)
    elif args[:2] == ["pr", "list"]:
        head = _option(args, "--head")
        out = json.dumps(
            [
                item
                for item in pulls.values()
                if item.get("head") == head and item.get("state") == "open"
            ]
        )
    elif args[:2] == ["pr", "create"]:
        number = max([int(key) for key in pulls] + [56]) + 1
        pulls[str(number)] = {
            "number": number,
            "title": _option(args, "--title"),
            "body": _option(args, "--body"),
            "labels": [{"name": _option(args, "--label")}],
            "url": f"https://github.com/acme/acme/pull/{number}",
            "head": _option(args, "--head"),
            "base": _option(args, "--base"),
            "state": "open",
        }
        out = pulls[str(number)]["url"]
    elif args[:2] == ["pr", "edit"]:
        pulls[args[2]]["title"] = _option(args, "--title")
        pulls[args[2]]["body"] = _option(args, "--body")
    else:
        code = 2
    state_path.write_text(json.dumps(state), encoding="utf-8")
    if out:
        print(out)
    sys.exit(code)
