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
Validation: the repository setup, titles, commit ranges and tag names.

Each function returns findings instead of raising, so the CLI can print every
problem at once and choose the exit code.

Example:
::
    from gitversioned.checks import check_title
    from gitversioned.config import load_config

    for finding in check_title(load_config(), "added a thing"):
        print(finding.status, finding.message)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from gitversioned import git, github
from gitversioned.commits import parse_subject
from gitversioned.config import Config
from gitversioned.errors import ConfigError
from gitversioned.model import Version
from gitversioned.resolve import match_tag, release_tags
from gitversioned.targets import all_targets

__all__ = [
    "Finding",
    "check_commits",
    "check_repo",
    "check_tag",
    "check_title",
    "worst_exit_code",
]

Status = Literal["ok", "warn", "fail"]


@dataclass(frozen=True)
class Finding:
    """
    One line of a check report.

    :param status: ``ok``, ``warn`` or ``fail``.
    :param area: What was checked.
    :param message: What was found, and the fix when there is one.
    :param exit_code: Exit code this finding asks for when it is a failure.
    """

    status: Status
    area: str
    message: str
    exit_code: int = 1


def worst_exit_code(findings: list[Finding]) -> int:
    """
    :return: The highest exit code among failed findings, or 0.
    """
    return max(
        (item.exit_code for item in findings if item.status == "fail"), default=0
    )


def check_title(config: Config, title: str, area: str = "title") -> list[Finding]:
    """
    Validate a pull request title or commit subject.

    :param config: The loaded configuration.
    :param title: The title to validate.
    :param area: Label for the report line.
    :return: A single ``ok`` finding, or one finding per problem.
    """
    parsed = parse_subject(title)
    if parsed is None:
        return [
            Finding(
                "fail",
                area,
                f"{title!r} is not a Conventional Commit title. Expected "
                f"type(scope): subject. Types: {', '.join(config.types)}.",
            )
        ]
    problems: list[Finding] = []
    if parsed.type not in config.types:
        problems.append(
            Finding(
                "fail",
                area,
                f"unknown type {parsed.type!r}. Types: {', '.join(config.types)}.",
            )
        )
    scopes = config.allowed_scopes()
    if parsed.scope and scopes:
        unknown = [
            scope.strip()
            for scope in parsed.scope.split(",")
            if scope.strip() not in scopes
        ]
        if unknown:
            problems.append(
                Finding(
                    "fail",
                    area,
                    f"unknown scope {unknown[0]!r}. Scopes: {', '.join(scopes)}.",
                )
            )
    return problems or [Finding("ok", area, title)]


def check_commits(config: Config, revision_range: str) -> list[Finding]:
    """
    Validate every commit subject in a git range.

    :param config: The loaded configuration.
    :param revision_range: A range such as ``origin/main..HEAD``.
    :return: One finding per invalid commit, or a single ``ok`` finding.
    """
    repo = git.Repo.open(config.root)
    if repo is None:
        return [Finding("fail", "commits", "not a git repository.", exit_code=3)]
    since, _, ref = revision_range.partition("..")
    if repo.git("rev-parse", "--verify", "-q", since, check=False) is None:
        return [Finding("fail", "commits", f"unknown revision {since!r}.", exit_code=2)]
    commits = repo.commits(since, ref or "HEAD")
    problems: list[Finding] = []
    for commit in commits:
        if commit.subject.startswith(("Merge ", 'Revert "')):
            continue
        found = check_title(config, commit.subject, area=commit.sha[:7])
        problems += [item for item in found if item.status == "fail"]
    return problems or [Finding("ok", "commits", f"{len(commits)} commits")]


def check_tag(
    config: Config, name: str, *, template: str | None = None
) -> list[Finding]:
    """
    Validate a tag name and that it is newer than the last release.

    :param config: The loaded configuration.
    :param name: Tag name to validate.
    :param template: Tag template to use instead of the configured one.
    :return: A single finding.
    """
    pattern = template or config.tag
    version = match_tag(pattern, name)
    if version is None:
        return [
            Finding(
                "fail",
                "tag",
                f"{name!r} is not a release tag. Expected "
                f"{pattern.replace('{version}', 'X.Y.Z')} with an optional "
                "pre-release such as -rc.1.",
            )
        ]
    repo = git.Repo.open(config.root)
    existing: dict[str, Version] = {}
    if repo is not None:
        existing = release_tags(
            pattern, [tag for tag in repo.all_tags() if tag != name]
        )
    if existing:
        latest = max(existing, key=lambda tag: existing[tag].sort_key())
        if version.sort_key() <= existing[latest].sort_key():
            return [
                Finding(
                    "fail",
                    "tag",
                    f"{version.pep440()} is not newer than {latest}.",
                )
            ]
        return [Finding("ok", "tag", f"{version.pep440()}, newer than {latest}")]
    return [Finding("ok", "tag", f"{version.pep440()}, first release")]


def _check_git(config: Config, repo: git.Repo | None) -> Finding:
    """Report whether git history can give a trustworthy version."""
    severity: Status = "fail" if git.is_ci() else "warn"
    if repo is None or repo.head() is None:
        has_other = (
            config.version != "auto"
            or git.read_archive(config.root) is not None
            or git.read_sdist_version(config.root) is not None
        )
        if has_other:
            return Finding(
                "ok",
                "git",
                "no repository; the version comes from a pin, the archive file or "
                "package metadata",
            )
        return Finding(
            severity,
            "git",
            "no git history here and no archive file, so builds use the fallback "
            "version. Set GITVERSIONED__VERSION to pin one.",
            exit_code=3,
        )
    tags = release_tags(config.tag, list(repo.tags_merged()))
    latest = max(tags, key=lambda tag: tags[tag].sort_key()) if tags else None
    if repo.is_shallow() and not tags:
        return Finding(
            severity,
            "git",
            "shallow clone, no tags reachable. Set fetch-depth: 0 on actions/checkout.",
            exit_code=3,
        )
    if repo.is_shallow():
        return Finding(
            "warn",
            "git",
            f"shallow clone; latest reachable tag {latest}. Commit counts may be "
            "short. Set fetch-depth: 0 on actions/checkout.",
        )
    if latest:
        return Finding(
            "ok", "git", f"full history, {len(tags)} release tags, latest {latest}"
        )
    return Finding(
        "warn",
        "git",
        f"no release tags match {config.tag!r}; versions start from the fallback "
        f"{config.fallback}.",
    )


def _check_targets(config: Config) -> list[Finding]:
    """Report the files that will be stamped and the allowed scopes."""
    try:
        targets = all_targets(config)
        scopes = config.allowed_scopes()
    except ConfigError as error:
        return [Finding("fail", "targets", str(error), exit_code=2)]
    root = config.root.resolve()
    names = ", ".join(
        target.path.resolve().relative_to(root).as_posix() for target in targets
    )
    findings = [
        Finding("ok", "targets", names)
        if targets
        else Finding("warn", "targets", "no files to stamp were found.")
    ]
    if scopes:
        findings.append(Finding("ok", "scopes", ", ".join(scopes)))
    return findings


def _check_archive(config: Config, repo: git.Repo) -> Finding:
    """Report whether source tarballs will keep their version."""
    attributes = repo.top / ".gitattributes"
    marked = attributes.is_file() and "export-subst" in attributes.read_text(
        encoding="utf-8", errors="replace"
    )
    if (config.root / git.ARCHIVE_FILE).is_file() and marked:
        return Finding(
            "ok", "archive file", f"{git.ARCHIVE_FILE} and .gitattributes export-subst"
        )
    return Finding(
        "warn",
        "archive file",
        f"{git.ARCHIVE_FILE} is not set up, so source tarballs lose the version. "
        "Run `gitversioned init`.",
    )


def _check_github(config: Config) -> Finding:
    """Report whether the GitHub CLI is usable."""
    if github.available(config.root):
        return Finding("ok", "github", "gh is signed in")
    return Finding(
        "warn",
        "github",
        "gh is missing or not signed in: release --pr and pull request titles in "
        "the changelog are unavailable.",
    )


def check_repo(config: Config) -> list[Finding]:
    """
    Check that the repository can give a trustworthy version.

    :param config: The loaded configuration.
    :return: One finding per area: config, git, targets, archive file, github.
    """
    repo = git.Repo.open(config.root)
    findings = [Finding("ok", "config", config.home), _check_git(config, repo)]
    findings += _check_targets(config)
    if repo is not None and repo.head() is not None:
        findings += [_check_archive(config, repo), _check_github(config)]
    return findings
