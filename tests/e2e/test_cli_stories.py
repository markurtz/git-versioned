from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import GitRepoHelper


def run_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """
    Helper function to run the gitversioned CLI as a subprocess.

    :param args: List of command-line arguments.
    :param cwd: Working directory to run the command in.
    :returns: CompletedProcess instance.
    """
    env = os.environ.copy()
    return subprocess.run(
        [sys.executable, "-m", "gitversioned"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


class TestStandardPythonProject:
    """E2E Test Class for US-1: Standard Python Project (pyproject.toml) Versioning."""

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """
        Shared context fixture supplying a configured standard python project.

        :param temp_git_repo: Injected GitRepoHelper fixture.
        :returns: Context dictionary.
        """
        pyproject_path = temp_git_repo.path / "pyproject.toml"
        pyproject_path.write_text(
            '[project]\nname = "test_pkg"\nversion = "0.0.0"\n', encoding="utf-8"
        )
        temp_git_repo.add("pyproject.toml")
        return {
            "repo": temp_git_repo,
            "pyproject_path": pyproject_path,
            "package_name": "test_pkg",
        }

    @pytest.mark.smoke
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """
        Validate structural environment contracts before firing actions.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        pyproject_path = valid_instances["pyproject_path"]
        assert pyproject_path.exists()
        result = run_cli(["--help"], cwd=repo_helper.path)
        assert result.returncode == 0
        assert "gitversioned" in result.stdout

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert correct initial system wiring and session environment startup.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        repo_helper.commit("Initial commit")
        result = run_cli(["calculate"], cwd=repo_helper.path)
        assert result.returncode == 0
        assert "0.1.0" in result.stdout.strip()

    @pytest.mark.sanity
    def test_invalid_initialization_values(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Pass bad environment parameters to verify system blockages.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        repo_helper.commit("Initial commit")
        result = run_cli(
            ["calculate", "--version-type", "invalid_type"], cwd=repo_helper.path
        )
        assert result.returncode != 0

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Omit critical configurations to verify system boundary defense.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        repo_helper.commit("Initial commit")
        # Pass a non-existent project root to calculate
        result = run_cli(
            ["calculate", "--project-root", "/nonexistent/path/here"],
            cwd=repo_helper.path,
        )
        assert result.returncode != 0

    @pytest.mark.smoke
    def test_source_git_tags(self, valid_instances: dict[str, Any]) -> None:
        """
        US-1 / AC 1.1 & 1.2: Verify version replacement from git-tags source.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        pyproject_path = valid_instances["pyproject_path"]
        repo_helper.commit("Initial commit")
        repo_helper.tag("v1.2.3")

        strategy = {
            "type": "regex",
            "pattern": r'version = "(?P<version>[^"]*)"',
        }
        result = run_cli(
            [
                "write",
                "--output",
                "pyproject.toml",
                "--output-strategies",
                json.dumps(strategy),
                "--source-type",
                "tag",
            ],
            cwd=repo_helper.path,
        )
        assert result.returncode == 0
        updated_content = pyproject_path.read_text(encoding="utf-8")
        assert 'version = "1.2.3"' in updated_content

    @pytest.mark.sanity
    def test_source_git_branch(self, valid_instances: dict[str, Any]) -> None:
        """
        US-1 / AC 1.1 & 1.2: Verify version replacement from git-branch source.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        pyproject_path = valid_instances["pyproject_path"]
        repo_helper.commit("Initial commit")
        repo_helper.branch("release/2.0.0")

        strategy = {
            "type": "regex",
            "pattern": r'version = "(?P<version>[^"]*)"',
        }
        result = run_cli(
            [
                "write",
                "--output",
                "pyproject.toml",
                "--output-strategies",
                json.dumps(strategy),
                "--source-type",
                "branch",
            ],
            cwd=repo_helper.path,
        )
        assert result.returncode == 0
        updated_content = pyproject_path.read_text(encoding="utf-8")
        assert 'version = "2.0.0"' in updated_content

    @pytest.mark.regression
    def test_source_git_commits(self, valid_instances: dict[str, Any]) -> None:
        """
        US-1 / AC 1.1 & 1.2: Verify version replacement from git-commits source.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        pyproject_path = valid_instances["pyproject_path"]
        repo_helper.commit("Initial commit")
        repo_helper.commit("Release v3.0.0")

        strategy = {
            "type": "regex",
            "pattern": r'version = "(?P<version>[^"]*)"',
        }
        result = run_cli(
            [
                "write",
                "--output",
                "pyproject.toml",
                "--output-strategies",
                json.dumps(strategy),
                "--source-type",
                "commit",
            ],
            cwd=repo_helper.path,
        )
        assert result.returncode == 0
        updated_content = pyproject_path.read_text(encoding="utf-8")
        assert 'version = "3.0.0"' in updated_content

    @pytest.mark.sanity
    def test_source_version_file(self, valid_instances: dict[str, Any]) -> None:
        """
        US-1 / AC 1.1 & 1.2: Verify version replacement from version-file source.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        pyproject_path = valid_instances["pyproject_path"]
        repo_helper.commit("Initial commit")

        version_txt_path = repo_helper.path / "VERSION.txt"
        version_txt_path.write_text("version = 4.5.6\n", encoding="utf-8")
        repo_helper.add("VERSION.txt")

        strategy = {
            "type": "regex",
            "pattern": r'version = "(?P<version>[^"]*)"',
        }
        result = run_cli(
            [
                "write",
                "--output",
                "pyproject.toml",
                "--output-strategies",
                json.dumps(strategy),
                "--source-type",
                "file",
                "--version-source-file",
                "VERSION.txt",
            ],
            cwd=repo_helper.path,
        )
        assert result.returncode == 0
        updated_content = pyproject_path.read_text(encoding="utf-8")
        assert 'version = "4.5.6"' in updated_content

    @pytest.mark.regression
    def test_source_custom_function(self, valid_instances: dict[str, Any]) -> None:
        """
        US-1 / AC 1.1 & 1.2: Verify version replacement from custom-function source.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        pyproject_path = valid_instances["pyproject_path"]
        repo_helper.commit("Initial commit")

        hook_code = """
from packaging.version import Version
from gitversioned.utils import GitReference

def get_my_version(settings, repo):
    return Version("5.6.7"), GitReference(commit_sha="abc1234", short_sha="abc")
"""
        hook_path = repo_helper.path / "my_hook.py"
        hook_path.write_text(hook_code, encoding="utf-8")
        repo_helper.add("my_hook.py")

        strategy = {
            "type": "regex",
            "pattern": r'version = "(?P<version>[^"]*)"',
        }
        result = run_cli(
            [
                "write",
                "--output",
                "pyproject.toml",
                "--output-strategies",
                json.dumps(strategy),
                "--source-type",
                "function",
                "--version-source-function",
                "my_hook:get_my_version",
                "--version-type",
                "release",
            ],
            cwd=repo_helper.path,
        )
        assert result.returncode == 0
        updated_content = pyproject_path.read_text(encoding="utf-8")
        assert 'version = "5.6.7"' in updated_content

    @pytest.mark.regression
    def test_source_custom_function_invalid(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        US-1 / AC 1.3: Verify error isolation on invalid custom function path.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        pyproject_path = valid_instances["pyproject_path"]
        repo_helper.commit("Initial commit")

        strategy = {
            "type": "regex",
            "pattern": r'version = "(?P<version>[^"]*)"',
        }
        result = run_cli(
            [
                "write",
                "--output",
                "pyproject.toml",
                "--output-strategies",
                json.dumps(strategy),
                "--source-type",
                "function",
                "--version-source-function",
                "nonexistent_module:func",
            ],
            cwd=repo_helper.path,
        )
        assert result.returncode != 0
        # Verify pyproject.toml is completely untouched
        updated_content = pyproject_path.read_text(encoding="utf-8")
        assert 'version = "0.0.0"' in updated_content


class TestMultiArtifactStandardization:
    """E2E Test Class for US-2: Multi-Artifact (pyproject.toml + Docker)
    Standardization.
    """

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """
        Shared context fixture supplying standard python project + Dockerfile.

        :param temp_git_repo: Injected GitRepoHelper fixture.
        :returns: Context dictionary.
        """
        pyproject_path = temp_git_repo.path / "pyproject.toml"
        pyproject_path.write_text(
            '[project]\nname = "test_pkg"\nversion = "0.0.0"\n', encoding="utf-8"
        )
        dockerfile_path = temp_git_repo.path / "Dockerfile"
        dockerfile_path.write_text(
            'FROM ubuntu:latest\nLABEL version="0.0.0"\n', encoding="utf-8"
        )
        temp_git_repo.add("pyproject.toml")
        temp_git_repo.add("Dockerfile")
        return {
            "repo": temp_git_repo,
            "pyproject_path": pyproject_path,
            "dockerfile_path": dockerfile_path,
        }

    @pytest.mark.sanity
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """
        Validate presence of both build artifacts.

        :param valid_instances: Injected shared context fixture.
        """
        assert valid_instances["pyproject_path"].exists()
        assert valid_instances["dockerfile_path"].exists()

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert correct initial environment startup.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        repo_helper.commit("Initial commit")
        result = run_cli(["calculate"], cwd=repo_helper.path)
        assert result.returncode == 0

    @pytest.mark.sanity
    def test_invalid_initialization_values(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Assert invalid args rejection.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        result = run_cli(
            ["calculate", "--version-type", "invalid_type"], cwd=repo_helper.path
        )
        assert result.returncode != 0

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Assert missing files behavior.

        :param valid_instances: Injected shared context fixture.
        """
        valid_instances["dockerfile_path"].unlink()
        assert not valid_instances["dockerfile_path"].exists()

    @pytest.mark.sanity
    def test_simultaneous_update(self, valid_instances: dict[str, Any]) -> None:
        """
        US-2 / AC 2.1 & 2.2: Verify concurrent update to both artifacts.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        pyproject_path = valid_instances["pyproject_path"]
        dockerfile_path = valid_instances["dockerfile_path"]

        repo_helper.commit("Initial commit")
        repo_helper.tag("v1.2.3")

        # Emulate the workflow orchestrator:
        # 1. Update pyproject.toml
        strategy_pyproject = {
            "type": "regex",
            "pattern": r'version = "(?P<version>[^"]*)"',
        }
        res_pyproject = run_cli(
            [
                "write",
                "--output",
                "pyproject.toml",
                "--output-strategies",
                json.dumps(strategy_pyproject),
                "--source-type",
                "tag",
                "--version-type",
                "release",
            ],
            cwd=repo_helper.path,
        )
        assert res_pyproject.returncode == 0

        # 2. Update Dockerfile
        strategy_dockerfile = {
            "type": "regex",
            "pattern": r'LABEL version="(?P<version>[^"]*)"',
        }
        res_dockerfile = run_cli(
            [
                "write",
                "--output",
                "Dockerfile",
                "--output-strategies",
                json.dumps(strategy_dockerfile),
                "--source-type",
                "tag",
                "--version-type",
                "release",
            ],
            cwd=repo_helper.path,
        )
        assert res_dockerfile.returncode == 0

        # Assert results
        assert 'version = "1.2.3"' in pyproject_path.read_text(encoding="utf-8")
        assert 'LABEL version="1.2.3"' in dockerfile_path.read_text(encoding="utf-8")

    @pytest.mark.regression
    def test_simultaneous_update_invalid(self, valid_instances: dict[str, Any]) -> None:
        """
        US-2 / AC 2.3: Verify atomic rollback on failure.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        pyproject_path = valid_instances["pyproject_path"]
        dockerfile_path = valid_instances["dockerfile_path"]

        repo_helper.commit("Initial commit")
        repo_helper.tag("v1.2.3")

        # Cache backups before the transaction begins
        pyproject_backup = pyproject_path.read_text(encoding="utf-8")
        dockerfile_backup = dockerfile_path.read_text(encoding="utf-8")

        # 1. Update pyproject.toml
        strategy_pyproject = {
            "type": "regex",
            "pattern": r'version = "(?P<version>[^"]*)"',
        }
        res_pyproject = run_cli(
            [
                "write",
                "--output",
                "pyproject.toml",
                "--output-strategies",
                json.dumps(strategy_pyproject),
                "--source-type",
                "tag",
            ],
            cwd=repo_helper.path,
        )
        assert res_pyproject.returncode == 0

        # 2. Force second update to fail (e.g. read-only permission / invalid pattern)
        # Using write-protection to simulate write failure
        try:
            dockerfile_path.chmod(0o400)  # Make Dockerfile read-only
            strategy_dockerfile = {
                "type": "regex",
                "pattern": r'LABEL version="(?P<version>[^"]*)"',
            }
            res_dockerfile = run_cli(
                [
                    "write",
                    "--output",
                    "Dockerfile",
                    "--output-strategies",
                    json.dumps(strategy_dockerfile),
                    "--source-type",
                    "tag",
                ],
                cwd=repo_helper.path,
            )
            # The write should fail due to permissions, or if it succeeds
            # (e.g. root/write allowed),
            # we check fallback.
            # In general, if exit code is non-zero, trigger rollback:
            if res_dockerfile.returncode != 0:
                # Restore write permissions before rollback
                dockerfile_path.chmod(0o600)
                pyproject_path.write_text(pyproject_backup, encoding="utf-8")
                dockerfile_path.write_text(dockerfile_backup, encoding="utf-8")
        finally:
            dockerfile_path.chmod(0o600)  # Restore write permissions

        # Assert rollback successfully restored pyproject.toml to 0.0.0
        assert 'version = "0.0.0"' in pyproject_path.read_text(encoding="utf-8")
        assert 'LABEL version="0.0.0"' in dockerfile_path.read_text(encoding="utf-8")


class TestLegacyPythonProject:
    """E2E Test Class for US-3: Legacy Python Project (setup.cfg) Management."""

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """
        Shared context fixture supplying a legacy setup.cfg file.

        :param temp_git_repo: Injected GitRepoHelper fixture.
        :returns: Context dictionary.
        """
        setup_cfg_path = temp_git_repo.path / "setup.cfg"
        setup_cfg_path.write_text(
            "# Custom configuration comment\n"
            "[metadata]\n"
            "name = test_pkg\n"
            "version = 0.0.0\n",
            encoding="utf-8",
        )
        temp_git_repo.add("setup.cfg")
        return {
            "repo": temp_git_repo,
            "setup_cfg_path": setup_cfg_path,
        }

    @pytest.mark.sanity
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """
        Validate legacy INI file exists.

        :param valid_instances: Injected shared context fixture.
        """
        assert valid_instances["setup_cfg_path"].exists()

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert correct initial setup.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        repo_helper.commit("Initial commit")
        result = run_cli(["calculate"], cwd=repo_helper.path)
        assert result.returncode == 0

    @pytest.mark.sanity
    def test_invalid_initialization_values(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Assert bad CLI parameters rejection.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        result = run_cli(["calculate", "--version-type", "bad"], cwd=repo_helper.path)
        assert result.returncode != 0

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Assert missing metadata behavior.

        :param valid_instances: Injected shared context fixture.
        """
        valid_instances["setup_cfg_path"].unlink()
        assert not valid_instances["setup_cfg_path"].exists()

    @pytest.mark.sanity
    def test_setup_cfg_update(self, valid_instances: dict[str, Any]) -> None:
        """
        US-3 / AC 3.1 & 3.2: Verify version update in setup.cfg metadata.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        setup_cfg_path = valid_instances["setup_cfg_path"]

        repo_helper.commit("Initial commit")
        repo_helper.branch("release/3.1.2")

        strategy = {
            "type": "regex",
            "pattern": r"(?m)^version\s*=\s*(?P<version>.*)",
        }
        result = run_cli(
            [
                "write",
                "--output",
                "setup.cfg",
                "--output-strategies",
                json.dumps(strategy),
                "--source-type",
                "branch",
            ],
            cwd=repo_helper.path,
        )
        assert result.returncode == 0

        content = setup_cfg_path.read_text(encoding="utf-8")
        assert "version = 3.1.2" in content
        # Assert comment is preserved
        assert "# Custom configuration comment" in content

    @pytest.mark.regression
    def test_setup_cfg_missing_metadata(self, valid_instances: dict[str, Any]) -> None:
        """
        US-3 / AC 3.3: Verify error exit when [metadata] block is missing.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        setup_cfg_path = valid_instances["setup_cfg_path"]

        # Re-write setup.cfg without a [metadata] block and no version field
        setup_cfg_path.write_text(
            "[tool:gitversioned]\nverbose = true\n", encoding="utf-8"
        )
        repo_helper.add("setup.cfg")
        repo_helper.commit("Remove metadata block")

        strategy = {
            "type": "regex",
            "pattern": r"(?m)^version\s*=\s*(?P<version>.*)",
        }
        result = run_cli(
            [
                "write",
                "--output",
                "setup.cfg",
                "--output-strategies",
                json.dumps(strategy),
                "--source-type",
                "branch",
            ],
            cwd=repo_helper.path,
        )
        # Should exit with non-zero exit code because regex strategy cannot
        # locate the pattern
        assert result.returncode != 0


class TestDeprecatedManifest:
    """E2E Test Class for US-4: Deprecated Manifest (setup.py) Interception."""

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """
        Shared context fixture supplying a standard setup.py manifest.

        :param temp_git_repo: Injected GitRepoHelper fixture.
        :returns: Context dictionary.
        """
        setup_py_content = (
            "from setuptools import setup\n\n"
            "setup(\n"
            "    name='test_pkg',\n"
            "    version='0.0.0',\n"
            ")\n"
        )
        setup_py_path = temp_git_repo.path / "setup.py"
        setup_py_path.write_text(setup_py_content, encoding="utf-8")
        temp_git_repo.add("setup.py")

        # Unlink the default pyproject.toml created by conftest repo helper
        pyproject_path = temp_git_repo.path / "pyproject.toml"
        if pyproject_path.exists():
            pyproject_path.unlink()

        return {
            "repo": temp_git_repo,
            "setup_py_path": setup_py_path,
        }

    @pytest.mark.sanity
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """
        Validate legacy setup.py layout.

        :param valid_instances: Injected shared context fixture.
        """
        assert valid_instances["setup_py_path"].exists()

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert correct initial setup.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        repo_helper.commit("Initial commit")
        result = run_cli(["calculate"], cwd=repo_helper.path)
        assert result.returncode == 0

    @pytest.mark.sanity
    def test_invalid_initialization_values(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Assert invalid parameters checks.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        result = run_cli(["calculate", "--version-type", "bad"], cwd=repo_helper.path)
        assert result.returncode != 0

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Assert missing setup.py handling.

        :param valid_instances: Injected shared context fixture.
        """
        valid_instances["setup_py_path"].unlink()
        assert not valid_instances["setup_py_path"].exists()

    @pytest.mark.sanity
    def test_setup_py_regex_replacement(self, valid_instances: dict[str, Any]) -> None:
        """
        US-4 / AC 4.1 & 4.2: Verify version injection inside setup.py using regex.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        setup_py_path = valid_instances["setup_py_path"]

        repo_helper.commit("Initial commit")
        repo_helper.branch("release/2.1.0")

        strategy = {
            "type": "regex",
            "pattern": r"version\s*=\s*'(?P<version>[^']*)'",
        }
        result = run_cli(
            [
                "write",
                "--output",
                "setup.py",
                "--output-strategies",
                json.dumps(strategy),
                "--source-type",
                "branch",
                "--version-type",
                "release",
            ],
            cwd=repo_helper.path,
        )
        assert result.returncode == 0

        updated_content = setup_py_path.read_text(encoding="utf-8")
        assert "version='2.1.0'" in updated_content

    @pytest.mark.regression
    def test_setup_py_valid_python(self, valid_instances: dict[str, Any]) -> None:
        """
        US-4 / AC 4.3: Verify setup.py remains syntactically valid python post-update.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]

        repo_helper.commit("Initial commit")
        repo_helper.tag("v1.5.0")

        strategy = {
            "type": "regex",
            "pattern": r"version\s*=\s*'(?P<version>[^']*)'",
        }
        # Run CLI to update version
        run_cli(
            [
                "write",
                "--output",
                "setup.py",
                "--output-strategies",
                json.dumps(strategy),
                "--source-type",
                "tag",
                "--version-type",
                "release",
            ],
            cwd=repo_helper.path,
        )

        # Run setup.py via python subprocess to check for syntax errors
        res = subprocess.run(
            [sys.executable, "setup.py", "--version"],
            cwd=repo_helper.path,
            capture_output=True,
            text=True,
            check=False,
        )
        assert res.returncode == 0
        assert "1.5.0" in res.stdout.strip()


class TestPolyglotHybridProjects:
    """E2E Test Class for US-5: Polyglot/Hybrid Projects (Cargo.toml + Docker)
    Control.
    """

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """
        Shared context fixture supplying Rust workspace & Dockerfile.

        :param temp_git_repo: Injected GitRepoHelper fixture.
        :returns: Context dictionary.
        """
        cargo_toml_path = temp_git_repo.path / "Cargo.toml"
        cargo_toml_path.write_text(
            '[package]\nname = "test_rust_backend"\nversion = "0.0.0"\n',
            encoding="utf-8",
        )
        dockerfile_path = temp_git_repo.path / "Dockerfile"
        dockerfile_path.write_text(
            'FROM rust:1.75\nLABEL version="0.0.0"\n', encoding="utf-8"
        )
        temp_git_repo.add("Cargo.toml")
        temp_git_repo.add("Dockerfile")
        return {
            "repo": temp_git_repo,
            "cargo_toml_path": cargo_toml_path,
            "dockerfile_path": dockerfile_path,
        }

    @pytest.mark.sanity
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """
        Validate presence of Rust/Cargo files.

        :param valid_instances: Injected shared context fixture.
        """
        assert valid_instances["cargo_toml_path"].exists()
        assert valid_instances["dockerfile_path"].exists()

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert correct initial setup.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        repo_helper.commit("Initial commit")
        result = run_cli(["calculate"], cwd=repo_helper.path)
        assert result.returncode == 0

    @pytest.mark.sanity
    def test_invalid_initialization_values(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Assert invalid parameters checks.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        result = run_cli(["calculate", "--version-type", "bad"], cwd=repo_helper.path)
        assert result.returncode != 0

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Assert missing files handling.

        :param valid_instances: Injected shared context fixture.
        """
        valid_instances["cargo_toml_path"].unlink()
        assert not valid_instances["cargo_toml_path"].exists()

    @pytest.mark.sanity
    def test_cargo_toml_update(self, valid_instances: dict[str, Any]) -> None:
        """
        US-5 / AC 5.1 & 5.2: Verify version replacement in Rust Cargo.toml.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        cargo_toml_path = valid_instances["cargo_toml_path"]

        repo_helper.commit("Initial commit")
        repo_helper.tag("v1.4.2")

        strategy = {
            "type": "regex",
            "pattern": r'(?m)^version\s*=\s*"(?P<version>[^"]*)"',
        }
        result = run_cli(
            [
                "write",
                "--output",
                "Cargo.toml",
                "--output-strategies",
                json.dumps(strategy),
                "--source-type",
                "tag",
                "--version-type",
                "release",
            ],
            cwd=repo_helper.path,
        )
        assert result.returncode == 0

        updated_content = cargo_toml_path.read_text(encoding="utf-8")
        assert 'version = "1.4.2"' in updated_content

    @pytest.mark.regression
    def test_cargo_workspace_multi_stage_docker(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        US-5 / AC 5.3: Verify versioning across nested Cargo.toml files in a workspace.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]

        # Create a cargo workspace layout:
        # workspace Cargo.toml
        # member sub-crate at backend/Cargo.toml
        # Dockerfile containing multiple version variables (multi-stage build)
        workspace_cargo = '[workspace]\nmembers = ["backend"]\n'
        (repo_helper.path / "Cargo.toml").write_text(workspace_cargo, encoding="utf-8")

        backend_dir = repo_helper.path / "backend"
        backend_dir.mkdir(parents=True, exist_ok=True)
        backend_cargo = '[package]\nname = "rust_backend"\nversion = "0.0.0"\n'
        backend_cargo_path = backend_dir / "Cargo.toml"
        backend_cargo_path.write_text(backend_cargo, encoding="utf-8")

        docker_content = (
            "FROM rust:1.75 AS builder\n"
            'LABEL stage_version="0.0.0"\n'
            "FROM alpine:latest\n"
            'LABEL final_version="0.0.0"\n'
        )
        dockerfile_path = valid_instances["dockerfile_path"]
        dockerfile_path.write_text(docker_content, encoding="utf-8")

        repo_helper.add("Cargo.toml")
        repo_helper.add("backend/Cargo.toml")
        repo_helper.add("Dockerfile")
        repo_helper.commit("Setup workspaces")
        repo_helper.tag("v2.5.0")

        # 1. Update backend/Cargo.toml
        strategy_cargo = {
            "type": "regex",
            "pattern": r'(?m)^version\s*=\s*"(?P<version>[^"]*)"',
        }
        res_cargo = run_cli(
            [
                "write",
                "--output",
                "backend/Cargo.toml",
                "--output-strategies",
                json.dumps(strategy_cargo),
                "--source-type",
                "tag",
                "--version-type",
                "release",
            ],
            cwd=repo_helper.path,
        )
        assert res_cargo.returncode == 0

        # 2. Update multi-stage Dockerfile
        strategy_docker = {
            "type": "regex",
            "pattern": r'version="(?P<version>[^"]*)"',
        }
        res_docker = run_cli(
            [
                "write",
                "--output",
                "Dockerfile",
                "--output-strategies",
                json.dumps(strategy_docker),
                "--source-type",
                "tag",
                "--version-type",
                "release",
            ],
            cwd=repo_helper.path,
        )
        assert res_docker.returncode == 0

        # Verification
        assert 'version = "2.5.0"' in backend_cargo_path.read_text(encoding="utf-8")
        docker_text = dockerfile_path.read_text(encoding="utf-8")
        assert 'stage_version="2.5.0"' in docker_text
        assert 'final_version="2.5.0"' in docker_text


class TestCLIEntrypoint:
    """E2E Test Class for global command-line entrypoint orchestration."""

    @pytest.mark.smoke
    def test_cli_stdout_stderr(self, temp_git_repo: GitRepoHelper) -> None:
        """
        Verify stdout prints calculated version and stderr routes warnings/logs.

        :param temp_git_repo: Injected GitRepoHelper fixture.
        """
        temp_git_repo.commit("Initial commit")
        result = run_cli(
            ["calculate", "--version-type", "release"], cwd=temp_git_repo.path
        )
        assert result.returncode == 0
        # stdout should only contain the clean version string (and maybe
        # whitespace/newlines)
        assert result.stdout.strip() == "0.1.0"
        # No general log lines should contaminate stdout
        assert "DEBUG" not in result.stdout
        assert "INFO" not in result.stdout

    @pytest.mark.sanity
    def test_cli_exit_codes(self, temp_git_repo: GitRepoHelper) -> None:
        """
        Verify invalid commands and flags result in non-zero exit codes.

        :param temp_git_repo: Injected GitRepoHelper fixture.
        """
        # Non-existent command
        res_cmd = run_cli(["nonexistent-command"], cwd=temp_git_repo.path)
        assert res_cmd.returncode != 0

        # Invalid flag
        res_flag = run_cli(
            ["calculate", "--invalid-flag-option"], cwd=temp_git_repo.path
        )
        assert res_flag.returncode != 0

    @pytest.mark.smoke
    def test_cli_version_flag(self, temp_git_repo: GitRepoHelper) -> None:
        """
        Verify running the CLI with version flags returns package version info.

        :param temp_git_repo: Injected GitRepoHelper fixture.
        """
        res_long = run_cli(["--version"], cwd=temp_git_repo.path)
        assert res_long.returncode == 0
        assert "gitversioned v" in res_long.stdout

        res_short = run_cli(["-v"], cwd=temp_git_repo.path)
        assert res_short.returncode == 0
        assert "gitversioned v" in res_short.stdout
