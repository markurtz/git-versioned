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
The command line: ``version``, ``check``, ``release`` and the optional ``init``.

Every command accepts ``--root``, ``--package``, ``--json``, ``--verbose`` and
``--quiet``. Exit codes are 0 for success, 1 for a failed check or nothing to
release, 2 for bad usage or configuration and 3 for an environment problem.

Example:
::
    gitversioned version --next --explain
    gitversioned check "feat(cli): add explain"
    gitversioned release --pr
"""

from __future__ import annotations

import functools
import json
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

import typer

from gitversioned import git
from gitversioned.checks import (
    Finding,
    check_commits,
    check_repo,
    check_tag,
    check_title,
    worst_exit_code,
)
from gitversioned.commits import env_bump, next_version
from gitversioned.config import Config, load_config
from gitversioned.errors import ConfigError, GitVersionedError
from gitversioned.logging import configure_logging
from gitversioned.model import Version
from gitversioned.release import (
    open_release_pr,
    package_context,
    plan_release,
    tag_release,
    write_release,
)
from gitversioned.resolve import Resolved, resolve
from gitversioned.scaffold import scaffold
from gitversioned.targets import stamp

__all__ = ["app", "main"]

app = typer.Typer(
    name="gitversioned",
    help="Versions from git tags, stamped into every manifest, with checks and releases.",
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
)

RootOpt = Annotated[
    Path | None,
    typer.Option("--root", "-C", help="Run as if started in DIR.", metavar="DIR"),
]
PackageOpt = Annotated[
    str | None,
    typer.Option(
        "--package", "-p", help="Act on one package from [packages].", metavar="NAME"
    ),
]
JsonOpt = Annotated[
    bool, typer.Option("--json", help="Machine-readable output on stdout.")
]
VerboseOpt = Annotated[
    int,
    typer.Option(
        "--verbose", "-v", count=True, help="More detail on stderr (-vv for debug)."
    ),
]
QuietOpt = Annotated[bool, typer.Option("--quiet", "-q", help="Errors only.")]

_LEVELS = ("major", "minor", "patch")
_PRE = ("rc", "beta", "alpha")
_TYPES = ("dev", "nightly", "release")
_STANDARDS = ("pep440", "semver")


def _choice(value: str | None, allowed: tuple[str, ...], flag: str) -> str | None:
    """Validate an option that takes one of a few words."""
    if value is not None and value not in allowed:
        raise ConfigError(f"{flag} must be one of: {', '.join(allowed)}.")
    return value


def _emit(data: dict[str, Any]) -> None:
    """Print a JSON document."""
    typer.echo(json.dumps(data, indent=2))


def _fail(error: GitVersionedError, as_json: bool) -> None:
    """Report an error and exit with its code."""
    if as_json:
        _emit({"ok": False, "error": str(error), "exit_code": error.exit_code})
    else:
        typer.echo(f"fail  {error}", err=True)
    raise typer.Exit(error.exit_code)


def _command(function: Callable[..., None]) -> Callable[..., None]:
    """Give a command logging setup and uniform error handling."""

    @functools.wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        verbosity = -1 if kwargs.get("quiet") else int(kwargs.get("verbose") or 0)
        configure_logging(verbosity)
        try:
            function(*args, **kwargs)
        except GitVersionedError as error:
            _fail(error, bool(kwargs.get("json_output")))

    return wrapper


def _default_standard(config: Config) -> str:
    """Pick PEP 440 for a Python project and SemVer otherwise."""
    pyproject = config.root / "pyproject.toml"
    if pyproject.is_file() and "[project]" in pyproject.read_text(encoding="utf-8"):
        return "pep440"
    return "semver"


def _next(
    config: Config, resolved: Resolved, bump: str | None, pre: str | None
) -> Version:
    """Compute the next release version for the ``version --next`` path."""
    override = bump or env_bump()
    explicit = override if override and override not in _LEVELS else None
    return next_version(
        resolved.base,
        resolved.known,
        resolved.plan,
        fallback=Version.parse(config.fallback),
        explicit=explicit,
        bump=override if explicit is None else None,
        pre=pre,  # type: ignore[arg-type]
    )


def _explain(
    config: Config, resolved: Resolved, upcoming: Version | None, standard: str
) -> list[str]:
    """Build the lines of an ``--explain`` report."""
    lines: list[str] = []
    if upcoming is not None:
        lines.append(f"next      {upcoming.render(standard)}")  # type: ignore[arg-type]
    else:
        lines.append(f"version   {resolved.version.render(standard)}")  # type: ignore[arg-type]
        lines.append(f"type      {resolved.type}")
    if resolved.base is not None:
        where = f"tag {resolved.tag}" if resolved.tag else resolved.source
        sha = f", {resolved.short_sha}" if resolved.short_sha else ""
        lines.append(
            f"current   {resolved.base.render(standard)}  ({where}{sha}, "  # type: ignore[arg-type]
            f"{resolved.distance} commits since)"
        )
    else:
        lines.append(f"current   none ({resolved.source}; fallback {config.fallback})")
    if resolved.plan.reasons:
        counts: dict[str, int] = {}
        for level, _commit in resolved.plan.reasons:
            counts[level or "none"] = counts.get(level or "none", 0) + 1
        summary = ", ".join(f"{count} {name}" for name, count in counts.items())
        lines.append(f"why       {resolved.plan.level or 'no release'}: {summary}")
        for level, commit in resolved.plan.reasons[:20]:
            lines.append(f"  {(level or 'none'):<7} {commit.subject}")
    if resolved.dirty:
        shown = ", ".join(resolved.dirty[:5])
        more = f" and {len(resolved.dirty) - 5} more" if len(resolved.dirty) > 5 else ""
        lines.append(f"dirty     {shown}{more}")
    for note in resolved.notes:
        lines.append(f"note      {note}")
    total = len(Config.key_names())
    used = len(config.keys_set)
    lines.append(f"config    {config.home}  ({used} keys set, {total - used} defaults)")
    return lines


@app.command("version")
@_command
def version_command(
    version: Annotated[
        str | None,
        typer.Argument(
            help="Use this version instead of resolving one.", metavar="[VERSION]"
        ),
    ] = None,
    next_release: Annotated[
        bool, typer.Option("--next", help="The version the next release would get.")
    ] = False,
    bump: Annotated[
        str | None,
        typer.Option(
            "--bump", help="With --next: force major, minor or patch.", metavar="LEVEL"
        ),
    ] = None,
    pre: Annotated[
        str | None,
        typer.Option("--pre", help="With --next: rc, beta or alpha.", metavar="KIND"),
    ] = None,
    build_type: Annotated[
        str | None,
        typer.Option("--type", help="Force dev, nightly or release.", metavar="TYPE"),
    ] = None,
    standard: Annotated[
        str | None,
        typer.Option("--standard", help="Print as pep440 or semver.", metavar="STD"),
    ] = None,
    write: Annotated[
        bool, typer.Option("--write", help="Stamp the version into every target.")
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="With --write: show the diff, change nothing."),
    ] = False,
    explain: Annotated[
        bool, typer.Option("--explain", help="Show how the answer was reached.")
    ] = False,
    root: RootOpt = None,
    package: PackageOpt = None,
    json_output: JsonOpt = False,
    verbose: VerboseOpt = 0,
    quiet: QuietOpt = False,
) -> None:
    """Print the version of this checkout; --next for the upcoming release; --write to stamp files."""
    _choice(bump, _LEVELS, "--bump")
    _choice(pre, _PRE, "--pre")
    _choice(build_type, _TYPES, "--type")
    _choice(standard, _STANDARDS, "--standard")
    if (bump or pre) and not next_release:
        raise ConfigError("--bump and --pre need --next.")
    if dry_run and not write:
        raise ConfigError("--dry-run needs --write.")
    config = load_config(root)
    template, scope = package_context(config, package)
    resolved = resolve(
        config,
        pin=version,
        build_type=build_type,  # type: ignore[arg-type]
        tag_template=template,
        path_scope=scope,
    )
    spelling = standard or _default_standard(config)
    upcoming: Version | None = None
    if next_release:
        upcoming = _next(config, resolved, bump, pre)
        resolved = Resolved(
            version=upcoming,
            type="release",
            source=resolved.source,
            tag=resolved.tag,
            base=resolved.base,
            distance=resolved.distance,
            sha=resolved.sha,
            date=resolved.date,
            dirty=resolved.dirty,
            known=resolved.known,
            plan=resolved.plan,
            notes=resolved.notes,
            warnings=resolved.warnings,
        )
    changes = stamp(config, resolved, dry_run=dry_run, package=package) if write else []
    shown = resolved.version
    if json_output:
        _emit(
            {
                "version": shown.render(spelling),  # type: ignore[arg-type]
                "pep440": shown.pep440(),
                "semver": shown.semver(),
                "type": resolved.type,
                "source": resolved.source,
                "tag": resolved.tag,
                "distance": resolved.distance,
                "sha": resolved.short_sha,
                "dirty": bool(resolved.dirty),
                "warnings": resolved.warnings,
                "written": [
                    {
                        "path": change.path,
                        "old": change.old,
                        "new": change.new,
                        "changed": bool(change.diff),
                    }
                    for change in changes
                ],
            }
        )
        return
    if explain:
        for line in _explain(config, resolved, upcoming, spelling):
            typer.echo(line)
    else:
        typer.echo(shown.render(spelling))  # type: ignore[arg-type]
    if write and dry_run:
        for change in changes:
            if change.diff:
                typer.echo(change.diff, nl=False)
    elif write:
        width = max((len(change.path) for change in changes), default=0)
        for change in changes:
            state = change.new if change.diff else f"{change.new} (unchanged)"
            typer.echo(f"  {change.path:<{width}}  {state}")
        if not changes:
            typer.echo("  no targets found", err=True)


def _report(findings: list[Finding], as_json: bool, warn_only: bool) -> None:
    """Print findings and exit with the right code."""
    code = worst_exit_code(findings)
    if as_json:
        _emit(
            {
                "ok": code == 0,
                "findings": [
                    {"status": item.status, "area": item.area, "message": item.message}
                    for item in findings
                ],
            }
        )
    else:
        simple = (
            len(findings) == 1
            and findings[0].status == "ok"
            and findings[0].area == "title"
        )
        if simple:
            typer.echo("ok")
        else:
            width = max(len(item.area) for item in findings)
            for item in findings:
                typer.echo(
                    f"{item.status:<5} {item.area:<{width}}  {item.message}",
                    err=item.status == "fail",
                )
    if code and not warn_only:
        raise typer.Exit(code)


@app.command("check")
@_command
def check_command(
    title: Annotated[
        str | None,
        typer.Argument(
            help="A pull request title or commit subject to validate.",
            metavar="[TITLE]",
        ),
    ] = None,
    commits: Annotated[
        str | None,
        typer.Option(
            "--commits",
            help="Validate every commit subject in a git range.",
            metavar="RANGE",
        ),
    ] = None,
    tag: Annotated[
        str | None,
        typer.Option("--tag", help="Validate a tag name.", metavar="NAME"),
    ] = None,
    file: Annotated[
        Path | None,
        typer.Option(
            "--file",
            help="Read the message from a file (commit-msg hook).",
            metavar="PATH",
        ),
    ] = None,
    warn: Annotated[
        bool, typer.Option("--warn", help="Report problems but exit 0.")
    ] = False,
    root: RootOpt = None,
    package: PackageOpt = None,
    json_output: JsonOpt = False,
    verbose: VerboseOpt = 0,
    quiet: QuietOpt = False,
) -> None:
    """Validate the repo setup, a pull request title, commits or a tag."""
    if sum(item is not None for item in (title, commits, tag, file)) > 1:
        raise ConfigError("give one of TITLE, --commits, --tag or --file.")
    config = load_config(root)
    if file is not None:
        try:
            lines = file.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            raise ConfigError(f"cannot read {file}: {error}") from error
        title = next(
            (line for line in lines if line.strip() and not line.startswith("#")), ""
        )
    if title is not None:
        findings = check_title(config, title)
    elif commits is not None:
        findings = check_commits(config, commits)
    elif tag is not None:
        template, _scope = package_context(config, package)
        findings = check_tag(config, tag, template=template)
    else:
        findings = check_repo(config)
    _report(findings, json_output, warn)


@app.command("release")
@_command
def release_command(
    version: Annotated[
        str | None,
        typer.Argument(help="Release exactly this version.", metavar="[VERSION]"),
    ] = None,
    bump: Annotated[
        str | None,
        typer.Option(
            "--bump",
            help="Override the level chosen from commits and labels.",
            metavar="LEVEL",
        ),
    ] = None,
    pre: Annotated[
        str | None,
        typer.Option(
            "--pre", help="Make it a pre-release: rc, beta or alpha.", metavar="KIND"
        ),
    ] = None,
    write: Annotated[
        bool,
        typer.Option(
            "--write",
            help="Update the changelog and committed targets in the working tree.",
        ),
    ] = False,
    pr: Annotated[
        bool,
        typer.Option(
            "--pr",
            help="Commit the release to the release branch and open or update the PR.",
        ),
    ] = False,
    tag: Annotated[
        bool, typer.Option("--tag", help="Tag the release commit and push the tag.")
    ] = False,
    root: RootOpt = None,
    package: PackageOpt = None,
    json_output: JsonOpt = False,
    verbose: VerboseOpt = 0,
    quiet: QuietOpt = False,
) -> None:
    """Plan a release; --pr to open the release pull request; --tag to tag it."""
    _choice(bump, _LEVELS, "--bump")
    _choice(pre, _PRE, "--pre")
    if sum((write, pr, tag)) > 1:
        raise ConfigError("give one of --write, --pr or --tag.")
    config = load_config(root)
    if tag:
        if bump or pre:
            raise ConfigError("--tag takes a VERSION, not --bump or --pre.")
        name, sha, pushed = tag_release(config, version=version, package=package)
        if json_output:
            _emit({"stage": "tag", "tag": name, "sha": sha, "pushed": pushed})
        else:
            typer.echo(
                f"tag       {name} at {sha[:7]}, {'pushed' if pushed else 'created locally'}"
            )
        return
    if pr:
        plan, request, opened = open_release_pr(
            config,
            version=version,
            bump=bump,
            pre=pre,
            package=package,  # type: ignore[arg-type]
        )
        if json_output:
            _emit(
                {
                    "stage": "pr",
                    "version": plan.version.pep440(),
                    "tag": plan.tag,
                    "branch": plan.branch,
                    "title": plan.title,
                    "files": plan.files,
                    "pr": {
                        "number": request.number,
                        "url": request.url,
                        "opened": opened,
                    },
                }
            )
        else:
            typer.echo(f"release   {plan.version.pep440()}")
            typer.echo(
                f"branch    {plan.branch}  (rebuilt from {git.Repo.open(config.root).branch() or 'HEAD'})"
            )  # type: ignore[union-attr]
            typer.echo(f"commit    {plan.title}")
            typer.echo(
                f"pr        #{request.number} {'opened' if opened else 'updated'}  {request.url}"
            )
        return
    plan = plan_release(config, version=version, bump=bump, pre=pre, package=package)  # type: ignore[arg-type]
    changed = write_release(config, plan) if write else []
    if json_output:
        _emit(
            {
                "stage": "write" if write else "plan",
                "version": plan.version.pep440(),
                "semver": plan.version.semver(),
                "previous": plan.previous.pep440() if plan.previous else None,
                "tag": plan.tag,
                "level": plan.level,
                "files": plan.files,
                "changed": changed,
                "changelog": plan.section,
            }
        )
        return
    typer.echo(f"release   {plan.version.pep440()}  ({plan.level})")
    typer.echo(f"tag       {plan.tag}")
    typer.echo(f"files     {', '.join(plan.files) or 'none'}")
    typer.echo("")
    typer.echo(plan.section)
    if write:
        typer.echo(f"Wrote {', '.join(changed) or 'nothing (already up to date)'}.")
    else:
        typer.echo("Nothing changed. Run with --write, --pr or --tag.")


@app.command("init")
@_command
def init_command(
    root: RootOpt = None,
    json_output: JsonOpt = False,
    verbose: VerboseOpt = 0,
    quiet: QuietOpt = False,
) -> None:
    """Optional: add the archive file and wire up the build backend."""
    config = load_config(root)
    actions = scaffold(config)
    if json_output:
        _emit(
            {
                "actions": [
                    {"action": action, "path": path, "detail": detail}
                    for action, path, detail in actions
                ]
            }
        )
        return
    for action, path, detail in actions:
        typer.echo(f"{action:<5}  {path:<22}{('  ' + detail) if detail else ''}")
    if not config.keys_set:
        typer.echo(
            "No gitversioned settings needed: defaults and discovery cover this repo."
        )


def main() -> None:
    """Run the command line."""
    app()
