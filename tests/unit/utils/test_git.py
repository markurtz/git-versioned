from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from pydantic import ValidationError

from gitversioned.utils.git import GitReference, GitRepository, NotAGitRepositoryError


class TestNotAGitRepositoryError:
    @pytest.mark.smoke
    def test_initialization(self) -> None:
        error_instance = NotAGitRepositoryError("test message")
        assert isinstance(error_instance, Exception)
        assert str(error_instance) == "test message"


class TestGitReference:
    @pytest.fixture(
        params=[
            {
                "commit_sha": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
                "short_sha": "a1b2c3d",
                "timestamp": datetime.now(timezone.utc),
                "distance_from_head": 5,
                "is_head_commit": False,
                "total_commits": 100,
            },
            {
                "commit_sha": "0987654321098765432109876543210987654321",
                "short_sha": "0987654",
                "timestamp": datetime.now(timezone.utc),
                "distance_from_head": 0,
                "is_head_commit": True,
                "total_commits": 1,
            },
        ]
    )
    def valid_instances(self, request: pytest.FixtureRequest) -> dict[str, Any]:
        return request.param

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        model_instance = GitReference(**valid_instances)
        assert model_instance.commit_sha == valid_instances["commit_sha"]
        assert model_instance.short_sha == valid_instances["short_sha"]
        assert model_instance.timestamp == valid_instances["timestamp"]
        assert (
            model_instance.distance_from_head == valid_instances["distance_from_head"]
        )
        assert model_instance.is_head_commit == valid_instances["is_head_commit"]
        assert model_instance.total_commits == valid_instances["total_commits"]

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("invalid_field", "invalid_value"),
        [("distance_from_head", "invalid"), ("is_head_commit", "invalid")],
    )
    def test_invalid_initialization_values(
        self, valid_instances: dict[str, Any], invalid_field: str, invalid_value: Any
    ) -> None:
        invalid_data = valid_instances.copy()
        invalid_data[invalid_field] = invalid_value
        with pytest.raises(ValidationError):
            GitReference(**invalid_data)

    @pytest.mark.regression
    def test_marshalling(self, valid_instances: dict[str, Any]) -> None:
        model_instance = GitReference(**valid_instances)
        dumped_data = model_instance.model_dump()
        assert dumped_data["commit_sha"] == valid_instances["commit_sha"]
        validated_instance = GitReference.model_validate(dumped_data)
        assert validated_instance == model_instance


class TestGitRepository:
    @pytest.fixture(
        params=[
            {
                "repository_path": None,
            },
            {
                "repository_path": "/some/path",
            },
        ]
    )
    def valid_instances(self, request: pytest.FixtureRequest) -> dict[str, Any]:
        return request.param

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        repo_instance = GitRepository(**valid_instances)
        expected_path = Path(valid_instances["repository_path"] or Path.cwd()).resolve()
        assert repo_instance.base_path == expected_path

    @pytest.mark.smoke
    def test_is_available(self) -> None:
        repo_instance = GitRepository()
        with patch.object(
            repo_instance, "_execute_command", return_value="true"
        ) as mock_exec:
            assert repo_instance.is_available is True
            mock_exec.assert_called_once_with(["rev-parse", "--is-inside-work-tree"])

        with patch.object(repo_instance, "_execute_command", return_value="false"):
            assert repo_instance.is_available is False

    @pytest.mark.smoke
    def test_root_directory(self) -> None:
        repo_instance = GitRepository()
        with (
            patch.object(repo_instance, "_ensure_valid_repository") as mock_ensure,
            patch.object(
                repo_instance, "_execute_command", return_value="/mock/root"
            ) as mock_exec,
        ):
            assert repo_instance.root_directory == Path("/mock/root")
            mock_ensure.assert_called_once()
            mock_exec.assert_called_once_with(["rev-parse", "--show-toplevel"])

    @pytest.mark.smoke
    def test_repository_name(self) -> None:
        repo_instance = GitRepository()
        with patch.object(
            GitRepository, "remote_origin_url", new_callable=PropertyMock
        ) as mock_remote:
            mock_remote.return_value = "https://github.com/user/repo.git"
            assert repo_instance.repository_name == "repo"

        repo_instance2 = GitRepository()
        with (
            patch.object(
                GitRepository, "remote_origin_url", new_callable=PropertyMock
            ) as mock_remote2,
            patch.object(
                GitRepository, "root_directory", new_callable=PropertyMock
            ) as mock_root,
        ):
            mock_remote2.return_value = ""
            mock_root.return_value = Path("/local/dir/test-repo")
            assert repo_instance2.repository_name == "test-repo"

    @pytest.mark.smoke
    def test_remote_origin_url(self) -> None:
        repo_instance = GitRepository()
        with patch.object(
            repo_instance, "_execute_command", return_value="https://github.com"
        ) as mock_exec:
            assert repo_instance.remote_origin_url == "https://github.com"
            mock_exec.assert_called_once_with(["config", "--get", "remote.origin.url"])

    @pytest.mark.smoke
    def test_commit_count(self) -> None:
        repo_instance = GitRepository()
        with (
            patch.object(
                GitRepository,
                "is_available",
                new_callable=PropertyMock,
                return_value=True,
            ),
            patch.object(
                repo_instance, "_execute_command", return_value="2"
            ) as mock_exec,
        ):
            assert repo_instance.commit_count == 2
            mock_exec.assert_called_once_with(["rev-list", "--count", "HEAD"])

        with (
            patch.object(
                GitRepository,
                "is_available",
                new_callable=PropertyMock,
                return_value=True,
            ),
            patch.object(repo_instance, "_execute_command", return_value=""),
        ):
            assert repo_instance.commit_count == 0

        with patch.object(
            GitRepository, "is_available", new_callable=PropertyMock, return_value=False
        ):
            assert repo_instance.commit_count == 0

    @pytest.mark.smoke
    def test_is_dirty(self) -> None:
        repo_instance = GitRepository()
        with patch.object(
            GitRepository, "dirty_files", new_callable=PropertyMock
        ) as mock_dirty:
            mock_dirty.return_value = ["file1.txt", "file2.txt"]
            assert repo_instance.is_dirty is True

        repo_instance2 = GitRepository()
        with patch.object(
            GitRepository, "dirty_files", new_callable=PropertyMock
        ) as mock_dirty2:
            mock_dirty2.return_value = []
            assert repo_instance2.is_dirty is False

    @pytest.mark.smoke
    def test_dirty_files(self) -> None:
        repo_instance = GitRepository()
        mock_output = " M file1.txt\n?? file2.txt\n"
        with patch.object(
            repo_instance, "_execute_command", return_value=mock_output
        ) as mock_exec:
            assert repo_instance.dirty_files == ["file1.txt", "file2.txt"]
            mock_exec.assert_called_once_with(["status", "--porcelain"])

    @pytest.mark.smoke
    def test_current_commit(self) -> None:
        repo_instance = GitRepository()
        mock_commit_data = MagicMock()
        with patch.object(
            GitRepository, "commits", new_callable=PropertyMock
        ) as mock_get:
            mock_get.return_value = iter([mock_commit_data])
            assert repo_instance.current_commit == mock_commit_data
            mock_get.assert_called_once()

    @pytest.mark.smoke
    def test_last_tag(self) -> None:
        repo_instance = GitRepository()
        mock_tag_data = MagicMock()
        with patch.object(GitRepository, "tags", new_callable=PropertyMock) as mock_get:
            mock_get.return_value = iter([mock_tag_data])
            assert repo_instance.last_tag == mock_tag_data
            mock_get.assert_called_once()

    @pytest.mark.smoke
    def test_current_branch(self) -> None:
        repo_instance = GitRepository()
        mock_branch1 = MagicMock(is_current_branch=False)
        mock_branch2 = MagicMock(is_current_branch=True)
        with patch.object(
            GitRepository, "branches", new_callable=PropertyMock
        ) as mock_get:
            mock_get.return_value = iter([mock_branch1, mock_branch2])
            assert repo_instance.current_branch == mock_branch2
            mock_get.assert_called_once()

    @pytest.mark.smoke
    def test_head_name(self) -> None:
        repo_instance1 = GitRepository()
        with patch.object(
            GitRepository, "current_branch", new_callable=PropertyMock
        ) as mock_branch:
            mock_branch.return_value = MagicMock(branch_name="main")
            assert repo_instance1.head_name == "main"

        repo_instance2 = GitRepository()
        with (
            patch.object(
                GitRepository, "current_branch", new_callable=PropertyMock
            ) as mock_branch2,
            patch.object(
                GitRepository, "current_commit", new_callable=PropertyMock
            ) as mock_commit,
        ):
            mock_branch2.return_value = None
            mock_commit.return_value = MagicMock(short_sha="abcdefg")
            assert repo_instance2.head_name == "abcdefg"

        repo_instance3 = GitRepository()
        with (
            patch.object(
                GitRepository, "current_branch", new_callable=PropertyMock
            ) as mock_branch3,
            patch.object(
                GitRepository, "current_commit", new_callable=PropertyMock
            ) as mock_commit3,
        ):
            mock_branch3.return_value = None
            mock_commit3.return_value = None
            assert repo_instance3.head_name == ""

    @pytest.mark.smoke
    def test_commits(self) -> None:
        repo_instance = GitRepository()
        mock_log_output = [
            "a1b2|a1b|2023-01-01T12:00:00Z|"
            "Author One|author1@test.com|feat: message one|HEAD -> main, tag: v1.0.0",
            "c3d4|c3d|2023-01-02T12:00:00Z|"
            "Author Two|author2@test.com|fix: message two|",
        ]
        with (
            patch.object(repo_instance, "_ensure_valid_repository"),
            patch.object(
                repo_instance, "_stream_command", return_value=iter(mock_log_output)
            ),
        ):
            commits_list = list(repo_instance.commits)
            assert len(commits_list) == 2
            assert commits_list[0].commit_message == "feat: message one"
            assert commits_list[0].is_head_commit is True
            assert commits_list[0].distance_from_head == 0
            assert commits_list[1].commit_message == "fix: message two"
            assert commits_list[1].is_head_commit is False
            assert commits_list[1].distance_from_head == 1

    @pytest.mark.smoke
    def test_tags(self) -> None:
        repo_instance = GitRepository()
        mock_tags_output = [
            "v1.0.0|2023-01-01T12:00:00Z|a1b2c3d4",
            "v1.1.0|2023-01-02T12:00:00Z|e5f6g7h8",
        ]
        with (
            patch.object(repo_instance, "_ensure_valid_repository"),
            patch.object(
                GitRepository, "current_commit", new_callable=PropertyMock
            ) as mock_commit,
        ):
            mock_commit.return_value = MagicMock(commit_sha="a1b2c3d4")
            with (
                patch.object(
                    repo_instance,
                    "_stream_command",
                    return_value=iter(mock_tags_output),
                ),
                patch.object(repo_instance, "_execute_command", return_value="5"),
            ):
                tags_list = list(repo_instance.tags)
                assert len(tags_list) == 2
                assert tags_list[0].tag_name == "v1.0.0"
                assert tags_list[0].is_head_commit is True
                assert tags_list[0].distance_from_head == 5
                assert tags_list[1].tag_name == "v1.1.0"
                assert tags_list[1].is_head_commit is False
                assert tags_list[1].distance_from_head == 5

    @pytest.mark.smoke
    def test_branches(self) -> None:
        repo_instance = GitRepository()
        mock_branches_output = [
            "main|a1b2c3d4|*|2023-01-01T12:00:00Z",
            "feature|e5f6g7h8| |2023-01-02T12:00:00Z",
        ]
        with (
            patch.object(repo_instance, "_ensure_valid_repository"),
            patch.object(
                GitRepository, "current_commit", new_callable=PropertyMock
            ) as mock_commit,
        ):
            mock_commit.return_value = MagicMock(commit_sha="a1b2c3d4")
            with patch.object(
                repo_instance,
                "_stream_command",
                return_value=iter(mock_branches_output),
            ):
                branches_list = list(repo_instance.branches)
                assert len(branches_list) == 2
                assert branches_list[0].branch_name == "main"
                assert branches_list[0].is_current_branch is True
                assert branches_list[0].is_head_commit is True
                assert branches_list[1].branch_name == "feature"
                assert branches_list[1].is_current_branch is False
                assert branches_list[1].is_head_commit is False

    @pytest.mark.regression
    def test_stream_command(self) -> None:
        repo_instance = GitRepository()
        mock_process = MagicMock()
        mock_process.stdout = ["line1\n", "  line2  \n", "\n", "line3"]
        mock_process.__enter__.return_value = mock_process

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            result_output = list(repo_instance._stream_command(["log"]))
            assert result_output == ["line1", "line2", "line3"]
            mock_popen.assert_called_once()

        with patch(
            "subprocess.Popen", side_effect=subprocess.CalledProcessError(1, [])
        ):
            result_error = list(repo_instance._stream_command(["invalid"]))
            assert result_error == []

    @pytest.mark.regression
    def test_execute_command(self) -> None:
        repo_instance = GitRepository()
        mock_run = MagicMock()
        mock_run.stdout = " success \n"
        with patch("subprocess.run", return_value=mock_run) as mock_subprocess_run:
            result_output = repo_instance._execute_command(["status"])
            assert result_output == "success"
            mock_subprocess_run.assert_called_once()

        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result_error = repo_instance._execute_command(["invalid"])
            assert result_error == ""

    @pytest.mark.smoke
    def test_ensure_valid_repository(self) -> None:
        repo_instance = GitRepository()
        with patch.object(
            GitRepository, "is_available", new_callable=PropertyMock
        ) as mock_is_avail:
            mock_is_avail.return_value = True
            repo_instance._ensure_valid_repository()  # Should not raise

            mock_is_avail.return_value = False
            with pytest.raises(NotAGitRepositoryError, match="not a Git repository"):
                repo_instance._ensure_valid_repository()
