from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from gitversioned.logging import LoggingSettings
from tests.conftest import GitRepoHelper


def run_python_snippet(
    snippet: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """
    Helper function to run a python snippet in a clean subprocess.

    :param snippet: The python code string to run.
    :param env: Optional environment overrides.
    :returns: CompletedProcess instance.
    """
    run_env = os.environ.copy()
    # Clean up any inherited GITVERSIONED environment variables to prevent pollution
    for key in list(run_env.keys()):
        if key.startswith("GITVERSIONED__"):
            run_env.pop(key)
    # Ensure standard paths and virtual environment python are preferred
    venv_bin = str(Path(sys.executable).parent)
    run_env["PATH"] = os.pathsep.join([venv_bin, run_env.get("PATH", "")])
    run_env["PYTHONPATH"] = str(Path(__file__).parent.parent.parent / "src")
    if env:
        run_env.update(env)
    return subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True,
        text=True,
        env=run_env,
        check=False,
    )


def run_build(
    cwd_path: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """
    Helper function to run the build command in a clean subprocess.

    :param cwd_path: Directory path to run build in.
    :param env: Optional environment overrides.
    :returns: CompletedProcess instance.
    """
    build_env = os.environ.copy()
    build_env.pop("HATCH_ENV", None)
    build_env.pop("HATCH_ENV_ACTIVE", None)
    # Clean up any inherited GITVERSIONED environment variables to prevent pollution
    for key in list(build_env.keys()):
        if key.startswith("GITVERSIONED__"):
            build_env.pop(key)
    venv_bin = str(Path(sys.executable).parent)
    build_env["PATH"] = os.pathsep.join([venv_bin, build_env.get("PATH", "")])
    build_env["PYTHONPATH"] = str(Path(__file__).parent.parent.parent / "src")
    build_env["PIP_NO_CACHE_DIR"] = "1"
    build_env["PIP_BREAK_SYSTEM_PACKAGES"] = "1"
    if env:
        build_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "build", "--no-isolation"],
        cwd=cwd_path,
        capture_output=True,
        text=True,
        env=build_env,
        check=False,
    )


def clean_dist(repo_path: Path) -> None:
    """
    Ensure build and dist directories are clean.

    :param repo_path: The project root path.
    """
    import shutil

    dist_dir = repo_path / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    build_dir = repo_path / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)


class TestLibraryImportLogging:
    """E2E Test Class for US-LOG-01: Imported and Used as a Library."""

    @pytest.fixture
    def valid_instances(self) -> dict[str, Any]:
        """
        Shared context fixture supplying library settings information.

        :returns: Context dictionary.
        """
        return {
            "default_level": "WARNING",
            "default_enabled": False,
        }

    @pytest.mark.smoke
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """
        Validate structural environment contracts before firing user actions.

        :param valid_instances: Injected shared context fixture.
        """
        # Verify package can be imported in a clean python shell
        snippet = "import gitversioned; print('OK')"
        result = run_python_snippet(snippet)
        assert result.returncode == 0
        assert result.stdout.strip() == "OK"

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert correct initial system wiring and session environment startup.

        Verify importing gitversioned does not call logger.add() or add stdlib handlers.

        :param valid_instances: Injected shared context fixture.
        """
        snippet = """
import logging
from loguru import logger
initial_loguru_handlers = list(logger._core.handlers.keys())
initial_stdlib_handlers = list(logging.getLogger().handlers)

import gitversioned

assert list(logger._core.handlers.keys()) == initial_loguru_handlers
assert list(logging.getLogger().handlers) == initial_stdlib_handlers
print("OK")
        """
        result = run_python_snippet(snippet)
        assert result.returncode == 0
        assert result.stdout.strip() == "OK"

    @pytest.mark.sanity
    def test_invalid_initialization_values(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Pass bad environment parameters to verify explicit system blockages.

        :param valid_instances: Injected shared context fixture.
        """
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            LoggingSettings(otel_formatting="invalid_option")  # type: ignore

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self, valid_instances: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Omit critical configurations to verify system boundary defense lines.

        :param valid_instances: Injected shared context fixture.
        :param monkeypatch: pytest monkeypatch fixture.
        """
        # Ensure default values load cleanly when configurations are missing
        monkeypatch.delenv("GITVERSIONED__LOGGING__LEVEL", raising=False)
        monkeypatch.delenv("GITVERSIONED__LOGGING__ENABLED", raising=False)
        settings = LoggingSettings()
        assert settings.enabled is valid_instances["default_enabled"]
        assert settings.level == valid_instances["default_level"]
        assert settings.clear_loggers is False

    @pytest.mark.smoke
    def test_library_silent_default(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert that gitversioned logs perform as silent no-ops by default (AC 1.2).

        :param valid_instances: Injected shared context fixture.
        """
        snippet = """
import sys
import types
dummy = types.ModuleType("gitversioned.dummy")
sys.modules["gitversioned.dummy"] = dummy

code = \"\"\"
from gitversioned.logging import logger
logger.debug("test debug statement")
logger.info("test info statement")
logger.warning("test warning statement")
\"\"\"
exec(code, dummy.__dict__)
print("DONE")
        """
        result = run_python_snippet(snippet)
        assert result.returncode == 0
        assert result.stdout.strip() == "DONE"
        assert result.stderr.strip() == ""

    @pytest.mark.sanity
    def test_library_explicit_enable(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert that logger.enable("gitversioned") activates logs cleanly (AC 1.3).

        :param valid_instances: Injected shared context fixture.
        """
        snippet = """
import sys
import types
from loguru import logger
from gitversioned.logging import configure_logger, LoggingSettings

parent_captured = []
gitversioned_captured = []

# Configure parent logger
logger.add(parent_captured.append, format="{message}", level="DEBUG")
logger.info("parent logger message")

# Configure gitversioned logger
configure_logger(LoggingSettings(enabled=True, sink=gitversioned_captured.append, format="{message}", otel_formatting="disable", enqueue=False))

# Create dummy module under gitversioned namespace
dummy = types.ModuleType("gitversioned.dummy")
sys.modules["gitversioned.dummy"] = dummy

code = '''
from gitversioned.logging import logger
logger.warning("gitversioned warning message")
logger.debug("gitversioned debug message")
'''
exec(code, dummy.__dict__)

assert any("parent logger message" in msg for msg in parent_captured)
assert any("gitversioned warning message" in msg for msg in gitversioned_captured)
# Debug should not be captured because LoggingSettings default level is WARNING
assert not any("gitversioned debug message" in msg for msg in gitversioned_captured)
print("SUCCESS")
        """
        result = run_python_snippet(
            snippet, env={"GITVERSIONED__LOGGING__LEVEL": "WARNING"}
        )
        assert result.returncode == 0
        assert "SUCCESS" in result.stdout

    @pytest.mark.regression
    def test_marshalling(self, valid_instances: dict[str, Any]) -> None:
        """
        Verify Pydantic model serialization and validation boundaries.

        :param valid_instances: Injected shared context fixture.
        """
        settings = LoggingSettings(enabled=True, level="INFO")
        dumped = settings.model_dump()
        assert dumped["enabled"] is True
        assert dumped["level"] == "INFO"

        validated = LoggingSettings.model_validate(dumped)
        assert validated.enabled is True
        assert validated.level == "INFO"


class TestHatchlingPluginLogging:
    """E2E Test Class for US-LOG-02: Used as a Plugin for Hatchling."""

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """
        Shared context fixture supplying a project configured with Hatchling.

        :param temp_git_repo: Injected GitRepoHelper fixture.
        :returns: Context dictionary.
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

        temp_git_repo.commit("Initial commit")

        return {
            "repo": temp_git_repo,
            "pyproject_path": pyproject_toml,
            "package_name": "test_pkg",
        }

    @pytest.mark.smoke
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """
        Validate structural environment contracts.

        :param valid_instances: Injected shared context fixture.
        """
        valid_instances["repo"]
        pyproject_toml = valid_instances["pyproject_path"]
        assert pyproject_toml.exists()
        # Verify hatchling plugin is available and registerable
        snippet = """
from gitversioned.plugins.hatchling_plugin import GitVersionedVersionSource
print("OK")
        """
        result = run_python_snippet(snippet)
        assert result.returncode == 0
        assert result.stdout.strip() == "OK"

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert correct initial system wiring and session environment startup.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0

    @pytest.mark.sanity
    def test_invalid_initialization_values(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Pass bad environment parameters to verify explicit system blockages.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        clean_dist(repo_helper.path)
        # Pass invalid level config via environment
        env = {"GITVERSIONED__LOGGING__LEVEL": "INVALID_LEVEL"}
        result = run_build(repo_helper.path, env=env)
        # Should exit with non-zero due to Pydantic ValidationError on loading env settings
        assert result.returncode != 0

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Omit critical configurations to verify system boundary defense lines.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        clean_dist(repo_helper.path)
        # Run build with no logging settings in env (defaults used)
        env = {"GITVERSIONED__LOGGING__ENABLED": "false"}
        result = run_build(repo_helper.path, env=env)
        assert result.returncode == 0
        # No logs should be printed at all since logging is disabled
        assert "[gitversioned:hatch]" not in result.stderr

    @pytest.mark.smoke
    def test_hatch_stderr_routing_and_format(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Assert that Hatch logs route to stderr and match standard format (AC 2.1, 2.2).

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        clean_dist(repo_helper.path)
        result = run_build(repo_helper.path)
        assert result.returncode == 0
        # Logs should not pollute stdout
        assert "[gitversioned:hatch]" not in result.stdout
        # Logs must go to stderr and match the default hatch prefix
        assert "[gitversioned:hatch]" in result.stderr
        # Verify that only INFO level logs are printed by the plugin handler, and DEBUG is ignored
        plugin_lines = [
            line
            for line in result.stderr.splitlines()
            if "[gitversioned:hatch]" in line
        ]
        assert any("gitversioned computed version" in line for line in plugin_lines)
        assert not any("get_version_data called" in line for line in plugin_lines)

    @pytest.mark.sanity
    def test_hatch_verbose_downgrade(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert log level is downgraded to DEBUG when verbose is toggled (AC 2.3).

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        clean_dist(repo_helper.path)
        # Pass DEBUG level via environment variable to emulate verbose mode
        env = {"GITVERSIONED__LOGGING__LEVEL": "DEBUG"}
        result = run_build(repo_helper.path, env=env)
        assert result.returncode == 0
        # Stderr should capture DEBUG logs
        assert "get_version_data called" in result.stderr

    @pytest.mark.regression
    def test_hatch_protect_native_sinks(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert Hatchling plugin preserves existing sinks by enforcing clear_loggers=False (AC 2.4).

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        # Run in subprocess to ensure isolated loguru state
        snippet = f"""
from loguru import logger
parent_logs = []
logger.add(parent_logs.append)

from gitversioned.plugins.hatchling_plugin import GitVersionedVersionSource
source = GitVersionedVersionSource("{str(repo_helper.path)}", {{}})
source.get_version_data()

# Pre-existing loguru handlers should not be cleared, so parent_logs collects the plugin output
assert len(parent_logs) > 0
assert any("get_version_data called" in msg or "gitversioned computed version" in msg for msg in parent_logs)
print("SUCCESS")
        """

        result = run_python_snippet(snippet)
        assert result.returncode == 0
        assert "SUCCESS" in result.stdout


class TestSetuptoolsPluginLogging:
    """E2E Test Class for US-LOG-03: Used as a Plugin for Setuptools."""

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """
        Shared context fixture supplying a Setuptools package structure.

        :param temp_git_repo: Injected GitRepoHelper fixture.
        :returns: Context dictionary.
        """
        setup_py = temp_git_repo.path / "setup.py"
        setup_py.write_text(
            "from setuptools import setup\n"
            "setup(\n"
            "    name='test_pkg',\n"
            "    version='0.0.0',\n"
            "    setup_requires=['gitversioned'],\n"
            "    gitversioned={},\n"
            ")\n",
            encoding="utf-8",
        )
        temp_git_repo.add("setup.py")

        # Unlink the default pyproject.toml created by conftest helper
        pyproject_path = temp_git_repo.path / "pyproject.toml"
        if pyproject_path.exists():
            pyproject_path.unlink()

        temp_git_repo.commit("Initial commit")

        return {
            "repo": temp_git_repo,
            "setup_py_path": setup_py,
        }

    @pytest.mark.smoke
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """
        Validate structural environment contracts.

        :param valid_instances: Injected shared context fixture.
        """
        valid_instances["repo"]
        # Verify setuptools plugin finalizer can be imported
        snippet = """
from gitversioned.plugins.setuptools_plugin import finalize_distribution_options
print("OK")
        """
        result = run_python_snippet(snippet)
        assert result.returncode == 0
        assert result.stdout.strip() == "OK"

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert correct initial system wiring and session environment startup.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        clean_dist(repo_helper.path)
        # Execute setup.py sdist command to verify build completes without error
        result = subprocess.run(
            [sys.executable, "setup.py", "sdist"],
            cwd=repo_helper.path,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0

    @pytest.mark.sanity
    def test_invalid_initialization_values(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Pass bad environment parameters to verify explicit system blockages.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        clean_dist(repo_helper.path)
        env = {"GITVERSIONED__LOGGING__LEVEL": "BAD_LEVEL"}
        result = subprocess.run(
            [sys.executable, "setup.py", "sdist"],
            cwd=repo_helper.path,
            capture_output=True,
            text=True,
            env={**os.environ, **env},
            check=False,
        )
        assert result.returncode != 0

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Omit critical configurations to verify system boundary defense lines.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        clean_dist(repo_helper.path)
        env = {"GITVERSIONED__LOGGING__ENABLED": "false"}
        result = subprocess.run(
            [sys.executable, "setup.py", "sdist"],
            cwd=repo_helper.path,
            capture_output=True,
            text=True,
            env={**os.environ, **env},
            check=False,
        )
        assert result.returncode == 0
        assert "[gitversioned:setuptools]" not in result.stderr

    @pytest.mark.smoke
    def test_setuptools_root_interception(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Assert InterceptHandler injection and standard warning interception (AC 3.1, 3.2).

        :param valid_instances: Injected shared context fixture.
        """
        valid_instances["repo"]
        snippet = """
import logging
from loguru import logger
from gitversioned.plugins.setuptools_plugin import finalize_distribution_options
from setuptools import Distribution

captured = []
logger.add(captured.append, format="{message}")

dist = Distribution({"name": "test_pkg", "version": "0.0.0"})
finalize_distribution_options(dist)

# Verify handler injection
root_logger = logging.getLogger()
assert any(type(h).__name__ == "InterceptHandler" for h in root_logger.handlers)

# Emit standard library warning
logging.warning("standard library warning message")

# Should log to our captured loguru stream
assert any("standard library warning message" in msg for msg in captured)
print("SUCCESS")
        """
        result = run_python_snippet(snippet)
        assert result.returncode == 0
        assert "SUCCESS" in result.stdout

    @pytest.mark.sanity
    def test_setuptools_protect_sinks_and_format(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Assert clear_loggers=False preserves sinks and format matches tag layout (AC 3.3, 3.4).

        :param valid_instances: Injected shared context fixture.
        """
        valid_instances["repo"]
        snippet = """
from loguru import logger
from gitversioned.plugins.setuptools_plugin import finalize_distribution_options
from setuptools import Distribution

parent_logs = []
logger.add(parent_logs.append, format="{message}")

dist = Distribution({"name": "test_pkg", "version": "0.0.0"})
finalize_distribution_options(dist)

# Verification 1: Parent sinks preserved
assert len(parent_logs) > 0
assert any("Finalizing distribution options" in msg or "Resolving version sources" in msg for msg in parent_logs)
print("SUCCESS")
        """
        result = run_python_snippet(snippet)
        assert result.returncode == 0
        assert "SUCCESS" in result.stdout
        # Verification 2: Plain tag layout matches expected pattern in stderr output
        assert "[gitversioned:setuptools] INFO -" in result.stderr


class TestMaturinPluginLogging:
    """E2E Test Class for US-LOG-04: Used as a Build Entrypoint Wrapper Around Maturin."""

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """
        Shared context fixture supplying a Maturin package structure.

        :param temp_git_repo: Injected GitRepoHelper fixture.
        :returns: Context dictionary.
        """
        pyproject_toml = temp_git_repo.path / "pyproject.toml"
        pyproject_toml.write_text(
            "[build-system]\n"
            'requires = ["maturin>=1.0,<2.0", "gitversioned"]\n'
            'build-backend = "gitversioned.plugins.maturin_plugin"\n\n'
            "[project]\n"
            'name = "test_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.maturin]\n"
            'bindings = "pyo3"\n',
            encoding="utf-8",
        )
        cargo_toml = temp_git_repo.path / "Cargo.toml"
        cargo_toml.write_text(
            "[package]\n"
            'name = "test_pkg"\n'
            'version = "0.0.0"\n'
            'edition = "2021"\n\n'
            "[lib]\n"
            'name = "test_pkg"\n'
            'crate-type = ["cdylib"]\n',
            encoding="utf-8",
        )
        # Create empty src/lib.rs
        src_dir = temp_git_repo.path / "src"
        src_dir.mkdir(exist_ok=True)
        (src_dir / "lib.rs").write_text("", encoding="utf-8")

        temp_git_repo.add("pyproject.toml")
        temp_git_repo.add("Cargo.toml")
        temp_git_repo.add("src/lib.rs")
        temp_git_repo.commit("Initial commit")

        return {
            "repo": temp_git_repo,
            "pyproject_path": pyproject_toml,
            "cargo_path": cargo_toml,
        }

    @pytest.mark.smoke
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """
        Validate structural environment contracts.

        :param valid_instances: Injected shared context fixture.
        """
        # Verify maturin plugin can be loaded
        snippet = """
from gitversioned.plugins.maturin_plugin import build_wheel
print("OK")
        """
        result = run_python_snippet(snippet)
        assert result.returncode == 0
        assert result.stdout.strip() == "OK"

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert correct initial system wiring and session environment startup.

        Verify clear_loggers=True removes active handlers (AC 4.1).

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        snippet = """
import sys
import unittest.mock
from loguru import logger
parent_logs = []
parent_id = logger.add(parent_logs.append)

mock_maturin = unittest.mock.MagicMock()

with unittest.mock.patch("gitversioned.plugins.maturin_plugin.maturin", mock_maturin):
    from gitversioned.plugins.maturin_plugin import _get_maturin
    try:
        _get_maturin()
    except Exception:
        pass

# Verification: Since clear_loggers=True, the parent logger handler is removed
assert parent_id not in logger._core.handlers
print("SUCCESS")
        """
        # Run with project root directory context
        result = run_python_snippet(
            snippet, env={"GITVERSIONED__PROJECT_ROOT": str(repo_helper.path)}
        )
        assert result.returncode == 0
        assert "SUCCESS" in result.stdout

    @pytest.mark.sanity
    def test_invalid_initialization_values(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Pass bad environment parameters to verify explicit system blockages.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        env = {"GITVERSIONED__LOGGING__LEVEL": "BAD_LEVEL"}
        # Execute build to trigger maturin wrapper initialization
        result = run_build(repo_helper.path, env=env)
        assert result.returncode != 0

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Omit critical configurations to verify system boundary defense lines.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        # Delete pyproject.toml
        valid_instances["pyproject_path"].unlink()
        result = run_build(repo_helper.path)
        assert result.returncode != 0

    @pytest.mark.smoke
    def test_maturin_filter_disabled(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert filter=False is enforced to permit non-package logs (AC 4.2).

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        snippet = """
import sys
import unittest.mock
from loguru import logger

mock_maturin = unittest.mock.MagicMock()

with unittest.mock.patch("gitversioned.plugins.maturin_plugin.maturin", mock_maturin):
    from gitversioned.plugins.maturin_plugin import _get_maturin
    try:
        _get_maturin()
    except Exception:
        pass

# Log outside gitversioned namespace
logger.bind(name="other_module").warning("external log statement")
        """
        result = run_python_snippet(
            snippet, env={"GITVERSIONED__PROJECT_ROOT": str(repo_helper.path)}
        )
        # Since filter=False, the log should propagate and be printed to stderr
        assert "external log statement" in result.stderr

    @pytest.mark.sanity
    def test_maturin_queue_and_styling(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert thread-safe queueing and color styling layout (AC 4.3, 4.4).

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        snippet = """
import sys
import unittest.mock
from loguru import logger

mock_maturin = unittest.mock.MagicMock()

with unittest.mock.patch("gitversioned.plugins.maturin_plugin.maturin", mock_maturin):
    from gitversioned.plugins.maturin_plugin import _get_maturin
    try:
        _get_maturin()
    except Exception:
        pass

# Verification 1: Verify enqueue=True is active
handlers = list(logger._core.handlers.values())
assert any(h._enqueue for h in handlers)
# Emit warning and debug logs
logger.bind(name="gitversioned").warning("maturin test warning log")
logger.bind(name="gitversioned").debug("maturin test debug log")
import time
time.sleep(0.5)
print("SUCCESS")
        """
        result = run_python_snippet(
            snippet,
            env={
                "GITVERSIONED__PROJECT_ROOT": str(repo_helper.path),
                "GITVERSIONED__LOGGING__OTEL_FORMATTING": "disable",
            },
        )
        assert result.returncode == 0
        assert "SUCCESS" in result.stdout
        # Verification 2: Stderr prefix matching maturin prefix, warning is printed, debug is not
        assert "[gitversioned:maturin]" in result.stderr
        assert "maturin test warning log" in result.stderr
        assert "maturin test debug log" not in result.stderr


class TestDirectCLILogging:
    """E2E Test Class for US-LOG-05: Used Directly as a CLI or Python API Script."""

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """
        Shared context fixture supplying standard project settings.

        :param temp_git_repo: Injected GitRepoHelper fixture.
        :returns: Context dictionary.
        """
        temp_git_repo.commit("Initial commit")
        return {
            "repo": temp_git_repo,
        }

    @pytest.mark.smoke
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """
        Validate structural environment contracts.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        # Verify CLI help executes correctly
        result = subprocess.run(
            [sys.executable, "-m", "gitversioned", "calculate", "--help"],
            cwd=repo_helper.path,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "gitversioned" in result.stdout

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert correct initial system wiring and session environment startup.

        Verify CLI clear_loggers=True path (AC 5.1).

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        snippet = """
from loguru import logger
parent_logs = []
logger.add(parent_logs.append)

import gitversioned.__main__ as main_mod
with main_mod._cli_execution_context("calculate", {}):
    pass

# Verification: Since clear_loggers=True is default in execution context, the parent logger is removed
assert len(logger._core.handlers) == 1
print("SUCCESS")
        """
        result = run_python_snippet(
            snippet, env={"GITVERSIONED__PROJECT_ROOT": str(repo_helper.path)}
        )
        assert result.returncode == 0
        assert "SUCCESS" in result.stdout

    @pytest.mark.sanity
    def test_invalid_initialization_values(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Pass bad environment parameters to verify explicit system blockages.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        env = {"GITVERSIONED__LOGGING__LEVEL": "BAD_LEVEL"}
        result = subprocess.run(
            [sys.executable, "-m", "gitversioned", "calculate"],
            cwd=repo_helper.path,
            capture_output=True,
            text=True,
            env={**os.environ, **env},
            check=False,
        )
        assert result.returncode != 0

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Omit critical configurations to verify system boundary defense lines.

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        env = {"GITVERSIONED__LOGGING__ENABLED": "false"}
        # Clean up any inherited GITVERSIONED environment variables to prevent pollution
        run_env = {**os.environ}
        for key in list(run_env.keys()):
            if key.startswith("GITVERSIONED__"):
                run_env.pop(key)
        run_env.update(env)

        result = subprocess.run(
            [sys.executable, "-m", "gitversioned", "calculate"],
            cwd=repo_helper.path,
            capture_output=True,
            text=True,
            env=run_env,
            check=False,
        )
        # Calculates version successfully
        assert result.returncode == 0
        version_str = result.stdout.strip()
        assert version_str != ""
        from packaging.version import Version

        # This will raise an InvalidVersion exception if not a valid PEP 440 version
        Version(version_str)

    @pytest.mark.smoke
    def test_cli_default_log_stream(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert stderr output stream and dynamic debug level toggling (AC 5.2).

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        # Clean up any inherited GITVERSIONED environment variables to prevent pollution
        run_env_base = {**os.environ}
        for key in list(run_env_base.keys()):
            if key.startswith("GITVERSIONED__"):
                run_env_base.pop(key)

        # Scenario 1: Default logs (level INFO or level auto) -> prints INFO but not DEBUG
        env_info = {
            "GITVERSIONED__LOGGING__ENABLED": "true",
            "GITVERSIONED__LOGGING__LEVEL": "INFO",
        }
        res_info = subprocess.run(
            [sys.executable, "-m", "gitversioned", "calculate"],
            cwd=repo_helper.path,
            capture_output=True,
            text=True,
            env={**run_env_base, **env_info},
            check=False,
        )
        assert res_info.returncode == 0
        assert "INFO" in res_info.stderr
        assert "DEBUG" not in res_info.stderr

        # Scenario 2: Downgraded log level to DEBUG via config pathway
        env_debug = {
            "GITVERSIONED__LOGGING__ENABLED": "true",
            "GITVERSIONED__LOGGING__LEVEL": "DEBUG",
        }
        res_debug = subprocess.run(
            [sys.executable, "-m", "gitversioned", "calculate"],
            cwd=repo_helper.path,
            capture_output=True,
            text=True,
            env={**run_env_base, **env_debug},
            check=False,
        )
        assert res_debug.returncode == 0
        assert "DEBUG" in res_debug.stderr

    @pytest.mark.regression
    def test_cli_otel_json_formatting(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert OTel formatting generates single-line JSON log structures (AC 5.3).

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        # Run CLI calculate in Otel format. Mock trace presence.
        snippet = """
import sys
import types
dummy = types.ModuleType("gitversioned.dummy")
sys.modules["gitversioned.dummy"] = dummy

class MockContext:
    is_valid = True
    trace_id = 11111111111111111111111111111111
    span_id = 2222222222222222
    trace_flags = 1

class MockSpan:
    def get_span_context(self) -> MockContext:
        return MockContext()

class MockTrace:
    def get_current_span(self) -> MockSpan:
        return MockSpan()

import sys
import unittest.mock
mock_trace = MockTrace()

with unittest.mock.patch("gitversioned.logging.opentelemetry_trace", mock_trace):
    import gitversioned.__main__ as main_mod
    with main_mod._cli_execution_context("calculate", {}):
        code = "from gitversioned.logging import logger; logger.info('OTel test message payload')"
        exec(code, dummy.__dict__)
        """
        result = run_python_snippet(
            snippet,
            env={
                "GITVERSIONED__PROJECT_ROOT": str(repo_helper.path),
                "GITVERSIONED__LOGGING__LEVEL": "INFO",
                "GITVERSIONED__LOGGING__OTEL_FORMATTING": "enable",
                "GITVERSIONED__LOGGING__ENQUEUE": "false",
            },
        )
        assert result.returncode == 0
        # Stderr must contain OTel compliant JSON matching attributes
        log_lines = result.stderr.strip().splitlines()
        otel_line = [line for line in log_lines if "OTel test message payload" in line]
        assert len(otel_line) == 1
        data = json.loads(otel_line[0])
        assert data["severity_text"] == "INFO"
        assert data["body"] == "OTel test message payload"
        assert data["trace_id"] == format(11111111111111111111111111111111, "032x")
        assert data["span_id"] == format(2222222222222222, "016x")
        assert "process_id" in data["attributes"]

    @pytest.mark.regression
    def test_cli_multi_line_exception_handling(
        self, valid_instances: dict[str, Any]
    ) -> None:
        """
        Assert that multi-line exceptions are correctly escaped in JSON structures (AC 5.4).

        :param valid_instances: Injected shared context fixture.
        """
        repo_helper = valid_instances["repo"]
        snippet = """
import sys
import types
dummy = types.ModuleType("gitversioned.dummy")
sys.modules["gitversioned.dummy"] = dummy

class MockContext:
    is_valid = True
    trace_id = 99999999999999999999999999999999
    span_id = 8888888888888888
    trace_flags = 1

class MockSpan:
    def get_span_context(self) -> MockContext:
        return MockContext()

class MockTrace:
    def get_current_span(self) -> MockSpan:
        return MockSpan()

import sys
import unittest.mock
mock_trace = MockTrace()

with unittest.mock.patch("gitversioned.logging.opentelemetry_trace", mock_trace):
    import gitversioned.__main__ as main_mod
    with main_mod._cli_execution_context("calculate", {}):
        code = \"\"\"
from gitversioned.logging import logger
try:
    raise ValueError("multi\\\\nline\\\\nexception")
except ValueError as err:
    logger.opt(exception=err).error("Failed calculating version")
\"\"\"
        exec(code, dummy.__dict__)
        """
        result = run_python_snippet(
            snippet,
            env={
                "GITVERSIONED__PROJECT_ROOT": str(repo_helper.path),
                "GITVERSIONED__LOGGING__LEVEL": "ERROR",
                "GITVERSIONED__LOGGING__OTEL_FORMATTING": "enable",
                "GITVERSIONED__LOGGING__ENQUEUE": "false",
            },
        )
        assert result.returncode == 0
        log_lines = result.stderr.strip().splitlines()
        err_line = [line for line in log_lines if "Failed calculating version" in line]
        assert len(err_line) == 1
        # Parse JSON and ensure it succeeded (JSON text integrity maintained, not split into multiple lines)
        data = json.loads(err_line[0])
        assert data["body"] == "Failed calculating version"
        assert data["attributes"]["exception.type"] == "ValueError"
        assert "multi\nline\nexception" in data["attributes"]["exception.message"]
        # Stack trace should be present and contain standard traceback details
        assert "traceback" in data["attributes"]["exception.stacktrace"].lower()
