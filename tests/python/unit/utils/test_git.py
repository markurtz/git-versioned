from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from pydantic import BaseModel, ValidationError

from gitversioned.utils.git import (
    GitReference,
    GitRepository,
    NotAGitRepositoryError,
)


class TestNotAGitRepositoryError:
    @pytest.fixture(
        params=[
            "Not a Git repository error message",
            "Another repository error message",
        ]
    )
    def valid_instances(self, request: pytest.FixtureRequest) -> NotAGitRepositoryError:
        return NotAGitRepositoryError(request.param)

    @pytest.mark.smoke
    def test_signature_validation(self) -> None:
        assert issubclass(NotAGitRepositoryError, Exception)

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: NotAGitRepositoryError) -> None:
        assert isinstance(valid_instances, Exception)

    @pytest.mark.sanity
    def test_invalid_initialization_values(self) -> None:
        error_instance = NotAGitRepositoryError(12345)
        assert str(error_instance) == "12345"

    @pytest.mark.sanity
    def test_invalid_initialization_missing(self) -> None:
        error_instance = NotAGitRepositoryError()
        assert str(error_instance) == ""


class TestGitReference:
    @pytest.fixture(
        params=[
            {
                "commit_sha": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
                "short_sha": "a1b2c3d",
                "timestamp": datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                "distance_from_head": 5,
                "is_head_commit": False,
                "total_commits": 100,
                "author_name": "Author One",
                "author_email": "author1@test.com",
                "commit_message": "feat: init",
                "tag_name": "v1.0.0",
                "branch_name": "main",
                "is_current_branch": True,
            },
            {
                "commit_sha": "0987654321098765432109876543210987654321",
                "short_sha": "0987654",
                "timestamp": datetime(2023, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
                "distance_from_head": 0,
                "is_head_commit": True,
                "total_commits": 1,
                "author_name": "Author Two",
                "author_email": "author2@test.com",
                "commit_message": "fix: bug",
                "tag_name": "",
                "branch_name": "",
                "is_current_branch": False,
            },
        ]
    )
    def valid_instances(self, request: pytest.FixtureRequest) -> GitReference:
        return GitReference(**request.param)

    @pytest.mark.smoke
    def test_signature_validation(self) -> None:
        assert issubclass(GitReference, BaseModel)
        expected_fields = {
            "commit_sha",
            "short_sha",
            "timestamp",
            "distance_from_head",
            "is_head_commit",
            "total_commits",
            "author_name",
            "author_email",
            "commit_message",
            "tag_name",
            "branch_name",
            "is_current_branch",
        }
        for field_name in expected_fields:
            assert field_name in GitReference.model_fields
        assert hasattr(GitReference, "parse_git_references")
        assert callable(GitReference.parse_git_references)

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: GitReference) -> None:
        assert isinstance(valid_instances.commit_sha, str)
        assert isinstance(valid_instances.short_sha, str)
        assert isinstance(valid_instances.timestamp, datetime)
        assert isinstance(valid_instances.distance_from_head, int)
        assert isinstance(valid_instances.is_head_commit, bool)

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("field_name", "invalid_value"),
        [
            ("timestamp", "invalid-date"),
            ("distance_from_head", "not-an-int"),
            ("is_head_commit", "not-a-bool"),
            ("total_commits", "not-an-int"),
            ("is_current_branch", "not-a-bool"),
        ],
    )
    def test_invalid_initialization_values(
        self, field_name: str, invalid_value: Any
    ) -> None:
        with pytest.raises(ValidationError):
            GitReference(**{field_name: invalid_value})

    @pytest.mark.sanity
    def test_invalid_initialization_missing(self) -> None:
        ref = GitReference()
        assert ref.commit_sha == ""
        assert ref.short_sha == ""
        assert ref.timestamp == datetime.min
        assert ref.distance_from_head == sys.maxsize
        assert ref.is_head_commit is False
        assert ref.total_commits == 0

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("raw_data", "expected_results"),
        [
            (
                "plain string payload",
                "plain string payload",
            ),
            (
                {},
                {},
            ),
            (
                {"ref_names": "HEAD -> main"},
                {
                    "refs": "HEAD -> main",
                    "ref_names": "HEAD -> main",
                    "branch_name": "main",
                    "is_current_branch": True,
                },
            ),
            (
                {"refs": "tag: v1.0.0"},
                {"refs": "tag: v1.0.0", "tag_name": "v1.0.0"},
            ),
            (
                {"refs": "feature/branch-name"},
                {"refs": "feature/branch-name", "branch_name": "feature/branch-name"},
            ),
            (
                {"refs": "HEAD -> development, tag: v1.2.3, tag: v1.2.4"},
                {
                    "refs": "HEAD -> development, tag: v1.2.3, tag: v1.2.4",
                    "branch_name": "development",
                    "is_current_branch": True,
                    "tag_name": "v1.2.3",
                },
            ),
        ],
    )
    def test_parse_git_references(self, raw_data: Any, expected_results: Any) -> None:
        result = getattr(GitReference, "parse_git_references")(raw_data)  # noqa: B009
        if isinstance(raw_data, dict):
            for key_name, expected_value in expected_results.items():
                assert result[key_name] == expected_value
        else:
            assert result == expected_results

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("ref_data", "expected_str_regex"),
        [
            (
                {
                    "tag_name": "v1.0.0",
                    "short_sha": "a1b2c3d",
                    "timestamp": datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                },
                r"v1\.0\.0 -> a1b2c3d \(2023-01-01T12:00:00\+00:00\)",
            ),
            (
                {
                    "branch_name": "main",
                    "is_current_branch": True,
                    "short_sha": "a1b2c3d",
                    "timestamp": datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                },
                r"\* main -> a1b2c3d \(2023-01-01T12:00:00\+00:00\)",
            ),
            (
                {
                    "branch_name": "dev",
                    "is_current_branch": False,
                    "short_sha": "a1b2c3d",
                    "timestamp": datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                },
                r"  dev -> a1b2c3d \(2023-01-01T12:00:00\+00:00\)",
            ),
            (
                {
                    "short_sha": "a1b2c3d",
                    "commit_message": "feat: message",
                    "author_name": "Author",
                    "timestamp": datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                },
                r"a1b2c3d feat: message - Author \(2023-01-01T12:00:00\+00:00\)",
            ),
            (
                {
                    "short_sha": "a1b2c3d",
                    "timestamp": datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                },
                r"a1b2c3d \(2023-01-01T12:00:00\+00:00\)",
            ),
        ],
    )
    def test_str(self, ref_data: dict[str, Any], expected_str_regex: str) -> None:
        reference = GitReference(**ref_data)
        assert re.match(expected_str_regex, str(reference))

    @pytest.mark.regression
    def test_marshalling(self, valid_instances: GitReference) -> None:
        dumped_data = valid_instances.model_dump()
        assert isinstance(dumped_data, dict)
        assert dumped_data["commit_sha"] == valid_instances.commit_sha
        validated_instance = GitReference.model_validate(dumped_data)
        assert validated_instance == valid_instances


class TestGitRepository:
    @pytest.fixture(
        params=[
            None,
            "/mock/repo/path",
        ]
    )
    def valid_instances(self, request: pytest.FixtureRequest) -> GitRepository:
        return GitRepository(request.param)

    @pytest.mark.smoke
    def test_signature_validation(self) -> None:
        properties = [
            "is_available",
            "root_directory",
            "repository_name",
            "remote_origin_url",
            "commit_count",
            "is_dirty",
            "dirty_files",
            "current_commit",
            "current_commit_or_fallback",
            "last_tag",
            "current_branch",
            "head_name",
            "commits",
            "tags",
            "branches",
        ]
        for prop_name in properties:
            prop = getattr(GitRepository, prop_name)
            assert isinstance(prop, property)

        assert hasattr(GitRepository, "filtered_dirty_files")
        assert callable(GitRepository.filtered_dirty_files)

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: GitRepository) -> None:
        assert isinstance(valid_instances.base_path, Path)
        assert valid_instances.base_path.is_absolute()

    @pytest.mark.sanity
    def test_invalid_initialization_values(self) -> None:
        invalid_path: Any = 12345
        with pytest.raises(TypeError):
            GitRepository(invalid_path)

    @pytest.mark.sanity
    def test_invalid_initialization_missing(self) -> None:
        repo_instance = GitRepository()
        assert repo_instance.base_path == Path.cwd().resolve()

    @pytest.mark.smoke
    def test_is_available(self) -> None:
        repo_instance = GitRepository()
        mock_result = MagicMock()
        mock_result.stdout = "true\n"
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            assert repo_instance.is_available is True
            mock_run.assert_called_once()

        mock_result.stdout = "false\n"
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            assert repo_instance.is_available is False

    @pytest.mark.smoke
    def test_root_directory(self) -> None:
        repo_instance = GitRepository()
        mock_avail = MagicMock()
        mock_avail.stdout = "true\n"
        mock_root = MagicMock()
        mock_root.stdout = "/mock/root/dir\n"

        def mock_subprocess_run(*args: Any, **kwargs: Any) -> Any:
            cmd = args[0]
            if "--is-inside-work-tree" in cmd:
                return mock_avail
            return mock_root

        with patch("subprocess.run", side_effect=mock_subprocess_run):
            assert repo_instance.root_directory == Path("/mock/root/dir")

        # Test NotAGitRepositoryError raised when unavailable
        mock_avail.stdout = "false\n"
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            pytest.raises(NotAGitRepositoryError),
        ):
            _ = repo_instance.root_directory

    @pytest.mark.smoke
    def test_repository_name(self) -> None:
        repo_instance = GitRepository()

        # Scenario 1: Remote origin URL ends with .git
        with patch.object(
            GitRepository,
            "remote_origin_url",
            new_callable=PropertyMock,
            return_value="https://github.com/user/my-project.git",
        ):
            assert repo_instance.repository_name == "my-project"

        # Scenario 2: Remote origin URL does not end with .git
        with patch.object(
            GitRepository,
            "remote_origin_url",
            new_callable=PropertyMock,
            return_value="https://github.com/user/other-project",
        ):
            assert repo_instance.repository_name == "other-project"

        # Scenario 3: Remote origin URL empty, fallback to folder name
        mock_avail = MagicMock(stdout="true\n")
        mock_root = MagicMock(stdout="/mock/root/some-folder\n")

        def mock_run_call(*args: Any, **kwargs: Any) -> Any:
            cmd = args[0]
            if "--is-inside-work-tree" in cmd:
                return mock_avail
            return mock_root

        with (
            patch.object(
                GitRepository,
                "remote_origin_url",
                new_callable=PropertyMock,
                return_value="",
            ),
            patch("subprocess.run", side_effect=mock_run_call),
        ):
            assert repo_instance.repository_name == "some-folder"

    @pytest.mark.smoke
    def test_remote_origin_url(self) -> None:
        repo_instance = GitRepository()
        mock_result = MagicMock()
        mock_result.stdout = "git@github.com:user/project.git\n"
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            assert repo_instance.remote_origin_url == "git@github.com:user/project.git"
            mock_run.assert_called_once()

        # Test subprocess exception handling in _execute_command
        with patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(1, ["git"]),
        ):
            assert repo_instance.remote_origin_url == ""

    @pytest.mark.smoke
    def test_commit_count(self) -> None:
        repo_instance = GitRepository()

        # Case 1: Available and count returns 15
        mock_avail = MagicMock(stdout="true\n")
        mock_count = MagicMock(stdout="15\n")

        def mock_run_calls(*args: Any, **kwargs: Any) -> Any:
            cmd = args[0]
            if "--is-inside-work-tree" in cmd:
                return mock_avail
            return mock_count

        with patch("subprocess.run", side_effect=mock_run_calls):
            assert repo_instance.commit_count == 15

        # Case 2: Not available
        mock_not_avail = MagicMock(stdout="false\n")
        with patch("subprocess.run", return_value=mock_not_avail):
            assert repo_instance.commit_count == 0

        # Case 3: ValueError exception
        mock_bad_count = MagicMock(stdout="not-an-int\n")

        def mock_run_bad_calls(*args: Any, **kwargs: Any) -> Any:
            cmd = args[0]
            if "--is-inside-work-tree" in cmd:
                return mock_avail
            return mock_bad_count

        with patch("subprocess.run", side_effect=mock_run_bad_calls):
            assert repo_instance.commit_count == 0

    @pytest.mark.smoke
    def test_is_dirty(self) -> None:
        repo_instance = GitRepository()
        with patch.object(
            GitRepository,
            "dirty_files",
            new_callable=PropertyMock,
            return_value=[Path("file1.txt")],
        ):
            assert repo_instance.is_dirty is True

        with patch.object(
            GitRepository,
            "dirty_files",
            new_callable=PropertyMock,
            return_value=[],
        ):
            assert repo_instance.is_dirty is False

    @pytest.mark.smoke
    def test_dirty_files(self) -> None:
        repo_instance = GitRepository()
        mock_output = MagicMock()
        mock_output.stdout = (
            " M modified.txt\n?? untracked.txt\nR  old_file.txt -> new_file.txt\n"
        )
        with patch("subprocess.run", return_value=mock_output) as mock_run:
            dirty = repo_instance.dirty_files
            assert len(dirty) == 3
            assert dirty[0] == (repo_instance.base_path / "modified.txt").resolve()
            assert dirty[1] == (repo_instance.base_path / "untracked.txt").resolve()
            assert dirty[2] == (repo_instance.base_path / "new_file.txt").resolve()
            mock_run.assert_called_once()

    @pytest.mark.smoke
    def test_current_commit(self) -> None:
        repo_instance = GitRepository()
        mock_commit = MagicMock()
        with patch.object(
            GitRepository,
            "commits",
            new_callable=PropertyMock,
            return_value=iter([mock_commit]),
        ):
            assert repo_instance.current_commit == mock_commit

    @pytest.mark.smoke
    def test_current_commit_or_fallback(self) -> None:
        repo_instance = GitRepository()
        mock_commit = MagicMock()

        # Scenario 1: available and commit exists
        with (
            patch.object(
                GitRepository,
                "is_available",
                new_callable=PropertyMock,
                return_value=True,
            ),
            patch.object(
                GitRepository,
                "current_commit",
                new_callable=PropertyMock,
                return_value=mock_commit,
            ),
        ):
            assert repo_instance.current_commit_or_fallback == mock_commit

        # Scenario 2: unavailable
        with patch.object(
            GitRepository,
            "is_available",
            new_callable=PropertyMock,
            return_value=False,
        ):
            fallback = repo_instance.current_commit_or_fallback
            assert isinstance(fallback, GitReference)
            assert fallback.is_head_commit is True
            assert (datetime.now(timezone.utc) - fallback.timestamp).total_seconds() < 5

    @pytest.mark.smoke
    def test_last_tag(self) -> None:
        repo_instance = GitRepository()
        mock_tag = MagicMock()
        with patch.object(
            GitRepository,
            "tags",
            new_callable=PropertyMock,
            return_value=iter([mock_tag]),
        ):
            assert repo_instance.last_tag == mock_tag

    @pytest.mark.smoke
    def test_current_branch(self) -> None:
        repo_instance = GitRepository()
        mock_branch1 = MagicMock(is_current_branch=False)
        mock_branch2 = MagicMock(is_current_branch=True)
        with patch.object(
            GitRepository,
            "branches",
            new_callable=PropertyMock,
            return_value=iter([mock_branch1, mock_branch2]),
        ):
            assert repo_instance.current_branch == mock_branch2

    @pytest.mark.smoke
    def test_head_name(self) -> None:
        repo_instance = GitRepository()
        mock_branch = MagicMock(branch_name="feature-branch")
        mock_commit = MagicMock(short_sha="f1a2b3c")

        # Scenario 1: branch exists
        with patch.object(
            GitRepository,
            "current_branch",
            new_callable=PropertyMock,
            return_value=mock_branch,
        ):
            assert repo_instance.head_name == "feature-branch"

        # Scenario 2: branch is None, commit exists
        with (
            patch.object(
                GitRepository,
                "current_branch",
                new_callable=PropertyMock,
                return_value=None,
            ),
            patch.object(
                GitRepository,
                "current_commit",
                new_callable=PropertyMock,
                return_value=mock_commit,
            ),
        ):
            assert repo_instance.head_name == "f1a2b3c"

        # Scenario 3: both are None
        with (
            patch.object(
                GitRepository,
                "current_branch",
                new_callable=PropertyMock,
                return_value=None,
            ),
            patch.object(
                GitRepository,
                "current_commit",
                new_callable=PropertyMock,
                return_value=None,
            ),
        ):
            assert repo_instance.head_name == ""

    @pytest.mark.smoke
    def test_commits(self) -> None:
        repo_instance = GitRepository()

        mock_avail = MagicMock(stdout="true\n")
        mock_count = MagicMock(stdout="2\n")
        mock_process = MagicMock()
        mock_process.stdout = [
            (
                "sha1|s1|2023-01-01T12:00:00+00:00|Author One|author1@test.com|"
                "feat: message|HEAD -> main, tag: v1.0.0, origin/main, HEAD\n"
            ),
            (
                "sha2|s2|2023-01-02T12:00:00+00:00|Author Two|author2@test.com|"
                "fix: message|another_branch\n"
            ),
            "sha3|s3|short-line\n",
        ]
        mock_process.__enter__.return_value = mock_process

        def mock_run_calls(*args: Any, **kwargs: Any) -> Any:
            cmd = args[0]
            if "--is-inside-work-tree" in cmd:
                return mock_avail
            return mock_count

        with (
            patch("subprocess.run", side_effect=mock_run_calls),
            patch("subprocess.Popen", return_value=mock_process),
        ):
            commits_list = list(repo_instance.commits)
            assert len(commits_list) == 2

            # Check first commit
            assert commits_list[0].commit_sha == "sha1"
            assert commits_list[0].short_sha == "s1"
            assert commits_list[0].tag_name == "v1.0.0"
            assert commits_list[0].branch_name == "main"
            assert commits_list[0].is_current_branch is True
            assert commits_list[0].distance_from_head == 0
            assert commits_list[0].is_head_commit is True
            assert commits_list[0].total_commits == 2

            # Check second commit
            assert commits_list[1].commit_sha == "sha2"
            assert commits_list[1].short_sha == "s2"
            assert commits_list[1].tag_name == ""
            assert commits_list[1].branch_name == "another_branch"
            assert commits_list[1].is_current_branch is False
            assert commits_list[1].distance_from_head == 1
            assert commits_list[1].is_head_commit is False

        # Test subprocess exception handling
        with (
            patch("subprocess.run", side_effect=mock_run_calls),
            patch("subprocess.Popen", side_effect=OSError("Failed")),
        ):
            assert list(repo_instance.commits) == []

    @pytest.mark.smoke
    def test_tags(self) -> None:
        repo_instance = GitRepository()

        mock_avail = MagicMock(stdout="true\n")
        mock_count = MagicMock(stdout="5\n")
        mock_process = MagicMock()
        mock_process.stdout = [
            "v1.0.0|2023-01-01T12:00:00+00:00|sha1\n",
        ]
        mock_process.__enter__.return_value = mock_process

        mock_distance = MagicMock(stdout="3\n")

        def mock_run_calls(*args: Any, **kwargs: Any) -> Any:
            cmd = args[0]
            if "--is-inside-work-tree" in cmd:
                return mock_avail
            elif "rev-list" in cmd:
                return mock_distance
            return mock_count

        mock_commit = MagicMock(commit_sha="sha1")

        with (
            patch.object(
                GitRepository,
                "current_commit",
                new_callable=PropertyMock,
                return_value=mock_commit,
            ),
            patch("subprocess.run", side_effect=mock_run_calls),
            patch("subprocess.Popen", return_value=mock_process),
        ):
            tags_list = list(repo_instance.tags)
            assert len(tags_list) == 1
            assert tags_list[0].tag_name == "v1.0.0"
            assert tags_list[0].commit_sha == "sha1"
            assert tags_list[0].distance_from_head == 3
            assert tags_list[0].is_head_commit is True

    @pytest.mark.smoke
    def test_branches(self) -> None:
        repo_instance = GitRepository()

        mock_avail = MagicMock(stdout="true\n")
        mock_count = MagicMock(stdout="5\n")
        mock_process = MagicMock()
        mock_process.stdout = [
            "main|sha1|*|2023-01-01T12:00:00+00:00\n",
            "dev|sha2| |2023-01-02T12:00:00+00:00\n",
        ]
        mock_process.__enter__.return_value = mock_process

        def mock_run_calls(*args: Any, **kwargs: Any) -> Any:
            cmd = args[0]
            if "--is-inside-work-tree" in cmd:
                return mock_avail
            return mock_count

        mock_commit = MagicMock(commit_sha="sha1")

        with (
            patch.object(
                GitRepository,
                "current_commit",
                new_callable=PropertyMock,
                return_value=mock_commit,
            ),
            patch("subprocess.run", side_effect=mock_run_calls),
            patch("subprocess.Popen", return_value=mock_process),
        ):
            branches_list = list(repo_instance.branches)
            assert len(branches_list) == 2
            assert branches_list[0].branch_name == "main"
            assert branches_list[0].is_current_branch is True
            assert branches_list[0].is_head_commit is True

            assert branches_list[1].branch_name == "dev"
            assert branches_list[1].is_current_branch is False
            assert branches_list[1].is_head_commit is False

    @pytest.mark.smoke
    def test_filtered_dirty_files(self) -> None:
        repo_instance = GitRepository("/mock/repo")

        with (
            patch.object(
                GitRepository,
                "is_available",
                new_callable=PropertyMock,
                return_value=True,
            ),
            patch.object(
                GitRepository,
                "dirty_files",
                new_callable=PropertyMock,
                return_value=[
                    Path("/mock/repo/file1.txt"),
                    Path("/mock/repo/ignored/file2.txt"),
                    Path("/mock/repo/ignored_dir/file3.txt"),
                ],
            ),
        ):
            ignored_list = [
                Path("ignored/file2.txt"),
                Path("/mock/repo/ignored_dir"),
            ]
            result = repo_instance.filtered_dirty_files(ignore_paths=ignored_list)
            assert result == ["/mock/repo/file1.txt"]

    @pytest.mark.sanity
    def test_filtered_dirty_files_invalid(self) -> None:
        repo_instance = GitRepository()

        # Case 1: unavailable and fail_on_unavailable is True
        with patch.object(
            GitRepository,
            "is_available",
            new_callable=PropertyMock,
            return_value=False,
        ):
            with pytest.raises(NotAGitRepositoryError):
                repo_instance.filtered_dirty_files(fail_on_unavailable=True)

            # Case 2: unavailable and fail_on_unavailable is False
            result = repo_instance.filtered_dirty_files(fail_on_unavailable=False)
            assert result == []

    @pytest.mark.sanity
    def test_str(self) -> None:
        repo_instance = GitRepository()

        # Case 1: unavailable
        with patch.object(
            GitRepository,
            "is_available",
            new_callable=PropertyMock,
            return_value=False,
        ):
            expected_str = f"GitRepository({repo_instance.base_path}) - Unavailable"
            assert str(repo_instance) == expected_str

        # Case 2: available and has dirty files, branch, last tag
        mock_branch = MagicMock(branch_name="dev")
        mock_tag = MagicMock(tag_name="v1.0")
        mock_commit = MagicMock(short_sha="a1b2c3d")
        with (
            patch.object(
                GitRepository,
                "is_available",
                new_callable=PropertyMock,
                return_value=True,
            ),
            patch.object(
                GitRepository,
                "dirty_files",
                new_callable=PropertyMock,
                return_value=[Path("file.py")],
            ),
            patch.object(
                GitRepository,
                "commit_count",
                new_callable=PropertyMock,
                return_value=12,
            ),
            patch.object(
                GitRepository,
                "current_commit",
                new_callable=PropertyMock,
                return_value=mock_commit,
            ),
            patch.object(
                GitRepository,
                "last_tag",
                new_callable=PropertyMock,
                return_value=mock_tag,
            ),
            patch.object(
                GitRepository,
                "current_branch",
                new_callable=PropertyMock,
                return_value=mock_branch,
            ),
        ):
            result = str(repo_instance)
            assert "is_available=True" in result
            assert "commit_count=12" in result
            assert "is_dirty=True" in result
            assert "dev*" in result

        # Case 3: branch is None, current_commit exists
        with (
            patch.object(
                GitRepository,
                "is_available",
                new_callable=PropertyMock,
                return_value=True,
            ),
            patch.object(
                GitRepository,
                "dirty_files",
                new_callable=PropertyMock,
                return_value=[],
            ),
            patch.object(
                GitRepository,
                "commit_count",
                new_callable=PropertyMock,
                return_value=10,
            ),
            patch.object(
                GitRepository,
                "current_commit",
                new_callable=PropertyMock,
                return_value=mock_commit,
            ),
            patch.object(
                GitRepository,
                "last_tag",
                new_callable=PropertyMock,
                return_value=None,
            ),
            patch.object(
                GitRepository,
                "current_branch",
                new_callable=PropertyMock,
                return_value=None,
            ),
        ):
            result = str(repo_instance)
            assert "current_commit=a1b2c3d" in result
            assert "last_tag=None" in result
            assert "current_branch=None" in result
            assert "- a1b2c3d" in result

    @pytest.mark.sanity
    def test_repr(self) -> None:
        repo_instance = GitRepository("/mock/path")
        assert repr(repo_instance) == "GitRepository(base_path=PosixPath('/mock/path'))"
