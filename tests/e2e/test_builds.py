from __future__ import annotations

import datetime
import os
import subprocess
import tarfile
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path

import pytest

from tests.integration.conftest import GitRepoHelper


def get_version_function() -> str:
    return "1.4.5"


class BuildTestHelper(ABC):
    @classmethod
    def setup_base_repo(
        cls,
        repo: GitRepoHelper,
        pyproject_content: str,
        package_name: str = "test_pkg",
        package_version: str = "1.2.3",
        source_dirs: list[str] | None = None,
        include_version_txt: bool = False,
        commit: str | None = None,
        tag: str | None = None,
        branch: str | None = None,
        dirty: bool = False,
    ) -> Path:
        # Create pyproject.toml
        pyproject_content = pyproject_content.format(
            PACKAGE=package_name,
            VERSION=package_version,
            ROOT=Path(__file__).resolve().parent.parent.parent,
        )
        (repo.path / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")
        repo.add("pyproject.toml")

        # Create package directory structure
        if source_dirs is None:
            source_dirs = ["src", "{PACKAGE}"]
        package_path: Path = repo.path
        for src_dir in source_dirs:
            package_path = package_path / src_dir.format(PACKAGE=package_name)
        package_path.mkdir(parents=True, exist_ok=True)

        # Create .gitignore
        (repo.path / ".gitignore").write_text("dist/*\n")
        repo.add(".gitignore")

        # Create package source files
        (package_path / "__init__.py").write_text("from .version import __version__\n")
        repo.add(str(package_path / "__init__.py"))

        if include_version_txt:
            (package_path / "version.txt").write_text(f"version={package_version}")
            repo.add(str(package_path / "version.txt"))

        # Setup git repo
        repo.commit("Initial commit")
        if branch:
            repo.branch(branch.format(PACKAGE=package_name, VERSION=package_version))
        if commit:
            (package_path / "extra.py").write_text("extra=True")
            repo.add(str(package_path / "extra.py"))
            repo.commit(commit.format(PACKAGE=package_name, VERSION=package_version))
        if tag:
            repo.tag(tag.format(PACKAGE=package_name, VERSION=package_version))
        if dirty:
            repo.dirty()

        return package_path

    @classmethod
    def get_version_from_artifacts(
        cls, repo_path: Path, package_name: str = "test_pkg"
    ):
        dist_dir = repo_path / "dist"
        wheels = list(dist_dir.glob("*.whl"))
        sdists = list(dist_dir.glob("*.tar.gz"))

        assert len(wheels) == 1, f"Expected 1 wheel, found {len(wheels)}"
        assert len(sdists) == 1, f"Expected 1 sdist, found {len(sdists)}"

        wheel_name = wheels[0].name
        sdist_name = sdists[0].name

        # Filename example: test_pkg-1.2.3-py2.py3-none-any.whl
        wheel_version = wheel_name.split("-")[1]
        assert wheel_version in sdist_name, (
            f"Version mismatch: wheel={wheel_version}, sdist={sdist_name}"
        )

        with zipfile.ZipFile(wheels[0]) as zf:
            version_file = f"{package_name}/version.py"
            assert version_file in zf.namelist(), f"Expected {version_file} in wheel"
            content = zf.read(version_file).decode("utf-8")
            assert wheel_version in content, (
                f"Expected {wheel_version} in wheel {version_file}"
            )

        with tarfile.open(sdists[0]) as tf:
            sdist_pkg_dir = sdist_name.replace(".tar.gz", "")
            version_file = f"{sdist_pkg_dir}/src/{package_name}/version.py"
            names = tf.getnames()
            if version_file not in names:
                version_file = f"{sdist_pkg_dir}/{package_name}/version.py"
            assert version_file in names, f"Expected {version_file} in sdist"
            f = tf.extractfile(version_file)
            assert f is not None
            content = f.read().decode("utf-8")
            assert wheel_version in content, (
                f"Expected {wheel_version} in sdist {version_file}"
            )

        return wheel_version

    @pytest.mark.smoke
    def test_smoke_build(self, e2e_git_repo: GitRepoHelper) -> None:
        """Smoke test for building a wheel with hatchling."""
        pyproject_content = self.pyproject_content()
        self.setup_base_repo(
            e2e_git_repo, pyproject_content=pyproject_content, tag="{VERSION}"
        )
        self.run_build(e2e_git_repo)
        version = self.get_version_from_artifacts(e2e_git_repo.path)
        assert version == "1.2.3"

    @pytest.mark.sanity
    def test_version_source_file(self, e2e_git_repo: GitRepoHelper) -> None:
        pyproject_content = self.pyproject_content() + 'source_type = "file"'
        self.setup_base_repo(
            e2e_git_repo,
            pyproject_content=pyproject_content,
            package_version="4.5.6",
            include_version_txt=True,
        )
        self.run_build(e2e_git_repo)
        version = self.get_version_from_artifacts(e2e_git_repo.path)
        assert version == "4.5.6"

    @pytest.mark.sanity
    def test_version_source_tag(self, e2e_git_repo: GitRepoHelper) -> None:
        pyproject_content = self.pyproject_content() + 'source_type = "tag"'
        self.setup_base_repo(
            e2e_git_repo,
            pyproject_content=pyproject_content,
            tag="v7.8.9",
        )
        self.run_build(e2e_git_repo)
        version = self.get_version_from_artifacts(e2e_git_repo.path)
        assert version == "7.8.9"

    @pytest.mark.sanity
    def test_version_source_branch(self, e2e_git_repo: GitRepoHelper) -> None:
        pyproject_content = self.pyproject_content() + 'source_type = "branch"'
        self.setup_base_repo(
            e2e_git_repo,
            pyproject_content=pyproject_content,
            branch="v2.1.0",
        )
        self.run_build(e2e_git_repo)
        version = self.get_version_from_artifacts(e2e_git_repo.path)
        assert version == "2.1.0"

    @pytest.mark.sanity
    def test_version_source_commit(self, e2e_git_repo: GitRepoHelper) -> None:
        pyproject_content = self.pyproject_content() + 'source_type = "commit"'
        self.setup_base_repo(
            e2e_git_repo,
            pyproject_content=pyproject_content,
            commit="Release v3.0.0",
        )
        self.run_build(e2e_git_repo)
        version = self.get_version_from_artifacts(e2e_git_repo.path)
        assert version == "3.0.0"

    @pytest.mark.regression
    def test_config_version(self, e2e_git_repo: GitRepoHelper) -> None:
        pyproject_content = self.pyproject_content() + 'version = "6.6.6"'
        self.setup_base_repo(e2e_git_repo, pyproject_content=pyproject_content)
        self.run_build(e2e_git_repo)
        version = self.get_version_from_artifacts(e2e_git_repo.path)
        assert version == "6.6.6"

    @pytest.mark.regression
    def test_tool_table_config(self, e2e_git_repo: GitRepoHelper) -> None:
        pyproject_content = (
            self.pyproject_content() + "[tool.gitversioned]\n" + 'version = "5.5.5"'
        )
        self.setup_base_repo(e2e_git_repo, pyproject_content=pyproject_content)
        self.run_build(e2e_git_repo)
        version = self.get_version_from_artifacts(e2e_git_repo.path)
        assert version == "5.5.5"

    @pytest.mark.parametrize(
        ("version_type", "expected_suffix", "extra_commit"),
        [
            ("auto", "", False),
            (
                "auto",
                f".dev{datetime.date.today().strftime('%Y%m%d')}+" + "{SHORT_SHA}",
                True,
            ),
            ("release", "", True),
            ("release", "", False),
            (
                "dev",
                f".dev{datetime.date.today().strftime('%Y%m%d')}+" + "{SHORT_SHA}",
                True,
            ),
            (
                "dev",
                f".dev{datetime.date.today().strftime('%Y%m%d')}+" + "{SHORT_SHA}",
                False,
            ),
            ("pre", f"a{datetime.date.today().strftime('%Y%m%d')}", True),
            ("alpha", f"a{datetime.date.today().strftime('%Y%m%d')}", True),
            ("nightly", f"a{datetime.date.today().strftime('%Y%m%d')}", True),
            ("post", ".post0", False),
            ("post", ".post1", True),
        ],
    )
    @pytest.mark.regression
    def test_settings_formats_and_types(
        self,
        e2e_git_repo: GitRepoHelper,
        version_type: str,
        expected_suffix: str,
        extra_commit: bool,
    ):
        pyproject_content = (
            self.pyproject_content() + f'version_type = "{version_type}"\n'
        )
        package_path = self.setup_base_repo(
            e2e_git_repo,
            pyproject_content=pyproject_content,
            tag="v1.2.3",
            commit="fix: something",
        )
        expected_suffix = expected_suffix.format(SHORT_SHA=e2e_git_repo.short_sha)

        if extra_commit:
            (package_path / "dummy_file.txt").write_text("content")
            e2e_git_repo.add(str(package_path / "dummy_file.txt"))
            e2e_git_repo.commit("add dummy_file.txt")

        self.run_build(e2e_git_repo)
        version = self.get_version_from_artifacts(e2e_git_repo.path)
        assert version == f"1.2.3{expected_suffix}"

    @classmethod
    @abstractmethod
    def run_build(cls, repo: GitRepoHelper):
        pass

    @classmethod
    @abstractmethod
    def pyproject_content(cls) -> str:
        pass


class TestHatchlingBuilds(BuildTestHelper):
    @classmethod
    def run_build(cls, repo: GitRepoHelper):
        env = os.environ.copy()
        # Remove Hatch's tracking variables to avoid "Unknown environment" errors
        env.pop("HATCH_ENV", None)
        env.pop("HATCH_ENV_ACTIVE", None)
        result = subprocess.run(
            ["hatch", "build"],
            cwd=str(repo.path),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        assert result.returncode == 0, f"Build failed: {result.stdout}\n{result.stderr}"

    @classmethod
    def pyproject_content(cls) -> str:
        return """[build-system]
requires = ["hatchling", "gitversioned @ file://{ROOT}"]
build-backend = "hatchling.build"

[project]
name = "{PACKAGE}"
dynamic = ["version"]

[tool.hatch.version]
source = "gitversioned"
"""


class TestSetuptoolsBuilds(BuildTestHelper):
    @classmethod
    def run_build(cls, repo: GitRepoHelper):
        env = os.environ.copy()
        # Remove Hatch's tracking variables to avoid "Unknown environment" errors
        env.pop("HATCH_ENV", None)
        env.pop("HATCH_ENV_ACTIVE", None)
        result = subprocess.run(
            ["python", "-m", "build"],
            cwd=str(repo.path),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        assert result.returncode == 0, f"Build failed: {result.stdout}\n{result.stderr}"

    @classmethod
    def pyproject_content(cls) -> str:
        return """[build-system]
requires = ["setuptools>=61.0", "wheel", "gitversioned @ file://{ROOT}"]
build-backend = "setuptools.build_meta"

[project]
name = "{PACKAGE}"
dynamic = ["version"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.gitversioned]
"""
