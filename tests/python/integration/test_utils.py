from __future__ import annotations

import inspect
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Annotated

import pytest
from pydantic import BaseModel, ValidationError

from gitversioned.utils import (
    BuildEnvironment,
    EnsureBool,
    EnsureList,
    EnsurePath,
    GitReference,
    GitRepository,
    NotAGitRepositoryError,
    coerce_bool,
    coerce_list,
    coerce_path,
    get_ci_info,
    get_user,
)
from gitversioned.utils.environment import get_ram_gb
from tests.conftest import GitRepoHelper


@pytest.mark.sanity
def test_interface_signature_validation() -> None:
    """Validate the interface signatures and inheritance of gitversioned.utils."""
    # Check inheritance lineages
    assert issubclass(GitReference, BaseModel)
    assert issubclass(BuildEnvironment, BaseModel)

    # Check method signatures and parameter names
    repo_sig = inspect.signature(GitRepository.__init__)
    assert "repository_path" in repo_sig.parameters

    filter_sig = inspect.signature(GitRepository.filtered_dirty_files)
    assert "ignore_paths" in filter_sig.parameters
    assert "fail_on_unavailable" in filter_sig.parameters

    # coerce_bool
    coerce_bool_sig = inspect.signature(coerce_bool)
    assert "value" in coerce_bool_sig.parameters

    # coerce_path
    coerce_path_sig = inspect.signature(coerce_path)
    assert "value" in coerce_path_sig.parameters

    # coerce_list
    coerce_list_sig = inspect.signature(coerce_list)
    assert "value" in coerce_list_sig.parameters
    assert "item_pre_coercer" in coerce_list_sig.parameters


@pytest.mark.regression
def test_get_user_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_user fallback logic when getlogin raises OSError."""

    def mock_getlogin() -> str:
        raise OSError("Mock OSError")

    monkeypatch.setattr(os, "getlogin", mock_getlogin)
    monkeypatch.setenv("USER", "mock_user")
    assert get_user() == "mock_user"

    monkeypatch.delenv("USER", raising=False)
    monkeypatch.setenv("USERNAME", "mock_username")
    assert get_user() == "mock_username"

    monkeypatch.delenv("USERNAME", raising=False)
    assert get_user() == "unknown"


@pytest.mark.regression
def test_get_ram_gb_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_ram_gb with mocked psutil."""
    mock_psutil = ModuleType("psutil")

    class MockVirtualMemory:
        total: int = 16 * (1024**3)

    attr_name = "virtual_memory"
    setattr(mock_psutil, attr_name, MockVirtualMemory)
    monkeypatch.setattr("gitversioned.utils.environment.psutil", mock_psutil)

    assert get_ram_gb() == 16.0


class TestGitRepository:
    """Integration test suite for GitRepository."""

    @pytest.fixture
    def valid_instances(
        self, temp_git_repo: GitRepoHelper, request: pytest.FixtureRequest
    ) -> GitRepository:
        """Fixture supplying properly initialized repository instances.

        Returns a GitRepository configured to the requested state name.
        """
        state_name = request.param
        repo_helper = temp_git_repo.setup_state(state_name)
        return GitRepository(repo_helper.path)

    @pytest.mark.smoke
    def test_initialization(self, temp_git_repo: GitRepoHelper) -> None:
        """Test GitRepository initialization with valid paths."""
        repo_str = GitRepository(str(temp_git_repo.path))
        assert repo_str.base_path == temp_git_repo.path.resolve()

        repo_path = GitRepository(temp_git_repo.path)
        assert repo_path.base_path == temp_git_repo.path.resolve()

        repo_default = GitRepository()
        assert repo_default.base_path == Path.cwd().resolve()

    @pytest.mark.sanity
    def test_invalid_initialization_values(self) -> None:
        """Test initialization with invalid types raises error during execution."""
        repo_invalid = GitRepository("/nonexistent/path/to/repo")
        attr_name = "root_directory"
        with pytest.raises(NotAGitRepositoryError):
            getattr(repo_invalid, attr_name)

    @pytest.mark.sanity
    def test_invalid_initialization_missing(self) -> None:
        """Test behavior when the repository directory is missing."""
        repo_missing = GitRepository(Path("/nonexistent/directory/structure"))
        assert repo_missing.is_available is False
        with pytest.raises(NotAGitRepositoryError):
            repo_missing._ensure_valid_repository()

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "valid_instances", ["clean", "tagged", "no_git"], indirect=True
    )
    def test_is_available(self, valid_instances: GitRepository) -> None:
        """Test availability verification across repository states."""
        git_dir = valid_instances.base_path / ".git"
        if not git_dir.exists():
            assert valid_instances.is_available is False
        else:
            assert valid_instances.is_available is True

    @pytest.mark.sanity
    @pytest.mark.parametrize("valid_instances", ["clean", "tagged"], indirect=True)
    def test_root_directory(self, valid_instances: GitRepository) -> None:
        """Test root directory resolution is correct."""
        assert valid_instances.root_directory == valid_instances.base_path

    @pytest.mark.sanity
    @pytest.mark.parametrize("valid_instances", ["clean"], indirect=True)
    def test_repository_name(
        self, valid_instances: GitRepository, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test repository name extraction from path or remote origin URL."""
        assert valid_instances.repository_name == valid_instances.base_path.name

        subprocess.check_call(
            [
                "git",
                "config",
                "remote.origin.url",
                "git@github.com:markurtz/git-versioned.git",
            ],
            cwd=valid_instances.base_path,
        )
        assert valid_instances.repository_name == "git-versioned"

        subprocess.check_call(
            [
                "git",
                "config",
                "remote.origin.url",
                "https://github.com/markurtz/another-repo",
            ],
            cwd=valid_instances.base_path,
        )
        assert valid_instances.repository_name == "another-repo"

    @pytest.mark.regression
    @pytest.mark.parametrize("valid_instances", ["clean"], indirect=True)
    def test_remote_origin_url(self, valid_instances: GitRepository) -> None:
        """Test remote origin URL retrieval."""
        assert valid_instances.remote_origin_url == ""

        url_val = "git@github.com:markurtz/git-versioned.git"
        subprocess.check_call(
            [
                "git",
                "config",
                "remote.origin.url",
                url_val,
            ],
            cwd=valid_instances.base_path,
        )
        assert valid_instances.remote_origin_url == url_val

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "valid_instances", ["clean", "tagged_plus_commit"], indirect=True
    )
    def test_commit_count(self, valid_instances: GitRepository) -> None:
        """Test calculating commit count."""
        git_dir = valid_instances.base_path / ".git"
        if not git_dir.exists():
            assert valid_instances.commit_count == 0
        else:
            try:
                out_bytes = subprocess.check_output(
                    ["git", "rev-list", "--count", "HEAD"],
                    cwd=valid_instances.base_path,
                )
                expected_count = int(out_bytes.strip())
            except subprocess.CalledProcessError:
                expected_count = 0
            assert valid_instances.commit_count == expected_count

    @pytest.mark.regression
    def test_commit_count_unavailable(self) -> None:
        """Test commit count returns 0 when repository is unavailable."""
        repo = GitRepository("/nonexistent")
        assert repo.commit_count == 0

    @pytest.mark.smoke
    @pytest.mark.parametrize("valid_instances", ["clean", "dirty"], indirect=True)
    def test_is_dirty(self, valid_instances: GitRepository) -> None:
        """Test repository dirty check."""
        dirty_files_list = valid_instances.dirty_files
        assert valid_instances.is_dirty == bool(dirty_files_list)

    @pytest.mark.sanity
    @pytest.mark.parametrize("valid_instances", ["dirty"], indirect=True)
    def test_dirty_files(self, valid_instances: GitRepository) -> None:
        """Test dirty files list retrieval."""
        dirty_list = valid_instances.dirty_files
        assert len(dirty_list) > 0
        for path_item in dirty_list:
            assert path_item.is_absolute()
        names = {path_item.name for path_item in dirty_list}
        assert "dirty.txt" in names

    @pytest.mark.regression
    def test_dirty_files_rename(self, temp_git_repo: GitRepoHelper) -> None:
        """Test dirty files logic handles file renames and reports them correctly."""
        temp_git_repo.dirty("original.txt")
        temp_git_repo.add("original.txt")
        temp_git_repo.commit("Commit original")
        subprocess.check_call(
            ["git", "mv", "original.txt", "renamed.txt"],
            cwd=temp_git_repo.path,
        )
        repo = GitRepository(temp_git_repo.path)
        dirty_list = repo.dirty_files
        assert len(dirty_list) > 0
        names = {path_item.name for path_item in dirty_list}
        assert "renamed.txt" in names

    @pytest.mark.smoke
    @pytest.mark.parametrize("valid_instances", ["clean", "tagged"], indirect=True)
    def test_current_commit(self, valid_instances: GitRepository) -> None:
        """Test fetching the most recent commit reference."""
        commit_ref = valid_instances.current_commit
        if not valid_instances.is_available or valid_instances.commit_count == 0:
            assert commit_ref is None
        else:
            assert isinstance(commit_ref, GitReference)
            assert commit_ref.commit_sha != ""
            assert commit_ref.short_sha != ""

    @pytest.mark.regression
    @pytest.mark.parametrize("valid_instances", ["clean", "no_git"], indirect=True)
    def test_current_commit_or_fallback(self, valid_instances: GitRepository) -> None:
        """Test fallback commit reference logic."""
        commit_ref = valid_instances.current_commit_or_fallback
        assert isinstance(commit_ref, GitReference)
        assert commit_ref.is_head_commit is True

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "valid_instances", ["clean", "tagged", "tagged_plus_commit"], indirect=True
    )
    def test_last_tag(self, valid_instances: GitRepository) -> None:
        """Test retrieval of the most recent tag."""
        tag_ref = valid_instances.last_tag
        if "clean" in str(valid_instances.base_path):
            assert tag_ref is None
        elif "tagged" in str(valid_instances.base_path):
            assert tag_ref is not None
            assert tag_ref.tag_name == "v1.0.0"

    @pytest.mark.sanity
    @pytest.mark.parametrize("valid_instances", ["clean", "detached"], indirect=True)
    def test_current_branch(self, valid_instances: GitRepository) -> None:
        """Test checked out branch retrieval."""
        branch_ref = valid_instances.current_branch
        if "detached" in str(valid_instances.base_path):
            assert branch_ref is None
        elif valid_instances.is_available and valid_instances.commit_count > 0:
            assert branch_ref is not None
            assert branch_ref.is_current_branch is True

    @pytest.mark.sanity
    @pytest.mark.parametrize("valid_instances", ["clean", "detached"], indirect=True)
    def test_head_name(self, valid_instances: GitRepository) -> None:
        """Test head name resolution."""
        head_str = valid_instances.head_name
        if not valid_instances.is_available or valid_instances.commit_count == 0:
            assert head_str == ""
        elif "detached" in str(valid_instances.base_path):
            assert len(head_str) == 7
        else:
            assert head_str in ("main", "master")

    @pytest.mark.regression
    def test_head_name_empty(self, temp_git_repo: GitRepoHelper) -> None:
        """Test head name is empty when no commits exist."""
        repo = GitRepository(temp_git_repo.path)
        assert repo.head_name == ""

    @pytest.mark.regression
    def test_commits(self, temp_git_repo: GitRepoHelper) -> None:
        """Test commits iterator properties."""
        temp_git_repo.commit("Commit one")
        temp_git_repo.commit("Commit two")
        repo = GitRepository(temp_git_repo.path)
        commits_list = list(repo.commits)
        assert len(commits_list) == 2
        assert commits_list[0].commit_message == "Commit two"
        assert commits_list[0].distance_from_head == 0
        assert commits_list[0].is_head_commit is True
        assert commits_list[1].commit_message == "Commit one"
        assert commits_list[1].distance_from_head == 1
        assert commits_list[1].is_head_commit is False

    @pytest.mark.regression
    def test_tags(self, temp_git_repo: GitRepoHelper) -> None:
        """Test tags sorting and fields."""
        temp_git_repo.commit("Initial commit")
        temp_git_repo.tag("v1.0.0", annotated=True, message="Annotated tag")
        temp_git_repo.commit("Second commit")
        temp_git_repo.tag("v2.0.0")

        repo = GitRepository(temp_git_repo.path)
        tags_list = list(repo.tags)
        assert len(tags_list) == 2
        tag_names = {ref.tag_name for ref in tags_list}
        assert tag_names == {"v1.0.0", "v2.0.0"}

    @pytest.mark.regression
    def test_branches(self, temp_git_repo: GitRepoHelper) -> None:
        """Test branches list and current status."""
        temp_git_repo.commit("Initial commit")
        temp_git_repo.branch("feature-branch")
        repo = GitRepository(temp_git_repo.path)
        branches_list = list(repo.branches)
        names = {ref.branch_name for ref in branches_list}
        assert "feature-branch" in names
        current_branches = [ref for ref in branches_list if ref.is_current_branch]
        assert len(current_branches) == 1
        assert current_branches[0].branch_name == "feature-branch"

    @pytest.mark.sanity
    def test_filtered_dirty_files(self, temp_git_repo: GitRepoHelper) -> None:
        """Test filtering modified files with ignore paths."""
        temp_git_repo.add("pyproject.toml")
        temp_git_repo.commit("Initial commit")
        (temp_git_repo.path / "subfolder").mkdir(exist_ok=True)
        temp_git_repo.dirty("file1.txt")
        temp_git_repo.dirty("subfolder/file2.txt")
        temp_git_repo.dirty("subfolder/file3.txt")

        repo = GitRepository(temp_git_repo.path)
        all_dirty = repo.filtered_dirty_files()
        assert len(all_dirty) == 2

        filtered_one = repo.filtered_dirty_files(ignore_paths=[Path("file1.txt")])
        assert len(filtered_one) == 1
        assert not any("file1.txt" in path_str for path_str in filtered_one)

        filtered_sub = repo.filtered_dirty_files(ignore_paths=[Path("subfolder")])
        assert len(filtered_sub) == 1
        assert any("file1.txt" in path_str for path_str in filtered_sub)

    @pytest.mark.regression
    def test_filtered_dirty_files_raises(self) -> None:
        """Test filtered_dirty_files raises when repo is unavailable.

        Ensures NotAGitRepositoryError is raised when fail_on_unavailable is True.
        """
        repo = GitRepository("/nonexistent")
        attr_name = "filtered_dirty_files"
        func = getattr(repo, attr_name)
        with pytest.raises(NotAGitRepositoryError):
            func(fail_on_unavailable=True)

    @pytest.mark.regression
    def test_stream_command_failure(self, temp_git_repo: GitRepoHelper) -> None:
        """Test that stream command handles subprocess failure gracefully."""
        repo = GitRepository(temp_git_repo.path)
        lines = list(repo._stream_command(["log", "nonexistent-branch-xyz"]))
        assert len(lines) == 0

    @pytest.mark.regression
    def test_str_repr_methods(self, temp_git_repo: GitRepoHelper) -> None:
        """Test string representations and formatting of GitRepository."""
        repo = GitRepository(temp_git_repo.path)
        assert str(repo) != ""
        assert repr(repo) != ""

        repo_invalid = GitRepository("/nonexistent")
        assert "Unavailable" in str(repo_invalid)
        assert repr(repo_invalid) != ""


class TestGitReference:
    """Integration test suite for GitReference."""

    @pytest.mark.regression
    def test_marshalling(self) -> None:
        """Test marshalling and Pydantic validation / refs parsing of GitReference."""
        now_time = datetime.now(timezone.utc)
        ref_dict = {
            "commit_sha": "a" * 40,
            "short_sha": "a" * 7,
            "timestamp": now_time,
            "distance_from_head": 2,
            "is_head_commit": False,
            "total_commits": 10,
            "author_name": "Developer",
            "author_email": "dev@example.com",
            "commit_message": "Chore: update dependencies",
            "ref_names": "HEAD -> main, tag: v1.5.0, origin/main",
        }
        ref_obj = GitReference.model_validate(ref_dict)
        assert ref_obj.branch_name == "main"
        assert ref_obj.is_current_branch is True
        assert ref_obj.tag_name == "v1.5.0"

        dumped_dict = ref_obj.model_dump()
        reloaded_obj = GitReference.model_validate(dumped_dict)
        assert reloaded_obj.branch_name == "main"
        assert reloaded_obj.is_current_branch is True
        assert reloaded_obj.tag_name == "v1.5.0"

        alternate_ref_dict = {
            "commit_sha": "b" * 40,
            "short_sha": "b" * 7,
            "refs": "tag: v2.0.0-rc1, release-branch",
        }
        alt_ref_obj = GitReference.model_validate(alternate_ref_dict)
        assert alt_ref_obj.tag_name == "v2.0.0-rc1"
        assert alt_ref_obj.branch_name == "release-branch"

    @pytest.mark.regression
    def test_parse_git_references_not_dict(self) -> None:
        """Test parse_git_references returns value directly if not a dict."""
        with pytest.raises(ValidationError):
            GitReference.model_validate(42)

    @pytest.mark.regression
    def test_str_method(self) -> None:
        """Test string representation formatting under various configurations."""
        now_time = datetime.now(timezone.utc)
        ref_tag = GitReference(
            tag_name="v1.0.0", short_sha="abc1234", timestamp=now_time
        )
        assert "v1.0.0 -> abc1234" in str(ref_tag)

        ref_branch = GitReference(
            branch_name="main",
            short_sha="abc1234",
            timestamp=now_time,
            is_current_branch=True,
        )
        assert "* main -> abc1234" in str(ref_branch)

        ref_msg = GitReference(
            commit_message="Initial commit",
            short_sha="abc1234",
            timestamp=now_time,
            author_name="Coder",
        )
        assert "abc1234 Initial commit - Coder" in str(ref_msg)

        ref_plain = GitReference(short_sha="abc1234", timestamp=now_time)
        assert "abc1234" in str(ref_plain)


class TestBuildEnvironment:
    """Integration test suite for BuildEnvironment."""

    @pytest.mark.smoke
    def test_initialization(self) -> None:
        """Test BuildEnvironment default factories and initial state values."""
        build_env = BuildEnvironment()
        assert build_env.hostname != ""
        assert build_env.user != ""
        assert build_env.os_system in ("Darwin", "Linux", "Windows", "unknown")
        assert build_env.cpu_arch != ""
        assert build_env.cpu_cores >= 0
        assert build_env.total_ram_gb >= 0.0
        assert build_env.python_version != ""
        assert build_env.build_id != ""

    @pytest.mark.sanity
    def test_invalid_initialization_values(self) -> None:
        """Test Pydantic validation fails for invalid field types."""
        with pytest.raises(ValidationError):
            BuildEnvironment.model_validate({"cpu_cores": "not-an-int"})

        with pytest.raises(ValidationError):
            BuildEnvironment.model_validate({"timestamp": "not-a-datetime"})

    @pytest.mark.sanity
    def test_invalid_initialization_missing(self) -> None:
        """Test default values are successfully generated.

        Ensures defaults are generated when fields are missing.
        """
        build_env = BuildEnvironment.model_validate({})
        assert build_env.hostname is not None
        assert build_env.build_id is not None

    @pytest.mark.regression
    def test_marshalling(self) -> None:
        """Test serialization, deserialization, and frozen state assertions."""
        build_env = BuildEnvironment()
        dumped_dict = build_env.model_dump()
        reloaded_env = BuildEnvironment.model_validate(dumped_dict)

        assert reloaded_env.hostname == build_env.hostname
        assert reloaded_env.build_id == build_env.build_id
        assert reloaded_env.project_root == build_env.project_root

        # Assert frozen status raises ValidationError on mutability
        attr_name = "hostname"
        with pytest.raises(ValidationError):
            setattr(build_env, attr_name, "new-host")

    @pytest.mark.sanity
    def test_ci_provider_resolution(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test CI environment provider resolution based on environment variables."""
        ci_vars = [
            "GITHUB_ACTIONS",
            "GITLAB_CI",
            "CIRCLECI",
            "TRAVIS",
            "JENKINS_URL",
            "BITBUCKET_COMMIT",
            "CI",
        ]
        for var_name in ci_vars:
            monkeypatch.delenv(var_name, raising=False)

        assert get_ci_info() == (False, None)
        local_build = BuildEnvironment()
        assert local_build.is_ci is False
        assert local_build.ci_provider is None

        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        assert get_ci_info() == (True, "GitHub Actions")
        github_build = BuildEnvironment()
        assert github_build.is_ci is True
        assert github_build.ci_provider == "GitHub Actions"

        monkeypatch.delenv("GITHUB_ACTIONS")
        monkeypatch.setenv("GITLAB_CI", "true")
        assert get_ci_info() == (True, "GitLab CI")
        gitlab_build = BuildEnvironment()
        assert gitlab_build.is_ci is True
        assert gitlab_build.ci_provider == "GitLab CI"

        monkeypatch.delenv("GITLAB_CI")
        monkeypatch.setenv("CI", "true")
        assert get_ci_info() == (True, "Unknown CI")
        generic_build = BuildEnvironment()
        assert generic_build.is_ci is True
        assert generic_build.ci_provider == "Unknown CI"

    @pytest.mark.regression
    def test_str_repr_methods(self) -> None:
        """Test string representations and formatting of BuildEnvironment."""
        build_env = BuildEnvironment()
        assert str(build_env) != ""
        assert repr(build_env) != ""


class TestPydanticCoercion:
    """Integration test suite for Pydantic coercion helpers and annotations."""

    class CoercionDummyModel(BaseModel):
        flag: EnsureBool
        path: EnsurePath
        list_ints: EnsureList[int]
        list_strs: Annotated[list[str], EnsureList()]
        annotated_list: Annotated[list[int], EnsureList()]
        annotated_set: Annotated[set[str], EnsureList()]
        annotated_plain_list: Annotated[list, EnsureList()]

    @pytest.mark.regression
    def test_marshalling(self) -> None:
        """Test marshalling of values via EnsureBool, EnsurePath, and EnsureList."""
        payload = {
            "flag": "yes",
            "path": "  /some/clean/path.log   ",
            "list_ints": "10, 20, 30",
            "list_strs": "foo, bar, baz",
            "annotated_list": "100, 200",
            "annotated_set": "apple, banana",
            "annotated_plain_list": "one, two",
        }
        model_obj = self.CoercionDummyModel.model_validate(payload)
        assert model_obj.flag is True
        assert model_obj.path == Path("/some/clean/path.log")
        assert model_obj.list_ints == [10, 20, 30]
        assert model_obj.list_strs == ["foo", "bar", "baz"]
        assert model_obj.annotated_list == [100, 200]
        assert sorted(model_obj.annotated_set) == ["apple", "banana"]
        assert model_obj.annotated_plain_list == ["one", "two"]

        payload_alt = {
            "flag": "0",
            "path": "relative/path",
            "list_ints": [5, 6, 7],
            "list_strs": ["apple", "banana"],
            "annotated_list": [100, 200],
            "annotated_set": {"apple", "banana"},
            "annotated_plain_list": [42],
        }
        model_obj_alt = self.CoercionDummyModel.model_validate(payload_alt)
        assert model_obj_alt.flag is False
        assert model_obj_alt.path == Path("relative/path")
        assert model_obj_alt.list_ints == [5, 6, 7]
        assert model_obj_alt.list_strs == ["apple", "banana"]
        assert model_obj_alt.annotated_list == [100, 200]
        assert sorted(model_obj_alt.annotated_set) == ["apple", "banana"]
        assert model_obj_alt.annotated_plain_list == [42]

        with pytest.raises(ValidationError):
            self.CoercionDummyModel.model_validate(
                {
                    "flag": True,
                    "path": "/some/invalid/path",
                    "list_ints": "1, not-an-int, 3",
                    "list_strs": "ok",
                    "annotated_list": "100",
                    "annotated_set": "apple",
                    "annotated_plain_list": "one",
                }
            )

        assert coerce_bool("TRUE") is True
        assert coerce_bool("no") is False
        assert coerce_bool(42) == 42

        assert coerce_path("  /abc  ") == Path("/abc")
        assert coerce_path(123) == 123

        assert coerce_list("a, b, c") == ["a", "b", "c"]
        assert coerce_list(None) == []
        assert coerce_list(42) == [42]
        assert coerce_list("yes, no, yes", coerce_bool) == [True, False, True]
