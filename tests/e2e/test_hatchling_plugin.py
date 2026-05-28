from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Any

import pytest

from gitversioned.plugins.hatchling_plugin import (
    GitVersionedVersionSource,
    hatch_register_version_source,
)
from gitversioned.settings import RegexStrategy, Settings, TemplatePathStrategy
from tests.conftest import GitRepoHelper


def run_build(cwd_path: Path) -> subprocess.CompletedProcess[str]:
    """Helper function to run the build as a subprocess using the current venv."""
    build_env = os.environ.copy()
    build_env.pop("HATCH_ENV", None)
    build_env.pop("HATCH_ENV_ACTIVE", None)
    venv_bin = str(Path(sys.executable).parent)
    build_env["PATH"] = os.pathsep.join([venv_bin, build_env.get("PATH", "")])

    build_env["PIP_NO_CACHE_DIR"] = "1"
    build_env["PIP_BREAK_SYSTEM_PACKAGES"] = "1"

    return subprocess.run(
        [sys.executable, "-m", "build", "--no-isolation"],
        cwd=cwd_path,
        capture_output=True,
        text=True,
        env=build_env,
        check=False,
    )


def clean_dist(repo_path: Path) -> None:
    """Ensure dist directory is clean before building."""
    dist_dir = repo_path / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)


def get_wheel_version(repo_path: Path) -> str:
    """Extract version from the generated wheel file."""
    dist_dir = repo_path / "dist"
    wheels = list(dist_dir.glob("*.whl"))
    assert len(wheels) == 1, f"Expected exactly 1 wheel, found {len(wheels)}"
    wheel_name = wheels[0].name
    return wheel_name.split("-")[1]


def verify_artifacts(repo_path: Path, package_name: str, expected_version: str) -> None:
    """Verify that wheel and sdist both have expected version.py and versions."""
    dist_dir = repo_path / "dist"
    wheels = list(dist_dir.glob("*.whl"))
    sdists = list(dist_dir.glob("*.tar.gz"))
    assert len(wheels) == 1
    assert len(sdists) == 1

    wheel_name = wheels[0].name
    sdist_name = sdists[0].name
    wheel_version = wheel_name.split("-")[1]
    assert wheel_version == expected_version
    assert expected_version in sdist_name

    with zipfile.ZipFile(wheels[0]) as zip_file:
        file_list = zip_file.namelist()
        version_file = f"{package_name}/version.py"
        assert version_file in file_list, f"Expected {version_file} in wheel"
        file_content = zip_file.read(version_file).decode("utf-8")
        assert expected_version in file_content

    with tarfile.open(sdists[0]) as tar_file:
        sdist_pkg_dir = sdist_name.replace(".tar.gz", "")
        names = tar_file.getnames()
        version_file_in_sdist = f"{sdist_pkg_dir}/src/{package_name}/version.py"
        if version_file_in_sdist not in names:
            version_file_in_sdist = f"{sdist_pkg_dir}/{package_name}/version.py"
        msg = f"Expected {version_file_in_sdist} in sdist"
        assert version_file_in_sdist in names, msg
        extracted_file = tar_file.extractfile(version_file_in_sdist)
        assert extracted_file is not None
        file_content = extracted_file.read().decode("utf-8")
        assert expected_version in file_content


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.regression
class TestHatchlingBuildBackendDeclarativeMetadataHooks:
    """E2E Test Class for US-1: Hatchling Build Backend Declarative Metadata Hooks."""

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """Shared context fixture supplying a project configured with Hatchling."""
        pyproject_toml = temp_git_repo.path / "pyproject.toml"
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        temp_git_repo.add("pyproject.toml")

        # Create package source structure
        src_dir = temp_git_repo.path / "src" / "test_pkg"
        src_dir.mkdir(parents=True, exist_ok=True)
        init_file = src_dir / "__init__.py"
        init_file.write_text("from .version import __version__\n", encoding="utf-8")
        temp_git_repo.add(str(init_file))

        gitignore = temp_git_repo.path / ".gitignore"
        gitignore.write_text(
            "dist/*\n*.egg-info/\n*.egg-info\n__pycache__/\n*.pyc\n",
            encoding="utf-8",
        )
        temp_git_repo.add(".gitignore")

        temp_git_repo.commit("Initial commit")

        return {
            "repo": temp_git_repo,
            "pyproject_path": pyproject_toml,
            "package_name": "test_pkg",
            "src_dir": src_dir,
        }

    @pytest.mark.smoke
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """Validate structural environment contracts before firing user actions."""
        assert valid_instances["pyproject_path"].exists()
        assert (valid_instances["src_dir"] / "__init__.py").exists()

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """Assert correct initial system wiring and session environment startup."""
        repo_helper = valid_instances["repo"]
        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        msg = f"Stdout: {result.stdout}\nStderr: {result.stderr}"
        assert result.returncode == 0, msg
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "0.1.0"
        verify_artifacts(repo_helper.path, "test_pkg", "0.1.0")

    @pytest.mark.sanity
    def test_invalid_initialization_values(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """Pass bad environment parameters to verify explicit system blockages."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        # Set an invalid version type
        original_content = pyproject_toml.read_text(encoding="utf-8")
        pyproject_toml.write_text(
            original_content + '\nversion_type = "invalid_type_here"\n',
            encoding="utf-8",
        )
        repo_helper.commit("Update pyproject.toml with invalid version_type")
        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode != 0

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """Omit critical configurations to verify system boundary defense lines."""
        repo_helper = valid_instances["repo"]
        # Delete pyproject.toml entirely
        valid_instances["pyproject_path"].unlink()
        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode != 0

    @pytest.mark.smoke
    def test_source_git_tags(self, valid_instances: dict[str, Any]) -> None:
        """US-1: Verify tags resolution strategy."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'source_type = ["tag"]\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure tag source type")
        repo_helper.tag("v2.4.1")

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "2.4.1"
        verify_artifacts(repo_helper.path, "test_pkg", "2.4.1")

    @pytest.mark.sanity
    def test_source_git_branch(self, valid_instances: dict[str, Any]) -> None:
        """US-1: Verify branch resolution strategy."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'source_type = ["branch"]\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure branch source type")
        repo_helper.branch("v3.1.2")
        repo_helper.commit("Commit on branch")

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "3.1.2"

    @pytest.mark.regression
    def test_source_git_commits(self, valid_instances: dict[str, Any]) -> None:
        """US-1: Verify commit message resolution strategy."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'source_type = ["commit"]\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure commit source type")
        repo_helper.commit("Release v1.0.2")

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "1.0.2"

    @pytest.mark.sanity
    def test_source_version_file(self, valid_instances: dict[str, Any]) -> None:
        """US-1: Verify flat file resolution strategy."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'source_type = ["file"]\n'
            'version_source_file = "VERSION.txt"\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure file source type")
        version_txt = repo_helper.path / "VERSION.txt"
        version_txt.write_text("version = 4.5.6", encoding="utf-8")
        repo_helper.add("VERSION.txt")
        repo_helper.commit("Add VERSION.txt")

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "4.5.6"

    @pytest.mark.regression
    def test_source_custom_function(self, valid_instances: dict[str, Any]) -> None:
        """US-1: Verify custom function hook resolution strategy."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'source_type = ["function"]\n'
            'version_source_function = "custom_hook:get_my_version"\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure function source type")

        hook_code = (
            "from packaging.version import Version\n"
            "from gitversioned.utils import GitReference\n"
            "def get_my_version(settings, repo):\n"
            "    return Version('5.6.7'), repo.current_commit_or_fallback\n"
        )
        (repo_helper.path / "custom_hook.py").write_text(hook_code, encoding="utf-8")
        repo_helper.add("custom_hook.py")
        repo_helper.commit("Add custom hook code")

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0, f"Stderr: {result.stderr}"
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "5.6.7"

    @pytest.mark.regression
    def test_source_git_archive(self, valid_instances: dict[str, Any]) -> None:
        """US-1: Verify git archive fallback parsing."""
        repo_helper = valid_instances["repo"]
        archive_content = (
            "commit_sha: abc1234\n"
            "short_sha: abc\n"
            "timestamp: 2023-01-01T00:00:00Z\n"
            "author_name: test\n"
            "author_email: test@test.com\n"
            "ref_names: HEAD -> main, tag: v9.9.9\n"
            "distance_from_head: 0\n"
            "is_head_commit: true\n"
            "total_commits: 10\n"
            "is_current_branch: true\n"
            "commit_message:\n"
            "Release 9.9.9\n"
        )
        arch_txt = repo_helper.path / ".git_archival.txt"
        arch_txt.write_text(archive_content, encoding="utf-8")
        repo_helper.remove_git_dir()

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "9.9.9"

    @pytest.mark.regression
    def test_marshalling(self, valid_instances: dict[str, Any]) -> None:
        """US-1: Verify Pydantic settings model marshalling limits."""
        settings_obj = Settings(
            package_name=valid_instances["package_name"],
            version="auto",
            source_type=["tag"],
        )
        dumped_data = settings_obj.model_dump()
        assert isinstance(dumped_data, dict)
        assert dumped_data["package_name"] == valid_instances["package_name"]
        assert dumped_data["source_type"] == ["tag"]

        validated_settings = Settings.model_validate(dumped_data)
        assert validated_settings.package_name == valid_instances["package_name"]
        assert validated_settings.source_type == ["tag"]

    @pytest.mark.sanity
    def test_dynamic_registry(self, valid_instances: dict[str, Any]) -> None:
        """US-1: Verify registry-based dynamic sources parse and execute."""
        strategy_obj = TemplatePathStrategy(path=Path("templates/release.py.template"))
        assert strategy_obj.type == "template_path"
        assert strategy_obj.path == Path("templates/release.py.template")

    @pytest.mark.regression
    def test_resolved_version_env_override(
        self, valid_instances: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify that GITVERSIONED_RESOLVED_VERSION environment variable
        overrides resolution.
        """
        repo_helper = valid_instances["repo"]
        monkeypatch.setenv("GITVERSIONED_RESOLVED_VERSION", "9.8.7")
        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "9.8.7"

    @pytest.mark.regression
    def test_set_version(self, valid_instances: dict[str, Any]) -> None:
        """Verify that setting version via Hatch CLI persists version to file."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'version_source_file = "VERSION.txt"\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure version_source_file")

        venv_bin = Path(sys.executable).parent
        hatch_path = venv_bin / "hatch"
        clean_env = os.environ.copy()
        clean_env.pop("HATCH_ENV", None)
        clean_env.pop("HATCH_ENV_ACTIVE", None)
        subprocess.run(
            [str(hatch_path), "version", "7.8.9"],
            cwd=repo_helper.path,
            check=True,
            capture_output=True,
            env=clean_env,
        )
        version_file = repo_helper.path / "VERSION.txt"
        assert version_file.exists()
        assert "version=7.8.9" in version_file.read_text(encoding="utf-8")

    @pytest.mark.regression
    def test_set_version_no_source_file(self, valid_instances: dict[str, Any]) -> None:
        """Verify set_version warning when version_source_file is omitted."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'version_source_file = ""\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure empty version_source_file")

        venv_bin = Path(sys.executable).parent
        hatch_path = venv_bin / "hatch"
        clean_env = os.environ.copy()
        clean_env.pop("HATCH_ENV", None)
        clean_env.pop("HATCH_ENV_ACTIVE", None)
        subprocess.run(
            [str(hatch_path), "version", "7.8.9"],
            cwd=repo_helper.path,
            check=True,
            capture_output=True,
            env=clean_env,
        )
        assert not (repo_helper.path / "VERSION.txt").exists()
        assert not (repo_helper.path / "version.txt").exists()

    @pytest.mark.regression
    def test_explicit_src_root(self, valid_instances: dict[str, Any]) -> None:
        """Verify explicit src_root configuration."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["custom_src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'src_root = "custom_src"\n'
            'output = "custom_src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure explicit src_root")

        custom_src = repo_helper.path / "custom_src"
        custom_src.mkdir(exist_ok=True)
        shutil.move(
            str(repo_helper.path / "src" / "test_pkg"),
            str(custom_src / "test_pkg"),
        )
        repo_helper.add("custom_src/test_pkg")
        subprocess.run(
            ["git", "add", "-A"],
            cwd=repo_helper.path,
            check=False,
        )
        repo_helper.commit("Move package to custom_src")

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "0.1.0"

    @pytest.mark.regression
    def test_sources_key_in_hatch_config(self, valid_instances: dict[str, Any]) -> None:
        """Verify get_src_root with sources dictionary mapping in hatch config."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'sources = { "src" = "" }\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure sources wheel target")

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "0.1.0"

    @pytest.mark.regression
    def test_package_directly_in_root(self, valid_instances: dict[str, Any]) -> None:
        """Verify get_src_root when package is directly under project root."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'output = "test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure root package version source")

        shutil.rmtree(repo_helper.path / "src")
        pkg_dir = repo_helper.path / "test_pkg"
        pkg_dir.mkdir(exist_ok=True)
        init_file = pkg_dir / "__init__.py"
        init_file.write_text("from .version import __version__\n", encoding="utf-8")
        repo_helper.add("test_pkg")
        subprocess.run(
            ["git", "add", "-A"],
            cwd=repo_helper.path,
            check=False,
        )
        repo_helper.commit("Move package to root directory")

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "0.1.0"


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.regression
class TestHatchlingVersionOutputTypeEnforcementAndCoercion:
    """E2E Test Class for US-2: Hatchling Version Output Type Enforcement & Coercion."""

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """Shared context fixture supplying a project with customized
        version type configurations.
        """
        pyproject_toml = temp_git_repo.path / "pyproject.toml"
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        temp_git_repo.add("pyproject.toml")

        # Create package source structure
        src_dir = temp_git_repo.path / "src" / "test_pkg"
        src_dir.mkdir(parents=True, exist_ok=True)
        init_file = src_dir / "__init__.py"
        init_file.write_text("from .version import __version__\n", encoding="utf-8")
        temp_git_repo.add(str(init_file))

        gitignore = temp_git_repo.path / ".gitignore"
        gitignore.write_text(
            "dist/*\n*.egg-info/\n*.egg-info\n__pycache__/\n*.pyc\n",
            encoding="utf-8",
        )
        temp_git_repo.add(".gitignore")

        temp_git_repo.commit("Initial commit")

        return {
            "repo": temp_git_repo,
            "pyproject_path": pyproject_toml,
            "package_name": "test_pkg",
            "src_dir": src_dir,
        }

    @pytest.mark.smoke
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """Validate structural environment contracts."""
        assert valid_instances["pyproject_path"].exists()

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """Assert correct initial startup and state-aware auto-resolution
        in clean state.
        """
        repo_helper = valid_instances["repo"]
        repo_helper.tag("v1.5.0")
        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "1.5.0"

    @pytest.mark.sanity
    def test_invalid_initialization_values(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """Pass bad version_type parameter to verify failure."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'version_type = "unsupported_type"\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure invalid version_type")
        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode != 0

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """Omit dynamic version field in project settings to verify Hatchling error."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Remove dynamic version configuration")
        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode != 0

    @pytest.mark.smoke
    def test_state_aware_auto_resolution_dirty(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """US-2: Verify auto resolution converts format when dirty files exist."""
        repo_helper = valid_instances["repo"]
        repo_helper.tag("v1.0.0")

        # Create uncommitted dirty file
        dirty_file = repo_helper.path / "src" / "test_pkg" / "dirty.txt"
        dirty_file.write_text("uncommitted change", encoding="utf-8")

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert ".dev" in wheel_version or "dev" in wheel_version

    @pytest.mark.sanity
    def test_state_aware_auto_resolution_detached(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """US-2: Verify auto resolution converts format when HEAD is detached."""
        repo_helper = valid_instances["repo"]
        repo_helper.tag("v2.0.0")

        # Checkout detached head
        repo_helper.checkout_detached()

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "2.0.0"

        # Commit on top of detached HEAD to move ahead
        dummy_file = repo_helper.path / "dummy.txt"
        dummy_file.write_text("detached commit", encoding="utf-8")
        repo_helper.add("dummy.txt")
        repo_helper.commit("Detached commit message")

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert ".dev" in wheel_version or "dev" in wheel_version

    @pytest.mark.smoke
    def test_version_type_release(self, valid_instances: dict[str, Any]) -> None:
        """US-2: Verify 'release' output type enforcement."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'version_type = "release"\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure release version type")
        repo_helper.tag("v3.0.0")
        dummy_file = repo_helper.path / "dummy.txt"
        dummy_file.write_text("commit ahead", encoding="utf-8")
        repo_helper.add("dummy.txt")
        repo_helper.commit("Commit ahead of tag")

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "3.0.0"

    @pytest.mark.sanity
    def test_version_type_dev(self, valid_instances: dict[str, Any]) -> None:
        """US-2: Verify 'dev' output type enforcement."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'version_type = "dev"\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure dev version type")
        repo_helper.tag("v1.1.0")

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert ".dev" in wheel_version or "dev" in wheel_version

    @pytest.mark.sanity
    def test_version_type_pre(self, valid_instances: dict[str, Any]) -> None:
        """US-2: Verify 'pre'/'nightly' output type enforcement."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'version_type = "pre"\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure pre version type")
        repo_helper.tag("v1.1.0")
        dummy_file = repo_helper.path / "dummy.txt"
        dummy_file.write_text("commit ahead", encoding="utf-8")
        repo_helper.add("dummy.txt")
        repo_helper.commit("Commit ahead of tag")

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert "a" in wheel_version

    @pytest.mark.regression
    def test_version_type_post(self, valid_instances: dict[str, Any]) -> None:
        """US-2: Verify 'post' output type enforcement."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'version_type = "post"\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure post version type")
        repo_helper.tag("v2.2.0")
        dummy_file = repo_helper.path / "dummy.txt"
        dummy_file.write_text("commit ahead", encoding="utf-8")
        repo_helper.add("dummy.txt")
        repo_helper.commit("Commit ahead of tag")

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert ".post" in wheel_version or "post" in wheel_version

    @pytest.mark.regression
    def test_isolated_build_serialization(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """US-2: Verify wheel and sdist files match computed version string."""
        repo_helper = valid_instances["repo"]
        repo_helper.tag("v1.4.3")

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "1.4.3"
        verify_artifacts(repo_helper.path, "test_pkg", "1.4.3")

    @pytest.mark.regression
    def test_marshalling(self, valid_instances: dict[str, Any]) -> None:
        """US-2: Verify Pydantic settings model marshalling limits."""
        settings_obj = Settings(
            package_name=valid_instances["package_name"],
            version_type="dev",
        )
        dumped = settings_obj.model_dump()
        assert dumped["version_type"] == "dev"
        assert Settings.model_validate(dumped).version_type == "dev"

    @pytest.mark.sanity
    def test_dynamic_registry(self, valid_instances: dict[str, Any]) -> None:
        """US-2: Verify registry-based dynamic sources parse and execute."""
        regex_strategy = RegexStrategy(pattern=r'__version__ = "(?P<version>.*?)"')
        assert regex_strategy.type == "regex"
        assert regex_strategy.pattern == r'__version__ = "(?P<version>.*?)"'


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.regression
class TestHatchlingGranularAutoIncrementScoping:
    """E2E Test Class for US-3: Hatchling Granular Auto-Increment Scoping."""

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """Shared context fixture supplying a project with customizable
        auto-increment configurations.
        """
        pyproject_toml = temp_git_repo.path / "pyproject.toml"
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        temp_git_repo.add("pyproject.toml")

        # Create package source structure
        src_dir = temp_git_repo.path / "src" / "test_pkg"
        src_dir.mkdir(parents=True, exist_ok=True)
        init_file = src_dir / "__init__.py"
        init_file.write_text("from .version import __version__\n", encoding="utf-8")
        temp_git_repo.add(str(init_file))

        gitignore = temp_git_repo.path / ".gitignore"
        gitignore.write_text(
            "dist/*\n*.egg-info/\n*.egg-info\n__pycache__/\n*.pyc\n",
            encoding="utf-8",
        )
        temp_git_repo.add(".gitignore")

        temp_git_repo.commit("Initial commit")

        return {
            "repo": temp_git_repo,
            "pyproject_path": pyproject_toml,
            "package_name": "test_pkg",
            "src_dir": src_dir,
        }

    @pytest.mark.smoke
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """Validate structural environment contracts."""
        assert valid_instances["pyproject_path"].exists()

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """Assert correct initial startup and default increment behavior."""
        repo_helper = valid_instances["repo"]
        repo_helper.tag("v1.0.0")

        # Commit ahead
        dummy_file = repo_helper.path / "dummy.txt"
        dummy_file.write_text("commit ahead", encoding="utf-8")
        repo_helper.add("dummy.txt")
        repo_helper.commit("Commit ahead of tag")

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        # Default behavior: without auto_increment, it defaults to no
        # core segment bump (starts with 1.0.0)
        assert wheel_version.startswith("1.0.0")

    @pytest.mark.sanity
    def test_invalid_initialization_values(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """Pass bad auto_increment level to verify build abort."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'auto_increment = { release = "invalid_level" }\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure invalid auto_increment level")
        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode != 0

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """Provide invalid type mapping for auto_increment to check
        validation boundaries.
        """
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            # auto_increment expects a dictionary, not a list of lists
            'auto_increment = [["release", "patch"]]\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure invalid auto_increment type format")
        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode != 0

    @pytest.mark.smoke
    def test_auto_increment_none(self, valid_instances: dict[str, Any]) -> None:
        """US-3: Verify auto_increment = 'none' skips mutation engine."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'auto_increment = "none"\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure auto_increment = none")
        repo_helper.tag("v1.2.3")

        # Commit ahead to verify no bump is applied
        dummy_file = repo_helper.path / "dummy.txt"
        dummy_file.write_text("commit ahead", encoding="utf-8")
        repo_helper.add("dummy.txt")
        repo_helper.commit("Commit ahead of tag")

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        # Should remain on the 1.2.3 base (e.g. 1.2.3.dev...)
        assert wheel_version.startswith("1.2.3")

    @pytest.mark.smoke
    def test_auto_increment_patch(self, valid_instances: dict[str, Any]) -> None:
        """US-3: Verify auto_increment patch increments correct segment."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'version_type = "release"\n'
            'auto_increment = { release = "patch" }\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure patch auto_increment")
        repo_helper.tag("v1.2.3")

        # Commit ahead to trigger increment
        dummy_file = repo_helper.path / "dummy.txt"
        dummy_file.write_text("commit ahead", encoding="utf-8")
        repo_helper.add("dummy.txt")
        repo_helper.commit("Commit ahead of tag")

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        # Should bump release to 1.2.4
        assert wheel_version == "1.2.4"

    @pytest.mark.sanity
    def test_auto_increment_pre(self, valid_instances: dict[str, Any]) -> None:
        """US-3: Verify prerelease auto_increment increments preview sub-counter."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'version_type = "pre"\n'
            'auto_increment = { pre = "patch" }\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure pre auto_increment")
        repo_helper.tag("v1.2.3")

        # Commit ahead to trigger increment
        dummy_file = repo_helper.path / "dummy.txt"
        dummy_file.write_text("commit ahead", encoding="utf-8")
        repo_helper.add("dummy.txt")
        repo_helper.commit("Commit ahead of tag")

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        # Should bump patch from 1.2.3 to 1.2.4, and format as pre (e.g. 1.2.4a2026...)
        assert wheel_version.startswith("1.2.4a")

    @pytest.mark.regression
    def test_auto_increment_dev(self, valid_instances: dict[str, Any]) -> None:
        """US-3: Verify dev auto_increment increments dev sub-counter."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["src/test_pkg"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'version_type = "dev"\n'
            'auto_increment = { dev = "minor" }\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure dev auto_increment")
        repo_helper.tag("v1.2.3")

        # Commit ahead to trigger increment
        dummy_file = repo_helper.path / "dummy.txt"
        dummy_file.write_text("commit ahead", encoding="utf-8")
        repo_helper.add("dummy.txt")
        repo_helper.commit("Commit ahead of tag")

        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        # Should bump minor from 2 to 3, micro to 0 (1.3.0) and dev suffix
        # (e.g. 1.3.0.dev...)
        assert wheel_version.startswith(("1.3.0.dev", "1.3.0dev"))

    @pytest.mark.regression
    def test_marshalling(self, valid_instances: dict[str, Any]) -> None:
        """US-3: Verify Pydantic settings model marshalling limits."""
        settings_obj = Settings(
            package_name=valid_instances["package_name"],
            auto_increment={"release": "patch", "dev": "minor"},
        )
        dumped = settings_obj.model_dump()
        assert dumped["auto_increment"] == {"release": "patch", "dev": "minor"}
        validated = Settings.model_validate(dumped).auto_increment
        assert validated == {"release": "patch", "dev": "minor"}

    @pytest.mark.sanity
    def test_dynamic_registry(self, valid_instances: dict[str, Any]) -> None:
        """US-3: Verify registry-based dynamic sources parse and execute."""
        strategy_obj = TemplatePathStrategy(path=Path("templates/dev.py.template"))
        assert strategy_obj.type == "template_path"
        assert strategy_obj.path == Path("templates/dev.py.template")


class TestHatchlingPluginDirectCoverage:
    """Class to directly execute all internal branches of hatchling plugin
    for coverage.
    """

    def test_direct_plugin_coverage(self, temp_git_repo: GitRepoHelper) -> None:
        assert hatch_register_version_source() is GitVersionedVersionSource

        # Configure dummy project in temp repo
        pyproject_toml = temp_git_repo.path / "pyproject.toml"
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test-coverage-pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n'
            'version_source_file = "version_source.txt"\n'
            'output = "version_out.py"\n',
            encoding="utf-8",
        )
        temp_git_repo.add("pyproject.toml")
        temp_git_repo.commit("Init coverage repo")

        plugin_source = GitVersionedVersionSource(
            root=str(temp_git_repo.path),
            config={"version_source_file": "version_source.txt"},
        )

        # Test set_version when file configured
        version_data_dict: dict[str, Any] = {}
        plugin_source.set_version("1.2.3", version_data_dict)
        version_source_file = temp_git_repo.path / "version_source.txt"
        assert version_source_file.exists()
        assert "version=1.2.3" in version_source_file.read_text(encoding="utf-8")

        # Test set_version when file is empty/none
        plugin_no_file = GitVersionedVersionSource(
            root=str(temp_git_repo.path), config={"version_source_file": ""}
        )
        plugin_no_file.set_version("1.2.4", version_data_dict)

        # Test get_src_root layout branches
        # 1. explicit src_root config
        plugin_src_config = GitVersionedVersionSource(
            root=str(temp_git_repo.path), config={"src_root": "custom_dir"}
        )
        assert plugin_src_config.get_src_root() == temp_git_repo.path / "custom_dir"

        # 2. packages target wheel layout
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test-coverage-pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'packages = ["packages_dir/test-coverage-pkg"]\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n',
            encoding="utf-8",
        )
        plugin_packages = GitVersionedVersionSource(
            root=str(temp_git_repo.path), config={}
        )
        # Reset internal metadata cache to force re-reading config
        plugin_packages._metadata = None
        assert plugin_packages.get_src_root() == (
            temp_git_repo.path / "packages_dir/test-coverage-pkg"
        )

        # 3. sources target wheel layout
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test-coverage-pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.build.targets.wheel]\n"
            'sources = { "sources_dir" = "" }\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n',
            encoding="utf-8",
        )
        plugin_sources = GitVersionedVersionSource(
            root=str(temp_git_repo.path), config={}
        )
        plugin_sources._metadata = None
        assert plugin_sources.get_src_root() == temp_git_repo.path / "sources_dir"

        # 4. src/package_name layout
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["hatchling", "gitversioned"]\n'
            'build-backend = "hatchling.build"\n\n'
            "[project]\n"
            'name = "test-coverage-pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.hatch.version]\n"
            'source = "gitversioned"\n',
            encoding="utf-8",
        )
        src_pkg_dir = temp_git_repo.path / "src" / "test_coverage_pkg"
        src_pkg_dir.mkdir(parents=True, exist_ok=True)
        plugin_src_layout = GitVersionedVersionSource(
            root=str(temp_git_repo.path), config={}
        )
        plugin_src_layout._metadata = None
        assert plugin_src_layout.get_src_root() == src_pkg_dir

        # 5. package_name directly in root layout
        shutil.rmtree(temp_git_repo.path / "src")
        root_pkg_dir = temp_git_repo.path / "test_coverage_pkg"
        root_pkg_dir.mkdir(exist_ok=True)
        plugin_root_layout = GitVersionedVersionSource(
            root=str(temp_git_repo.path), config={}
        )
        plugin_root_layout._metadata = None
        assert plugin_root_layout.get_src_root() == root_pkg_dir

        # 6. Fallback layout when nothing matches
        shutil.rmtree(root_pkg_dir)
        plugin_fallback_layout = GitVersionedVersionSource(
            root=str(temp_git_repo.path), config={}
        )
        plugin_fallback_layout._metadata = None
        assert plugin_fallback_layout.get_src_root() == temp_git_repo.path
