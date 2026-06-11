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
Automated regression test verifying the General webapp example.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import urllib.request
import zipfile
from http.server import HTTPServer
from pathlib import Path

import pytest

from tests.conftest import GitRepoHelper

__all__ = ["TestGeneralWebappExample"]


@pytest.mark.regression
class TestGeneralWebappExample:
    """
    Regression tests validating that a webapp dynamically resolves and serves
    versioning resolved by GitVersioned during CI/CD package build processes.
    """

    def test_example_build_and_service(self, tmp_path: Path) -> None:  # noqa: PLR0915
        """
        Build the example webapp, verify version output in wheel, launch
        the HTTPServer in a background thread, and query `/version`.
        """
        example_dir = Path(__file__).parent.resolve()
        temp_dir = tmp_path / "general_webapp"
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
        repo.add("src/webapp/__init__.py")
        repo.add("src/webapp/main.py")
        repo.commit("Initial commit")

        # Tag the repository
        version_tag = "0.9.8"
        repo.tag(f"v{version_tag}")

        # Run Hatchling build to generate wheel/version file
        build_env = os.environ.copy()
        build_env.pop("HATCH_ENV", None)
        build_env.pop("HATCH_ENV_ACTIVE", None)
        venv_bin = str(Path(sys.executable).parent)
        build_env["PATH"] = os.pathsep.join([venv_bin, build_env.get("PATH", "")])
        build_env["PIP_NO_CACHE_DIR"] = "1"
        build_env["PIP_BREAK_SYSTEM_PACKAGES"] = "1"

        # Execute build using current Python
        result = subprocess.run(
            [sys.executable, "-m", "build", "--no-isolation"],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            env=build_env,
            check=False,
        )

        assert result.returncode == 0, f"Build failed: {result.stdout}\n{result.stderr}"

        # Assert version is set inside wheel version.py
        dist_dir = temp_dir / "dist"
        wheels = list(dist_dir.glob("*.whl"))
        assert len(wheels) == 1
        with zipfile.ZipFile(wheels[0]) as zip_file:
            filenames = zip_file.namelist()
            version_file = "webapp/version.py"
            assert version_file in filenames
            content = zip_file.read(version_file).decode("utf-8")
            assert version_tag in content

        # Now test running the webapp server
        # We dynamic-import the version file we just wrote during build
        sys_path_save = list(sys.path)
        sys.path.insert(0, str(temp_dir / "src"))
        try:
            # Clear out modules to avoid cache
            for key in list(sys.modules.keys()):
                if "webapp" in key:
                    sys.modules.pop(key)

            from webapp.main import VersionHandler  # noqa: PLC0415

            # Setup ephemeral local server
            port = 19188
            httpd = HTTPServer(("", port), VersionHandler)

            # Start server in background thread
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()

            try:
                # Query localhost endpoint
                target_url = f"http://127.0.0.1:{port}/version"
                with urllib.request.urlopen(target_url) as response:  # noqa: S310
                    status_ok = 200
                    assert response.status == status_ok
                    response_bytes = response.read()
                    data = json.loads(response_bytes.decode("utf-8"))
                    assert data["version"] == version_tag
            finally:
                httpd.shutdown()
                thread.join()
        finally:
            sys.path = sys_path_save
