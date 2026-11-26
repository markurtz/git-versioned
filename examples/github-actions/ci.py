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
Run a workflow's steps here, the way GitHub Actions would run them.

Usage: ``python ci.py WORKFLOW [--event KEY=VALUE ...]``. Each ``run`` step runs
with ``bash`` in this folder, with its ``env`` and ``CI=true``, and what it
appends to ``$GITHUB_ENV`` is printed. ``${{ <expression> }}`` takes the value
given with ``--event``, or an empty string. A job's
``if: startsWith(<expression>, '<text>')`` is evaluated, with an optional
leading ``!``. ``uses`` steps are listed and skipped, since this
folder is already the checkout, except the gitversioned action itself: with
``GITVERSIONED_ACTION_PATH`` naming a checkout of it, its step runs with the
step's ``with`` inputs and the outputs it writes are printed. ``pipx run`` and
``uvx`` run the tool already installed.

Only the shapes used in this folder's workflows are understood; it is a test
harness, not a workflow engine.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

EXPRESSION = re.compile(r"\$\{\{\s*(.*?)\s*\}\}")
CONDITION = re.compile(
    r"^(?P<neg>!?)startsWith\((?P<expr>[\w.]+),\s*'(?P<text>[^']*)'\)$"
)
PIPX = """pipx() {
  [ "$1" = run ] && shift
  if [ "$1" = build ]; then
    shift; python -m build --no-isolation "$@" >/dev/null 2>&1 && ls dist
  else "$@"; fi
}
"""


JOB, JOB_KEY, STEP, STEP_KEY, STEP_VALUE = 2, 4, 6, 8, 10


def parse_jobs(text: str) -> dict[str, dict]:
    """Read jobs, their ``if`` and their steps from a workflow's text."""
    jobs: dict[str, dict] = {}
    job: dict = {}
    step: dict = {}
    block = ""
    section = ""
    for line in text.splitlines():
        indent = len(line) - len(line.lstrip())
        content = line.strip()
        if block and (not content or indent >= STEP_VALUE):
            step[block] += line[STEP_VALUE:] + "\n"
            continue
        block = ""
        if not content or content.startswith("#"):
            continue
        if indent == 0:
            section = content.rstrip(":")
        elif section != "jobs":
            continue
        elif indent == JOB:
            job = jobs.setdefault(content.rstrip(":"), {"if": "", "steps": []})
        elif indent == JOB_KEY and content.startswith("if:"):
            job["if"] = content[3:].strip()
        elif indent == STEP and content.startswith("- "):
            step = {"env": {}}
            job["steps"].append(step)
            block = _step_line(step, STEP_KEY, content[2:])
        elif step and indent >= STEP_KEY:
            block = _step_line(step, indent, content)
    return jobs


def _step_line(step: dict, indent: int, content: str) -> str:
    """Record one line of a step; return the key a ``|`` block fills, if any."""
    key, _, value = content.partition(":")
    value = value.strip()
    if indent == STEP_KEY:
        step["_last"] = key
        if value == "|":
            step[key] = ""
            return key
        if key not in ("env", "with"):
            step[key] = value
    elif indent == STEP_VALUE and step.get("_last") in ("env", "with"):
        step.setdefault(step["_last"], {})[key] = value
    return ""


def expand(text: str, event: dict[str, str]) -> str:
    """Replace ``${{ expression }}`` with the given values."""
    return EXPRESSION.sub(lambda found: event.get(found[1], ""), text)


def should_run(condition: str, event: dict[str, str]) -> bool:
    """Evaluate a job's ``if``."""
    condition = EXPRESSION.sub(r"\1", condition).strip()
    if not condition:
        return True
    found = CONDITION.match(condition)
    if found is None:
        raise SystemExit(f"unsupported condition: {condition}")
    result = event.get(found["expr"], "").startswith(found["text"])
    return result != bool(found["neg"])


def run_action(step: dict, event: dict[str, str], env: dict[str, str]) -> int:
    """Run the gitversioned action's step with the step's inputs."""
    folder = Path(tempfile.mkdtemp())
    shim = folder / "uvx"
    shim.write_text('#!/usr/bin/env bash\nshift 3\nexec "$@"\n', encoding="utf-8")
    shim.chmod(0o755)
    output = folder / "github-output"
    inputs = {key: expand(value, event) for key, value in step.get("with", {}).items()}
    run_env = {
        **env,
        "PATH": f"{folder}{os.pathsep}{env['PATH']}",
        "GITHUB_OUTPUT": str(output),
        "INPUT_COMMAND": inputs.get("command", "version"),
        "INPUT_TITLE": inputs.get("title", ""),
        "INPUT_VERSION": inputs.get("version", ""),
    }
    script = Path(env["GITVERSIONED_ACTION_PATH"]) / "action" / "run.sh"
    code = subprocess.run(["bash", str(script)], env=run_env, check=False).returncode  # noqa: S603, S607
    if output.is_file():
        for line in output.read_text(encoding="utf-8").splitlines():
            if line.startswith("version="):
                print(f"  output {line}")
    return code


def main() -> int:
    """Run the workflow and return the exit code of the first failing step."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("workflow", type=Path)
    parser.add_argument("--event", action="append", default=[], metavar="KEY=VALUE")
    args = parser.parse_args()
    event = dict(item.split("=", 1) for item in args.event)
    github_env = Path(tempfile.mkdtemp()) / "github-env"
    github_env.write_text("", encoding="utf-8")
    for name, job in parse_jobs(args.workflow.read_text(encoding="utf-8")).items():
        if not should_run(job["if"], event):
            print(f"job {name}: skipped")
            continue
        print(f"job {name}")
        for step in job["steps"]:
            env = {**os.environ, "CI": "true", "GITHUB_ACTIONS": "true"}
            env["GITHUB_ENV"] = str(github_env)
            uses = step.get("uses", "")
            if uses.startswith("markurtz/git-versioned@") and env.get(
                "GITVERSIONED_ACTION_PATH"
            ):
                print(f"  uses {uses}")
                sys.stdout.flush()
                code = run_action(step, event, env)
                if code:
                    print(f"  failed with exit code {code}")
                    return code
                continue
            if uses:
                print(f"  uses {uses}: skipped")
                continue
            print(f"  step {step.get('name', 'run')}")
            sys.stdout.flush()
            env.update(
                {key: expand(value, event) for key, value in step["env"].items()}
            )
            script = PIPX + expand(step["run"], event)
            code = subprocess.run(
                ["bash", "-e", "-c", script], env=env, check=False
            ).returncode  # noqa: S603, S607
            for line in github_env.read_text(encoding="utf-8").splitlines():
                print(f"  env {line}")
            github_env.write_text("", encoding="utf-8")
            if code:
                print(f"  failed with exit code {code}")
                return code
    return 0


if __name__ == "__main__":
    sys.exit(main())
