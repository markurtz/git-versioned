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
Run every example's README as a test.

Each ``examples/<topic>/README.md`` holds console transcripts in ```` ```console ````
fences. A line starting with ``$`` is a command (``>`` continues it), and the
lines after it are the output it must print, stdout and stderr together. A line
that is only ``...`` stands for any number of lines, ``...`` inside a line for
any text, and a final ``[exit N]`` line for a non-zero exit code.

The example folder is copied, without its README, into a fresh folder; every
command runs there with ``bash`` in order, so later commands see earlier ones.
Git identities and dates are fixed, and ``SOURCE_DATE_EPOCH`` pins the build
date, so hashes and versions are the same on every run. A fake ``gh`` on
``PATH`` records pull requests in a JSON file, and ``origin`` can be a bare
repository next to the example.

Run ``pytest examples --update-examples`` to rewrite the expected output of
every command whose output changed; lines that still match are kept, so
wildcards survive.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests import fake_gh  # noqa: E402

__all__ = [
    "EXAMPLES",
    "MANIFEST",
    "Command",
    "TranscriptItem",
    "load_manifest",
    "parse_transcript",
    "pytest_addoption",
    "pytest_collect_file",
]

EXAMPLES: Annotated[Path, "Folder holding every example topic."] = Path(__file__).parent
MANIFEST: Annotated[Path, "The examples manifest, the index of every topic."] = (
    EXAMPLES / "manifest.toml"
)
EPOCH: Annotated[int, "Fixed time of every commit and build: 2026-11-25 12:00 UTC."] = (
    1795608000
)
_FENCE_RE = re.compile(r"^```console[ \t]*\n(?P<body>.*?)^```[ \t]*$", re.M | re.S)
_EXIT_RE = re.compile(r"^\[exit (?P<code>\d+)\]$")
_SKIP_COPY = {"README.md", "__pycache__", ".pytest_cache", "dist", "target", "build"}


@dataclass
class Command:
    """One command of a transcript and the output it must print."""

    text: str
    expected: list[str] = field(default_factory=list)
    code: int = 0
    start: int = 0
    end: int = 0


def load_manifest() -> dict:
    """Read ``examples/manifest.toml``."""
    with MANIFEST.open("rb") as handle:
        return tomllib.load(handle)


def parse_transcript(text: str) -> list[Command]:
    """
    Read the commands of every ``console`` fence in a README.

    :param text: README content.
    :return: Commands in order, with the character span of each one's output.
    """
    commands: list[Command] = []
    for fence in _FENCE_RE.finditer(text):
        offset = fence.start("body")
        current: Command | None = None
        position = offset
        for line in fence["body"].splitlines(keepends=True):
            stripped = line.rstrip("\n")
            if stripped.startswith("$ ") or stripped == "$":
                if current is not None:
                    current.end = position
                current = Command(stripped[2:], start=position + len(line))
                commands.append(current)
            elif stripped.startswith("> ") and current and not current.expected:
                current.text += "\n" + stripped[2:]
                current.start = position + len(line)
            elif current is not None:
                current.expected.append(stripped)
            position += len(line)
        if current is not None:
            current.end = position
    for command in commands:
        if command.expected and (found := _EXIT_RE.match(command.expected[-1])):
            command.code = int(found["code"])
            command.expected.pop()
    return commands


def _line_matches(expected: str, actual: str) -> bool:
    if "..." not in expected:
        return expected == actual
    pattern = ".*".join(re.escape(part) for part in expected.split("..."))
    return re.fullmatch(pattern, actual) is not None


def _matches(expected: list[str], actual: list[str]) -> bool:
    """Compare output lines, honouring ``...`` wildcards."""
    if not expected:
        return not actual
    head, *rest = expected
    if head == "...":
        return any(_matches(rest, actual[index:]) for index in range(len(actual) + 1))
    return (
        bool(actual) and _line_matches(head, actual[0]) and _matches(rest, actual[1:])
    )


def _environment(work: Path, tools: Path) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GITVERSIONED__", "GIT_", "GH_", "GITHUB_"))
        and key not in ("CI", "VIRTUAL_ENV", "FAKE_GH_SIGNED_OUT")
    }
    stamp = f"@{EPOCH} +0000"
    env.update(
        {
            "PATH": os.pathsep.join(
                [str(tools), str(Path(sys.executable).parent), env.get("PATH", "")]
            ),
            "HOME": str(work.parent / "home"),
            "GIT_AUTHOR_NAME": "Example",
            "GIT_AUTHOR_EMAIL": "example@example.com",
            "GIT_COMMITTER_NAME": "Example",
            "GIT_COMMITTER_EMAIL": "example@example.com",
            "GIT_AUTHOR_DATE": stamp,
            "GIT_COMMITTER_DATE": stamp,
            "GIT_CONFIG_GLOBAL": str(work.parent / "home" / ".gitconfig"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "SOURCE_DATE_EPOCH": str(EPOCH),
            "FAKE_GH_STATE": str(work.parent / "gh-state.json"),
            "NO_COLOR": "1",
            "TERM": "dumb",
            "COLUMNS": "100",
            "TZ": "UTC",
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "CARGO_TARGET_DIR": str(work.parent / "cargo-target"),
        }
    )
    return env


def _prepare(source: Path, root: Path, entry: dict) -> tuple[Path, dict[str, str]]:
    """Copy an example into a fresh folder and build the environment."""
    work = root / source.name
    shutil.copytree(source, work, ignore=lambda _dir, names: _SKIP_COPY & set(names))
    tools = root / "tools"
    fake_gh.install(tools, root / "gh-state.json")
    (root / "home").mkdir()
    (root / "home" / ".gitconfig").write_text(
        "[init]\n\tdefaultBranch = main\n[advice]\n\tdetachedHead = false\n",
        encoding="utf-8",
    )
    env = _environment(work, tools)
    if not entry.get("gh", False):
        env["FAKE_GH_SIGNED_OUT"] = "1"
    return work, env


def _run(
    command: Command, work: Path, env: dict[str, str], timeout: int
) -> tuple[int, list[str]]:
    result = subprocess.run(  # noqa: S603
        ["bash", "-o", "pipefail", "-c", command.text],  # noqa: S607
        cwd=work,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
        check=False,
    )
    output = result.stdout.replace(str(work.parent), "/tmp")  # noqa: S108
    return result.returncode, [line.rstrip() for line in output.splitlines()]


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add ``--update-examples``."""
    parser.addoption(
        "--update-examples",
        action="store_true",
        default=False,
        help="Rewrite the expected output in example READMEs from a real run.",
    )


def pytest_collect_file(
    parent: pytest.Collector, file_path: Path
) -> pytest.Collector | None:
    """Collect ``examples/<topic>/README.md`` files listed in the manifest."""
    if file_path.name != "README.md" or file_path.parent.parent != EXAMPLES:
        return None
    if file_path.parent.name not in load_manifest().get("example", {}):
        return None
    return TranscriptFile.from_parent(parent, path=file_path)


class TranscriptFile(pytest.File):
    """An example README, collected as one test."""

    def collect(self):  # noqa: ANN201
        """Yield the README's single transcript test."""
        topic = self.path.parent.name
        entry = load_manifest()["example"][topic]
        item = TranscriptItem.from_parent(self, name=f"example[{topic}]", entry=entry)
        item.add_marker(entry.get("marker", "sanity"))
        yield item


class TranscriptItem(pytest.Item):
    """Runs a README's commands in order and compares their output."""

    def __init__(self, *, entry: dict, **kwargs) -> None:  # noqa: ANN003
        super().__init__(**kwargs)
        self.entry = entry

    def runtest(self) -> None:
        """Run every command and fail on the first mismatch."""
        for tool in self.entry.get("requires", []):
            if shutil.which(tool) is None:
                pytest.skip(f"needs {tool}")
        readme = self.path
        text = readme.read_text(encoding="utf-8")
        commands = parse_transcript(text)
        assert commands, f"{readme} has no console transcript"
        root = Path(self.config._tmp_path_factory.mktemp(self.path.parent.name))  # noqa: SLF001
        work, env = _prepare(readme.parent, root, self.entry)
        update = self.config.getoption("--update-examples")
        timeout = int(self.entry.get("timeout", 120))
        replacements: list[tuple[Command, list[str], int]] = []
        for command in commands:
            code, actual = _run(command, work, env, timeout)
            if code == command.code and _matches(command.expected, actual):
                continue
            if not update:
                raise TranscriptError(command, code, actual)
            replacements.append((command, actual, code))
        if replacements:
            for command, actual, code in reversed(replacements):
                lines = actual + ([f"[exit {code}]"] if code else [])
                body = "".join(f"{line}\n" for line in lines)
                text = text[: command.start] + body + text[command.end :]
            readme.write_text(text, encoding="utf-8")

    def repr_failure(self, excinfo, style=None):  # noqa: ANN001, ANN201, ARG002
        """Show the command, the expected and the actual output."""
        if isinstance(excinfo.value, TranscriptError):
            error = excinfo.value
            return "\n".join(
                [
                    f"$ {error.command.text}",
                    f"--- expected (exit {error.command.code})",
                    *error.command.expected,
                    f"--- actual (exit {error.code})",
                    *error.actual,
                ]
            )
        return super().repr_failure(excinfo)

    def reportinfo(self):  # noqa: ANN201
        """Name the README in reports."""
        return self.path, 0, self.name


class TranscriptError(AssertionError):
    """A command printed something other than its transcript says."""

    def __init__(self, command: Command, code: int, actual: list[str]) -> None:
        super().__init__(command.text)
        self.command = command
        self.code = code
        self.actual = actual
