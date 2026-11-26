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

"""Story tests for the gaps the runnable examples exposed, grouped by story."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import RepoBuilder
from tests.e2e.test_check_release_stories import no_gh  # noqa: F401

HATCH = """[build-system]
requires = ["hatchling", "gitversioned>=0.4"]
build-backend = "hatchling.build"

[project]
name = "demo"
dynamic = ["version"]

[tool.hatch.version]
source = "gitversioned"

[tool.hatch.build.hooks.gitversioned]

[tool.hatch.build.targets.wheel]
packages = ["src/demo"]
"""

CHANGELOG = """# Changelog

## [Unreleased]

### Deprecated

- `old()` is deprecated.

## [1.0.0] - 2026-01-01

### Added

- First release.
"""


@pytest.mark.sanity
class TestNightlyBuilds:
    """A builder publishes nightlies from the build hook, which takes no flags."""

    def test_type_from_the_environment(self, repo: RepoBuilder) -> None:
        """GITVERSIONED__TYPE picks the build type, as --type does."""
        repo.tag("v1.0.0")
        repo.commit("feat: more")
        result = repo.run("version", env={"GITVERSIONED__TYPE": "nightly"})
        assert result.code == 0
        assert result.first.startswith("1.1.0.dev")
        assert "+" not in result.first

    def test_unknown_type_is_a_usage_error(self, repo: RepoBuilder) -> None:
        """Any other value stops with exit code 2."""
        result = repo.run("version", env={"GITVERSIONED__TYPE": "weekly"})
        assert result.code == 2
        assert "GITVERSIONED__TYPE" in result.err

    def test_hatchling_builds_a_nightly(
        self, repo: RepoBuilder, tmp_path: Path
    ) -> None:
        """The build hook reads the type, so the wheel has no local part."""
        repo.commit(
            "feat: package",
            {
                "pyproject.toml": HATCH,
                "src/demo/__init__.py": "",
                ".gitignore": "src/demo/version.py\n",
            },
        )
        repo.tag("v1.0.0")
        repo.commit("fix: more")
        out = tmp_path / "dist"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "build",
                "--wheel",
                "--no-isolation",
                "--outdir",
                str(out),
            ],
            cwd=repo.path,
            check=True,
            capture_output=True,
            env={**os.environ, "GITVERSIONED__TYPE": "nightly"},
        )
        (wheel,) = out.glob("*.whl")
        assert wheel.name.startswith("demo-1.0.1.dev")
        assert "+" not in wheel.name


@pytest.mark.sanity
class TestTemplateScopes:
    """A template render allows its block names plus a few fixed scopes."""

    def test_file_and_names_mix(self, repo: RepoBuilder) -> None:
        """A `.toml` entry contributes its table names; other entries are names."""
        repo.commit(
            "chore: blocks",
            {
                ".config/blocks.toml": "[python]\nfolder = '.'\n\n[web]\nfolder = 'apps/web'\n",
                ".config/gitversioned.toml": 'scopes = [".config/blocks.toml", "deps"]\n',
            },
        )
        assert repo.run("check", "feat(web): x").code == 0
        assert repo.run("check", "fix(deps): bump").code == 0
        failed = repo.run("check", "feat(frontend): x")
        assert failed.code == 1
        assert "python, web, deps" in failed.out + failed.err


@pytest.mark.sanity
class TestDiscoveryEdges:
    """A polyglot maintainer gets every shipped manifest and nothing else."""

    def test_never_released_manifests_are_left_alone(self, repo: RepoBuilder) -> None:
        """A private Python project and a cargo-fuzz harness keep their versions."""
        repo.commit(
            "chore: apps",
            {
                "apps/api/pyproject.toml": (
                    '[project]\nname = "api"\nversion = "0.0.0"\n'
                    'classifiers = ["Private :: Do Not Upload"]\n'
                ),
                "fuzz/Cargo.toml": (
                    '[package]\nname = "fuzz"\nversion = "0.0.0"\n\n'
                    "[package.metadata]\ncargo-fuzz = true\n"
                ),
                "lib/pyproject.toml": '[project]\nname = "lib"\nversion = "0.0.0"\n',
            },
        )
        repo.tag("v2.0.0")
        result = repo.run("version", "--write")
        assert "lib/pyproject.toml" in result.out
        assert "apps/api" not in result.out
        assert "fuzz" not in result.out

    def test_containerfiles_anywhere(self, repo: RepoBuilder) -> None:
        """A Containerfile and a nested Dockerfile have their label stamped."""
        label = 'LABEL org.opencontainers.image.version="0.0.0"\n'
        repo.commit(
            "chore: images",
            {
                "Containerfile": f"FROM scratch\n{label}",
                "worker/Dockerfile": f"FROM scratch\n{label}",
            },
        )
        repo.tag("v2.0.0")
        repo.run("version", "--write")
        assert '"2.0.0"' in repo.read("Containerfile")
        assert '"2.0.0"' in repo.read("worker/Dockerfile")

    def test_npm_internal_dependencies(self, repo: RepoBuilder) -> None:
        """A dependency on a sibling package follows, keeping its operator."""
        repo.commit(
            "chore: npm",
            {
                "packages/core/package.json": '{\n  "name": "@x/core",\n  "version": "0.0.0"\n}\n',
                "packages/app/package.json": (
                    '{\n  "name": "@x/app",\n  "version": "0.0.0",\n'
                    '  "dependencies": {\n    "@x/core": "^0.0.0",\n'
                    '    "left-pad": "^1.0.0",\n    "@x/ws": "workspace:*"\n  }\n}\n'
                ),
            },
        )
        repo.tag("v2.0.0")
        repo.run("version", "--write")
        app = json.loads(repo.read("packages/app/package.json"))
        assert app["dependencies"] == {
            "@x/core": "^2.0.0",
            "left-pad": "^1.0.0",
            "@x/ws": "workspace:*",
        }

    def test_citation_without_version(self, repo: RepoBuilder) -> None:
        """A citation file that lacks the keys gets them on a release."""
        repo.commit(
            "chore: citation",
            {"CITATION.cff": 'cff-version: 1.2.0\ntitle: "demo"\n'},
        )
        repo.tag("v2.0.0")
        repo.run("version", "--write")
        text = repo.read("CITATION.cff")
        assert 'version: "2.0.0"' in text
        assert "date-released:" in text


@pytest.mark.sanity
class TestUnreleasedSection:
    """A maintainer keeps notes under [Unreleased] until the release."""

    @pytest.mark.usefixtures("no_gh")
    def test_release_takes_over_unreleased(self, repo: RepoBuilder) -> None:
        """The notes join the new section and [Unreleased] is left empty."""
        repo.commit("chore: changelog", {"CHANGELOG.md": CHANGELOG})
        repo.tag("v1.0.0")
        repo.commit("feat: streaming")
        assert repo.run("release", "--write").code == 0
        text = repo.read("CHANGELOG.md")
        unreleased, rest = text.split("## [1.1.0] - ", 1)
        assert unreleased.rstrip().endswith("## [Unreleased]")
        section = rest.split("## [1.0.0]")[0]
        assert "- streaming" in section
        assert "- `old()` is deprecated." in section


@pytest.mark.sanity
class TestCheckTag:
    """A maintainer tagging by hand gets the same checks as release --tag."""

    def test_existing_tag_must_be_at_head(self, repo: RepoBuilder) -> None:
        """A tag that exists on another commit fails."""
        repo.tag("v1.0.0")
        repo.commit("fix: later")
        result = repo.run("check", "--tag", "v1.0.0")
        assert result.code == 1
        assert "not at HEAD" in result.out + result.err
        assert repo.run("check", "--tag", "v1.0.1").code == 0

    @pytest.mark.usefixtures("no_gh")
    def test_changelog_section_is_required(self, repo: RepoBuilder) -> None:
        """With a changelog, the version needs its section, here and in release --tag."""
        repo.commit("chore: changelog", {"CHANGELOG.md": CHANGELOG})
        repo.tag("v1.0.0")
        repo.commit("feat: more")
        result = repo.run("check", "--tag", "v1.1.0")
        assert result.code == 1
        assert "no [1.1.0] section" in result.out + result.err
        assert repo.run("release", "1.1.0", "--tag").code == 1
        assert not repo.git("tag", "-l", "v1.1.0")


@pytest.mark.sanity
class TestReports:
    """Reports say what happened in the words a reader expects."""

    @pytest.mark.usefixtures("no_gh")
    def test_zero_major_shift_is_named(self, repo: RepoBuilder) -> None:
        """Below 1.0.0 the plan says a feature makes a patch release."""
        repo.tag("v0.3.0")
        repo.commit("feat: more")
        result = repo.run("release")
        assert (
            "0.3.1  (minor, a patch below 1.0.0, from commits, from 0.3.0)"
            in result.out
        )

    def test_warn_relabels_failures(self, repo: RepoBuilder) -> None:
        """--warn reports a bad title as a warning and exits 0."""
        result = repo.run("check", "--warn", "Add a thing")
        assert result.code == 0
        assert (result.out + result.err).startswith("warn")

    def test_json_names_prereleases(self, repo: RepoBuilder) -> None:
        """version --json says whether the version is a pre-release."""
        repo.tag("v1.0.0-rc.1")
        assert repo.run("version", "--json").json["prerelease"] is True
        repo.tag("v1.0.0")
        assert repo.run("version", "--json").json["prerelease"] is False

    def test_lookalike_tags_are_named(self, repo: RepoBuilder) -> None:
        """A version-like tag that misses the template is ignored with a warning."""
        repo.tag("1.2.0")
        result = repo.run("version")
        assert "1.2.0" in result.err


@pytest.mark.sanity
class TestReproducibleDates:
    """A packager rebuilding a nightly gets the same version."""

    def test_build_date_honours_source_date_epoch(self, repo: RepoBuilder) -> None:
        """With date = "build", SOURCE_DATE_EPOCH fixes the date."""
        repo.commit(
            "chore: settings", {".config/gitversioned.toml": 'date = "build"\n'}
        )
        repo.tag("v1.0.0")
        repo.commit("fix: more")
        result = repo.run("version", env={"SOURCE_DATE_EPOCH": "1795608000"})
        assert ".dev20261125" in result.first


@pytest.mark.smoke
class TestLibraryLogging:
    """An API user sees no log output unless they ask for it."""

    def test_import_is_silent(self, repo: RepoBuilder) -> None:
        """Resolving through the API writes nothing to standard error."""
        repo.tag("v1.0.0")
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import gitversioned; print(gitversioned.get_version())",
            ],
            cwd=repo.path,
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == "1.0.0"
        assert result.stderr == ""
