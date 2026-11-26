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
The GitHub side of a release, through the ``gh`` command line tool.

Nothing here is needed to resolve, stamp or check a version. The release pull
request, pull request titles for the changelog and label overrides use it, and
each caller degrades or fails with a clear message when ``gh`` is not usable.

Example:
::
    from pathlib import Path

    from gitversioned import github

    if github.available(Path.cwd()):
        print(github.pull_request(Path.cwd(), 41))
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loguru import logger

from gitversioned import git
from gitversioned.errors import EnvironmentProblemError

__all__ = [
    "PullRequest",
    "available",
    "create_pull_request",
    "create_release",
    "find_open_pull_request",
    "gh",
    "pull_request",
    "repo_url",
    "update_pull_request",
]


@dataclass(frozen=True)
class PullRequest:
    """
    The parts of a pull request gitversioned reads.

    :param number: Pull request number.
    :param title: Title.
    :param body: Description.
    :param labels: Label names.
    :param url: Web address.
    """

    number: int
    title: str
    body: str
    labels: tuple[str, ...]
    url: str = ""


def gh(args: list[str], cwd: Path, *, check: bool = True) -> str | None:
    """
    Run a ``gh`` command.

    :param args: Arguments after ``gh``.
    :param cwd: Folder to run in.
    :param check: When False, failure returns ``None`` instead of raising.
    :return: Standard output, or ``None`` on failure when ``check`` is False.
    :raises EnvironmentProblemError: If ``gh`` is missing or the command fails
        and ``check`` is True.
    """
    if shutil.which("gh") is None:
        if check:
            raise EnvironmentProblemError(
                "the GitHub CLI `gh` is not installed. Install it from "
                "https://cli.github.com to use release --pr."
            )
        return None
    logger.debug(f"gh {' '.join(args[:3])}")
    result = subprocess.run(  # noqa: S603
        ["gh", *args],  # noqa: S607
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        if check:
            raise EnvironmentProblemError(
                f"gh {' '.join(args[:2])} failed: {result.stderr.strip()}"
            )
        return None
    return result.stdout.strip()


def available(cwd: Path) -> bool:
    """
    :return: True when ``gh`` is installed and signed in for this repository.
    """
    return gh(["auth", "status"], cwd, check=False) is not None


def repo_url(repo: git.Repo) -> str | None:
    """
    Work out the web address of the repository from its ``origin`` remote.

    :param repo: The repository.
    :return: An ``https://github.com/owner/name`` address, or ``None``.
    """
    remote = repo.git("remote", "get-url", "origin", check=False)
    if not remote:
        return None
    match = re.match(
        r"^(?:https?://|git@|ssh://git@)(?P<host>[^/:]+)[/:](?P<path>.+?)(?:\.git)?/?$",
        remote.strip(),
    )
    if match is None or "github" not in match["host"]:
        return None
    return f"https://{match['host']}/{match['path']}"


def _to_pull_request(data: dict[str, Any]) -> PullRequest:
    """Build a pull request from ``gh`` JSON."""
    return PullRequest(
        number=int(data["number"]),
        title=data.get("title", ""),
        body=data.get("body", "") or "",
        labels=tuple(label["name"] for label in data.get("labels", [])),
        url=data.get("url", ""),
    )


def pull_request(cwd: Path, number: int) -> PullRequest | None:
    """
    Read one pull request.

    :param cwd: Folder inside the repository.
    :param number: Pull request number.
    :return: The pull request, or ``None`` when it cannot be read.
    """
    out = gh(
        ["pr", "view", str(number), "--json", "number,title,body,labels,url"],
        cwd,
        check=False,
    )
    if not out:
        return None
    try:
        return _to_pull_request(json.loads(out))
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def find_open_pull_request(cwd: Path, head: str) -> PullRequest | None:
    """
    Find the open pull request for a head branch.

    :param cwd: Folder inside the repository.
    :param head: Head branch name.
    :return: The pull request, or ``None`` when none is open.
    """
    out = gh(
        [
            "pr",
            "list",
            "--head",
            head,
            "--state",
            "open",
            "--json",
            "number,title,body,labels,url",
        ],
        cwd,
    )
    items = json.loads(out or "[]")
    return _to_pull_request(items[0]) if items else None


def create_pull_request(
    cwd: Path, *, head: str, base: str, title: str, body: str, label: str
) -> PullRequest:
    """
    Open a pull request and label it.

    :param cwd: Folder inside the repository.
    :param head: Head branch.
    :param base: Base branch.
    :param title: Title.
    :param body: Description.
    :param label: Label to add; created when missing.
    :return: The opened pull request.
    """
    # Without --force an existing label (and its colour) is left as it is.
    gh(["label", "create", label], cwd, check=False)
    url = gh(
        [
            "pr",
            "create",
            "--head",
            head,
            "--base",
            base,
            "--title",
            title,
            "--body",
            body,
            "--label",
            label,
        ],
        cwd,
    )
    found = find_open_pull_request(cwd, head)
    if found is not None:
        return found
    return PullRequest(number=0, title=title, body=body, labels=(label,), url=url or "")


def update_pull_request(cwd: Path, number: int, *, title: str, body: str) -> None:
    """
    Replace the title and description of a pull request.

    :param cwd: Folder inside the repository.
    :param number: Pull request number.
    :param title: New title.
    :param body: New description.
    """
    gh(["pr", "edit", str(number), "--title", title, "--body", body], cwd)


def create_release(
    cwd: Path,
    *,
    tag: str,
    notes: str,
    prerelease: bool,
    files: list[Path] | None = None,
) -> str:
    """
    Create a GitHub release for an existing tag, with its notes and files.

    The release is created as a draft, the files are uploaded, then it is
    published, which also works with immutable releases.

    :param cwd: Folder inside the repository.
    :param tag: Tag the release is for; it must already be pushed.
    :param notes: Release notes in Markdown.
    :param prerelease: Mark the release as a pre-release.
    :param files: Files to attach.
    :return: The release's web address.
    """
    args = ["release", "create", tag, "--title", tag, "--notes", notes]
    args += ["--verify-tag", "--draft"]
    if prerelease:
        args.append("--prerelease")
    url = gh(args, cwd) or ""
    if files:
        gh(["release", "upload", tag, "--clobber", *map(str, files)], cwd)
    published = gh(["release", "edit", tag, "--draft=false"], cwd)
    return (published or url).strip()
