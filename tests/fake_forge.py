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
A stand-in for the GitLab (v4) and Gitea (v1) REST APIs, served on localhost.

It answers the merge request, pull request, label and release calls
gitversioned makes, keeps them in memory, and records every call. Run it as a
script to serve until stopped, writing its address to a file::

    python -m tests.fake_forge gitlab address.txt state.json
"""

from __future__ import annotations

import json
import re
import sys
import threading
import urllib.parse
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

__all__ = ["TOKEN", "FakeForge", "main"]

TOKEN = "test-token"  # noqa: S105


@dataclass
class FakeForge:
    """
    One fake forge server.

    :param kind: ``gitlab`` or ``gitea``.
    :param pulls: Merge or pull requests by number.
    :param releases: Releases by tag.
    :param labels: Gitea labels by name, with their ids.
    :param calls: ``METHOD path`` of every call.
    :param state: File the state is written to after each call, if any.
    """

    kind: str
    pulls: dict[int, dict[str, Any]] = field(default_factory=dict)
    releases: dict[str, dict[str, Any]] = field(default_factory=dict)
    labels: dict[str, int] = field(default_factory=dict)
    calls: list[str] = field(default_factory=list)
    state: Path | None = None
    server: ThreadingHTTPServer | None = None

    @property
    def url(self) -> str:
        """:return: The API root, such as ``http://127.0.0.1:PORT/api/v4``."""
        assert self.server is not None
        host, port = self.server.server_address[:2]
        suffix = "/api/v4" if self.kind == "gitlab" else "/api/v1"
        return f"http://{host}:{port}{suffix}"

    def start(self) -> FakeForge:
        """Serve in a background thread."""
        forge = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args: object) -> None:
                pass

            def _answer(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"null")
                code, data = forge.handle(self.command, self.path, body, self.headers)
                text = json.dumps(data).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(text)))
                self.end_headers()
                self.wfile.write(text)

            do_GET = do_POST = do_PUT = do_PATCH = _answer  # noqa: N815

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def stop(self) -> None:
        """Stop serving."""
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()

    def _save(self) -> None:
        if self.state is not None:
            self.state.write_text(
                json.dumps(
                    {
                        "pulls": self.pulls,
                        "releases": self.releases,
                        "calls": self.calls,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

    def handle(
        self, method: str, path: str, body: Any, headers: Any
    ) -> tuple[int, Any]:
        """Answer one call."""
        self.calls.append(f"{method} {urllib.parse.unquote(path)}")
        token = (
            headers.get("PRIVATE-TOKEN")
            if self.kind == "gitlab"
            else headers.get("Authorization", "").removeprefix("token ")
        )
        if token != TOKEN:
            return 401, {"message": "401 Unauthorized"}
        answer = (
            self._gitlab(method, path, body)
            if self.kind == "gitlab"
            else self._gitea(method, path, body)
        )
        self._save()
        return answer

    def _gitlab(  # noqa: PLR0911
        self, method: str, path: str, body: Any
    ) -> tuple[int, Any]:
        url = urllib.parse.urlsplit(path)
        query = dict(urllib.parse.parse_qsl(url.query))
        match = re.match(
            r"^/api/v4/projects/(?P<project>[^/]+)/(?P<rest>.*)$", url.path
        )
        if match is None:
            return 404, {"message": "404 Not Found"}
        project = urllib.parse.unquote(match["project"])
        rest = match["rest"]
        if rest == "merge_requests" and method == "GET":
            return 200, [
                item
                for item in self.pulls.values()
                if item["state"] == query.get("state")
                and item["source_branch"] == query.get("source_branch")
            ]
        if rest == "merge_requests" and method == "POST":
            number = max([*self.pulls, 56]) + 1
            self.pulls[number] = {
                "iid": number,
                "title": body["title"],
                "description": body["description"],
                "labels": [body["labels"]],
                "source_branch": body["source_branch"],
                "target_branch": body["target_branch"],
                "state": "opened",
                "web_url": f"https://gitlab.example/{project}/-/merge_requests/{number}",
            }
            return 201, self.pulls[number]
        found = re.match(r"^merge_requests/(\d+)$", rest)
        if found and int(found[1]) in self.pulls:
            item = self.pulls[int(found[1])]
            if method == "PUT":
                item.update(body)
            return 200, item
        if rest == "releases" and method == "POST":
            self.releases[body["tag_name"]] = body
            web = f"https://gitlab.example/{project}/-/releases/{body['tag_name']}"
            return 201, {**body, "_links": {"self": web}}
        return 404, {"message": "404 Not Found"}

    def _gitea(  # noqa: PLR0911
        self, method: str, path: str, body: Any
    ) -> tuple[int, Any]:
        url = urllib.parse.urlsplit(path)
        match = re.match(
            r"^/api/v1/repos/(?P<project>[^/]+/[^/]+)/(?P<rest>.*)$", url.path
        )
        if match is None:
            return 404, {"message": "not found"}
        project, rest = match["project"], match["rest"]
        if rest == "pulls" and method == "GET":
            return 200, [
                item for item in self.pulls.values() if item["state"] == "open"
            ]
        if rest == "labels" and method == "GET":
            return 200, [{"id": i, "name": n} for n, i in self.labels.items()]
        if rest == "labels" and method == "POST":
            self.labels[body["name"]] = len(self.labels) + 1
            return 201, {"id": self.labels[body["name"]], "name": body["name"]}
        if rest == "pulls" and method == "POST":
            number = max([*self.pulls, 56]) + 1
            names = {i: n for n, i in self.labels.items()}
            self.pulls[number] = {
                "number": number,
                "title": body["title"],
                "body": body["body"],
                "labels": [{"name": names[i]} for i in body.get("labels", [])],
                "head": {"ref": body["head"]},
                "base": {"ref": body["base"]},
                "state": "open",
                "html_url": f"https://gitea.example/{project}/pulls/{number}",
            }
            return 201, self.pulls[number]
        found = re.match(r"^pulls/(\d+)$", rest)
        if found and int(found[1]) in self.pulls:
            item = self.pulls[int(found[1])]
            if method == "PATCH":
                item.update(body)
            return 200, item
        if rest == "releases" and method == "POST":
            self.releases[body["tag_name"]] = body
            web = f"https://gitea.example/{project}/releases/tag/{body['tag_name']}"
            return 201, {**body, "html_url": web}
        return 404, {"message": "not found"}


def main() -> None:
    """Serve one fake forge until killed; write its API root to a file."""
    kind, address, state = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    forge = FakeForge(kind, state=state).start()
    address.write_text(forge.url, encoding="utf-8")
    assert forge.server is not None
    threading.Event().wait()


if __name__ == "__main__":
    main()
