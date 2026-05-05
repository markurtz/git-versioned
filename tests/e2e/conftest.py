from __future__ import annotations

from pathlib import Path

import pytest

from tests.integration.conftest import GitRepoHelper


@pytest.fixture
def e2e_git_repo(tmp_path: Path) -> GitRepoHelper:
    """Yield a temporary git repository helper configured for E2E tests."""
    repo = GitRepoHelper(tmp_path)
    # The default GitRepoHelper creates a basic pyproject.toml, which we'll overwrite
    # in the tests based on whether we are testing hatchling or setuptools.
    return repo
