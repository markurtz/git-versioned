"""Integration tests for the GitVersioned wrapping build backend."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import hatchling.build
import setuptools.build_meta

from gitversioned import build


def test_build_backend_delegation_default(tmp_path: Path) -> None:
    """Test that build backend delegates to setuptools.build_meta by default."""
    build._BuildState.target_backend = None
    build._BuildState.version_resolved = False

    with patch("gitversioned.build.resolve_and_generate_version") as mock_resolve:
        mock_resolve.return_value = ("1.2.3", tmp_path / "version.py")

        # Accessing any standard attribute should trigger version resolution
        # and delegate to setuptools.build_meta
        hook = build.get_requires_for_build_wheel
        assert hook is not None
        assert mock_resolve.call_count == 1

        # Check that we got the hook from setuptools.build_meta
        assert hook == setuptools.build_meta.get_requires_for_build_wheel


def test_build_backend_delegation_env_override(tmp_path: Path) -> None:
    """Test that build backend respects the target env variable."""
    build._BuildState.target_backend = None
    build._BuildState.version_resolved = False

    with (
        patch("gitversioned.build.resolve_and_generate_version") as mock_resolve,
        patch.dict(os.environ, {"GITVERSIONED_BUILD_BACKEND": "hatchling.build"}),
    ):
        mock_resolve.return_value = ("2.0.0", tmp_path / "version.py")

        hook = build.build_wheel
        assert hook is not None

        assert hook == hatchling.build.build_wheel


def test_build_backend_dir() -> None:
    """Test that __dir__ includes both module and target backend attributes."""
    build._BuildState.target_backend = None

    with patch.dict(os.environ, {"GITVERSIONED_BUILD_BACKEND": "hatchling.build"}):
        members = dir(build)
        assert "build_wheel" in members
        assert "build_sdist" in members
        assert "_ensure_version_resolved" in members
