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
Automated validation tests for the GitVersioned CLI regex replacement example.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from examples.general.advanced.regex_replacement.main import (
    create_sandbox_repo,
    run_gitversioned_cli,
)

__all__ = ["TestCliRegexReplacement"]


@pytest.mark.regression
class TestCliRegexReplacement:
    """
    Test suite verifying the behavior of the CLI regex-based replacement example.
    """

    def test_example_execution(self, tmp_path: Path) -> None:
        """
        Simulate the example execution workflow in a temporary directory
        and verify that the files are correctly updated.

        :param tmp_path: Pytest temporary directory fixture.
        """
        sandbox_dir = tmp_path / "sandbox"
        create_sandbox_repo(sandbox_dir)

        pyproject_file = sandbox_dir / "pyproject.toml"
        init_file = sandbox_dir / "src" / "my_app" / "__init__.py"

        # Verify initial states
        assert pyproject_file.exists()
        assert init_file.exists()
        assert 'version = "0.0.0"' in pyproject_file.read_text(encoding="utf-8")
        assert '__version__ = "0.0.0"' in init_file.read_text(encoding="utf-8")

        # Run replacement on pyproject.toml
        pyproject_strategy = {
            "type": "regex",
            "pattern": r"(?m)^version\s*=\s*\"(?P<version>.*?)\"",
        }
        run_gitversioned_cli(
            project_root=sandbox_dir,
            output_file=Path("pyproject.toml"),
            strategy=pyproject_strategy,
            version_type="release",
        )

        # Run replacement on __init__.py
        init_strategy = {
            "type": "regex",
            "pattern": r"(?m)^__version__\s*=\s*\"(?P<version>.*?)\"",
        }
        run_gitversioned_cli(
            project_root=sandbox_dir,
            output_file=Path("src/my_app/__init__.py"),
            strategy=init_strategy,
            version_type="release",
        )

        # Assert final version matches the git tag v2.5.4
        updated_pyproject = pyproject_file.read_text(encoding="utf-8")
        updated_init = init_file.read_text(encoding="utf-8")

        assert 'version = "2.5.4"' in updated_pyproject
        assert '__version__ = "2.5.4"' in updated_init
