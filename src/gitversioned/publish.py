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
Publishing a tagged release to package registries, and API checks before one.

``release --publish`` builds and uploads what the ``publish`` setting names:
``pypi`` (``uv build`` and ``uv publish``, or ``python -m build`` and
``twine upload`` without uv),
``crates`` (``cargo publish --workspace --locked``) and ``npm`` (``npm publish``,
with ``--tag next`` for pre-releases). Unset, the registries follow the
manifests at the project or package root. Each tool reads its own credentials:
``UV_PUBLISH_TOKEN`` or ``TWINE_PASSWORD`` (or trusted publishing in CI),
``CARGO_REGISTRY_TOKEN`` and ``NODE_AUTH_TOKEN``.

``semver_checks = true`` runs ``cargo semver-checks`` against the last release
tag when a plan is made, and a breaking API change raises the release to major.

Example:
::
    from gitversioned.config import load_config
    from gitversioned.publish import registries

    print(registries(load_config()))
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # noqa: S404
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from gitversioned.errors import CheckFailedError, EnvironmentProblemError

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

if TYPE_CHECKING:
    from gitversioned.config import Config

__all__ = ["Published", "publish", "registries", "semver_breaks"]

_PRIVATE = "Private :: Do Not Upload"


@dataclass
class Published:
    """
    What a publish ran.

    :param commands: Each command, as it would be typed.
    :param files: Built files worth attaching to the forge release.
    :param dry_run: True when the registries were not changed.
    """

    commands: list[str] = field(default_factory=list)
    files: list[Path] = field(default_factory=list)
    dry_run: bool = False


def _folder(config: Config, package: str | None) -> Path:
    """The folder a release of the repository or a package publishes from."""
    if package is None:
        return config.root
    return config.root / config.packages[package].path


def _python_public(folder: Path) -> bool:
    """True when the folder holds a Python project meant for PyPI."""
    path = folder / "pyproject.toml"
    if not path.is_file():
        return False
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return False
    project = data.get("project")
    return isinstance(project, dict) and _PRIVATE not in project.get("classifiers", [])


def _npm_manifest(folder: Path) -> dict[str, object] | None:
    """Read ``package.json``, or ``None``."""
    path = folder / "package.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def registries(config: Config, package: str | None = None) -> list[str]:
    """
    Name the registries a release publishes to.

    :param config: The loaded configuration.
    :param package: Package being released, or ``None``.
    :return: ``pypi``, ``crates`` and ``npm``, in that order, as configured or
        as the manifests at the release's folder suggest.
    """
    if config.publish is not None:
        return list(config.publish)
    folder = _folder(config, package)
    found: list[str] = []
    if _python_public(folder):
        found.append("pypi")
    if (folder / "Cargo.toml").is_file():
        found.append("crates")
    manifest = _npm_manifest(folder)
    if manifest is not None and (
        not manifest.get("private") or manifest.get("workspaces")
    ):
        found.append("npm")
    return found


def _run(
    command: list[str], cwd: Path, *, what: str
) -> subprocess.CompletedProcess[str]:
    """Run one tool, failing with its output when it fails."""
    tool = shutil.which(command[0])
    if tool is None:
        raise EnvironmentProblemError(f"{what} needs `{command[0]}` on PATH.")
    logger.info("running {}", " ".join(command))
    result = subprocess.run(  # noqa: S603
        [tool, *command[1:]],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()[-5:]
        raise CheckFailedError(
            f"`{' '.join(command)}` failed ({result.returncode}): " + " ".join(detail)
        )
    return result


def _pypi(folder: Path, dry_run: bool) -> tuple[list[list[str]], list[Path]]:
    """Build the sdist and wheel, then upload them."""
    dist = folder / "dist"
    shutil.rmtree(dist, ignore_errors=True)
    uv = shutil.which("uv") is not None
    build = (
        ["uv", "build", "--out-dir", "dist"]
        if uv
        else [sys.executable, "-m", "build", "--outdir", "dist"]
    )
    commands = [build]
    _run(build, folder, what="publishing to PyPI")
    files = sorted(
        path
        for pattern in ("*.whl", "*.tar.gz", "*.zip")
        for path in (dist.glob(pattern) if dist.is_dir() else [])
    )
    names = [path.relative_to(folder).as_posix() for path in files]
    if uv:
        upload = ["uv", "publish", *(["--dry-run"] if dry_run else []), *names]
    elif dry_run:
        upload = [sys.executable, "-m", "twine", "check", *names]
    else:
        upload = [sys.executable, "-m", "twine", "upload", *names]
    commands.append(upload)
    _run(upload, folder, what="publishing to PyPI")
    return commands, files


def _crates(folder: Path, dry_run: bool) -> list[list[str]]:
    """Publish every crate of the workspace in dependency order."""
    command = ["cargo", "publish", "--workspace", "--locked"]
    command += ["--dry-run"] if dry_run else []
    _run(command, folder, what="publishing to crates.io")
    return [command]


def _npm(folder: Path, dry_run: bool, prerelease: bool) -> list[list[str]]:
    """Publish the package, or the workspace packages, to npm."""
    manifest = _npm_manifest(folder) or {}
    command = ["npm", "publish"]
    if manifest.get("workspaces"):
        command += ["--workspaces"]
        if not manifest.get("private"):
            command += ["--include-workspace-root"]
    command += ["--tag", "next"] if prerelease else []
    command += ["--dry-run"] if dry_run else []
    _run(command, folder, what="publishing to npm")
    return [command]


def publish(
    config: Config,
    *,
    package: str | None = None,
    prerelease: bool = False,
    dry_run: bool = False,
) -> Published:
    """
    Build and upload a release to its registries.

    :param config: The loaded configuration.
    :param package: Package being released, or ``None``.
    :param prerelease: The release is a pre-release (npm gets ``--tag next``).
    :param dry_run: Run each tool's dry run instead of uploading.
    :return: What ran and the built files.
    :raises EnvironmentProblemError: If a tool is missing.
    :raises CheckFailedError: If a tool fails or there is nothing to publish.
    """
    folder = _folder(config, package)
    chosen = registries(config, package)
    if not chosen:
        raise CheckFailedError(
            "nothing to publish: no public pyproject.toml, Cargo.toml or "
            'package.json here. Set publish = ["pypi"] (or crates, npm) to choose.'
        )
    done = Published(dry_run=dry_run)
    # PyPI goes last: its dist/ folder would otherwise be packed into the crate
    # and the npm tarball.
    for name in sorted(chosen, key=("crates", "npm", "pypi").index):
        if name == "pypi":
            commands, files = _pypi(folder, dry_run)
            done.files += files
        elif name == "crates":
            commands = _crates(folder, dry_run)
        else:
            commands = _npm(folder, dry_run, prerelease)
        done.commands += [
            " ".join("python" if part == sys.executable else part for part in command)
            for command in commands
        ]
    return done


def semver_breaks(config: Config, baseline: str) -> bool:
    """
    Run ``cargo semver-checks`` against a release tag.

    :param config: The loaded configuration.
    :param baseline: Tag of the release to compare with.
    :return: True when the public API changed in a breaking way.
    :raises EnvironmentProblemError: If ``cargo semver-checks`` is not
        installed.
    """
    if not (config.root / "Cargo.toml").is_file():
        return False
    cargo = shutil.which("cargo")
    if cargo is None:
        raise EnvironmentProblemError("semver_checks needs `cargo` on PATH.")
    command = [cargo, "semver-checks", "--workspace", "--baseline-rev", baseline]
    logger.info("running cargo semver-checks --baseline-rev {}", baseline)
    result = subprocess.run(  # noqa: S603
        command,
        cwd=config.root,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "CARGO_TERM_COLOR": "never"},
    )
    output = result.stdout + result.stderr
    if result.returncode != 0 and "no such command" in output:
        raise EnvironmentProblemError(
            "semver_checks needs cargo-semver-checks: "
            "cargo install cargo-semver-checks --locked."
        )
    if result.returncode == 0:
        return False
    if "major" in output.lower():
        return True
    detail = " ".join(output.strip().splitlines()[-3:])
    raise CheckFailedError(f"cargo semver-checks failed: {detail}")
