"""
End-to-end checks that every example project works as its README says.

Each test copies an example into a fresh git repository, tags it and runs the
real command line against it.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).parent
_GIT_ENV = {
    "GIT_AUTHOR_NAME": "Example",
    "GIT_AUTHOR_EMAIL": "example@example.com",
    "GIT_COMMITTER_NAME": "Example",
    "GIT_COMMITTER_EMAIL": "example@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}


def _env() -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GITVERSIONED__") and key not in ("CI", "GITHUB_ACTIONS")
    }
    return {**env, **_GIT_ENV}


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, env=_env())


def _cli(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "gitversioned", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=_env(),
    )


def _project(tmp_path: Path, name: str, tag: str) -> Path:
    """Copy an example into a new repository and tag its first commit."""
    path = tmp_path / name
    shutil.copytree(EXAMPLES / name, path)
    _git(path, "init", "-q", "-b", "main")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "feat: first version")
    _git(path, "tag", tag)
    return path


def _targets(path: Path) -> dict[str, dict[str, str]]:
    """Run a dry-run stamp and index the planned changes by file."""
    result = _cli(path, "version", "--write", "--dry-run", "--json")
    assert result.returncode == 0, result.stderr
    return {item["path"]: item for item in json.loads(result.stdout)["written"]}


class TestHatchlingExample:
    """The zero-config Hatchling project."""

    @pytest.mark.smoke
    def test_version_and_check(self, tmp_path: Path) -> None:
        """The tag is the version and the setup check passes."""
        path = _project(tmp_path, "hatchling", "v1.2.3")
        assert _cli(path, "version").stdout.strip() == "1.2.3"
        assert "src/demo_hatch/version.py" in _targets(path)
        assert _cli(path, "check", "--warn").returncode == 0

    @pytest.mark.sanity
    def test_build(self, tmp_path: Path) -> None:
        """The wheel is named for the tag and carries the generated module."""
        pytest.importorskip("hatchling")
        pytest.importorskip("build")
        path = _project(tmp_path, "hatchling", "v1.2.3")
        subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--no-isolation"],
            cwd=path,
            check=True,
            capture_output=True,
            env=_env(),
        )
        (wheel,) = (path / "dist").glob("*.whl")
        assert wheel.name.startswith("demo_hatch-1.2.3-")


class TestSetuptoolsExample:
    """The setuptools project with settings in pyproject.toml."""

    @pytest.mark.smoke
    def test_version_and_scopes(self, tmp_path: Path) -> None:
        """Scopes from the settings table are enforced."""
        path = _project(tmp_path, "setuptools", "v2.1.0")
        assert _cli(path, "version").stdout.strip() == "2.1.0"
        assert _cli(path, "check", "feat(core): add a thing").returncode == 0
        assert _cli(path, "check", "feat(nope): add a thing").returncode == 1

    @pytest.mark.sanity
    def test_build(self, tmp_path: Path) -> None:
        """The wheel is named for the tag."""
        pytest.importorskip("setuptools")
        pytest.importorskip("build")
        path = _project(tmp_path, "setuptools", "v2.1.0")
        subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--no-isolation"],
            cwd=path,
            check=True,
            capture_output=True,
            env=_env(),
        )
        (wheel,) = (path / "dist").glob("*.whl")
        assert wheel.name.startswith("demo_setuptools-2.1.0-")


class TestMaturinExample:
    """The Rust extension built through the wrapper backend."""

    @pytest.mark.smoke
    def test_cargo_manifest_is_a_target(self, tmp_path: Path) -> None:
        """Cargo.toml is stamped in SemVer form and the tree stays clean."""
        path = _project(tmp_path, "maturin", "v0.3.0-rc.1")
        assert _cli(path, "version").stdout.strip() == "0.3.0rc1"
        targets = _targets(path)
        assert targets["Cargo.toml"]["new"] == "0.3.0-rc.1"
        assert _cli(path, "version", "--write").returncode == 0
        assert 'version = "0.3.0-rc.1"' in (path / "Cargo.toml").read_text()
        assert _cli(path, "version").stdout.strip() == "0.3.0rc1"


class TestPolyglotExample:
    """Python, Rust, npm, Helm, citation, Dockerfile and a listed target."""

    @pytest.mark.smoke
    def test_every_manifest_is_stamped(self, tmp_path: Path) -> None:
        """One command stamps each file in its own spelling."""
        path = _project(tmp_path, "polyglot", "v1.4.0")
        _git(path, "tag", "web-v0.9.0")
        assert _cli(path, "version", "--write").returncode == 0
        assert 'version = "1.4.0"' in (path / "crates/core/Cargo.toml").read_text()
        cli_manifest = (path / "crates/cli/Cargo.toml").read_text()
        assert 'version = "1.4.0"' in cli_manifest
        assert 'version = "=1.4.0"' in cli_manifest
        assert 'version = "0.0.0"' not in (path / "Cargo.lock").read_text()
        chart = (path / "charts/demo/Chart.yaml").read_text()
        assert "version: 1.4.0" in chart
        assert 'appVersion: "1.4.0"' in chart
        assert "version: 1.4.0" in (path / "CITATION.cff").read_text()
        assert 'image.version="1.4.0"' in (path / "Dockerfile").read_text()
        assert "demo-cli@1.4.0" in (path / "docs/install.md").read_text()
        assert '"1.4.0"' in (path / "src/demo/version.py").read_text()
        web = json.loads((path / "packages/web/package.json").read_text())
        assert web["version"] == "0.0.0"
        assert _cli(path, "version").stdout.strip() == "1.4.0"

    @pytest.mark.sanity
    def test_package_has_its_own_line(self, tmp_path: Path) -> None:
        """The web package follows its own tags and its own commits."""
        path = _project(tmp_path, "polyglot", "v1.4.0")
        _git(path, "tag", "web-v0.9.0")
        (path / "packages/web/index.js").write_text('export const name = "web";\n')
        _git(path, "commit", "-q", "-am", "fix(web): shorter name")
        assert _cli(path, "version", "-p", "web", "--next").stdout.strip() == "0.9.1"
        assert _cli(path, "version", "--next").returncode == 1
        assert _cli(path, "version", "-p", "web", "--write").returncode == 0
        web = json.loads((path / "packages/web/package.json").read_text())
        assert web["version"].startswith("0.9.1-dev.")
