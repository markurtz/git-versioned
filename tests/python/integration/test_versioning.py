from __future__ import annotations

import pytest

from gitversioned.settings import Settings
from gitversioned.utils import BuildEnvironment, GitRepository
from gitversioned.versioning import resolve_version
from tests.conftest import GitRepoHelper


@pytest.mark.smoke
@pytest.mark.sanity
class TestResolveVersion:
    @pytest.mark.parametrize(
        ("repo_state", "expected_version_prefix"),
        [
            ("clean", "0.1"),
            ("commit_no_tag", "0.1"),
            ("lightweight_tag", "1.0"),
            ("annotated_tag", "1.0"),
            ("tagged_plus_commit", "1.0"),
            ("dirty", "0.1"),
            ("tagged_dirty", "1.0"),
            ("detached", "1.0"),
            ("shallow", "1.0"),
            ("no_git", "0.1"),
        ],
    )
    def test_invocation(
        self,
        temp_git_repo: GitRepoHelper,
        repo_state: str,
        expected_version_prefix: str,
    ) -> None:
        """Test version resolution across various repository states."""
        temp_git_repo = temp_git_repo.setup_state(repo_state)

        settings = Settings(package_name="test_pkg", project_root=temp_git_repo.path)
        repository = GitRepository(temp_git_repo.path)
        environment = BuildEnvironment(project_root=temp_git_repo.path)
        version, _ = resolve_version(
            settings=settings, repository=repository, environment=environment
        )

        assert str(version).startswith(expected_version_prefix)
