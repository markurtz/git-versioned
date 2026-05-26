"""
Unit tests for standard output and error redirection, custom templates,
and regex replacement mode in GitVersioned.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from packaging.version import Version

from gitversioned.settings import Settings
from gitversioned.utils import BuildEnvironment, GitReference, GitRepository
from gitversioned.versioning import generate_version_file


def test_generate_version_file_stdout_template(tmp_path: Path) -> None:
    """Test generating version info to stdout using custom templates."""
    settings = Settings(
        package_name="test_pkg",
        output="sys.stdout",
        pattern_release="Version is {version}",
        project_root=tmp_path,
    )
    version = Version("1.2.3")
    reference = GitReference(
        commit_sha="abcd123",
        short_sha="abcd",
        timestamp=datetime.now(timezone.utc),
        distance_from_head=0,
        is_head_commit=True,
    )
    repository = MagicMock(spec=GitRepository)
    environment = MagicMock(spec=BuildEnvironment)

    # Capture stdout
    captured_stdout = io.StringIO()
    with patch("sys.stdout", captured_stdout):
        result = generate_version_file(
            version, reference, settings, repository, environment
        )

    assert result is None
    assert captured_stdout.getvalue() == "Version is 1.2.3\n"


def test_generate_version_file_stderr_template(tmp_path: Path) -> None:
    """Test generating version info to stderr using custom templates."""
    settings = Settings(
        package_name="test_pkg",
        output="sys.stderr",
        pattern_release="Version is {version}",
        project_root=tmp_path,
    )
    version = Version("2.0.1")
    reference = GitReference(
        commit_sha="abcd123",
        short_sha="abcd",
        timestamp=datetime.now(timezone.utc),
        distance_from_head=0,
        is_head_commit=True,
    )
    repository = MagicMock(spec=GitRepository)
    environment = MagicMock(spec=BuildEnvironment)

    # Capture stderr
    captured_stderr = io.StringIO()
    with patch("sys.stderr", captured_stderr):
        result = generate_version_file(
            version, reference, settings, repository, environment
        )

    assert result is None
    assert captured_stderr.getvalue() == "Version is 2.0.1\n"


def test_generate_version_file_stdout_regex_cargo(tmp_path: Path) -> None:
    """Test injecting version info into Cargo.toml and outputting to stdout."""
    cargo_content = '[package]\nname = "test_pkg"\nversion = "0.1.0"\n'
    cargo_file = tmp_path / "Cargo.toml"
    cargo_file.write_text(cargo_content, encoding="utf-8")

    settings = Settings(
        package_name="test_pkg",
        output="sys.stdout",
        pattern_release="cargo",
        project_root=tmp_path,
    )
    version = Version("1.2.3")
    reference = GitReference(
        commit_sha="abcd123",
        short_sha="abcd",
        timestamp=datetime.now(timezone.utc),
        distance_from_head=0,
        is_head_commit=True,
    )
    repository = MagicMock(spec=GitRepository)
    environment = MagicMock(spec=BuildEnvironment)

    captured_stdout = io.StringIO()
    with patch("sys.stdout", captured_stdout):
        result = generate_version_file(
            version, reference, settings, repository, environment
        )

    assert result is None
    expected_output = '[package]\nname = "test_pkg"\nversion = "1.2.3"\n'
    assert captured_stdout.getvalue() == expected_output


def test_generate_version_file_stdout_regex_pyproject(tmp_path: Path) -> None:
    """Test injecting version info into pyproject.toml and outputting to stdout."""
    pyproject_content = '[project]\nname = "test_pkg"\nversion = "0.1.0"\n'
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text(pyproject_content, encoding="utf-8")

    settings = Settings(
        package_name="test_pkg",
        output="sys.stdout",
        pattern_release="pyproject",
        project_root=tmp_path,
    )
    version = Version("3.4.5")
    reference = GitReference(
        commit_sha="abcd123",
        short_sha="abcd",
        timestamp=datetime.now(timezone.utc),
        distance_from_head=0,
        is_head_commit=True,
    )
    repository = MagicMock(spec=GitRepository)
    environment = MagicMock(spec=BuildEnvironment)

    captured_stdout = io.StringIO()
    with patch("sys.stdout", captured_stdout):
        result = generate_version_file(
            version, reference, settings, repository, environment
        )

    assert result is None
    expected_output = '[project]\nname = "test_pkg"\nversion = "3.4.5"\n'
    assert captured_stdout.getvalue() == expected_output
