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
Automated regression test verifying Setuptools integration with custom configurations.
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

__all__ = ["TestSetuptoolsCustomConfigExample"]


@pytest.mark.regression
class TestSetuptoolsCustomConfigExample:
    """
    Regression tests validating that Setuptools correctly executes GitVersioned
    using custom overrides like format_main, format_dev, and auto_increment.
    """

    def test_example_build_and_custom_config(self, tmp_path: Path) -> None:
        """
        Build the package and assert that the version is resolved using
        the custom formats and auto-increment settings defined in pyproject.toml.
        """
        example_dir = Path(__file__).parent.resolve()
        temp_dir = tmp_path / "setuptools_custom_config"
        temp_dir.mkdir()

        # Initialize git repo first
        repo = GitRepoHelper(temp_dir, init=True)

        # Copy files to temp directory
        shutil.copy2(example_dir / "pyproject.toml", temp_dir / "pyproject.toml")
        shutil.copy2(example_dir / ".gitignore", temp_dir / ".gitignore")
        shutil.copy2(example_dir / "README.md", temp_dir / "README.md")
        shutil.copytree(example_dir / "src", temp_dir / "src", dirs_exist_ok=True)

        # Commit everything
        repo.add("pyproject.toml")
        repo.add(".gitignore")
        repo.add("README.md")
        repo.add("src/setuptools_custom_config/__init__.py")
        repo.add("src/setuptools_custom_config/main.py")
        repo.commit("Initial commit")

        # Tag the repository
        repo.tag("v1.2.3")

        # Make an extra commit to trigger the dev version auto-increment minor settings
        repo.commit("Another commit ahead of tag")

        # Run Setuptools build
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

        # Assert wheel has correct version (1.3.dev1)
        expected_version = "1.3.dev1"
        dist_dir = temp_dir / "dist"
        wheels = list(dist_dir.glob("*.whl"))
        assert len(wheels) == 1
        wheel_name = wheels[0].name
        assert expected_version in wheel_name, (
            f"Expected {expected_version} in wheel name: {wheel_name}"
        )

        # Assert version.py exists inside the wheel and has correct version
        with zipfile.ZipFile(wheels[0]) as zip_file:
            filenames = zip_file.namelist()
            version_file = "setuptools_custom_config/version.py"
            assert version_file in filenames
            content = zip_file.read(version_file).decode("utf-8")
            assert expected_version in content
