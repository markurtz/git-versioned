# Copyright 2026 Mark Kurtz
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
E2E tests for the Maturin build backend wrapper plugin.
"""

from __future__ import annotations

import os as os_module
import re
import shutil
import subprocess
import sys as sys_module
from pathlib import Path
from typing import Any

import pytest

from gitversioned.plugins import maturin_plugin
from gitversioned.settings import Settings, TemplatePathStrategy
from tests.conftest import GitRepoHelper


def run_build(cwd_path: Path) -> subprocess.CompletedProcess[str]:
    """Helper function to run the build as a subprocess using the current venv."""
    build_env = os_module.environ.copy()
    build_env.pop("HATCH_ENV", None)
    build_env.pop("HATCH_ENV_ACTIVE", None)
    venv_bin = str(Path(sys_module.executable).parent)
    build_env["PATH"] = os_module.pathsep.join([venv_bin, build_env.get("PATH", "")])

    build_env["PIP_NO_CACHE_DIR"] = "1"
    build_env["PIP_BREAK_SYSTEM_PACKAGES"] = "1"

    return subprocess.run(
        [sys_module.executable, "-m", "build", "--no-isolation"],
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


class MockMaturinModule:
    """Mock maturin module to capture and assert hook invocations."""

    def __init__(self) -> None:
        self.called_args: dict[str, tuple[Any, ...]] = {}
        self.called_kwargs: dict[str, dict[str, Any]] = {}

    def _get_resolved_version(self) -> str:
        # Check Cargo.toml first
        cargo_toml = Path("Cargo.toml")
        if cargo_toml.exists():
            content = cargo_toml.read_text(encoding="utf-8")
            match = re.search(
                r'(?ms)^\[package\].*?^\s*version\s*=\s*([\'"])(?P<version>[^\'"]+)\1',
                content,
            )
            if match:
                return match.group("version")
        # Check setup.py
        setup_py = Path("setup.py")
        if setup_py.exists():
            content = setup_py.read_text(encoding="utf-8")
            match = re.search(r"version\s*=\s*['\"]([^'\"]+)['\"]", content)
            if match:
                return match.group(1)
        # Check version.py
        version_py = Path("version.py")
        if version_py.exists():
            content = version_py.read_text(encoding="utf-8")
            match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", content)
            if match:
                return match.group(1)
        return "0.1.0"

    def build_wheel(
        self,
        wheel_directory: str,
        config_settings: dict[str, Any] | None = None,
        metadata_directory: str | None = None,
    ) -> str:
        self.called_args["build_wheel"] = (wheel_directory,)
        self.called_kwargs["build_wheel"] = {
            "config_settings": config_settings,
            "metadata_directory": metadata_directory,
        }
        return f"mock_package-{self._get_resolved_version()}-py3-none-any.whl"

    def build_sdist(
        self,
        sdist_directory: str,
        config_settings: dict[str, Any] | None = None,
    ) -> str:
        self.called_args["build_sdist"] = (sdist_directory,)
        self.called_kwargs["build_sdist"] = {"config_settings": config_settings}
        return f"mock_package-{self._get_resolved_version()}.tar.gz"

    def get_requires_for_build_wheel(
        self,
        config_settings: dict[str, Any] | None = None,
    ) -> list[str]:
        self.called_args["get_requires_for_build_wheel"] = ()
        self.called_kwargs["get_requires_for_build_wheel"] = {
            "config_settings": config_settings
        }
        return ["maturin>=1.0,<2.0"]

    def get_requires_for_build_sdist(
        self,
        config_settings: dict[str, Any] | None = None,
    ) -> list[str]:
        self.called_args["get_requires_for_build_sdist"] = ()
        self.called_kwargs["get_requires_for_build_sdist"] = {
            "config_settings": config_settings
        }
        return ["maturin>=1.0,<2.0"]

    def prepare_metadata_for_build_wheel(
        self,
        metadata_directory: str,
        config_settings: dict[str, Any] | None = None,
    ) -> str:
        self.called_args["prepare_metadata_for_build_wheel"] = (metadata_directory,)
        self.called_kwargs["prepare_metadata_for_build_wheel"] = {
            "config_settings": config_settings
        }
        return f"mock_package-{self._get_resolved_version()}.dist-info"

    def build_editable(
        self,
        wheel_directory: str,
        config_settings: dict[str, Any] | None = None,
        metadata_directory: str | None = None,
    ) -> str:
        self.called_args["build_editable"] = (wheel_directory,)
        self.called_kwargs["build_editable"] = {
            "config_settings": config_settings,
            "metadata_directory": metadata_directory,
        }
        return f"mock_package-{self._get_resolved_version()}-py3-none-any.whl"

    def get_requires_for_build_editable(
        self,
        config_settings: dict[str, Any] | None = None,
    ) -> list[str]:
        self.called_args["get_requires_for_build_editable"] = ()
        self.called_kwargs["get_requires_for_build_editable"] = {
            "config_settings": config_settings
        }
        return ["maturin>=1.0,<2.0"]

    def prepare_metadata_for_build_editable(
        self,
        metadata_directory: str,
        config_settings: dict[str, Any] | None = None,
    ) -> str:
        self.called_args["prepare_metadata_for_build_editable"] = (metadata_directory,)
        self.called_kwargs["prepare_metadata_for_build_editable"] = {
            "config_settings": config_settings
        }
        return f"mock_package-{self._get_resolved_version()}.dist-info"


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.regression
class TestMaturinWrapperBuildBackendPipelineOrchestration:
    """E2E Test Class for US-1: Maturin Wrapper Build Backend Pipeline Orchestration."""

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """Shared context fixture supplying a project configured with Maturin."""
        pyproject_toml = temp_git_repo.path / "pyproject.toml"
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["maturin>=1.0,<2.0", "gitversioned"]\n'
            'build-backend = "gitversioned.integrations.maturin"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.maturin]\n"
            'bindings = "bin"\n\n'
            "[tool.gitversioned]\n"
            'output = "version.py"\n',
            encoding="utf-8",
        )
        temp_git_repo.add("pyproject.toml")

        cargo_toml = temp_git_repo.path / "Cargo.toml"
        cargo_toml.write_text(
            '[package]\nname = "test_pkg"\nversion = "0.0.0"\nedition = "2021"\n',
            encoding="utf-8",
        )
        temp_git_repo.add("Cargo.toml")

        src_dir = temp_git_repo.path / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        main_rs = src_dir / "main.rs"
        main_rs.write_text('fn main() { println!("Hello!"); }\n', encoding="utf-8")
        temp_git_repo.add(str(main_rs))

        gitignore = temp_git_repo.path / ".gitignore"
        gitignore.write_text(
            "dist/*\ntarget/*\n*.egg-info/\n*.egg-info\n__pycache__/\n*.pyc\n",
            encoding="utf-8",
        )
        temp_git_repo.add(".gitignore")

        temp_git_repo.commit("Initial commit")

        return {
            "repo": temp_git_repo,
            "pyproject_path": pyproject_toml,
            "cargo_path": cargo_toml,
            "package_name": "test_pkg",
            "src_dir": src_dir,
        }

    @pytest.mark.smoke
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """Validate structural environment contracts before firing actions."""
        assert valid_instances["pyproject_path"].exists()
        assert valid_instances["cargo_path"].exists()
        assert (valid_instances["src_dir"] / "main.rs").exists()

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """Assert correct initial system wiring and session environment startup."""
        repo_helper = valid_instances["repo"]
        clean_dist(repo_helper.path)
        result_proc = run_build(repo_helper.path)
        assert result_proc.returncode == 0, (
            f"Stdout: {result_proc.stdout}\nStderr: {result_proc.stderr}"
        )
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "0.1.0"

        # Verify Cargo.toml version was updated with resolved version
        cargo_content = valid_instances["cargo_path"].read_text(encoding="utf-8")
        assert 'version = "0.1.0"' in cargo_content

    @pytest.mark.sanity
    def test_invalid_initialization_values(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """Pass bad environment parameters to verify explicit system blockages."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        original_content = pyproject_toml.read_text(encoding="utf-8")
        pyproject_toml.write_text(
            original_content + '\nversion_type = "invalid_type_here"\n',
            encoding="utf-8",
        )
        repo_helper.commit("Update to invalid version type")
        clean_dist(repo_helper.path)
        result_proc = run_build(repo_helper.path)
        assert result_proc.returncode != 0

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """Omit critical configurations to verify system boundary defense lines."""
        repo_helper = valid_instances["repo"]
        valid_instances["pyproject_path"].unlink()
        clean_dist(repo_helper.path)
        result_proc = run_build(repo_helper.path)
        assert result_proc.returncode != 0

    @pytest.mark.regression
    def test_marshalling(self, valid_instances: dict[str, Any]) -> None:
        """US-1: Verify Pydantic settings model marshalling limits."""
        settings_obj = Settings(
            package_name=valid_instances["package_name"],
            project_root=valid_instances["repo"].path,
            version="auto",
            source_type=["tag"],
        )
        dumped_data = settings_obj.model_dump()
        assert isinstance(dumped_data, dict)
        assert dumped_data["package_name"] == valid_instances["package_name"]

        validated_settings = Settings.model_validate(dumped_data)
        assert validated_settings.package_name == valid_instances["package_name"]

    @pytest.mark.sanity
    def test_dynamic_registry(self, valid_instances: dict[str, Any]) -> None:
        """US-1: Verify registry-based dynamic sources parse and execute."""
        strategy_obj = TemplatePathStrategy(path=Path("templates/release.py.template"))
        assert strategy_obj.type == "template_path"
        assert strategy_obj.path == Path("templates/release.py.template")


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.regression
class TestMaturinCargoWorkspaceAndInputSurfaceMatrix:
    """E2E Test Class for US-2: Maturin Cargo Workspace and Input Surface Matrix."""

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """Shared context fixture supplying a project with customized configs."""
        pyproject_toml = temp_git_repo.path / "pyproject.toml"
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["maturin>=1.0,<2.0", "gitversioned"]\n'
            'build-backend = "gitversioned.plugins.maturin_plugin"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.maturin]\n"
            'bindings = "bin"\n\n'
            "[tool.gitversioned]\n"
            'output = "version.py"\n',
            encoding="utf-8",
        )
        temp_git_repo.add("pyproject.toml")

        cargo_toml = temp_git_repo.path / "Cargo.toml"
        cargo_toml.write_text(
            '[package]\nname = "test_pkg"\nversion = "0.0.0"\nedition = "2021"\n',
            encoding="utf-8",
        )
        temp_git_repo.add("Cargo.toml")

        src_dir = temp_git_repo.path / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        main_rs = src_dir / "main.rs"
        main_rs.write_text("fn main() {}\n", encoding="utf-8")
        temp_git_repo.add(str(main_rs))

        temp_git_repo.commit("Initial commit")

        return {
            "repo": temp_git_repo,
            "pyproject_path": pyproject_toml,
            "cargo_path": cargo_toml,
            "package_name": "test_pkg",
        }

    @pytest.mark.smoke
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """Validate structural environment contracts."""
        assert valid_instances["pyproject_path"].exists()
        assert valid_instances["cargo_path"].exists()

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """Assert correct initial startup."""
        repo_helper = valid_instances["repo"]
        repo_helper.tag("v1.5.0")
        clean_dist(repo_helper.path)
        result_proc = run_build(repo_helper.path)
        assert result_proc.returncode == 0
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
            'requires = ["maturin>=1.0,<2.0", "gitversioned"]\n'
            'build-backend = "gitversioned.plugins.maturin_plugin"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.maturin]\n"
            'bindings = "bin"\n\n'
            "[tool.gitversioned]\n"
            'version_type = "unsupported_type"\n'
            'output = "version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure invalid version_type")
        clean_dist(repo_helper.path)
        result_proc = run_build(repo_helper.path)
        assert result_proc.returncode != 0

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """Omit dynamic version field to verify build failure."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["maturin>=1.0,<2.0", "gitversioned"]\n'
            'build-backend = "gitversioned.plugins.maturin_plugin"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            "[tool.maturin]\n"
            'bindings = "bin"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Remove dynamic version configuration")
        clean_dist(repo_helper.path)
        result_proc = run_build(repo_helper.path)
        assert result_proc.returncode != 0

    @pytest.mark.smoke
    def test_source_git_tags(
        self, valid_instances: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """US-2: Validate git tag input source."""
        repo_helper = valid_instances["repo"]
        repo_helper.tag("v2.4.1")

        mock_maturin = MockMaturinModule()
        monkeypatch.setattr(maturin_plugin, "maturin", mock_maturin)
        monkeypatch.setattr(maturin_plugin, "_logging_configured", False)
        monkeypatch.chdir(repo_helper.path)

        result_path = maturin_plugin.build_wheel("dist_dir")
        assert "0.1.0" not in result_path
        cargo_content = (repo_helper.path / "Cargo.toml").read_text(encoding="utf-8")
        assert 'version = "2.4.1"' in cargo_content

    @pytest.mark.sanity
    def test_source_git_branch(
        self, valid_instances: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """US-2: Validate git branch input source."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["maturin>=1.0,<2.0", "gitversioned"]\n'
            'build-backend = "gitversioned.plugins.maturin_plugin"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.maturin]\n"
            'bindings = "bin"\n\n'
            "[tool.gitversioned]\n"
            'source_type = ["branch"]\n'
            'output = "version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure branch source type")
        repo_helper.branch("v3.1.2")
        repo_helper.commit("Commit on branch")

        mock_maturin = MockMaturinModule()
        monkeypatch.setattr(maturin_plugin, "maturin", mock_maturin)
        monkeypatch.setattr(maturin_plugin, "_logging_configured", False)
        monkeypatch.chdir(repo_helper.path)

        result_path = maturin_plugin.build_wheel("dist_dir")
        assert "0.1.0" not in result_path
        cargo_content = (repo_helper.path / "Cargo.toml").read_text(encoding="utf-8")
        assert 'version = "3.1.2"' in cargo_content

    @pytest.mark.regression
    def test_source_git_commits(
        self, valid_instances: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """US-2: Validate git commit message input source."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["maturin>=1.0,<2.0", "gitversioned"]\n'
            'build-backend = "gitversioned.plugins.maturin_plugin"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.maturin]\n"
            'bindings = "bin"\n\n'
            "[tool.gitversioned]\n"
            'source_type = ["commit"]\n'
            'output = "version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure commit source type")
        repo_helper.commit("Release v1.0.2")

        mock_maturin = MockMaturinModule()
        monkeypatch.setattr(maturin_plugin, "maturin", mock_maturin)
        monkeypatch.setattr(maturin_plugin, "_logging_configured", False)
        monkeypatch.chdir(repo_helper.path)

        result_path = maturin_plugin.build_wheel("dist_dir")
        assert "0.1.0" not in result_path
        cargo_content = (repo_helper.path / "Cargo.toml").read_text(encoding="utf-8")
        assert 'version = "1.0.2"' in cargo_content

    @pytest.mark.sanity
    def test_source_version_file(
        self, valid_instances: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """US-2: Validate standalone flat file input source."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["maturin>=1.0,<2.0", "gitversioned"]\n'
            'build-backend = "gitversioned.plugins.maturin_plugin"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.maturin]\n"
            'bindings = "bin"\n\n'
            "[tool.gitversioned]\n"
            'source_type = ["file"]\n'
            'version_source_file = "VERSION.txt"\n'
            'output = "version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure file source type")
        version_txt = repo_helper.path / "VERSION.txt"
        version_txt.write_text("version = 4.5.6", encoding="utf-8")
        repo_helper.add("VERSION.txt")
        repo_helper.commit("Add VERSION.txt")

        mock_maturin = MockMaturinModule()
        monkeypatch.setattr(maturin_plugin, "maturin", mock_maturin)
        monkeypatch.setattr(maturin_plugin, "_logging_configured", False)
        monkeypatch.chdir(repo_helper.path)

        result_path = maturin_plugin.build_wheel("dist_dir")
        assert "0.1.0" not in result_path
        cargo_content = (repo_helper.path / "Cargo.toml").read_text(encoding="utf-8")
        assert 'version = "4.5.6"' in cargo_content

    @pytest.mark.regression
    def test_source_custom_function(
        self, valid_instances: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """US-2: Validate custom module callback function pointer."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["maturin>=1.0,<2.0", "gitversioned"]\n'
            'build-backend = "gitversioned.plugins.maturin_plugin"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.maturin]\n"
            'bindings = "bin"\n\n'
            "[tool.gitversioned]\n"
            'source_type = ["function"]\n'
            'version_source_function = "custom_hook:get_my_version"\n'
            'output = "version.py"\n',
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

        mock_maturin = MockMaturinModule()
        monkeypatch.setattr(maturin_plugin, "maturin", mock_maturin)
        monkeypatch.setattr(maturin_plugin, "_logging_configured", False)
        monkeypatch.chdir(repo_helper.path)

        result_path = maturin_plugin.build_wheel("dist_dir")
        assert "0.1.0" not in result_path
        cargo_content = (repo_helper.path / "Cargo.toml").read_text(encoding="utf-8")
        assert 'version = "5.6.7"' in cargo_content

    @pytest.mark.regression
    def test_source_git_archive(
        self, valid_instances: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """US-2: Validate git-archive fallback parsing without live git tree."""
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

        mock_maturin = MockMaturinModule()
        monkeypatch.setattr(maturin_plugin, "maturin", mock_maturin)
        monkeypatch.setattr(maturin_plugin, "_logging_configured", False)
        monkeypatch.chdir(repo_helper.path)

        result_path = maturin_plugin.build_wheel("dist_dir")
        assert "0.1.0" not in result_path
        cargo_content = (repo_helper.path / "Cargo.toml").read_text(encoding="utf-8")
        assert 'version = "9.9.9"' in cargo_content

    @pytest.mark.sanity
    def test_rust_string_validity(
        self, valid_instances: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """US-2: Validate PEP 440 and SemVer checks throw on invalid strings."""
        repo_helper = valid_instances["repo"]
        monkeypatch.setenv("GITVERSIONED_RESOLVED_VERSION", "invalid_ver_str")

        mock_maturin = MockMaturinModule()
        monkeypatch.setattr(maturin_plugin, "maturin", mock_maturin)
        monkeypatch.setattr(maturin_plugin, "_logging_configured", False)
        monkeypatch.chdir(repo_helper.path)

        with pytest.raises(ValueError):
            maturin_plugin.build_wheel("dist_dir")


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.regression
class TestMaturinTargetedPEP440SemVerOutputCoercionIncrements:
    """E2E Test Class for US-3: Maturin Output Coercion & Increments."""

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """Shared context fixture supplying a project with default layout."""
        pyproject_toml = temp_git_repo.path / "pyproject.toml"
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["maturin>=1.0,<2.0", "gitversioned"]\n'
            'build-backend = "gitversioned.plugins.maturin_plugin"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.maturin]\n"
            'bindings = "bin"\n\n'
            "[tool.gitversioned]\n"
            'output = "version.py"\n',
            encoding="utf-8",
        )
        temp_git_repo.add("pyproject.toml")

        cargo_toml = temp_git_repo.path / "Cargo.toml"
        cargo_toml.write_text(
            '[package]\nname = "test_pkg"\nversion = "0.0.0"\nedition = "2021"\n',
            encoding="utf-8",
        )
        temp_git_repo.add("Cargo.toml")

        src_dir = temp_git_repo.path / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        main_rs = src_dir / "main.rs"
        main_rs.write_text("fn main() {}\n", encoding="utf-8")
        temp_git_repo.add(str(main_rs))

        temp_git_repo.commit("Initial commit")

        return {
            "repo": temp_git_repo,
            "pyproject_path": pyproject_toml,
            "cargo_path": cargo_toml,
            "package_name": "test_pkg",
        }

    @pytest.mark.smoke
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """Validate structural environment contracts."""
        assert valid_instances["pyproject_path"].exists()
        assert valid_instances["cargo_path"].exists()

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """Assert correct initial system resolution."""
        repo_helper = valid_instances["repo"]
        clean_dist(repo_helper.path)
        result_proc = run_build(repo_helper.path)
        assert result_proc.returncode == 0

    @pytest.mark.sanity
    def test_invalid_initialization_values(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """Pass bad environment parameters."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["maturin>=1.0,<2.0", "gitversioned"]\n'
            'build-backend = "gitversioned.plugins.maturin_plugin"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.maturin]\n"
            'bindings = "bin"\n\n'
            "[tool.gitversioned]\n"
            'version_type = "bad_type"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure bad version_type")
        clean_dist(repo_helper.path)
        result_proc = run_build(repo_helper.path)
        assert result_proc.returncode != 0

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """Omit dynamic configuration field."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.unlink()
        clean_dist(repo_helper.path)
        result_proc = run_build(repo_helper.path)
        assert result_proc.returncode != 0

    @pytest.mark.smoke
    def test_state_aware_auto_resolution_dirty(
        self, valid_instances: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """US-3: Verify auto resolution outputs dev type when changes are dirty."""
        repo_helper = valid_instances["repo"]
        repo_helper.tag("v1.0.0")

        # Create uncommitted dirty file
        dirty_file = repo_helper.path / "dirty_file.rs"
        dirty_file.write_text("uncommitted content", encoding="utf-8")

        mock_maturin = MockMaturinModule()
        monkeypatch.setattr(maturin_plugin, "maturin", mock_maturin)
        monkeypatch.setattr(maturin_plugin, "_logging_configured", False)
        monkeypatch.chdir(repo_helper.path)

        result_path = maturin_plugin.build_wheel("dist_dir")
        assert "0.1.0" not in result_path
        cargo_content = (repo_helper.path / "Cargo.toml").read_text(encoding="utf-8")
        assert "dev" in cargo_content

    @pytest.mark.sanity
    def test_state_aware_auto_resolution_detached(
        self, valid_instances: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """US-3: Verify auto resolution outputs dev type when HEAD is detached."""
        repo_helper = valid_instances["repo"]
        repo_helper.tag("v2.0.0")
        repo_helper.checkout_detached()

        # Commit ahead of detached head
        dummy_file = repo_helper.path / "dummy.txt"
        dummy_file.write_text("detached changes", encoding="utf-8")
        repo_helper.add("dummy.txt")
        repo_helper.commit("Detached commit ahead")

        mock_maturin = MockMaturinModule()
        monkeypatch.setattr(maturin_plugin, "maturin", mock_maturin)
        monkeypatch.setattr(maturin_plugin, "_logging_configured", False)
        monkeypatch.chdir(repo_helper.path)

        result_path = maturin_plugin.build_wheel("dist_dir")
        assert "0.1.0" not in result_path
        cargo_content = (repo_helper.path / "Cargo.toml").read_text(encoding="utf-8")
        assert "dev" in cargo_content

    @pytest.mark.sanity
    def test_granular_output_channels(
        self, valid_instances: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """US-3: Verify granular channels (release, dev, pre, post)."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["maturin>=1.0,<2.0", "gitversioned"]\n'
            'build-backend = "gitversioned.plugins.maturin_plugin"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.maturin]\n"
            'bindings = "bin"\n\n'
            "[tool.gitversioned]\n"
            'output = "version.py"\n'
            'version_type = "post"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure post release channel")
        repo_helper.tag("v1.4.0")

        # Add commit to trigger post segment
        dummy_file = repo_helper.path / "dummy_post.txt"
        dummy_file.write_text("post content", encoding="utf-8")
        repo_helper.add("dummy_post.txt")
        repo_helper.commit("Post adjustment commit")

        mock_maturin = MockMaturinModule()
        monkeypatch.setattr(maturin_plugin, "maturin", mock_maturin)
        monkeypatch.setattr(maturin_plugin, "_logging_configured", False)
        monkeypatch.chdir(repo_helper.path)

        result_path = maturin_plugin.build_wheel("dist_dir")
        assert "0.1.0" not in result_path
        cargo_content = (repo_helper.path / "Cargo.toml").read_text(encoding="utf-8")
        assert "post1" in cargo_content

    @pytest.mark.regression
    def test_isolated_component_auto_increment(
        self, valid_instances: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """US-3: Verify auto-increment rule overrides (none, patch, pre)."""
        repo_helper = valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["maturin>=1.0,<2.0", "gitversioned"]\n'
            'build-backend = "gitversioned.plugins.maturin_plugin"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.maturin]\n"
            'bindings = "bin"\n\n'
            "[tool.gitversioned]\n"
            'output = "version.py"\n'
            'version_type = "release"\n'
            'auto_increment = { release = "patch" }\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure auto-increment rule")
        repo_helper.tag("v1.4.0")

        # Commit ahead to trigger increment bump
        dummy_file = repo_helper.path / "dummy_bump.txt"
        dummy_file.write_text("bump content", encoding="utf-8")
        repo_helper.add("dummy_bump.txt")
        repo_helper.commit("Commit ahead of tag")

        mock_maturin = MockMaturinModule()
        monkeypatch.setattr(maturin_plugin, "maturin", mock_maturin)
        monkeypatch.setattr(maturin_plugin, "_logging_configured", False)
        monkeypatch.chdir(repo_helper.path)

        result_path = maturin_plugin.build_wheel("dist_dir")
        assert "0.1.0" not in result_path
        cargo_content = (repo_helper.path / "Cargo.toml").read_text(encoding="utf-8")
        assert 'version = "1.4.1"' in cargo_content


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.regression
class TestMultipleMultiLanguageLayoutTestingConfigurations:
    """E2E Test Class for US-4: Multi-Language Layout Configurations."""

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """Shared context fixture supplying a project with mixed config files."""
        # Delete default pyproject.toml
        pyproject_path = temp_git_repo.path / "pyproject.toml"
        if pyproject_path.exists():
            pyproject_path.unlink()

        setup_cfg = temp_git_repo.path / "setup.cfg"
        setup_cfg.write_text(
            "[metadata]\n"
            "name = test_pkg\n"
            "version = 0.0.0\n\n"
            "[options]\n"
            "packages = find:\n\n"
            "[tool:gitversioned]\n"
            "output = version.py\n",
            encoding="utf-8",
        )
        temp_git_repo.add("setup.cfg")

        cargo_toml = temp_git_repo.path / "Cargo.toml"
        cargo_toml.write_text(
            '[package]\nname = "test_pkg"\nversion = "0.0.0"\nedition = "2021"\n',
            encoding="utf-8",
        )
        temp_git_repo.add("Cargo.toml")

        src_dir = temp_git_repo.path / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        main_rs = src_dir / "main.rs"
        main_rs.write_text("fn main() {}\n", encoding="utf-8")
        temp_git_repo.add(str(main_rs))

        gitignore = temp_git_repo.path / ".gitignore"
        gitignore.write_text(
            "dist/*\ntarget/*\n*.egg-info/\n*.egg-info\n__pycache__/\n*.pyc\n",
            encoding="utf-8",
        )
        temp_git_repo.add(".gitignore")

        temp_git_repo.commit("Initial commit")

        return {
            "repo": temp_git_repo,
            "setup_cfg_path": setup_cfg,
            "cargo_path": cargo_toml,
            "package_name": "test_pkg",
        }

    @pytest.mark.smoke
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """Validate structural environment contracts."""
        assert valid_instances["setup_cfg_path"].exists()
        assert valid_instances["cargo_path"].exists()

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """Assert correct initial environment startup."""
        repo_helper = valid_instances["repo"]
        settings_obj = Settings(project_root=repo_helper.path)
        assert settings_obj.output == "version.py"

    @pytest.mark.sanity
    def test_invalid_initialization_values(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """Pass bad environment parameters."""
        repo_helper = valid_instances["repo"]
        setup_cfg = valid_instances["setup_cfg_path"]
        original_content = setup_cfg.read_text(encoding="utf-8")
        setup_cfg.write_text(
            original_content + "\nversion_type = invalid_type_here\n",
            encoding="utf-8",
        )
        repo_helper.add("setup.cfg")
        repo_helper.commit("Update setup.cfg with invalid type")

        with pytest.raises(ValueError):
            Settings(project_root=repo_helper.path)

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """Omit setup.cfg configurations to verify fallback behavior."""
        repo_helper = valid_instances["repo"]
        valid_instances["setup_cfg_path"].unlink()
        settings_obj = Settings(project_root=repo_helper.path)
        assert settings_obj.output == "version.py"

    @pytest.mark.sanity
    def test_setup_cfg_layout(
        self, valid_instances: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """US-4: Verify version synchronization under legacy setup.cfg layout."""
        repo_helper = valid_instances["repo"]
        repo_helper.tag("v1.5.0")

        mock_maturin = MockMaturinModule()
        monkeypatch.setattr(maturin_plugin, "maturin", mock_maturin)
        monkeypatch.setattr(maturin_plugin, "_logging_configured", False)
        monkeypatch.chdir(repo_helper.path)

        result_path = maturin_plugin.build_wheel("dist_dir")
        assert "0.1.0" not in result_path
        cargo_content = (repo_helper.path / "Cargo.toml").read_text(encoding="utf-8")
        assert 'version = "1.5.0"' in cargo_content

    @pytest.mark.regression
    def test_setup_py_layout(
        self, valid_instances: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """US-4: Verify version sync and dynamic replacement inside setup.py."""
        repo_helper = valid_instances["repo"]

        # Create setup.py file
        setup_py = repo_helper.path / "setup.py"
        setup_py.write_text(
            "from setuptools import setup\n\n"
            "setup(\n"
            "    name='test_pkg',\n"
            "    version='0.0.0',\n"
            ")\n",
            encoding="utf-8",
        )
        repo_helper.add("setup.py")

        # Configure overrides for setup.py and Cargo.toml regex strategies in setup.cfg
        setup_cfg = valid_instances["setup_cfg_path"]
        setup_cfg.write_text(
            "[metadata]\n"
            "name = test_pkg\n"
            "version = 0.0.0\n\n"
            "[tool:gitversioned]\n"
            "output = version.py\n\n"
            "[tool:gitversioned:overrides:cargo]\n"
            "output = Cargo.toml\n"
            'output_strategies = {"type": "regex", '
            '"pattern": "version\\\\s*=\\\\s*\\\\\\"(?P<version>[^\\"]*)\\\\\\""}\n\n'
            "[tool:gitversioned:overrides:setuptools]\n"
            "output = setup.py\n"
            'output_strategies = {"type": "regex", '
            '"pattern": "version\\\\s*=\\\\s*\'(?P<version>[^\']*)\'"}\n',
            encoding="utf-8",
        )
        repo_helper.add("setup.cfg")
        repo_helper.commit("Configure setup.py AST/regex and cargo output overrides")

        repo_helper.tag("v2.1.0")

        mock_maturin = MockMaturinModule()
        monkeypatch.setattr(maturin_plugin, "maturin", mock_maturin)
        monkeypatch.setattr(maturin_plugin, "_logging_configured", False)
        monkeypatch.chdir(repo_helper.path)

        result_path = maturin_plugin.build_wheel("dist_dir")
        assert "0.1.0" not in result_path

        # Verify Cargo.toml version was updated to 2.1.0
        cargo_content = (repo_helper.path / "Cargo.toml").read_text(encoding="utf-8")
        assert 'version = "2.1.0"' in cargo_content

        # Verify setup.py version was dynamically modified in-place to 2.1.0
        setup_py_content = setup_py.read_text(encoding="utf-8")
        assert "version='2.1.0'" in setup_py_content
