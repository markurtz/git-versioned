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
Automated validation tests for the docker_build_args example.
"""

from __future__ import annotations

import pytest

from examples.general.advanced.docker_build_args.main import main

__all__ = ["TestDockerBuildArgs"]


class TestDockerBuildArgs:
    """
    Test suite for validating the docker_build_args example execution.
    """

    @pytest.mark.regression
    def test_execution_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        """
        Run the example main entry point and assert stdout formats.

        This test simulates full execution in the sandbox, verifying
        the stdout captures match expected tag and dev version formats.
        """
        main()
        captured = capsys.readouterr()

        assert "=== GitVersioned Docker Build Args Example ===" in captured.out
        assert "Calculated Version: '0.1.0'" in captured.out
        assert "Calculated Version: '1.2.0'" in captured.out
        assert "Calculated Version (Dev): '1.2.1.dev2'" in captured.out
        assert "Demo completed successfully!" in captured.out
