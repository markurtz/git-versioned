from __future__ import annotations

from pathlib import Path

import pytest

from tests.integration.conftest import GitRepoHelper


@pytest.fixture
def e2e_git_repo(tmp_path: Path) -> GitRepoHelper:
    """Yield a temporary git repository helper configured for E2E tests."""
    return GitRepoHelper(tmp_path)
