from __future__ import annotations

import typing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from packaging.version import Version

from gitversioned.settings import Settings
from gitversioned.utils import BuildEnvironment, GitReference, GitRepository
from gitversioned.versioning import (
    generate_version_file,
    resolve_and_generate_version,
    resolve_version,
)


class TestResolveVersion:
    """Test suite for the resolve_version function."""

    @pytest.mark.smoke
    def test_function_signatures(self) -> None:
        """Test resolve_version signature."""
        assert callable(resolve_version)

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("version_str", "expected", "expect_error"),
        [
            ("1.5.0", "1.5.0", False),
            ("v2.0.0", "2.0.0", False),
            ("releases/v3.1.2", "3.1.2", False),
            ("auto", None, True),
            ("dynamic", None, True),
            ("0.0.0", None, True),
            ("", None, True),
        ],
    )
    def test_source_configs(
        self, version_str: str, expected: str | None, expect_error: bool
    ) -> None:
        """Test 'explicit' version source type."""
        repository = MagicMock(spec=GitRepository)
        repository.is_available = True
        repository.is_dirty = False
        repository.current_commit = MagicMock(
            spec=GitReference, distance_from_head=0, is_head_commit=True
        )
        environment = MagicMock(spec=BuildEnvironment)

        settings = Settings(
            package_name="test_pkg",
            source_type=typing.cast("typing.Any", ["explicit"]),
            version=version_str,
            version_type="release",
        )

        if expect_error:
            with pytest.raises(ValueError):
                resolve_version(settings, repository, environment)
        else:
            version, _ = resolve_version(settings, repository, environment)
            assert str(version) == expected

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("file_exists", "content", "expected", "version_source_file"),
        [
            (True, "version = '1.2.3'", "1.2.3", "version.txt"),
            (True, "VERSION = '2.0.0'", "2.0.0", "version.txt"),
            (True, '__version__ = "v3.1.4-alpha"', "3.1.4", "__init__.py"),
            (False, "", "0.1.0", "version.txt"),
            (True, "version = '1.2.3'", "0.1.0", ""),
        ],
    )
    def test_source_version_file(
        self, file_exists: bool, content: str, expected: str, version_source_file: str
    ) -> None:
        """Test 'file' version source type."""
        repository = MagicMock(spec=GitRepository)
        repository.is_available = True
        repository.is_dirty = False
        repository.current_commit = MagicMock(
            spec=GitReference, distance_from_head=0, is_head_commit=True
        )
        environment = MagicMock(spec=BuildEnvironment)

        settings = Settings(
            package_name="test_pkg",
            source_type=typing.cast("typing.Any", ["file"]),
            version_source_file=version_source_file,
            version_type="release",
        )
        with (
            patch("gitversioned.versioning.Path.exists", return_value=file_exists),
            patch("gitversioned.versioning.Path.read_text", return_value=content),
        ):
            version, _ = resolve_version(settings, repository, environment)
            assert str(version) == expected

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("has_func_setting", "func_return", "expected", "expected_error"),
        [
            (True, (Version("2.3.4"), None), "2.3.4", None),
            (False, None, "0.1.0", None),
            (True, Exception("Mocked error"), None, "Mocked error"),
        ],
    )
    def test_source_version_function(
        self,
        has_func_setting: bool,
        func_return: Any,
        expected: str | None,
        expected_error: str | None,
    ) -> None:
        """Test 'function' version source type."""
        repository = MagicMock(spec=GitRepository)
        repository.is_available = True
        repository.is_dirty = False
        repository.current_commit = MagicMock(
            spec=GitReference, distance_from_head=0, is_head_commit=True
        )
        environment = MagicMock(spec=BuildEnvironment)

        settings = Settings(
            package_name="test_pkg",
            source_type=typing.cast("typing.Any", ["function"]),
            version_source_function="mock_mod:mock_func" if has_func_setting else "",
            version_type="release",
        )
        with patch("gitversioned.versioning.importlib.import_module") as mock_import:
            mock_module = MagicMock()
            if isinstance(func_return, Exception):
                mock_module.mock_func.side_effect = func_return
            else:
                mock_module.mock_func.return_value = func_return
            mock_import.return_value = mock_module

            if expected_error:
                with pytest.raises(Exception, match=expected_error):
                    resolve_version(settings, repository, environment)
            else:
                version, _ = resolve_version(settings, repository, environment)
                assert str(version) == expected

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("tag_name", "expected", "custom_regex", "is_available"),
        [
            ("v3.1.2", "3.1.2", None, True),
            ("release/4.0.0", "4.0.0", None, True),
            ("releases/v5.1.0", "5.1.0", None, True),
            ("1.0.0", "1.0.0", None, True),
            ("v3.1.2", "0.1.0", [r"(.*)"], True),
            ("v3.1.2", "0.1.0", None, False),
        ],
    )
    def test_source_git_tag(
        self,
        tag_name: str,
        expected: str,
        custom_regex: list[str] | None,
        is_available: bool,
    ) -> None:
        """Test 'tag' version source type."""
        repository = MagicMock(spec=GitRepository)
        repository.is_available = is_available
        repository.is_dirty = False
        repository.current_commit = MagicMock(
            spec=GitReference, distance_from_head=0, is_head_commit=True
        )
        repository.tags = (
            [
                MagicMock(
                    spec=GitReference,
                    tag_name=tag_name,
                    distance_from_head=0,
                    is_head_commit=True,
                    timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
                    short_sha="abc",
                    commit_sha="abc1234",
                )
            ]
            if is_available
            else []
        )
        environment = MagicMock(spec=BuildEnvironment)

        kwargs: dict[str, Any] = {
            "package_name": "test_pkg",
            "source_type": ["tag"],
            "version_type": "release",
        }
        if custom_regex is not None:
            kwargs["regex_tag"] = custom_regex

        settings = Settings(**kwargs)
        version, _ = resolve_version(settings, repository, environment)
        assert str(version) == expected

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("branch_name", "expected"),
        [
            ("release/4.2.0", "4.2.0"),
            ("releases/v5.0.0", "5.0.0"),
            ("v3.1.2", "3.1.2"),
            ("1.0.0", "1.0.0"),
            ("main", "0.1.0"),
        ],
    )
    def test_source_git_branch(self, branch_name: str, expected: str) -> None:
        """Test 'branch' version source type."""
        repository = MagicMock(spec=GitRepository)
        repository.is_available = True
        repository.is_dirty = False
        repository.current_commit = MagicMock(
            spec=GitReference, distance_from_head=0, is_head_commit=True
        )
        repository.current_branch = MagicMock(
            spec=GitReference,
            branch_name=branch_name,
            is_head_branch=True,
            distance_from_head=0,
            is_head_commit=True,
            timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
            short_sha="def",
            commit_sha="def1234",
        )
        environment = MagicMock(spec=BuildEnvironment)

        settings = Settings(
            package_name="test_pkg",
            source_type=typing.cast("typing.Any", ["branch"]),
            version_type="release",
        )
        version, _ = resolve_version(settings, repository, environment)
        assert str(version) == expected

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("commit_message", "expected"),
        [
            ("Release 5.0.0", "5.0.0"),
            ("bump v6.1.2", "6.1.2"),
            ("bump version 7.0.0", "7.0.0"),
            ("v8.2.1", "8.2.1"),
            ("Update README", "0.1.0"),
        ],
    )
    def test_source_git_commit(self, commit_message: str, expected: str) -> None:
        """Test 'commit' version source type."""
        repository = MagicMock(spec=GitRepository)
        repository.is_available = True
        repository.is_dirty = False
        repository.current_commit = MagicMock(
            spec=GitReference, distance_from_head=0, is_head_commit=True
        )
        repository.commits = [
            MagicMock(
                spec=GitReference,
                commit_message=commit_message,
                distance_from_head=0,
                is_head_commit=True,
                timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
                short_sha="123",
                commit_sha="1234567",
            )
        ]
        environment = MagicMock(spec=BuildEnvironment)

        settings = Settings(
            package_name="test_pkg",
            source_type=typing.cast("typing.Any", ["commit"]),
            version_type="release",
        )
        version, _ = resolve_version(settings, repository, environment)
        assert str(version) == expected

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("tag_name", "expected"),
        [
            ("v8.8.8", "8.8.8"),
            ("release/9.0.0", "9.0.0"),
        ],
    )
    def test_source_auto(self, tag_name: str, expected: str) -> None:
        """Test 'auto' version source type."""
        repository = MagicMock(spec=GitRepository)
        repository.is_available = True
        repository.is_dirty = False
        repository.current_commit = MagicMock(
            spec=GitReference, distance_from_head=0, is_head_commit=True
        )
        repository.tags = [
            MagicMock(
                spec=GitReference,
                tag_name=tag_name,
                distance_from_head=0,
                is_head_commit=True,
                timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
                short_sha="abc",
                commit_sha="abc1234",
            )
        ]
        environment = MagicMock(spec=BuildEnvironment)

        settings = Settings(
            package_name="test_pkg",
            source_type=typing.cast("typing.Any", ["auto"]),
            version="auto",
            version_type="release",
        )
        version, _ = resolve_version(settings, repository, environment)
        assert str(version) == expected

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("archive_content", "expected"),
        [
            (
                "commit_sha: abc1234\n"
                "short_sha: abc\n"
                "timestamp: 2023-01-01T00:00:00Z\n"
                "author_name: test\n"
                "author_email: test@test.com\n"
                "ref_names: HEAD -> main, tag: v9.9.9\n"
                "distance_from_head: 0\n"
                "is_head_commit: true\n"
                "total_commits: 10\n"
                "is_current_branch: true\n"
                "commit_message:\n"
                "Release 9.9.9\n",
                "9.9.9",
            ),
            (
                "commit_sha: abc1234\n"
                "short_sha: abc\n"
                "timestamp: 2023-01-01T00:00:00Z\n"
                "author_name: test\n"
                "author_email: test@test.com\n"
                "ref_names: HEAD -> main\n"
                "distance_from_head: 0\n"
                "is_head_commit: true\n"
                "total_commits: 10\n"
                "is_current_branch: true\n"
                "commit_message:\n"
                "chore: update something\n",
                "0.1.0",
            ),
        ],
    )
    def test_source_archive(self, archive_content: str, expected: str) -> None:
        """Test 'archive' version source fallback."""
        repository = MagicMock(spec=GitRepository)
        repository.is_available = False
        repository.is_dirty = False
        environment = MagicMock(spec=BuildEnvironment)

        settings = Settings(
            package_name="test_pkg",
            source_type=typing.cast("typing.Any", ["auto"]),
            version_source_archive=".git_archival.txt",
            version_type="release",
        )

        with (
            patch("gitversioned.versioning.Path.exists", return_value=True),
            patch(
                "gitversioned.versioning.Path.read_text", return_value=archive_content
            ),
        ):
            version, _ = resolve_version(settings, repository, environment)
            assert str(version) == expected

    @pytest.mark.smoke
    def test_source_invalid(self) -> None:
        """Test invalid version source type."""
        repository = MagicMock(spec=GitRepository)
        environment = MagicMock(spec=BuildEnvironment)

        settings = Settings(
            package_name="test_pkg",
            source_type=typing.cast("typing.Any", ["invalid_type"]),
            version_type="release",
        )
        with pytest.raises(ValueError):
            resolve_version(settings, repository, environment)


class TestGenerateVersionPy:
    """Test suite for the generate_version_file function."""

    @pytest.mark.smoke
    def test_callable(self):
        """Test generate_version_file signature."""
        assert callable(generate_version_file)

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "is_dev",
        [True, False],
    )
    def test_invocation(self, tmp_path: Path, is_dev: bool) -> None:
        """Test generate_version_py invocation."""
        settings = Settings(
            package_name="test_pkg",
            format_dev="dev0",
            format_pre="a0",
            format_post="post0",
            format_main="{version.major}.{version.minor}.{version.micro}",
            src_root=tmp_path,
        )
        version_str = "1.2.3.dev0" if is_dev else "1.2.3"
        version = Version(version_str)
        reference = GitReference(
            commit_sha="abcd123",
            short_sha="abcd",
            timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
            distance_from_head=0,
            is_head_commit=True,
            author_name="Test",
            author_email="test@test.com",
            commit_message="Test commit",
        )
        repository = MagicMock(spec=GitRepository)
        environment = MagicMock(spec=BuildEnvironment)

        out_file = tmp_path / "version.py"

        with (
            patch("gitversioned.versioning.render", return_value="content_mocked"),
            patch(
                "gitversioned.versioning.generate_template",
                return_value="template_mocked",
            ),
        ):
            result = generate_version_file(
                version, reference, settings, repository, environment
            )

            assert result == out_file
            assert out_file.exists()
            assert out_file.read_text(encoding="utf-8") == "content_mocked"


class TestResolveAndGenerateVersion:
    """Test suite for the resolve_and_generate_version function."""

    @pytest.mark.smoke
    def test_function_signatures(self) -> None:
        """Test resolve_and_generate_version signature."""
        assert callable(resolve_and_generate_version)

    @pytest.mark.smoke
    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "output",
        [
            "",
            "test_out.py",
        ],
    )
    def test_invocation(self, tmp_path: Path, output: str | None) -> None:
        """Test resolve_and_generate_version invocation."""
        kwargs: dict[str, Any] = {}
        if output:
            kwargs["output"] = output
            kwargs["src_root"] = tmp_path
        else:
            kwargs["output"] = ""

        settings = Settings(
            package_name="test_pkg",
            format_dev="dev0",
            format_pre="a0",
            format_post="post0",
            format_main="{version.major}.{version.minor}.{version.micro}",
            **kwargs,
        )
        repository = MagicMock(spec=GitRepository)
        environment = MagicMock(spec=BuildEnvironment)

        expected_version = Version("1.2.3")
        expected_reference = MagicMock(spec=GitReference)

        with patch("gitversioned.versioning.resolve_version") as mock_resolve:
            mock_resolve.return_value = (expected_version, expected_reference)
            with patch(
                "gitversioned.versioning.generate_version_file"
            ) as mock_generate:
                if output:
                    mock_generate.return_value = tmp_path / output
                else:
                    mock_generate.return_value = None

                version, path = resolve_and_generate_version(
                    settings, repository, environment
                )

                assert version == expected_version
                assert mock_generate.call_count == 1
                if output:
                    assert path is not None
                    assert path.name == "test_out.py"
                else:
                    assert path is None
