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
Automated regression test verifying Hatchling integration with Dockerfile overrides.
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

__all__ = ["TestHatchlingDockerOverridesExample"]


@pytest.mark.regression
class TestHatchlingDockerOverridesExample:
    """
    Regression tests validating that Hatchling correctly executes GitVersioned
    overrides to update both the package version and a local Dockerfile version.
    """

    def test_example_build_and_overrides(self, tmp_path: Path) -> None:
        """
        Build the package and assert that the version is written to both the
        python metadata and the Dockerfile.
        """
        example_dir = Path(__file__).parent.resolve()
        temp_dir = tmp_path / "hatchling_docker_overrides"
        temp_dir.mkdir()

        # Initialize git repo first
        repo = GitRepoHelper(temp_dir, init=True)

        # Copy files to temp directory
        shutil.copy2(example_dir / "pyproject.toml", temp_dir / "pyproject.toml")
        shutil.copy2(example_dir / "Dockerfile", temp_dir / "Dockerfile")
        shutil.copy2(example_dir / ".gitignore", temp_dir / ".gitignore")
        shutil.copy2(example_dir / "README.md", temp_dir / "README.md")
        shutil.copytree(example_dir / "src", temp_dir / "src", dirs_exist_ok=True)

        # Commit everything
        repo.add("pyproject.toml")
        repo.add("Dockerfile")
        repo.add(".gitignore")
        repo.add("README.md")
        repo.add("src/hatchling_docker_overrides/__init__.py")
        repo.add("src/hatchling_docker_overrides/main.py")
        repo.commit("Initial commit")

        # Tag the repository
        version_tag = "1.4.2"
        repo.tag(f"v{version_tag}")

        # Run Hatchling build
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
        assert len(wheels) == 1
        wheel_name = wheels[0].name
        assert version_tag in wheel_name

        # Assert version.py exists inside the wheel and has correct version
        with zipfile.ZipFile(wheels[0]) as zip_file:
            filenames = zip_file.namelist()
            version_file = "hatchling_docker_overrides/version.py"
            assert version_file in filenames
            content = zip_file.read(version_file).decode("utf-8")
            assert version_tag in content

        # Assert Dockerfile has been updated in-place by GitVersioned overrides
        dockerfile_content = (temp_dir / "Dockerfile").read_text(encoding="utf-8")
        expected_line = f'ARG VERSION="{version_tag}"'
        assert expected_line in dockerfile_content, (
            f"Expected {expected_line} in Dockerfile, but got:\n{dockerfile_content}"
        )
