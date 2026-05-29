"""
Automated regression test verifying the Setuptools setup.py example.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from tests.conftest import GitRepoHelper

__all__ = ["TestSetuptoolsSetupPyExample"]


@pytest.mark.regression
class TestSetuptoolsSetupPyExample:
    """
    Regression tests validating that setuptools dynamically resolves
    project versioning when configured via a setup.py keyword argument.
    """

    def test_example_build_and_execution(self, tmp_path: Path) -> None:
        """
        Build the example package under a temporary git repo and verify
        correct version resolution and command-line execution.
        """
        # Determine the paths
        example_dir = Path(__file__).parent.resolve()
        temp_dir = tmp_path / "setuptools_setup_py"
        temp_dir.mkdir()

        # Initialize git repo first (creates dummy files that we will overwrite)
        repo = GitRepoHelper(temp_dir, init=True)

        # Copy files to temp directory
        shutil.copy2(example_dir / "setup.py", temp_dir / "setup.py")
        shutil.copy2(example_dir / "pyproject.toml", temp_dir / "pyproject.toml")
        shutil.copy2(example_dir / ".gitignore", temp_dir / ".gitignore")
        shutil.copytree(example_dir / "src", temp_dir / "src", dirs_exist_ok=True)

        # Commit everything
        repo.add("setup.py")
        repo.add("pyproject.toml")
        repo.add(".gitignore")
        repo.add("src/setuptools_setup_py/__init__.py")
        repo.add("src/setuptools_setup_py/main.py")
        repo.commit("Initial commit")

        # Tag the repository
        version_tag = "0.3.7"
        repo.tag(f"v{version_tag}")

        # Run setuptools build
        build_env = os.environ.copy()
        build_env.pop("HATCH_ENV", None)
        build_env.pop("HATCH_ENV_ACTIVE", None)
        venv_bin = str(Path(sys.executable).parent)
        build_env["PATH"] = os.pathsep.join([venv_bin, build_env.get("PATH", "")])
        build_env["PIP_NO_CACHE_DIR"] = "1"
        build_env["PIP_BREAK_SYSTEM_PACKAGES"] = "1"

        # Execute build using the current python executable
        result = subprocess.run(
            [sys.executable, "-m", "build", "--no-isolation"],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            env=build_env,
            check=False,
        )

        # Assert build succeeded
        assert result.returncode == 0, f"Build failed: {result.stdout}\n{result.stderr}"

        # Assert wheel has correct version in its filename
        dist_dir = temp_dir / "dist"
        wheels = list(dist_dir.glob("*.whl"))
        assert len(wheels) == 1, f"Expected 1 wheel, found {len(wheels)}"
        wheel_name = wheels[0].name
        assert version_tag in wheel_name, f"Expected {version_tag} in {wheel_name}"

        # Assert that version.py exists inside the wheel and has correct version
        with zipfile.ZipFile(wheels[0]) as zip_file:
            filenames = zip_file.namelist()
            version_file = "setuptools_setup_py/version.py"
            assert version_file in filenames
            content = zip_file.read(version_file).decode("utf-8")
            assert version_tag in content, f"Expected {version_tag} in {content}"

        # Assert entrypoint outputs the correct version when invoked
        # We run the main module from the src directory
        run_result = subprocess.run(
            [sys.executable, "-m", "setuptools_setup_py.main"],
            cwd=temp_dir / "src",
            capture_output=True,
            text=True,
            check=False,
        )
        assert run_result.returncode == 0
        expected_output = f"Setuptools Setup.py Example Version: {version_tag}"
        assert expected_output in run_result.stdout
