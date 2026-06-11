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
Automated validation tests for the GitVersioned programmatic API example.
"""

from __future__ import annotations

import pytest

from examples.general.advanced.api_usage.main import main

__all__ = ["TestApiUsage"]


class TestApiUsage:
    """
    Test suite for validating the api_usage example execution.
    """

    @pytest.mark.regression
    def test_execution_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        """
        Run the API usage demo and verify stdout captures match expected values.
        """
        main()
        captured = capsys.readouterr()

        assert "=== GitVersioned Programmatic API Example ===" in captured.out
        assert "Resolved Version: 3.1.2" in captured.out
        assert "Version Type: release" in captured.out
        assert "Successfully wrote version file to:" in captured.out
        assert '__version__ = "3.1.2"' in captured.out
        assert "=== Example Completed Successfully! ===" in captured.out
