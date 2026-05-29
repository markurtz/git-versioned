"""Automated validation tests for the docker_build_args example."""

from __future__ import annotations

import pytest

from examples.docker_build_args.main import main


class TestDockerBuildArgs:
    """Test suite for validating the docker_build_args example execution."""

    @pytest.mark.regression
    def test_execution_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Run the example main entry point and assert stdout formats.

        This test simulates full execution in the sandbox, verifying
        the stdout captures match expected tag and dev version formats.
        """
        main()
        captured = capsys.readouterr()

        assert "=== GitVersioned Docker Build Args Example ===" in captured.out
        assert "Calculated Version: '0.1.0'" in captured.out
        assert "Calculated Version: '1.2.0'" in captured.out
        assert "Calculated Version (Dev): '1.2.0.dev2'" in captured.out
        assert "Demo completed successfully!" in captured.out
