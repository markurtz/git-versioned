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
The forge a release talks to: GitHub, GitLab or Gitea (and Forgejo).

GitHub goes through the ``gh`` command line tool, signed in with ``GH_TOKEN``.
GitLab and Gitea go through their REST APIs with ``GITLAB_TOKEN`` or
``GITEA_TOKEN``. The API address and project come from the ``origin`` remote;
``GITLAB_API_URL`` and ``GITEA_API_URL`` replace the address, and in CI
``CI_API_V4_URL`` with ``CI_PROJECT_PATH`` (GitLab) or ``GITHUB_SERVER_URL``
with ``GITHUB_REPOSITORY`` (Gitea Actions) fill in when the remote does not.
The ``forge`` setting picks one; ``auto`` reads the ``origin`` remote's host and
the CI environment.

Example:
::
    from gitversioned.config import load_config
    from gitversioned.forges import current

    forge = current(load_config())
    if forge.available():
        print(forge.name, forge.find_open("release/next"))
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

from gitversioned import git, github
from gitversioned.errors import EnvironmentProblemError
from gitversioned.github import PullRequest

if TYPE_CHECKING:
    from gitversioned.config import Config

__all__ = ["Forge", "GitHub", "GitLab", "Gitea", "PullRequest", "current", "remote"]

_REMOTE_RE = re.compile(
    r"^(?:(?P<scheme>https?)://(?:[^@/]+@)?|git@|ssh://(?:[^@/]+@)?)"
    r"(?P<host>[^/:]+)(?::\d+)?[/:](?P<path>.+?)(?:\.git)?/?$"
)


def remote(repo: git.Repo | None) -> tuple[str, str, str] | None:
    """
    Read the ``origin`` remote.

    :param repo: The repository.
    :return: The scheme, host and ``owner/name`` path, or ``None``.
    """
    url = repo.git("remote", "get-url", "origin", check=False) if repo else None
    match = _REMOTE_RE.match((url or "").strip())
    if match is None:
        return None
    return match["scheme"] or "https", match["host"], match["path"]


@dataclass
class Forge:
    """
    One forge: pull requests, labels and releases.

    :param root: Project root.
    :param name: ``github``, ``gitlab`` or ``gitea``.
    :param web: Web address of the repository, if known.
    :param pr_path: Path segment of a pull request's address.
    :param cli: What has to be set up, for error messages.
    """

    root: Path
    name: str = "github"
    web: str | None = None
    pr_path: str = "pull"
    cli: str = "the GitHub CLI `gh`, signed in (GH_TOKEN in CI)"
    release_label: str = field(default="release", repr=False)

    def available(self) -> bool:
        """:return: True when the forge can be used."""
        raise NotImplementedError

    def require(self, what: str) -> None:
        """
        Fail when the forge cannot be used.

        :param what: The command that needs it.
        :raises EnvironmentProblemError: If it is not available.
        """
        if not self.available():
            raise EnvironmentProblemError(f"{what} needs {self.cli}.")

    def pull_request(self, number: int) -> PullRequest | None:
        """:return: One pull request, or ``None`` when it cannot be read."""
        raise NotImplementedError

    def find_open(self, head: str) -> PullRequest | None:
        """:return: The open pull request for a head branch, if any."""
        raise NotImplementedError

    def create(
        self, *, head: str, base: str, title: str, body: str, label: str
    ) -> PullRequest:
        """:return: The pull request it opened."""
        raise NotImplementedError

    def update(self, number: int, *, title: str, body: str) -> None:
        """Replace a pull request's title and description."""
        raise NotImplementedError

    def create_release(
        self, *, tag: str, notes: str, prerelease: bool, files: list[Path]
    ) -> str:
        """:return: The address of the release it created for a tag."""
        raise NotImplementedError


class GitHub(Forge):
    """GitHub, through ``gh``."""

    def available(self) -> bool:  # noqa: D102
        return github.available(self.root)

    def pull_request(self, number: int) -> PullRequest | None:  # noqa: D102
        return github.pull_request(self.root, number)

    def find_open(self, head: str) -> PullRequest | None:  # noqa: D102
        return github.find_open_pull_request(self.root, head)

    def create(  # noqa: D102
        self, *, head: str, base: str, title: str, body: str, label: str
    ) -> PullRequest:
        return github.create_pull_request(
            self.root, head=head, base=base, title=title, body=body, label=label
        )

    def update(self, number: int, *, title: str, body: str) -> None:  # noqa: D102
        github.update_pull_request(self.root, number, title=title, body=body)

    def create_release(  # noqa: D102
        self, *, tag: str, notes: str, prerelease: bool, files: list[Path]
    ) -> str:
        return github.create_release(
            self.root, tag=tag, notes=notes, prerelease=prerelease, files=files
        )


@dataclass
class _Rest(Forge):
    """A forge reached over its REST API with a token."""

    api: str = ""
    project: str = ""
    token: str = ""

    def available(self) -> bool:  # noqa: D102
        return bool(self.api and self.project and self.token)

    def _headers(self) -> dict[str, str]:
        raise NotImplementedError

    def call(self, method: str, path: str, data: dict[str, Any] | None = None) -> Any:
        """
        Call the API.

        :param method: HTTP method.
        :param path: Path below the API root.
        :param data: JSON body.
        :return: The decoded JSON answer.
        :raises EnvironmentProblemError: If the call fails.
        """
        url = f"{self.api}{path}"
        if not url.startswith(("https://", "http://")):
            raise EnvironmentProblemError(
                f"{self.name} API address must be http or https: {self.api}"
            )
        body = json.dumps(data).encode() if data is not None else None
        request = urllib.request.Request(  # noqa: S310
            url,
            data=body,
            method=method,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                **self._headers(),
            },
        )
        logger.debug(f"{self.name} {method} {path}")
        try:
            # The scheme is checked above, so file:// and the like never reach here.
            # nosemgrep: dynamic-urllib-use-detected  # noqa: ERA001
            with urllib.request.urlopen(request, timeout=30) as answer:  # noqa: S310
                text = answer.read().decode()
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")[:200]
            raise EnvironmentProblemError(
                f"{self.name} {method} {path} failed: {error.code} {detail}"
            ) from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise EnvironmentProblemError(
                f"{self.name} API at {self.api} is unreachable: {error}"
            ) from error
        return json.loads(text) if text.strip() else None


@dataclass
class GitLab(_Rest):
    """GitLab, through its REST API (v4)."""

    def _headers(self) -> dict[str, str]:
        return {"PRIVATE-TOKEN": self.token}

    def _base(self) -> str:
        return f"/projects/{urllib.parse.quote(self.project, safe='')}"

    @staticmethod
    def _to_pr(data: dict[str, Any]) -> PullRequest:
        return PullRequest(
            number=int(data["iid"]),
            title=data.get("title", ""),
            body=data.get("description") or "",
            labels=tuple(data.get("labels") or ()),
            url=data.get("web_url", ""),
        )

    def pull_request(self, number: int) -> PullRequest | None:  # noqa: D102
        try:
            return self._to_pr(
                self.call("GET", f"{self._base()}/merge_requests/{number}")
            )
        except EnvironmentProblemError:
            return None

    def find_open(self, head: str) -> PullRequest | None:  # noqa: D102
        query = urllib.parse.urlencode({"state": "opened", "source_branch": head})
        items = self.call("GET", f"{self._base()}/merge_requests?{query}") or []
        return self._to_pr(items[0]) if items else None

    def create(  # noqa: D102
        self, *, head: str, base: str, title: str, body: str, label: str
    ) -> PullRequest:
        data = {
            "source_branch": head,
            "target_branch": base,
            "title": title,
            "description": body,
            "labels": label,
            "remove_source_branch": True,
        }
        return self._to_pr(self.call("POST", f"{self._base()}/merge_requests", data))

    def update(self, number: int, *, title: str, body: str) -> None:  # noqa: D102
        self.call(
            "PUT",
            f"{self._base()}/merge_requests/{number}",
            {"title": title, "description": body},
        )

    def create_release(  # noqa: D102
        self, *, tag: str, notes: str, prerelease: bool, files: list[Path]
    ) -> str:
        del prerelease  # GitLab infers it from the tag.
        if files:
            logger.warning("release files are attached on GitHub only; skipped")
        data = {"tag_name": tag, "name": tag, "description": notes}
        answer = self.call("POST", f"{self._base()}/releases", data) or {}
        links = answer.get("_links", {})
        return links.get("self", "") or f"{self.web}/-/releases/{tag}"


@dataclass
class Gitea(_Rest):
    """Gitea and Forgejo, through their REST API (v1)."""

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"token {self.token}"}

    def _base(self) -> str:
        return f"/repos/{self.project}"

    @staticmethod
    def _to_pr(data: dict[str, Any]) -> PullRequest:
        return PullRequest(
            number=int(data["number"]),
            title=data.get("title", ""),
            body=data.get("body") or "",
            labels=tuple(label["name"] for label in data.get("labels") or ()),
            url=data.get("html_url", ""),
        )

    def pull_request(self, number: int) -> PullRequest | None:  # noqa: D102
        try:
            return self._to_pr(self.call("GET", f"{self._base()}/pulls/{number}"))
        except EnvironmentProblemError:
            return None

    def find_open(self, head: str) -> PullRequest | None:  # noqa: D102
        items = self.call("GET", f"{self._base()}/pulls?state=open&limit=50") or []
        for item in items:
            if (item.get("head") or {}).get("ref") == head:
                return self._to_pr(item)
        return None

    def _label_id(self, name: str) -> int:
        for label in self.call("GET", f"{self._base()}/labels?limit=50") or []:
            if label.get("name") == name:
                return int(label["id"])
        made = self.call(
            "POST", f"{self._base()}/labels", {"name": name, "color": "#ededed"}
        )
        return int(made["id"])

    def create(  # noqa: D102
        self, *, head: str, base: str, title: str, body: str, label: str
    ) -> PullRequest:
        data = {
            "head": head,
            "base": base,
            "title": title,
            "body": body,
            "labels": [self._label_id(label)],
        }
        return self._to_pr(self.call("POST", f"{self._base()}/pulls", data))

    def update(self, number: int, *, title: str, body: str) -> None:  # noqa: D102
        self.call(
            "PATCH", f"{self._base()}/pulls/{number}", {"title": title, "body": body}
        )

    def create_release(  # noqa: D102
        self, *, tag: str, notes: str, prerelease: bool, files: list[Path]
    ) -> str:
        if files:
            logger.warning("release files are attached on GitHub only; skipped")
        data = {"tag_name": tag, "name": tag, "body": notes, "prerelease": prerelease}
        answer = self.call("POST", f"{self._base()}/releases", data) or {}
        return answer.get("html_url", "")


def _kind(config: Config, host: str | None) -> str:
    """Choose the forge for a repository."""
    if config.forge != "auto":
        return config.forge
    if os.environ.get("GITLAB_CI") or (host and "gitlab" in host):
        return "gitlab"
    if os.environ.get("GITEA_ACTIONS") or os.environ.get("FORGEJO_ACTIONS"):
        return "gitea"
    if host and any(word in host for word in ("gitea", "forgejo", "codeberg")):
        return "gitea"
    return "github"


def current(config: Config) -> Forge:
    """
    Build the forge for a repository.

    :param config: The loaded configuration.
    :return: The forge, which may not be available.
    """
    repo = git.Repo.open(config.root)
    found = remote(repo)
    scheme, host, path = found if found else ("https", None, "")
    web = f"https://{host}/{path}" if host else None
    kind = _kind(config, host)
    if kind == "gitlab":
        api = (
            os.environ.get("GITLAB_API_URL")
            or os.environ.get("CI_API_V4_URL")
            or (f"{scheme}://{host}/api/v4" if host else "")
        )
        path = path or os.environ.get("CI_PROJECT_PATH", "")
        return GitLab(
            root=config.root,
            name="gitlab",
            web=web,
            pr_path="-/merge_requests",
            cli="GITLAB_TOKEN, a token with the api scope",
            api=api.rstrip("/"),
            project=path,
            token=os.environ.get("GITLAB_TOKEN", ""),
        )
    if kind == "gitea":
        server = os.environ.get("GITHUB_SERVER_URL", "") if not host else ""
        api = os.environ.get("GITEA_API_URL") or (
            f"{scheme}://{host}/api/v1"
            if host
            else (f"{server.rstrip('/')}/api/v1" if server else "")
        )
        path = path or os.environ.get("GITHUB_REPOSITORY", "")
        return Gitea(
            root=config.root,
            name="gitea",
            web=web,
            pr_path="pulls",
            cli="GITEA_TOKEN, a token with repository access",
            api=api.rstrip("/"),
            project=path,
            token=os.environ.get("GITEA_TOKEN", ""),
        )
    return GitHub(
        root=config.root,
        name="github",
        web=github.repo_url(repo) if repo else None,
    )
