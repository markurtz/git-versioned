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

"""Story tests for the defects found in the 0.4.0 peer review, grouped by story."""

from __future__ import annotations

import json
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest
from packaging.version import Version as Pep440

from tests.conftest import RepoBuilder
from tests.e2e.test_check_release_stories import gh, no_gh, remote  # noqa: F401

WORKSPACE = """[workspace]
resolver = "2"
members = ["crates/core", "crates/cli"]

[workspace.package]
version = "0.1.0"
edition = "2021"

[workspace.dependencies]
demo-core = { path = "crates/core", version = "0.1.0" }
"""

CORE = """[package]
name = "demo-core"
version.workspace = true
edition.workspace = true
"""

CLI = """[package]
name = "demo-cli"
version.workspace = true
edition.workspace = true

[dependencies]
demo-core = { path = "../core", version = "^0.1.0" }

[dependencies.demo-extra]
path = "../core"
version = "0.1.0"
"""

HATCH = """[build-system]
requires = ["hatchling", "gitversioned>=0.4"]
build-backend = "hatchling.build"

[project]
name = "{name}"
dynamic = ["version"]

[tool.hatch.version]
source = "gitversioned"

[tool.hatch.build.hooks.gitversioned]
"""


def _build(folder: Path, out: Path, *kinds: str) -> list[Path]:
    subprocess.run(
        [sys.executable, "-m", "build", *kinds, "--no-isolation", "--outdir", str(out)],
        cwd=folder,
        check=True,
        capture_output=True,
    )
    return sorted(out.iterdir())


class TestS3BuildsAfterPreRelease:
    """S3 and S11: dev and nightly builds past a release candidate sort above it."""

    @pytest.mark.regression
    @pytest.mark.parametrize("build_type", ["dev", "nightly"])
    def test_sorts_above_candidate(self, repo: RepoBuilder, build_type: str) -> None:
        """A build after v1.3.0-rc.1 is based on rc2, not on 1.3.0."""
        repo.tag("v1.3.0-rc.1")
        repo.commit("fix: after the candidate")
        result = repo.run("version", "--type", build_type)
        version = result.first
        assert version.startswith("1.3.0rc2.dev")
        assert Pep440(version) > Pep440("1.3.0rc1")
        semver = repo.run("version", "--type", build_type, "--standard", "semver")
        assert semver.first.startswith("1.3.0-rc.2.")


class TestS5WorkspaceCrates:
    """S5: crates that inherit the workspace version keep their pins in step."""

    @pytest.mark.regression
    def test_path_requirements_follow_the_release(self, repo: RepoBuilder) -> None:
        """Path dependency requirements in inheriting crates are stamped too."""
        repo.commit(
            "feat: workspace",
            {
                "Cargo.toml": WORKSPACE,
                "crates/core/Cargo.toml": CORE,
                "crates/cli/Cargo.toml": CLI,
            },
        )
        repo.tag("v0.1.0")
        repo.commit("feat(core): more")
        result = repo.run("release", "--write")
        assert result.code == 0, result.err
        cli = repo.read("crates/cli/Cargo.toml")
        assert 'version = "^0.1.1"' in cli
        assert 'version = "0.1.1"' in cli
        assert "version.workspace = true" in cli
        assert 'version = "0.1.1"' in repo.read("Cargo.toml")

    @pytest.mark.regression
    def test_requirements_drop_build_metadata(self, repo: RepoBuilder) -> None:
        """A dev stamp gives requirements no ``+hash``, which Cargo would ignore."""
        repo.commit("feat: workspace", {"Cargo.toml": WORKSPACE})
        repo.tag("v0.1.0")
        repo.commit("fix: more")
        assert repo.run("version", "--write").code == 0
        text = repo.read("Cargo.toml")
        package = text.split("[workspace.package]")[1].split("\n")[1]
        dependency = next(line for line in text.splitlines() if "demo-core" in line)
        assert "+" in package
        assert "+" not in dependency


class TestS1PackageBuilds:
    """S1 and S13: a Python package below the project root builds on its own."""

    @pytest.mark.regression
    def test_extra_package_wheel(self, repo: RepoBuilder, tmp_path: Path) -> None:
        """The wheel ships its version.py, follows its own tag, writes nothing else."""
        repo.commit(
            "feat: two packages",
            {
                "pyproject.toml": HATCH.format(name="acme"),
                "src/acme/__init__.py": "",
                "packages/extra/pyproject.toml": HATCH.format(name="extra"),
                "packages/extra/src/extra/__init__.py": "",
                "gitversioned.toml": (
                    '[packages.extra]\npath = "packages/extra"\n'
                    'tag = "extra-v{version}"\n'
                ),
                ".gitignore": "version.py\n",
            },
        )
        repo.tag("v2.0.0")
        repo.tag("extra-v0.3.0")
        (wheel,) = _build(
            repo.path / "packages" / "extra", tmp_path / "dist", "--wheel"
        )
        assert wheel.name.startswith("extra-0.3.0-")
        with zipfile.ZipFile(wheel) as archive:
            assert '"0.3.0"' in archive.read("extra/version.py").decode()
        assert not (repo.path / "src" / "acme" / "version.py").exists()

    @pytest.mark.regression
    def test_sdist_inside_another_repository(
        self, repo: RepoBuilder, tmp_path: Path
    ) -> None:
        """An sdist unpacked in an unrelated checkout keeps its own version."""
        repo.commit(
            "feat: project",
            {
                "pyproject.toml": HATCH.format(name="acme"),
                "src/acme/__init__.py": "",
                ".gitignore": "version.py\ndist/\n",
            },
        )
        repo.tag("v2.0.0")
        (sdist,) = _build(repo.path, tmp_path / "sdist", "--sdist")
        outer = RepoBuilder(tmp_path / "outer")
        outer.commit("feat: unrelated", {"README.md": "x\n"})
        outer.tag("v9.9.9")
        with tarfile.open(sdist) as archive:
            archive.extractall(outer.path, filter="data")
        unpacked = outer.path / "acme-2.0.0"
        result = subprocess.run(
            [sys.executable, "-m", "gitversioned", "version", "-C", str(unpacked)],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == "2.0.0"
        (wheel,) = _build(unpacked, tmp_path / "wheel", "--wheel")
        with zipfile.ZipFile(wheel) as archive:
            assert '"2.0.0"' in archive.read("acme/version.py").decode()


@pytest.mark.usefixtures("remote", "gh")
class TestS8ReleasePrGuards:
    """S8 and S10: the release pull request is only cut from the release branch."""

    @pytest.mark.regression
    def test_refuses_other_branches(self, repo: RepoBuilder) -> None:
        """Running on a feature branch would release its unmerged commits."""
        repo.tag("v1.0.0")
        repo.git("checkout", "-q", "-b", "topic")
        repo.commit("feat: unmerged work")
        result = repo.run("release", "--pr")
        assert result.code == 1
        assert "runs on 'main'" in result.err

    @pytest.mark.regression
    def test_waits_for_the_tag(self, repo: RepoBuilder) -> None:
        """A merged but untagged release commit does not reopen the release."""
        repo.tag("v1.0.0")
        repo.commit("feat: new thing (#3)")
        repo.commit("release: v1.1.0 (#4)")
        result = repo.run("release", "--pr")
        assert result.code == 1
        assert "not tagged yet" in result.err
        assert repo.run("release", "--tag").first.startswith("tag       v1.1.0")

    @pytest.mark.regression
    def test_git_failure_is_reported(self, repo: RepoBuilder) -> None:
        """A rejected push is an environment error, and main is left clean."""
        repo.tag("v1.0.0")
        repo.commit("feat: new thing", {"package.json": '{"version": "1.0.0"}\n'})
        repo.git("remote", "set-url", "origin", str(repo.path / "missing.git"))
        result = repo.run("release", "--pr")
        assert result.code == 3
        assert "git push" in result.err
        assert repo.git("status", "--porcelain") == ""
        assert repo.git("branch", "--show-current") == "main"


@pytest.mark.usefixtures("no_gh")
class TestS13PackagesWithoutTags:
    """S13: a package without its own tag is released with the repository."""

    @pytest.mark.regression
    def test_release_needs_own_tag(self, repo: RepoBuilder) -> None:
        """``release -p`` refuses a package that follows the repository version."""
        repo.commit(
            "feat: package",
            {"gitversioned.toml": '[packages.web]\npath = "packages/web"\n'},
        )
        result = repo.run("release", "-p", "web")
        assert result.code == 2
        assert "no `tag` of its own" in result.err


@pytest.mark.usefixtures("no_gh")
class TestS7HookAndEnvironment:
    """S7 and S14: hooks skip git's own messages; stale variables only warn."""

    @pytest.mark.regression
    @pytest.mark.parametrize(
        "subject", ["Merge branch 'topic'", 'Revert "feat: x"', "fixup! feat: x"]
    )
    def test_hook_skips_generated_subjects(
        self, repo: RepoBuilder, subject: str
    ) -> None:
        """Messages git writes itself are not Conventional Commit titles."""
        repo.write("MSG", f"{subject}\n\n# comment\n")
        result = repo.run("check", "--file", str(repo.path / "MSG"))
        assert result.code == 0

    @pytest.mark.regression
    def test_unknown_environment_override_warns(self, repo: RepoBuilder) -> None:
        """A variable from an older release does not stop the command."""
        result = repo.run("version", env={"GITVERSIONED__DIRTY_IGNORE": '["x"]'})
        assert result.code == 0
        assert result.first

    @pytest.mark.sanity
    def test_json_has_next(self, repo: RepoBuilder) -> None:
        """``version --json`` carries the next release, or null."""
        repo.tag("v1.0.0")
        assert repo.run("version", "--json").json["next"] is None
        repo.commit("feat: more")
        assert repo.run("version", "--json").json["next"] == "1.1.0"

    @pytest.mark.sanity
    def test_home_label_is_relative(self, repo: RepoBuilder) -> None:
        """The config home is named relative to the project root."""
        repo.commit("chore: config", {"gitversioned.toml": 'scopes = ["core"]\n'})
        assert repo.run("check", "--json").json["findings"][0]["message"] == (
            "gitversioned.toml"
        )
        assert json.loads(repo.run("version", "--json").out)["type"] == "dev"
