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

"""Integration tests for the build backends and the init command."""

from __future__ import annotations

import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

from gitversioned.plugins import maturin as maturin_backend
from tests.conftest import RepoBuilder

SETUPTOOLS = """[build-system]
requires = ["setuptools>=64", "gitversioned>=0.4"]
build-backend = "setuptools.build_meta"

[project]
name = "acme"
dynamic = ["version"]

[tool.setuptools.packages.find]
where = ["src"]
"""

HATCH = """[build-system]
requires = ["hatchling", "gitversioned>=0.4"]
build-backend = "hatchling.build"

[project]
name = "acme"
dynamic = ["version"]

[tool.hatch.version]
source = "gitversioned"

[tool.hatch.build.hooks.gitversioned]

[tool.hatch.build.targets.wheel]
packages = ["src/acme"]
"""


def _build(repo: RepoBuilder, *kinds: str) -> list[Path]:
    subprocess.run(
        [sys.executable, "-m", "build", *kinds, "--no-isolation", "--outdir", "dist"],
        cwd=repo.path,
        check=True,
        capture_output=True,
    )
    return sorted((repo.path / "dist").iterdir())


class TestSetuptools:
    """Setuptools builds for projects that opt in."""

    @pytest.mark.smoke
    def test_wheel_and_module(self, repo: RepoBuilder) -> None:
        """The wheel carries the tag version and the generated module."""
        repo.commit(
            "feat: project",
            {
                "pyproject.toml": SETUPTOOLS,
                "src/acme/__init__.py": "",
                ".gitignore": "dist/\nbuild/\n*.egg-info/\nsrc/acme/version.py\n",
            },
        )
        repo.tag("v2.1.0")
        (wheel,) = _build(repo, "--wheel")
        assert wheel.name.startswith("acme-2.1.0-")
        with zipfile.ZipFile(wheel) as archive:
            assert '"2.1.0"' in archive.read("acme/version.py").decode()

    @pytest.mark.regression
    def test_not_active_without_opt_in(self, repo: RepoBuilder) -> None:
        """A setuptools project that does not list gitversioned is left alone."""
        repo.commit(
            "feat: project",
            {
                "pyproject.toml": SETUPTOOLS.replace(
                    ', "gitversioned>=0.4"', ""
                ).replace('dynamic = ["version"]', 'version = "9.9.9"'),
                "src/acme/__init__.py": "",
                ".gitignore": "dist/\nbuild/\n*.egg-info/\n",
            },
        )
        repo.tag("v2.1.0")
        (wheel,) = _build(repo, "--wheel")
        assert wheel.name.startswith("acme-9.9.9-")


class TestHatchling:
    """Hatchling builds, including a wheel built from the sdist."""

    @pytest.mark.regression
    def test_sdist_then_wheel_keeps_dev_version(
        self, repo: RepoBuilder, tmp_path: Path
    ) -> None:
        """A wheel built from an unpacked sdist has the sdist's version."""
        repo.commit(
            "feat: project",
            {
                "pyproject.toml": HATCH,
                "src/acme/__init__.py": "",
                ".gitignore": "dist/\nsrc/acme/version.py\n",
            },
        )
        repo.tag("v1.0.0")
        repo.commit("fix: more")
        (sdist,) = _build(repo, "--sdist")
        version = sdist.name[len("acme-") : -len(".tar.gz")]
        assert version.startswith("1.0.1.dev")
        with tarfile.open(sdist) as archive:
            names = archive.getnames()
            archive.extractall(tmp_path / "unpacked", filter="data")
        assert f"acme-{version}/src/acme/version.py" in names
        unpacked = tmp_path / "unpacked" / f"acme-{version}"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "build",
                "--wheel",
                "--no-isolation",
                "--outdir",
                str(tmp_path / "out"),
            ],
            cwd=unpacked,
            check=True,
            capture_output=True,
            env={**__import__("os").environ, "CI": "true"},
        )
        (wheel,) = (tmp_path / "out").iterdir()
        assert wheel.name.split("-")[1] == version


class TestMaturinBackend:
    """The Maturin wrapper stamps Cargo.toml for the build and restores it."""

    @pytest.mark.smoke
    def test_stamped_context(
        self, repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Inside the context the manifest has the version; afterwards it is restored."""
        cargo = '[package]\nname = "acme"\nversion = "0.0.0"\n'
        repo.commit(
            "feat: crate",
            {
                "Cargo.toml": cargo,
                "pyproject.toml": '[build-system]\nrequires = ["maturin", "gitversioned"]\n'
                'build-backend = "gitversioned.plugins.maturin"\n\n[project]\nname = "acme"\ndynamic = ["version"]\n',
                "python/acme/__init__.py": "",
            },
        )
        repo.tag("v3.0.0-rc.2")
        monkeypatch.chdir(repo.path)
        with maturin_backend.stamped() as version:
            assert version == "3.0.0rc2"
            assert 'version = "3.0.0-rc.2"' in repo.read("Cargo.toml")
            assert '"3.0.0rc2"' in repo.read("python/acme/version.py")
        assert repo.read("Cargo.toml") == cargo

    @pytest.mark.sanity
    def test_hooks_delegate(
        self, repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Each PEP 517 hook calls maturin while the version is stamped."""
        repo.commit(
            "feat: crate",
            {"Cargo.toml": '[package]\nname = "acme"\nversion = "0.0.0"\n'},
        )
        repo.tag("v3.0.0")
        monkeypatch.chdir(repo.path)
        seen: list[str] = []

        class Fake:
            def build_wheel(
                self, directory: str, settings: object = None, metadata: object = None
            ) -> str:
                seen.append(repo.read("Cargo.toml"))
                return "acme.whl"

            def get_requires_for_build_wheel(
                self, settings: object = None
            ) -> list[str]:
                return ["maturin"]

        monkeypatch.setattr(maturin_backend, "_maturin", Fake)
        assert maturin_backend.build_wheel("dist") == "acme.whl"
        assert maturin_backend.get_requires_for_build_wheel() == ["maturin"]
        assert 'version = "3.0.0"' in seen[0]
        assert 'version = "0.0.0"' in repo.read("Cargo.toml")


class TestInit:
    """The optional init command."""

    @pytest.mark.smoke
    def test_init_is_idempotent(self, repo: RepoBuilder) -> None:
        """init writes the archive file once and appends, never rewrites."""
        repo.write(".gitattributes", "*.png binary")
        repo.write(
            "pyproject.toml",
            '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n\n[project]\nname = "x"\ndynamic = ["version"]\n',
        )
        first = repo.run("init")
        assert "wrote  .git_archival.txt" in first.out
        assert (
            repo.read(".gitattributes")
            == "*.png binary\n.git_archival.txt  export-subst\n"
        )
        assert repo.read("pyproject.toml").endswith(
            '[tool.hatch.version]\nsource = "gitversioned"\n\n'
            "[tool.hatch.build.hooks.gitversioned]\n"
        )
        assert "$Format:%H$" in repo.read(".git_archival.txt")
        before = {
            name: repo.read(name)
            for name in (".gitattributes", "pyproject.toml", ".git_archival.txt")
        }
        second = repo.run("init")
        assert "already present" in second.out
        assert before == {name: repo.read(name) for name in before}
