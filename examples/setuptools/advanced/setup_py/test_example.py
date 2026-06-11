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
    project versioning when configured via legacy setup.py arguments.
    """

    def test_example_build_and_execution(self, tmp_path: Path) -> None:
        """
        Build the example package under a temporary git repo and verify
        correct version resolution and command-line execution.
        """
        example_dir = Path(__file__).parent.resolve()
        temp_dir = tmp_path / "setuptools_setup_py"
        temp_dir.mkdir()

        # Initialize git repo first
        repo = GitRepoHelper(temp_dir, init=True)

        # Delete default pyproject.toml created by GitRepoHelper
        # to test legacy setup.py
        pyproject_file = temp_dir / "pyproject.toml"
        if pyproject_file.exists():
            pyproject_file.unlink()

        # Copy files to temp directory
        shutil.copy2(example_dir / "setup.py", temp_dir / "setup.py")
        shutil.copy2(example_dir / ".gitignore", temp_dir / ".gitignore")
        shutil.copy2(example_dir / "README.md", temp_dir / "README.md")
        shutil.copytree(example_dir / "src", temp_dir / "src", dirs_exist_ok=True)

        # Commit everything
        repo.add("setup.py")
        repo.add(".gitignore")
        repo.add("README.md")
        repo.add("src/setuptools_setup_py/__init__.py")
        repo.add("src/setuptools_setup_py/main.py")
        repo.commit("Initial commit")

        # Tag the repository
        version_tag = "0.2.5"
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
        run_result = subprocess.run(
            [sys.executable, "-m", "setuptools_setup_py.main"],
            cwd=temp_dir / "src",
            capture_output=True,
            text=True,
            check=False,
        )
        expected_msg = f"Setuptools setup.py Example Version: {version_tag}"
        assert expected_msg in run_result.stdout
