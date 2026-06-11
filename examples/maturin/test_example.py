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
Automated regression test verifying the Maturin minimal example.
"""

from __future__ import annotations

import io
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

from gitversioned.plugins import maturin_plugin
from tests.conftest import GitRepoHelper

__all__ = ["TestMaturinExample"]


class MockMaturinModule:
    """Mock maturin module to capture hook invocations without Rust/Cargo."""

    def build_wheel(
        self,
        wheel_directory: str,
        config_settings: dict[str, Any] | None = None,
        metadata_directory: str | None = None,
    ) -> str:
        """
        Mock implementation of build_wheel.
        """
        _ = (wheel_directory, config_settings, metadata_directory)
        return "maturin_example-0.2.5-py3-none-any.whl"


def _setup_temp_repo(example_dir: Path, temp_dir: Path) -> GitRepoHelper:
    """Sets up a temporary git repository with the example files."""
    temp_dir.mkdir()
    repo = GitRepoHelper(temp_dir, init=True)

    # Copy files to temp directory
    shutil.copy2(example_dir / "pyproject.toml", temp_dir / "pyproject.toml")
    shutil.copy2(example_dir / "Cargo.toml", temp_dir / "Cargo.toml")
    shutil.copy2(example_dir / ".gitignore", temp_dir / ".gitignore")
    shutil.copy2(example_dir / "README.md", temp_dir / "README.md")
    shutil.copytree(example_dir / "src", temp_dir / "src", dirs_exist_ok=True)

    # Commit everything
    repo.add("pyproject.toml")
    repo.add("Cargo.toml")
    repo.add(".gitignore")
    repo.add("README.md")
    repo.add("src/lib.rs")
    repo.add("src/maturin_example/__init__.py")
    repo.add("src/maturin_example/main.py")
    repo.commit("Initial commit")
    return repo


@pytest.mark.regression
class TestMaturinExample:
    """
    Regression tests validating that Maturin dynamically resolves versioning,
    updating the Python version file during package builds.
    """

    def test_example_build_and_execution(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Build the example package under a temporary git repo, verify correct version
        resolution, and confirm execution.
        """
        example_dir = Path(__file__).parent.resolve()
        temp_dir = tmp_path / "maturin_example"

        repo = _setup_temp_repo(example_dir, temp_dir)

        # Tag the repository
        version_tag = "0.2.5"
        repo.tag(f"v{version_tag}")

        # Set up mock Maturin module to avoid invoking actual compiler
        mock_maturin = MockMaturinModule()
        monkeypatch.setattr(maturin_plugin, "maturin", mock_maturin)
        monkeypatch.setattr(maturin_plugin, "_logging_configured", False)
        monkeypatch.chdir(temp_dir)

        # Execute build hook directly
        result_wheel = maturin_plugin.build_wheel(str(temp_dir / "dist"))
        assert "maturin_example" in result_wheel

        # Assert that version.py exists and has the correct version
        version_py_path = temp_dir / "src" / "maturin_example" / "version.py"
        assert version_py_path.is_file(), "version.py was not created"
        version_py_content = version_py_path.read_text(encoding="utf-8")
        assert f'__version__ = "{version_tag}"' in version_py_content

        # Run the main package entrypoint from temp directory and assert version output
        for key in list(sys.modules.keys()):
            if "maturin_example" in key:
                sys.modules.pop(key)

        sys_path_save = list(sys.path)
        sys.path.insert(0, str(temp_dir / "src"))
        try:
            from maturin_example.main import run_example  # noqa: PLC0415

            stdout_capture = io.StringIO()
            monkeypatch.setattr(sys, "stdout", stdout_capture)

            run_example()

            output = stdout_capture.getvalue()
            expected_msg = f"Maturin Example Version: {version_tag}"
            assert expected_msg in output
        finally:
            sys.path = sys_path_save
