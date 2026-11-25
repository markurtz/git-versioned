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

"""Shared fixtures: scratch git repositories and a CLI runner."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from gitversioned.cli import app

__all__ = ["CliResult", "RepoBuilder", "clean_env", "repo"]


class CliResult:
    """
    The outcome of one CLI call.

    :param code: Exit code.
    :param out: Standard output.
    :param err: Standard error.
    """

    def __init__(self, code: int, out: str, err: str) -> None:
        self.code = code
        self.out = out
        self.err = err

    @property
    def json(self) -> dict:
        """
        :return: Standard output parsed as JSON.
        """
        return json.loads(self.out)

    @property
    def first(self) -> str:
        """
        :return: The first line of standard output.
        """
        return self.out.splitlines()[0] if self.out.strip() else ""


class RepoBuilder:
    """
    Builds a git repository in a temporary folder and runs the CLI in it.

    :param path: Folder to create the repository in.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        path.mkdir(parents=True, exist_ok=True)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Test User")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "tag.gpgsign", "false")
        self._clock = 1_700_000_000

    def git(self, *args: str) -> str:
        """Run git in the repository and return its output."""
        result = subprocess.run(
            ["git", *args], cwd=self.path, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()

    def write(self, name: str, text: str) -> Path:
        """Write a file, creating parent folders."""
        target = self.path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def read(self, name: str) -> str:
        """Read a file."""
        return (self.path / name).read_text(encoding="utf-8")

    def commit(self, message: str, files: dict[str, str] | None = None) -> str:
        """Commit the given files, or an empty commit, with a fixed date."""
        for name, text in (files or {}).items():
            self.write(name, text)
        self.git("add", "-A")
        self._clock += 86_400
        stamp = f"{self._clock} +0000"
        subprocess.run(
            ["git", "commit", "-q", "--allow-empty", "-m", message],
            cwd=self.path,
            check=True,
            env={**os.environ, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp},
        )
        return self.git("rev-parse", "HEAD")

    def tag(self, name: str, *, annotated: bool = False) -> None:
        """Create a lightweight or annotated tag at HEAD."""
        if annotated:
            self.git("tag", "-a", name, "-m", f"Release {name}")
        else:
            self.git("tag", name)

    def run(self, *args: str, env: dict[str, str] | None = None) -> CliResult:
        """Run the gitversioned CLI in the repository."""
        runner = CliRunner()
        result = runner.invoke(app, [*args, "--root", str(self.path)], env=env)
        if result.exception and not isinstance(result.exception, SystemExit):
            raise result.exception
        try:
            err = result.stderr
        except ValueError:
            err = ""
        return CliResult(result.exit_code, result.stdout, err)


@pytest.fixture(autouse=True)
def clean_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Remove settings that would leak from the host into a test."""
    for name in list(os.environ):
        if name.startswith("GITVERSIONED__") or name in (
            "CI",
            "GH_TOKEN",
            "GITHUB_TOKEN",
        ):
            monkeypatch.delenv(name, raising=False)
    empty = tmp_path_factory.mktemp("gitconfig") / "config"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("NO_COLOR", "1")


@pytest.fixture
def repo(tmp_path: Path) -> RepoBuilder:
    """A fresh repository with one commit."""
    builder = RepoBuilder(tmp_path / "repo")
    builder.commit(
        "chore: initial commit",
        {
            "README.md": "# demo\n",
            "pyproject.toml": '[project]\nname = "demo"\ndynamic = ["version"]\n',
        },
    )
    return builder
