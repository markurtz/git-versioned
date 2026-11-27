"""Unit tests for the REST forge clients."""

from __future__ import annotations

from pathlib import Path

import pytest

from gitversioned.errors import EnvironmentProblemError
from gitversioned.forges import GitLab


class TestRestCall:
    """Calls to a forge API go over http or https only."""

    @pytest.mark.sanity
    @pytest.mark.parametrize("api", ["file:///etc", "ftp://host/api", "host/api"])
    def test_rejects_other_schemes(self, tmp_path: Path, api: str) -> None:
        """An API address that is not http or https never reaches the network."""
        forge = GitLab(tmp_path, name="gitlab", api=api, project="a/b", token="t")
        with pytest.raises(EnvironmentProblemError, match="http or https"):
            forge.call("GET", "/projects")
