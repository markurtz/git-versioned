from __future__ import annotations

from distutils.errors import DistutilsSetupError
from typing import Any

import pytest

from gitversioned.plugins.hatchling_plugin import GitVersionedVersionSource
from gitversioned.plugins.setuptools_plugin import (
    finalize_distribution_options,
    setup_keywords,
)
from tests.integration.conftest import GitRepoHelper


class MockSetuptoolsMetadata:
    def __init__(self):
        self.version = None
        self.name = "test_pkg"


class MockSetuptoolsDistribution:
    def __init__(self, root: str):
        self.src_root = root
        self.metadata = MockSetuptoolsMetadata()
        self.version: str | None = None
        self.gitversioned_config: dict[str, Any] = {}
        self.package_dir: dict[str, str] = {}
        self._mock_name: str | None = None

    def get_name(self) -> str:
        return self._mock_name if self._mock_name is not None else "test_pkg"


@pytest.mark.sanity
class TestGitVersionedVersionSource:
    @pytest.mark.parametrize(
        ("repo_state", "expected_version_prefix"),
        [
            ("clean", "0.1"),
            ("tagged", "1.0"),
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
        """Test Hatchling plugin correctly resolves version across repository states."""
        if repo_state != "clean":
            temp_git_repo.commit("First commit")
        if repo_state in {"tagged", "tagged_dirty", "detached", "shallow"}:
            temp_git_repo.tag("v1.0.0")
        if repo_state in {"dirty", "tagged_dirty"}:
            temp_git_repo.dirty()
        if repo_state == "detached":
            temp_git_repo.checkout_detached()
        if repo_state == "shallow":
            clone_path = temp_git_repo.path.with_name(
                temp_git_repo.path.name + "_shallow"
            )
            temp_git_repo = temp_git_repo.shallow_clone(clone_path)
        if repo_state == "no_git":
            temp_git_repo.remove_git_dir()

        # Call the plugin logic
        source = GitVersionedVersionSource(root=str(temp_git_repo.path), config={})
        version_data = source.get_version_data()
        assert version_data["version"].startswith(expected_version_prefix)


@pytest.mark.sanity
class TestFinalizeDistributionOptions:
    @pytest.mark.parametrize(
        ("repo_state", "expected_version_prefix"),
        [
            ("clean", "0.1"),
            ("tagged", "1.0"),
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
        """Test Setuptools plugin correctly assigns version to distribution metadata."""
        if repo_state != "clean":
            temp_git_repo.commit("First commit")
        if repo_state in {"tagged", "tagged_dirty", "detached", "shallow"}:
            temp_git_repo.tag("v1.0.0")
        if repo_state in {"dirty", "tagged_dirty"}:
            temp_git_repo.dirty()
        if repo_state == "detached":
            temp_git_repo.checkout_detached()
        if repo_state == "shallow":
            clone_path = temp_git_repo.path.with_name(
                temp_git_repo.path.name + "_shallow"
            )
            temp_git_repo = temp_git_repo.shallow_clone(clone_path)
        if repo_state == "no_git":
            temp_git_repo.remove_git_dir()

        dist = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        # Note: setup_keywords is tested separately in TestSetupKeywords
        # We manually inject config here to simulate what setup_keywords does
        dist.gitversioned_config = {}
        finalize_distribution_options(dist)

        assert dist.metadata.version.startswith(expected_version_prefix)

    def test_unknown_package_name(self, temp_git_repo: GitRepoHelper) -> None:
        """Test error when package name cannot be determined."""

        dist = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        dist.metadata.name = "UNKNOWN"
        dist._mock_name = "UNKNOWN"
        with pytest.raises(
            DistutilsSetupError, match="Could not determine package name."
        ):
            finalize_distribution_options(dist)

    def test_package_dir_empty_string(self, temp_git_repo: GitRepoHelper) -> None:
        """Test rel_src_root extraction using empty string package_dir."""
        dist = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        dist.package_dir = {"": "src"}
        finalize_distribution_options(dist)
        assert dist.metadata.version

    def test_package_dir_package_name(self, temp_git_repo: GitRepoHelper) -> None:
        """Test rel_src_root extraction using package_name in package_dir."""
        dist = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        dist.package_dir = {"test_pkg": "src/test_pkg"}
        finalize_distribution_options(dist)
        assert dist.metadata.version

    def test_gitversioned_config(self, temp_git_repo: GitRepoHelper) -> None:
        """Test custom gitversioned_config updates kwargs."""
        dist = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        dist.gitversioned_config = {"version": "2.0.0"}
        finalize_distribution_options(dist)
        assert dist.metadata.version.startswith("2.0")


@pytest.mark.sanity
class TestSetupKeywords:
    def test_invocation(self) -> None:
        """Test valid setup_keywords invocation."""
        dist = MockSetuptoolsDistribution(root=".")
        setup_keywords(dist, "gitversioned", {"foo": "bar"})
        assert hasattr(dist, "gitversioned_config")
        assert dist.gitversioned_config == {"foo": "bar"}

    @pytest.mark.parametrize(
        ("attr", "value", "expected_error"),
        [
            ("wrong_attr", {}, "Unknown keyword argument: wrong_attr"),
            ("gitversioned", "not_a_dict", "gitversioned must be a dict"),
            ("gitversioned", [], "gitversioned must be a dict"),
            ("gitversioned", None, "gitversioned must be a dict"),
        ],
    )
    def test_invalid(self, attr: str, value: Any, expected_error: str) -> None:
        """Test invalid setup_keywords configurations."""

        dist = MockSetuptoolsDistribution(root=".")
        with pytest.raises(DistutilsSetupError, match=expected_error):
            setup_keywords(dist, attr, value)
