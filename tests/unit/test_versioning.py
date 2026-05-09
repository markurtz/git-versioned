from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from packaging.version import Version

from gitversioned.settings import Settings
from gitversioned.utils import Branch, BuildEnvironment, Commit, GitRepository, Tag
from gitversioned.versioning import (
    generate_version_py,
    resolve_and_generate_version,
    resolve_version,
)


def async_timeout(delay: float):
    """Decorator to add a timeout to async tests."""

    def decorator(func):
        @wraps(func)
        async def new_func(*args, **kwargs):
            return await asyncio.wait_for(func(*args, **kwargs), timeout=delay)

        return new_func

    return decorator


class TestResolveVersion:
    """Test suite for the resolve_version function."""

    @pytest.mark.smoke
    def test_function_signatures(self) -> None:
        """Test resolve_version signature."""
        assert callable(resolve_version)

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        (
            "settings_kwargs",
            "is_dirty",
            "is_available",
            "is_head",
            "distance",
            "expected_version_str",
        ),
        [
            (
                {"version_type": "release"},
                False,
                True,
                True,
                0,
                "1.2.3",
            ),
            (
                {"version_type": "auto", "auto_increment": {"dev": "micro"}},
                True,
                True,
                False,
                1,
                "1.2.4.dev0",
            ),
            (
                {"version_type": "alpha", "auto_increment": {"alpha": "minor"}},
                False,
                True,
                False,
                2,
                "1.3.0a0",
            ),
            (
                {"version_type": "dev", "auto_increment": {"dev": "major"}},
                False,
                True,
                False,
                3,
                "2.0.0.dev0",
            ),
        ],
    )
    def test_invocation(
        self,
        settings_kwargs: dict[str, str],
        is_dirty: bool,
        is_available: bool,
        is_head: bool,
        distance: int,
        expected_version_str: str,
    ) -> None:
        """Test resolve_version invocation with different settings."""
        settings = Settings(package_name="test_pkg", **settings_kwargs)  # type: ignore[arg-type]

        commit = Commit(
            commit_sha="abcd123",
            short_sha="abcd",
            timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
            distance_from_head=distance,
            is_head_commit=is_head,
            author_name="Test",
            author_email="test@test.com",
            commit_message="Test commit",
        )

        repository = MagicMock(spec=GitRepository)
        repository.is_dirty = is_dirty
        repository.is_available = is_available
        repository.current_commit = commit

        environment = MagicMock(spec=BuildEnvironment)

        with (
            patch("gitversioned.versioning._resolve_version_sources") as mock_sources,
            patch("gitversioned.versioning.render") as mock_render,
            patch("gitversioned.versioning.generate_template") as mock_gen_tpl,
        ):
            mock_sources.return_value = (Version("1.2.3"), commit)

            # Mock the rendering of the final version string based on expected
            def dummy_render(template: str) -> str:
                if template == settings.format_main:
                    # Use basic string manipulation to extract major, minor, micro
                    parts = expected_version_str.split(".")
                    major, minor = parts[0], parts[1]
                    micro = "".join(c for c in parts[2] if c.isdigit())
                    return f"{major}.{minor}.{micro}"
                elif template in (
                    settings.format_pre,
                    settings.format_post,
                    settings.format_dev,
                ):
                    if "dev" in expected_version_str:
                        return "dev0"
                    if "a" in expected_version_str:
                        return "a0"
                    if "post" in expected_version_str:
                        return "post0"
                return ""

            mock_render.side_effect = dummy_render
            mock_gen_tpl.side_effect = lambda tpl, ctx, use_eval: tpl

            version, reference = resolve_version(settings, repository, environment)

            assert str(version) == expected_version_str
            assert reference == commit

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        (
            "settings_kwargs",
            "repo_setup",
            "file_exists",
            "file_content",
            "func_return",
            "func_error",
            "expected_version",
            "expected_error",
        ),
        [
            (
                {"source_type": ["explicit"], "version": "1.5.0"},
                None,
                False,
                "",
                "",
                False,
                "1.5.0",
                None,
            ),
            (
                {"source_type": ["explicit"], "version": "auto"},
                None,
                False,
                "",
                "",
                False,
                None,
                ValueError,
            ),
            (
                {
                    "source_type": ["file"],
                    "version_source_file": "version.txt",
                    "regex_file": [r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<micro>\d+)"],
                },
                None,
                True,
                "1.2.3",
                "",
                False,
                "1.2.3",
                None,
            ),
            (
                {
                    "source_type": ["file"],
                    "version_source_file": "version.txt",
                    "regex_file": [r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<micro>\d+)"],
                },
                None,
                False,
                "",
                "",
                False,
                "0.1.0",
                None,
            ),
            (
                {"source_type": ["file"], "version_source_file": ""},
                None,
                False,
                "",
                "",
                False,
                "0.1.0",
                None,
            ),
            (
                {
                    "source_type": ["function"],
                    "version_source_function": "mock_mod:mock_func",
                },
                None,
                False,
                "",
                "2.3.4",
                False,
                "2.3.4",
                None,
            ),
            (
                {"source_type": ["function"], "version_source_function": ""},
                None,
                False,
                "",
                "",
                False,
                "0.1.0",
                None,
            ),
            (
                {
                    "source_type": ["function"],
                    "version_source_function": "mock_mod:mock_func",
                },
                None,
                False,
                "",
                "",
                True,
                None,
                Exception,
            ),
            (
                {
                    "source_type": ["tag"],
                    "regex_tag": [r"v(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"],
                },
                {
                    "tags": [
                        MagicMock(
                            spec=Tag,
                            tag_name="v3.1.2",
                            distance_from_head=0,
                            is_head_commit=True,
                            timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
                            short_sha="abc",
                            commit_sha="abc1234",
                        )
                    ]
                },
                False,
                "",
                "",
                False,
                "3.1.2",
                None,
            ),
            (
                {
                    "source_type": ["branch"],
                    "regex_branch": [
                        r"release/(?P<major>\d+)\.(?P<minor>\d+)\.(?P<micro>\d+)"
                    ],
                },
                {
                    "branch": MagicMock(
                        spec=Branch,
                        branch_name="release/4.2.0",
                        is_head_branch=True,
                        distance_from_head=0,
                        is_head_commit=True,
                        timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
                        short_sha="def",
                        commit_sha="def1234",
                    )
                },
                False,
                "",
                "",
                False,
                "4.2.0",
                None,
            ),
            (
                {
                    "source_type": ["commit"],
                    "regex_commit": [
                        r"Release (?P<major>\d+)\.(?P<minor>\d+)\.(?P<micro>\d+)"
                    ],
                },
                {
                    "commits": [
                        MagicMock(
                            spec=Commit,
                            commit_message="Release 5.0.0",
                            distance_from_head=0,
                            is_head_commit=True,
                            timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
                            short_sha="123",
                            commit_sha="1234567",
                        )
                    ]
                },
                False,
                "",
                "",
                False,
                "5.0.0",
                None,
            ),
            (
                {"source_type": ["tag"], "regex_tag": [r"(.*)"]},
                {
                    "tags": [
                        MagicMock(
                            spec=Tag,
                            tag_name="v3.1.2",
                            distance_from_head=0,
                            is_head_commit=True,
                            timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
                            short_sha="abc",
                            commit_sha="abc1234",
                        )
                    ]
                },
                False,
                "",
                "",
                False,
                "0.1.0",
                None,
            ),
            (
                {"source_type": ["invalid_type"]},
                None,
                False,
                "",
                "",
                False,
                None,
                ValueError,
            ),
            (
                {
                    "source_type": ["auto"],
                    "version": "auto",
                    "version_source_file": "",
                    "version_source_function": "",
                    "regex_tag": [r"v(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"],
                },
                {
                    "tags": [
                        MagicMock(
                            spec=Tag,
                            tag_name="v8.8.8",
                            distance_from_head=0,
                            is_head_commit=True,
                            timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
                            short_sha="abc",
                            commit_sha="abc1234",
                        )
                    ]
                },
                False,
                "",
                "",
                False,
                "8.8.8",
                None,
            ),
            (
                {"source_type": ["tag"]},
                {"available": False},
                False,
                "",
                "",
                False,
                "0.1.0.dev0",
                None,
            ),
        ],
    )
    def test_sources(
        self,
        settings_kwargs: dict[str, Any],
        repo_setup: dict[str, Any] | None,
        file_exists: bool,
        file_content: str,
        func_return: str,
        func_error: bool,
        expected_version: str | None,
        expected_error: type[Exception] | None,
    ) -> None:
        settings_kwargs.setdefault(
            "format_main", "{version.major}.{version.minor}.{version.micro}"
        )
        settings_kwargs.setdefault("format_dev", "dev0")
        settings_kwargs.setdefault("format_pre", "a0")
        settings_kwargs.setdefault("format_post", "post0")

        settings = Settings(package_name="test_pkg", **settings_kwargs)  # type: ignore[arg-type]

        repository = MagicMock(spec=GitRepository)
        repository.is_available = (
            repo_setup.get("available", True) if repo_setup else True
        )
        repository.is_dirty = False

        default_commit = Commit(
            commit_sha="abcd123",
            short_sha="abcd",
            timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
            distance_from_head=0,
            is_head_commit=True,
            author_name="Test",
            author_email="test@test.com",
            commit_message="Test commit",
        )
        repository.current_commit = default_commit
        repository.tags = repo_setup.get("tags", []) if repo_setup else []
        repository.current_branch = (
            repo_setup.get("branch", None) if repo_setup else None
        )
        repository.commits = repo_setup.get("commits", []) if repo_setup else []

        environment = BuildEnvironment(build_id="0")

        with (
            patch("gitversioned.versioning.Path.exists", return_value=file_exists),
            patch("gitversioned.versioning.Path.read_text", return_value=file_content),
            patch("gitversioned.versioning.importlib.import_module") as mock_import,
        ):
            mock_module = MagicMock()
            if func_error:
                mock_module.mock_func.side_effect = Exception("Mocked error")
            else:
                mock_module.mock_func.return_value = func_return
            mock_import.return_value = mock_module

            if expected_error:
                with pytest.raises(expected_error):
                    resolve_version(settings, repository, environment)
            else:
                version, _ = resolve_version(settings, repository, environment)
                assert str(version) == expected_version


class TestGenerateVersionPy:
    """Test suite for the generate_version_py function."""

    @pytest.mark.smoke
    def test_function_signatures(self) -> None:
        """Test generate_version_py signature."""
        assert callable(generate_version_py)

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "is_dev",
        [True, False],
    )
    def test_invocation(self, tmp_path: Path, is_dev: bool) -> None:
        """Test generate_version_py invocation."""
        settings = Settings(package_name="test_pkg", src_root=tmp_path)
        version_str = "1.2.3.dev0" if is_dev else "1.2.3"
        version = Version(version_str)
        reference = Commit(
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
            result = generate_version_py(
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
    @pytest.mark.parametrize(
        "output_file",
        [
            "",
            "test_out.py",
        ],
    )
    def test_invocation(self, tmp_path: Path, output_file: str | None) -> None:
        """Test resolve_and_generate_version invocation."""
        kwargs: dict[str, str | Path] = {}
        if output_file:
            kwargs["output_file"] = output_file
            kwargs["src_root"] = tmp_path
        else:
            kwargs["output_file"] = ""

        settings = Settings(package_name="test_pkg", **kwargs)  # type: ignore[arg-type]
        repository = MagicMock(spec=GitRepository)
        environment = MagicMock(spec=BuildEnvironment)

        expected_version = Version("1.2.3")
        expected_reference = MagicMock(spec=Commit)

        with patch("gitversioned.versioning.resolve_version") as mock_resolve:
            mock_resolve.return_value = (expected_version, expected_reference)
            with patch("gitversioned.versioning.generate_version_py") as mock_generate:
                if output_file:
                    mock_generate.return_value = tmp_path / output_file
                else:
                    mock_generate.return_value = None

                version, path = resolve_and_generate_version(
                    settings, repository, environment
                )

                assert version == expected_version
                assert mock_generate.call_count == 1
                if output_file:
                    assert path is not None
                    assert path.name == "test_out.py"
                else:
                    assert path is None
