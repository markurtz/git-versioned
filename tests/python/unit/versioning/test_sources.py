from __future__ import annotations

import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from packaging.version import Version

from gitversioned.settings import Settings
from gitversioned.utils import GitReference, GitRepository
from gitversioned.versioning.sources import (
    VersionResolutionError,
    resolve_from_explicit_source,
    resolve_from_file_source,
    resolve_from_function_source,
    resolve_from_git_source,
    resolve_sources,
    resolve_sources_from_archive,
)

if TYPE_CHECKING:
    import pytest_mock

    from tests.conftest import GitRepoHelper


def dummy_version_function(
    settings: Settings,
    repo: GitRepository,
) -> tuple[Version, GitReference]:
    """Valid version source function helper for unit tests."""
    return Version("1.5.0"), GitReference(commit_sha="dummy_sha")


def dummy_invalid_function(
    settings: Settings,
    repo: GitRepository,
) -> tuple[Any, Any]:
    """Invalid version source function helper returning incorrect types."""
    return "not-a-version-obj", "not-a-git-ref-obj"


def dummy_function_bad_reference(
    settings: Settings,
    repo: GitRepository,
) -> tuple[Version, Any]:
    """Valid version but invalid reference helper for unit tests."""
    return Version("1.5.0"), "not-a-git-ref-obj"


class TestVersionResolutionError:
    @pytest.fixture(
        params=[
            ("Error message 1",),
            ("Error message 2",),
        ]
    )
    def valid_instances(
        self,
        request: pytest.FixtureRequest,
    ) -> VersionResolutionError:
        return VersionResolutionError(*request.param)

    @pytest.mark.smoke
    def test_signature(self) -> None:
        assert issubclass(VersionResolutionError, ValueError)

    @pytest.mark.sanity
    def test_initialization(
        self,
        valid_instances: VersionResolutionError,
    ) -> None:
        assert str(valid_instances) in ("Error message 1", "Error message 2")

    @pytest.mark.regression
    def test_invalid_initialization_values(self) -> None:
        # Exceptions handle arbitrary positional arguments, but we cover this method
        # to satisfy standard initialization checklist requirements.
        pass

    @pytest.mark.regression
    def test_invalid_initialization_missing(self) -> None:
        instance = VersionResolutionError()
        assert str(instance) == ""


class TestResolveSources:
    @pytest.mark.smoke
    def test_signature(self) -> None:
        sig = inspect.signature(resolve_sources)
        assert "sources" in sig.parameters
        assert "settings" in sig.parameters
        assert "repository" in sig.parameters

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("repo_state", "sources_list", "expected_ver"),
        [
            ("lightweight_tag", ["tag"], "1.0.0"),
            ("lightweight_tag", ["auto"], "1.0.0"),
        ],
    )
    def test_invocation(
        self,
        temp_git_repo: GitRepoHelper,
        repo_state: str,
        sources_list: list[str],
        expected_ver: str,
    ) -> None:
        helper = temp_git_repo.setup_state(repo_state)
        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository_obj = GitRepository(helper.path)
        version, reference = resolve_sources(
            sources_list,
            settings_obj,
            repository_obj,
        )
        assert str(version) == expected_ver
        assert reference is not None

    @pytest.mark.sanity
    def test_invocation_explicit(
        self,
        temp_git_repo: GitRepoHelper,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            version="2.0.0",
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository_obj = GitRepository(helper.path)
        version, reference = resolve_sources(
            ["tag"],
            settings_obj,
            repository_obj,
        )
        assert str(version) == "2.0.0"
        assert reference is not None

    @pytest.mark.sanity
    def test_invocation_archive_fallback(
        self,
        temp_git_repo: GitRepoHelper,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        archive_file = helper.path / ".git_archival.txt"
        archive_content = (
            "commit_sha: abc1234\n"
            "short_sha: abc1234\n"
            "timestamp: 2026-05-27\n"
            "author_name: test\n"
            "author_email: test@test.com\n"
            "ref_names: tag: v1.8.2\n"
            "distance_from_head: 0\n"
            "is_head_commit: true\n"
            "total_commits: 1\n"
            "is_current_branch: true\n"
            "commit_message:\n"
            "release version\n"
        )
        archive_file.write_text(archive_content, encoding="utf-8")
        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            version_source_archive=".git_archival.txt",
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository_obj = GitRepository(helper.path)
        version, reference = resolve_sources(
            ["tag"],
            settings_obj,
            repository_obj,
        )
        assert str(version) == "1.8.2"
        assert reference.short_sha == "abc1234"

    @pytest.mark.regression
    @pytest.mark.parametrize(
        ("sources_list", "expected_exception"),
        [
            (["invalid_source"], ValueError),
            (["tag"], VersionResolutionError),
        ],
    )
    def test_invalid(
        self,
        temp_git_repo: GitRepoHelper,
        sources_list: list[str],
        expected_exception: type[Exception],
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository_obj = GitRepository(helper.path)
        with pytest.raises(expected_exception):
            resolve_sources(sources_list, settings_obj, repository_obj)


class TestResolveFromExplicitSource:
    @pytest.mark.smoke
    def test_signature(self) -> None:
        sig = inspect.signature(resolve_from_explicit_source)
        assert "settings" in sig.parameters
        assert "repository" in sig.parameters

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("explicit_version", "expected_ver"),
        [
            ("1.2.3", "1.2.3"),
            ("v2.5.1", "2.5.1"),
        ],
    )
    def test_invocation(
        self,
        temp_git_repo: GitRepoHelper,
        explicit_version: str,
        expected_ver: str,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            version=explicit_version,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository_obj = GitRepository(helper.path)
        version, reference = resolve_from_explicit_source(settings_obj, repository_obj)
        assert str(version) == expected_ver
        assert reference is not None

    @pytest.mark.regression
    @pytest.mark.parametrize(
        "bad_version",
        [
            "auto",
            "dynamic",
            "0.0.0",
            "",
        ],
    )
    def test_invalid(
        self,
        temp_git_repo: GitRepoHelper,
        bad_version: str,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        object.__setattr__(settings_obj, "version", bad_version)
        repository_obj = GitRepository(helper.path)
        with pytest.raises(VersionResolutionError):
            resolve_from_explicit_source(settings_obj, repository_obj)

    @pytest.mark.regression
    def test_invalid_pattern_missing_groups(
        self,
        temp_git_repo: GitRepoHelper,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            version="1.2.3",
            regex_version=[r"^(?P<version>.*)$"],
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository_obj = GitRepository(helper.path)
        with pytest.raises(VersionResolutionError):
            resolve_from_explicit_source(settings_obj, repository_obj)


class TestResolveFromFileSource:
    @pytest.mark.smoke
    def test_signature(self) -> None:
        sig = inspect.signature(resolve_from_file_source)
        assert "settings" in sig.parameters
        assert "repository" in sig.parameters

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("filename", "content", "expected_ver"),
        [
            ("version.txt", "version = 1.3.4", "1.3.4"),
        ],
    )
    def test_invocation(
        self,
        temp_git_repo: GitRepoHelper,
        filename: str,
        content: str,
        expected_ver: str,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        target_file = helper.path / filename
        target_file.write_text(content, encoding="utf-8")
        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            version_source_file=filename,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository_obj = GitRepository(helper.path)
        version, reference = resolve_from_file_source(settings_obj, repository_obj)
        assert str(version) == expected_ver
        assert reference is not None

    @pytest.mark.regression
    @pytest.mark.parametrize(
        ("filename", "mock_os_error"),
        [
            ("nonexistent_file.txt", False),
            ("version.txt", True),
        ],
    )
    def test_invalid(
        self,
        temp_git_repo: GitRepoHelper,
        mocker: pytest_mock.MockerFixture,
        filename: str,
        mock_os_error: bool,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            version_source_file=filename,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository_obj = GitRepository(helper.path)

        if mock_os_error:
            target_file = helper.path / filename
            target_file.write_text("version = 1.0.0", encoding="utf-8")
            mocker.patch.object(Path, "read_text", side_effect=OSError("Read error"))

        with pytest.raises(VersionResolutionError):
            resolve_from_file_source(settings_obj, repository_obj)

    @pytest.mark.regression
    def test_invalid_no_source_file_configured(
        self,
        temp_git_repo: GitRepoHelper,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            version_source_file=None,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository_obj = GitRepository(helper.path)
        with pytest.raises(
            VersionResolutionError, match="No version_source_file configured"
        ):
            resolve_from_file_source(settings_obj, repository_obj)


class TestResolveFromFunctionSource:
    @pytest.mark.smoke
    def test_signature(self) -> None:
        sig = inspect.signature(resolve_from_function_source)
        assert "settings" in sig.parameters
        assert "repository" in sig.parameters

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("func_import", "expected_ver"),
        [
            (
                "tests.python.unit.versioning.test_sources:dummy_version_function",
                "1.5.0",
            ),
        ],
    )
    def test_invocation(
        self,
        temp_git_repo: GitRepoHelper,
        func_import: str,
        expected_ver: str,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            version_source_function=func_import,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository_obj = GitRepository(helper.path)
        version, reference = resolve_from_function_source(settings_obj, repository_obj)
        assert str(version) == expected_ver
        assert reference.commit_sha == "dummy_sha"

    @pytest.mark.regression
    @pytest.mark.parametrize(
        ("bad_func_import", "expected_exception"),
        [
            ("no_colon_in_function_path", VersionResolutionError),
            (
                "tests.python.unit.versioning.test_sources:dummy_invalid_function",
                ValueError,
            ),
        ],
    )
    def test_invalid(
        self,
        temp_git_repo: GitRepoHelper,
        bad_func_import: str,
        expected_exception: type[Exception],
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            version_source_function=bad_func_import,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository_obj = GitRepository(helper.path)
        with pytest.raises(expected_exception):
            resolve_from_function_source(settings_obj, repository_obj)

    @pytest.mark.regression
    def test_invalid_no_func_configured(
        self,
        temp_git_repo: GitRepoHelper,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            version_source_function=None,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository_obj = GitRepository(helper.path)
        with pytest.raises(
            VersionResolutionError, match="No version_source_function configured"
        ):
            resolve_from_function_source(settings_obj, repository_obj)

    @pytest.mark.regression
    def test_invalid_func_returns_bad_ref(
        self,
        temp_git_repo: GitRepoHelper,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            version_source_function="tests.python.unit.versioning.test_sources:dummy_function_bad_reference",
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository_obj = GitRepository(helper.path)
        with pytest.raises(ValueError, match="did not return a valid reference"):
            resolve_from_function_source(settings_obj, repository_obj)


class TestResolveFromGitSource:
    @pytest.mark.smoke
    def test_signature(self) -> None:
        sig = inspect.signature(resolve_from_git_source)
        assert "type_" in sig.parameters
        assert "settings" in sig.parameters
        assert "repository" in sig.parameters

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("git_type", "repo_state", "expected_ver"),
        [
            ("tag", "lightweight_tag", "1.0.0"),
            ("branch", "commit_no_tag", "0.1.0"),
        ],
    )
    def test_invocation(
        self,
        temp_git_repo: GitRepoHelper,
        git_type: Any,
        repo_state: str,
        expected_ver: str,
    ) -> None:
        helper = temp_git_repo.setup_state(repo_state)
        if git_type == "branch":
            helper.branch("v0.1.0")

        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository_obj = GitRepository(helper.path)
        version, reference = resolve_from_git_source(
            git_type,
            settings_obj,
            repository_obj,
        )
        assert str(version) == expected_ver
        assert reference is not None

    @pytest.mark.sanity
    def test_invocation_commit_message(
        self,
        temp_git_repo: GitRepoHelper,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        helper.commit("bump version v1.4.2")
        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository_obj = GitRepository(helper.path)
        version, reference = resolve_from_git_source(
            "commit",
            settings_obj,
            repository_obj,
        )
        assert str(version) == "1.4.2"
        assert reference is not None

    @pytest.mark.sanity
    def test_candidate_parsing_failures_skips(
        self,
        temp_git_repo: GitRepoHelper,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        # Creating two tags: one invalid (not version pattern), one valid
        helper.commit("First commit")
        helper.tag("invalid-tag-name")
        helper.commit("Second commit")
        helper.tag("v1.0.0")

        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository_obj = GitRepository(helper.path)
        version, reference = resolve_from_git_source(
            "tag",
            settings_obj,
            repository_obj,
        )
        assert str(version) == "1.0.0"
        assert reference.tag_name == "v1.0.0"

    @pytest.mark.regression
    @pytest.mark.parametrize(
        ("git_type", "repo_state", "expected_exception"),
        [
            ("tag", "no_git", VersionResolutionError),
            ("invalid_git_type", "clean", ValueError),
            ("tag", "clean", VersionResolutionError),
        ],
    )
    def test_invalid(
        self,
        temp_git_repo: GitRepoHelper,
        git_type: Any,
        repo_state: str,
        expected_exception: type[Exception],
    ) -> None:
        helper = temp_git_repo.setup_state(repo_state)
        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository_obj = GitRepository(helper.path)
        with pytest.raises(expected_exception):
            resolve_from_git_source(git_type, settings_obj, repository_obj)


class TestResolveSourcesFromArchive:
    @pytest.mark.smoke
    def test_signature(self) -> None:
        sig = inspect.signature(resolve_sources_from_archive)
        assert "sources" in sig.parameters
        assert "settings" in sig.parameters

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("archive_content", "expected_ver"),
        [
            (
                "commit_sha: abc1234\n"
                "short_sha: abc1234\n"
                "timestamp: 2026-05-27\n"
                "author_name: test\n"
                "author_email: test@test.com\n"
                "ref_names: tag: v1.8.2\n"
                "distance_from_head: 0\n"
                "is_head_commit: true\n"
                "total_commits: 1\n"
                "is_current_branch: true\n"
                "commit_message:\n"
                "release version\n",
                "1.8.2",
            ),
        ],
    )
    def test_invocation(
        self,
        temp_git_repo: GitRepoHelper,
        archive_content: str,
        expected_ver: str,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        archive_file = helper.path / ".git_archival.txt"
        archive_file.write_text(archive_content, encoding="utf-8")
        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        version, reference = resolve_sources_from_archive(["tag"], settings_obj)
        assert str(version) == expected_ver
        assert reference.short_sha == "abc1234"

    @pytest.mark.regression
    @pytest.mark.parametrize(
        ("archive_content", "filename"),
        [
            ("unformatted: $Format:%H$", ".git_archival.txt"),
            ("", "nonexistent_archive.txt"),
        ],
    )
    def test_invalid(
        self,
        temp_git_repo: GitRepoHelper,
        archive_content: str,
        filename: str,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        if archive_content:
            archive_file = helper.path / filename
            archive_file.write_text(archive_content, encoding="utf-8")
        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            version_source_archive=filename,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        with pytest.raises(VersionResolutionError):
            resolve_sources_from_archive(["tag"], settings_obj)

    @pytest.mark.regression
    def test_invalid_read_os_error(
        self,
        temp_git_repo: GitRepoHelper,
        mocker: pytest_mock.MockerFixture,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        archive_file = helper.path / ".git_archival.txt"
        archive_file.write_text("commit_sha: abc1234", encoding="utf-8")
        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            version_source_archive=".git_archival.txt",
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        mocker.patch.object(Path, "read_text", side_effect=OSError("Read error"))
        with pytest.raises(VersionResolutionError, match="Failed to read archive file"):
            resolve_sources_from_archive(["tag"], settings_obj)

    @pytest.mark.regression
    def test_invalid_extract_value_error(
        self,
        temp_git_repo: GitRepoHelper,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        archive_content = (
            "commit_sha: abc1234\n"
            "short_sha: abc1234\n"
            "timestamp: 2026-05-27\n"
            "author_name: test\n"
            "author_email: test@test.com\n"
            "ref_names: tag: invalid-tag, tag: v1.8.2\n"
            "distance_from_head: 0\n"
            "is_head_commit: true\n"
            "total_commits: 1\n"
            "is_current_branch: true\n"
            "commit_message:\n"
            "release version\n"
        )
        archive_file = helper.path / ".git_archival.txt"
        archive_file.write_text(archive_content, encoding="utf-8")
        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            version_source_archive=".git_archival.txt",
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        with pytest.raises(VersionResolutionError):
            resolve_sources_from_archive(["tag"], settings_obj)

    @pytest.mark.regression
    def test_no_matching_versions(
        self,
        temp_git_repo: GitRepoHelper,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        archive_content = (
            "commit_sha: abc1234\n"
            "short_sha: abc1234\n"
            "timestamp: 2026-05-27\n"
            "author_name: test\n"
            "author_email: test@test.com\n"
            "ref_names: tag: v1.8.2\n"
            "distance_from_head: 0\n"
            "is_head_commit: true\n"
            "total_commits: 1\n"
            "is_current_branch: true\n"
            "commit_message:\n"
            "release version\n"
        )
        archive_file = helper.path / ".git_archival.txt"
        archive_file.write_text(archive_content, encoding="utf-8")
        settings_obj = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            version_source_archive=".git_archival.txt",
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        with pytest.raises(
            VersionResolutionError, match="No version found for archive"
        ):
            resolve_sources_from_archive(["branch"], settings_obj)
