from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest

from gitversioned.settings import Settings, TemplatePathStrategy
from tests.conftest import GitRepoHelper


def run_build(cwd_path: Path) -> subprocess.CompletedProcess[str]:
    """
    Helper function to run the python setuptools build as a subprocess.

    :param cwd_path: Working directory to run the build in.
    :returns: CompletedProcess instance.
    """
    build_env = os.environ.copy()
    # Remove Hatch's tracking variables to avoid environment contamination
    build_env.pop("HATCH_ENV", None)
    build_env.pop("HATCH_ENV_ACTIVE", None)
    venv_bin = str(Path(sys.executable).parent)
    build_env["PATH"] = os.pathsep.join([venv_bin, build_env.get("PATH", "")])

    # Force pip/build to ignore cache and use local packages
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


def get_wheel_version(repo_path: Path) -> str:
    """
    Extract the version string from the generated wheel filename.

    :param repo_path: The project repository path containing dist/ directory.
    :returns: Extracted version string.
    """
    dist_dir = repo_path / "dist"
    wheels = list(dist_dir.glob("*.whl"))
    assert len(wheels) == 1, f"Expected exactly 1 wheel, found {len(wheels)}"
    wheel_name = wheels[0].name
    # Filename layout: {package_name}-{version}-py3-none-any.whl
    return wheel_name.split("-")[1]


def verify_wheel_contents(
    repo_path: Path, package_name: str, expected_version: str
) -> None:
    """
    Verify that the generated version.py is inside the built wheel
    with the correct content.

    :param repo_path: The project repository path.
    :param package_name: The package folder name.
    :param expected_version: The expected version string inside the file.
    """
    dist_dir = repo_path / "dist"
    wheels = list(dist_dir.glob("*.whl"))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as zip_file:
        file_list = zip_file.namelist()
        version_file = f"{package_name}/version.py"
        assert version_file in file_list, f"Expected {version_file} in wheel"
        file_content = zip_file.read(version_file).decode("utf-8")
        assert expected_version in file_content, (
            f"Expected version {expected_version} in version file content"
        )


class TestSetuptoolsPyprojectToml:
    """E2E Test Class for US-1.

    Setuptools + pyproject.toml Build Backend Resolution Matrix.
    """

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """
        Shared context fixture supplying a configured standard pyproject.toml project.

        :param temp_git_repo: Temporary Git repository fixture.
        :returns: Context dictionary.
        """
        pyproject_toml = temp_git_repo.path / "pyproject.toml"
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["setuptools>=61.0", "wheel", "gitversioned"]\n'
            'build-backend = "setuptools.build_meta"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.setuptools.packages.find]\n"
            'where = ["src"]\n\n'
            "[tool.gitversioned]\n"
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
            "dist/*\n*.egg-info/\n*.egg-info\n__pycache__/\n*.pyc\nbuild/\n",
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
        """
        Validate structural environment contracts.

        :param valid_instances: Shared context dictionary.
        """
        assert valid_instances["pyproject_path"].exists()
        assert (valid_instances["src_dir"] / "__init__.py").exists()

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert correct initial system wiring and session environment startup.

        :param valid_instances: Shared context dictionary.
        """
        repo_helper = valid_instances["repo"]
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "0.1.0"
        verify_wheel_contents(repo_helper.path, "test_pkg", "0.1.0")

    @pytest.mark.sanity
    def test_invalid_initialization_values(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Pass bad environment parameters to verify explicit system blockages.

        :param valid_instances: Shared context dictionary.
        """
        repo_helper = valid_instances["repo"]
        # Set an invalid version type in pyproject.toml
        pyproject_toml = valid_instances["pyproject_path"]
        original_content = pyproject_toml.read_text(encoding="utf-8")
        pyproject_toml.write_text(
            original_content + '\nversion_type = "invalid_type_here"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Update to invalid version type")
        result = run_build(repo_helper.path)
        assert (
            "ValidationError" in result.stderr or "DistutilsSetupError" in result.stderr
        )

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Omit critical configurations to verify system boundary defense.

        :param valid_instances: Shared context dictionary.
        """
        repo_helper = valid_instances["repo"]
        # Delete pyproject.toml entirely
        valid_instances["pyproject_path"].unlink()
        result = run_build(repo_helper.path)
        assert result.returncode != 0

    @pytest.mark.smoke
    def test_source_git_tags(self, valid_instances: dict[str, Any]) -> None:
        """
        US-1 / AC 1.2: Validate tag strategy resolves version string.

        :param valid_instances: Shared context dictionary.
        """
        repo_helper = valid_instances["repo"]

        # Explicitly configure tag source first
        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["setuptools>=61.0", "wheel", "gitversioned"]\n'
            'build-backend = "setuptools.build_meta"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.setuptools.packages.find]\n"
            'where = ["src"]\n\n'
            "[tool.gitversioned]\n"
            'source_type = ["tag"]\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure tag source")

        # Tag the clean commit
        repo_helper.tag("v2.4.1")

        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "2.4.1"
        verify_wheel_contents(repo_helper.path, "test_pkg", "2.4.1")

    @pytest.mark.sanity
    def test_source_git_branch(self, valid_instances: dict[str, Any]) -> None:
        """
        US-1 / AC 1.2: Validate branch strategy resolves version.

        :param valid_instances: Shared context dictionary.
        """
        repo_helper = valid_instances["repo"]

        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["setuptools>=61.0", "wheel", "gitversioned"]\n'
            'build-backend = "setuptools.build_meta"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.setuptools.packages.find]\n"
            'where = ["src"]\n\n'
            "[tool.gitversioned]\n"
            'source_type = ["branch"]\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure branch source")

        repo_helper.branch("v3.1.2")
        repo_helper.commit("Work on branch")

        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "3.1.2"

    @pytest.mark.regression
    def test_source_git_commits(self, valid_instances: dict[str, Any]) -> None:
        """
        US-1 / AC 1.2: Validate commit message strategy resolves version.

        :param valid_instances: Shared context dictionary.
        """
        repo_helper = valid_instances["repo"]

        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["setuptools>=61.0", "wheel", "gitversioned"]\n'
            'build-backend = "setuptools.build_meta"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.setuptools.packages.find]\n"
            'where = ["src"]\n\n'
            "[tool.gitversioned]\n"
            'source_type = ["commit"]\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure commit source")

        repo_helper.commit("Release v1.0.2")

        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "1.0.2"

    @pytest.mark.sanity
    def test_source_version_file(self, valid_instances: dict[str, Any]) -> None:
        """
        US-1 / AC 1.2: Validate version file strategy resolves version.

        :param valid_instances: Shared context dictionary.
        """
        repo_helper = valid_instances["repo"]

        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["setuptools>=61.0", "wheel", "gitversioned"]\n'
            'build-backend = "setuptools.build_meta"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.setuptools.packages.find]\n"
            'where = ["src"]\n\n'
            "[tool.gitversioned]\n"
            'source_type = ["file"]\n'
            'version_source_file = "VERSION.txt"\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")

        version_txt = repo_helper.path / "VERSION.txt"
        version_txt.write_text("version = 4.5.6", encoding="utf-8")
        repo_helper.add("VERSION.txt")
        repo_helper.commit("Configure version file and add VERSION.txt")

        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "4.5.6"

    @pytest.mark.regression
    def test_source_custom_function(self, valid_instances: dict[str, Any]) -> None:
        """
        US-1 / AC 1.2: Validate callable strategy resolves version from hook.

        :param valid_instances: Shared context dictionary.
        """
        repo_helper = valid_instances["repo"]

        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["setuptools>=61.0", "wheel", "gitversioned"]\n'
            'build-backend = "setuptools.build_meta"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.setuptools.packages.find]\n"
            'where = ["src"]\n\n'
            "[tool.gitversioned]\n"
            'source_type = ["function"]\n'
            'version_source_function = "custom_hook:get_my_version"\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")

        hook_code = (
            "from packaging.version import Version\n"
            "from gitversioned.utils import GitReference\n"
            "def get_my_version(settings, repo):\n"
            "    return Version('5.6.7'), repo.current_commit_or_fallback\n"
        )
        hook_file = repo_helper.path / "custom_hook.py"
        hook_file.write_text(hook_code, encoding="utf-8")
        repo_helper.add("custom_hook.py")
        repo_helper.commit("Configure custom hook function")

        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "5.6.7"

    @pytest.mark.regression
    def test_source_git_archive(self, valid_instances: dict[str, Any]) -> None:
        """
        US-1 / AC 1.2: Validate git archived state fallback parsing.

        :param valid_instances: Shared context dictionary.
        """
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
        (repo_helper.path / ".git_archival.txt").write_text(
            archive_content, encoding="utf-8"
        )
        # Remove git history folder
        repo_helper.remove_git_dir()

        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "9.9.9"

    @pytest.mark.regression
    def test_output_combinations(self, valid_instances: dict[str, Any]) -> None:
        """
        US-1 / AC 1.3: Validate output types & auto-increment combinations.

        :param valid_instances: Shared context dictionary.
        """
        repo_helper = valid_instances["repo"]

        pyproject_toml = valid_instances["pyproject_path"]
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["setuptools>=61.0", "wheel", "gitversioned"]\n'
            'build-backend = "setuptools.build_meta"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.setuptools.packages.find]\n"
            'where = ["src"]\n\n'
            "[tool.gitversioned]\n"
            'version_type = "pre"\n'
            'auto_increment = { pre = "patch" }\n'
            'output = "src/test_pkg/version.py"\n',
            encoding="utf-8",
        )
        repo_helper.add("pyproject.toml")
        repo_helper.commit("Configure pre version type")

        repo_helper.tag("v1.0.0")

        # Create uncommitted file to force a dirty state
        (repo_helper.path / "src" / "test_pkg" / "dirty_file.py").write_text(
            "dirty = True\n", encoding="utf-8"
        )

        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        # Expected bump: 1.0.0 -> 1.0.1aN
        assert "1.0.1a" in wheel_version

    @pytest.mark.regression
    def test_marshalling(self, valid_instances: dict[str, Any]) -> None:
        """
        US-1: Verify Pydantic settings model marshalling limits.

        :param valid_instances: Shared context dictionary.
        """
        settings_obj = Settings(
            package_name="test_pkg",
            version="auto",
            source_type=["tag"],
        )
        dumped_data = settings_obj.model_dump()
        assert isinstance(dumped_data, dict)
        assert dumped_data["package_name"] == "test_pkg"
        assert dumped_data["source_type"] == ["tag"]

        validated_settings = Settings.model_validate(dumped_data)
        assert validated_settings.package_name == "test_pkg"
        assert validated_settings.source_type == ["tag"]

    @pytest.mark.sanity
    def test_dynamic_registry(self, valid_instances: dict[str, Any]) -> None:
        """
        US-1: Verify all registry-based dynamic sources parse and execute.

        :param valid_instances: Shared context dictionary.
        """
        # TemplatePathStrategy registry validation
        strategy_obj = TemplatePathStrategy(path=Path("templates/release.py.template"))
        assert strategy_obj.type == "template_path"
        assert strategy_obj.path == Path("templates/release.py.template")


class TestSetuptoolsSetupCfg:
    """E2E Test Class for US-2.

    Setuptools + Legacy setup.cfg Declarative Metadata Lifecycle.
    """

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """
        Shared context fixture supplying setup.cfg files.

        :param temp_git_repo: Temporary Git repository fixture.
        :returns: Context dictionary.
        """
        # Unlink the default pyproject.toml created by conftest repo helper
        pyproject_path = temp_git_repo.path / "pyproject.toml"
        if pyproject_path.exists():
            pyproject_path.unlink()

        setup_py = temp_git_repo.path / "setup.py"
        setup_py.write_text(
            "from setuptools import setup\n\nsetup()\n", encoding="utf-8"
        )
        temp_git_repo.add("setup.py")

        setup_cfg = temp_git_repo.path / "setup.cfg"
        setup_cfg.write_text(
            "[metadata]\n"
            "name = test_pkg\n"
            "version = 0.0.0\n\n"
            "[options]\n"
            "packages = find:\n"
            "package_dir =\n"
            "    = src\n\n"
            "[options.packages.find]\n"
            "where = src\n\n"
            "[tool:gitversioned]\n"
            "output = src/test_pkg/version.py\n",
            encoding="utf-8",
        )
        temp_git_repo.add("setup.cfg")

        # Create source structure
        src_dir = temp_git_repo.path / "src" / "test_pkg"
        src_dir.mkdir(parents=True, exist_ok=True)
        init_file = src_dir / "__init__.py"
        init_file.write_text("from .version import __version__\n", encoding="utf-8")
        temp_git_repo.add(str(init_file))

        gitignore = temp_git_repo.path / ".gitignore"
        gitignore.write_text(
            "dist/*\n*.egg-info/\n*.egg-info\n__pycache__/\n*.pyc\nbuild/\n",
            encoding="utf-8",
        )
        temp_git_repo.add(".gitignore")

        temp_git_repo.commit("Initial commit")

        return {
            "repo": temp_git_repo,
            "setup_cfg_path": setup_cfg,
            "setup_py_path": setup_py,
            "src_dir": src_dir,
            "package_name": "test_pkg",
        }

    @pytest.mark.smoke
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """
        Validate presence of setup.cfg.

        :param valid_instances: Shared context dictionary.
        """
        assert valid_instances["setup_cfg_path"].exists()
        assert valid_instances["setup_py_path"].exists()

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert correct initial environment startup.

        :param valid_instances: Shared context dictionary.
        """
        repo_helper = valid_instances["repo"]
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "0.1.0"

    @pytest.mark.sanity
    def test_invalid_initialization_values(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Pass bad environment parameters to verify system blockages.

        :param valid_instances: Shared context dictionary.
        """
        repo_helper = valid_instances["repo"]
        setup_cfg = valid_instances["setup_cfg_path"]
        original_content = setup_cfg.read_text(encoding="utf-8")
        # Add invalid config parameter to tool:gitversioned
        setup_cfg.write_text(
            original_content + "\nversion_type = invalid_type_here\n",
            encoding="utf-8",
        )
        repo_helper.add("setup.cfg")
        repo_helper.commit("Update setup.cfg with invalid type")
        result = run_build(repo_helper.path)
        assert result.returncode != 0

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Omit critical configurations to verify system boundary defense.

        :param valid_instances: Shared context dictionary.
        """
        repo_helper = valid_instances["repo"]
        # Delete setup.cfg and setup.py so there's no build configuration left
        valid_instances["setup_cfg_path"].unlink()
        valid_instances["setup_py_path"].unlink()
        result = run_build(repo_helper.path)
        # Should fail because build configuration is missing
        assert result.returncode != 0

    @pytest.mark.smoke
    def test_setup_cfg_ini_injection(self, valid_instances: dict[str, Any]) -> None:
        """
        US-2 / AC 2.1: Verify in-memory metadata version injection.

        :param valid_instances: Shared context dictionary.
        """
        repo_helper = valid_instances["repo"]
        repo_helper.tag("v1.5.0")

        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "1.5.0"
        # setup.cfg file must remain unchanged
        setup_cfg_text = valid_instances["setup_cfg_path"].read_text(encoding="utf-8")
        assert "version = 0.0.0" in setup_cfg_text

    @pytest.mark.sanity
    def test_setup_cfg_input_matrix(self, valid_instances: dict[str, Any]) -> None:
        """
        US-2 / AC 2.2: Verify input pathways (tag, branch, commit, file).

        :param valid_instances: Shared context dictionary.
        """
        repo_helper = valid_instances["repo"]

        setup_cfg = valid_instances["setup_cfg_path"]
        setup_cfg.write_text(
            "[metadata]\n"
            "name = test_pkg\n"
            "version = 0.0.0\n\n"
            "[options]\n"
            "packages = find:\n"
            "package_dir =\n"
            "    = src\n\n"
            "[options.packages.find]\n"
            "where = src\n\n"
            "[tool:gitversioned]\n"
            "source_type = tag\n"
            "output = src/test_pkg/version.py\n",
            encoding="utf-8",
        )
        repo_helper.add("setup.cfg")
        repo_helper.commit("Configure setup.cfg tag source")

        repo_helper.tag("v2.2.0")

        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "2.2.0"

    @pytest.mark.regression
    def test_setup_cfg_conditional_bumps(self, valid_instances: dict[str, Any]) -> None:
        """
        US-2 / AC 2.3: Validate conditional segment bumping in setup.cfg context.

        :param valid_instances: Shared context dictionary.
        """
        repo_helper = valid_instances["repo"]

        setup_cfg = valid_instances["setup_cfg_path"]
        setup_cfg.write_text(
            "[metadata]\n"
            "name = test_pkg\n"
            "version = 0.0.0\n\n"
            "[options]\n"
            "packages = find:\n"
            "package_dir =\n"
            "    = src\n\n"
            "[options.packages.find]\n"
            "where = src\n\n"
            "[tool:gitversioned]\n"
            "version_type = pre\n"
            "output = src/test_pkg/version.py\n\n"
            "[tool:gitversioned:auto_increment]\n"
            "pre = patch\n",
            encoding="utf-8",
        )
        repo_helper.add("setup.cfg")
        repo_helper.commit("Configure setup.cfg pre version bump")

        repo_helper.tag("v1.0.0")

        # Create uncommitted file to force a dirty state
        (repo_helper.path / "src" / "test_pkg" / "dirty_file.py").write_text(
            "dirty = True\n", encoding="utf-8"
        )

        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert "1.0.1a" in wheel_version

    @pytest.mark.regression
    def test_marshalling(self, valid_instances: dict[str, Any]) -> None:
        """
        US-2: Verify Pydantic settings model marshalling limits.

        :param valid_instances: Shared context dictionary.
        """
        settings_obj = Settings(
            package_name="test_pkg",
            version="auto",
            source_type=["branch"],
        )
        dumped_data = settings_obj.model_dump()
        validated_settings = Settings.model_validate(dumped_data)
        assert validated_settings.package_name == "test_pkg"
        assert validated_settings.source_type == ["branch"]

    @pytest.mark.sanity
    def test_dynamic_registry(self, valid_instances: dict[str, Any]) -> None:
        """
        US-2: Verify registry-based dynamic sources parse and execute.

        :param valid_instances: Shared context dictionary.
        """
        settings_obj = Settings(
            package_name="test_pkg",
            version="auto",
        )
        assert len(settings_obj.source_type) > 0


class TestSetuptoolsSetupPy:
    """E2E Test Class for US-3: Setuptools + Dynamic setup.py Script Interception."""

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """
        Shared context fixture supplying a project with setup.py.

        :param temp_git_repo: Temporary Git repository fixture.
        :returns: Context dictionary.
        """
        # Unlink the default pyproject.toml created by conftest repo helper
        pyproject_path = temp_git_repo.path / "pyproject.toml"
        if pyproject_path.exists():
            pyproject_path.unlink()

        setup_py = temp_git_repo.path / "setup.py"
        setup_py.write_text(
            "from setuptools import setup\n\n"
            "setup(\n"
            "    name='test_pkg',\n"
            "    packages=['test_pkg'],\n"
            "    package_dir={'': 'src'},\n"
            "    gitversioned={\n"
            "        'output': 'src/test_pkg/version.py',\n"
            "        'version': 'auto',\n"
            "    }\n"
            ")\n",
            encoding="utf-8",
        )
        temp_git_repo.add("setup.py")

        # Create package source structure
        src_dir = temp_git_repo.path / "src" / "test_pkg"
        src_dir.mkdir(parents=True, exist_ok=True)
        init_file = src_dir / "__init__.py"
        init_file.write_text("from .version import __version__\n", encoding="utf-8")
        temp_git_repo.add(str(init_file))

        gitignore = temp_git_repo.path / ".gitignore"
        gitignore.write_text(
            "dist/*\n*.egg-info/\n*.egg-info\n__pycache__/\n*.pyc\nbuild/\n",
            encoding="utf-8",
        )
        temp_git_repo.add(".gitignore")

        temp_git_repo.commit("Initial commit")

        return {
            "repo": temp_git_repo,
            "setup_py_path": setup_py,
            "src_dir": src_dir,
            "package_name": "test_pkg",
        }

    @pytest.mark.smoke
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """
        Validate legacy setup.py layout.

        :param valid_instances: Shared context dictionary.
        """
        assert valid_instances["setup_py_path"].exists()

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert correct initial setup.

        :param valid_instances: Shared context dictionary.
        """
        repo_helper = valid_instances["repo"]
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "0.1.0"

    @pytest.mark.sanity
    def test_invalid_initialization_values(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Assert bad parameters checks.

        :param valid_instances: Shared context dictionary.
        """
        repo_helper = valid_instances["repo"]
        setup_py = valid_instances["setup_py_path"]
        # Pass non-dict to gitversioned parameter in setup()
        setup_py.write_text(
            "from setuptools import setup\n\n"
            "setup(\n"
            "    name='test_pkg',\n"
            "    packages=['test_pkg'],\n"
            "    package_dir={'': 'src'},\n"
            "    gitversioned=['not_a_dict']\n"
            ")\n",
            encoding="utf-8",
        )
        repo_helper.add("setup.py")
        repo_helper.commit("Update setup.py with invalid type")
        result = run_build(repo_helper.path)
        assert result.returncode != 0
        assert "gitversioned must be a dict" in result.stderr

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Assert missing setup.py handling.

        :param valid_instances: Shared context dictionary.
        """
        repo_helper = valid_instances["repo"]
        valid_instances["setup_py_path"].unlink()
        result = run_build(repo_helper.path)
        assert result.returncode != 0

    @pytest.mark.smoke
    def test_setup_py_keyword_interception(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        US-3 / AC 3.1: Verify setup.py keyword interception.

        :param valid_instances: Shared context dictionary.
        """
        repo_helper = valid_instances["repo"]
        repo_helper.tag("v1.8.0")

        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        assert wheel_version == "1.8.0"

    @pytest.mark.sanity
    def test_setup_py_dynamic_stress(self, valid_instances: dict[str, Any]) -> None:
        """
        US-3 / AC 3.2: Verify dynamic matrix and targeted bumps.

        :param valid_instances: Shared context dictionary.
        """
        repo_helper = valid_instances["repo"]

        setup_py = valid_instances["setup_py_path"]
        setup_py.write_text(
            "from setuptools import setup\n\n"
            "setup(\n"
            "    name='test_pkg',\n"
            "    packages=['test_pkg'],\n"
            "    package_dir={'': 'src'},\n"
            "    gitversioned={\n"
            "        'output': 'src/test_pkg/version.py',\n"
            "        'version_type': 'post',\n"
            "        'auto_increment': None,\n"
            "    }\n"
            ")\n",
            encoding="utf-8",
        )
        repo_helper.add("setup.py")
        repo_helper.commit("Update setup.py post version bump")

        repo_helper.tag("v1.0.0")

        # Create uncommitted file to force a dirty state
        (repo_helper.path / "src" / "test_pkg" / "dirty_file.py").write_text(
            "dirty = True\n", encoding="utf-8"
        )

        result = run_build(repo_helper.path)
        assert result.returncode == 0
        wheel_version = get_wheel_version(repo_helper.path)
        # Expected post-release bump format (e.g. 1.0.0.postX)
        assert "1.0.0.post" in wheel_version

    @pytest.mark.regression
    def test_setup_py_guardrails_failure(self, valid_instances: dict[str, Any]) -> None:
        """
        US-3 / AC 3.3: Verify atomic rollback/exit and DistutilsSetupError on failures.

        :param valid_instances: Shared context dictionary.
        """
        repo_helper = valid_instances["repo"]
        setup_py = valid_instances["setup_py_path"]
        # Use an invalid function pointer to force resolution error
        setup_py.write_text(
            "from setuptools import setup\n\n"
            "setup(\n"
            "    name='test_pkg',\n"
            "    packages=['test_pkg'],\n"
            "    package_dir={'': 'src'},\n"
            "    gitversioned={\n"
            "        'source_type': ['function'],\n"
            "        'version_source_function': 'nonexistent_module:func',\n"
            "        'output': 'src/test_pkg/version.py',\n"
            "    }\n"
            ")\n",
            encoding="utf-8",
        )
        repo_helper.add("setup.py")
        repo_helper.commit("Update setup.py with failing function resolver")

        result = run_build(repo_helper.path)
        assert result.returncode != 0
        assert "Failed to resolve version" in result.stderr

    @pytest.mark.regression
    def test_marshalling(self, valid_instances: dict[str, Any]) -> None:
        """
        US-3: Verify Pydantic settings model marshalling limits.

        :param valid_instances: Shared context dictionary.
        """
        settings_obj = Settings(
            package_name="test_pkg",
            version="auto",
            source_type=["commit"],
        )
        dumped_data = settings_obj.model_dump()
        validated_settings = Settings.model_validate(dumped_data)
        assert validated_settings.package_name == "test_pkg"
        assert validated_settings.source_type == ["commit"]

    @pytest.mark.sanity
    def test_dynamic_registry(self, valid_instances: dict[str, Any]) -> None:
        """
        US-3: Verify registry-based dynamic sources parse and execute.

        :param valid_instances: Shared context dictionary.
        """
        settings_obj = Settings(
            package_name="test_pkg",
            version="auto",
        )
        assert len(settings_obj.source_type) > 0
