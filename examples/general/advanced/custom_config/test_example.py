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
Automated validation tests for the GitVersioned custom configuration example.
"""

from __future__ import annotations

import pytest

from examples.general.advanced.custom_config.main import main

__all__ = ["TestGeneralCustomConfig"]


class TestGeneralCustomConfig:
    """
    Test suite for validating the custom_config example execution.
    """

    @pytest.mark.regression
    def test_execution_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        """
        Run the custom config demo and verify stdout captures match expected values.
        """
        main()
        captured = capsys.readouterr()

        assert "=== GitVersioned Programmatic Custom Config Example ===" in captured.out
        assert "Resolved Tagged Version (Custom Format): 1.2" in captured.out
        expected_dev = (
            "Resolved Dev Version (Custom Format & Minor Increment): 1.3.dev1"
        )
        assert expected_dev in captured.out
        assert "=== Example Completed Successfully! ===" in captured.out
