from __future__ import annotations

import pytest

from gitversioned.settings import Settings
from gitversioned.utils import BuildEnvironment, GitRepository
from gitversioned.versioning import resolve_version
from tests.integration.conftest import GitRepoHelper


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
        # Setup repository state
        if repo_state != "clean":
            temp_git_repo.commit("First commit")

        if repo_state == "lightweight_tag":
            temp_git_repo.tag("v1.0.0")
        elif repo_state == "annotated_tag":
            temp_git_repo.tag("v1.0.0", annotated=True)
        elif repo_state == "tagged_plus_commit":
            temp_git_repo.tag("v1.0.0")
            temp_git_repo.commit("Second commit")
        elif repo_state == "dirty":
            temp_git_repo.dirty()
        elif repo_state == "tagged_dirty":
            temp_git_repo.tag("v1.0.0")
            temp_git_repo.dirty()
        elif repo_state == "detached":
            temp_git_repo.tag("v1.0.0")
            temp_git_repo.checkout_detached()
        elif repo_state == "shallow":
            temp_git_repo.tag("v1.0.0")
            # Create a shallow clone and use it instead
            clone_path = temp_git_repo.path.with_name(
                temp_git_repo.path.name + "_shallow"
            )
            temp_git_repo = temp_git_repo.shallow_clone(clone_path)
        elif repo_state == "no_git":
            temp_git_repo.remove_git_dir()

        settings = Settings(package_name="test_pkg", project_root=temp_git_repo.path)
        repository = GitRepository(temp_git_repo.path)
        environment = BuildEnvironment(project_root=temp_git_repo.path)
        version, _ = resolve_version(
            settings=settings, repository=repository, environment=environment
        )

        assert str(version).startswith(expected_version_prefix)
