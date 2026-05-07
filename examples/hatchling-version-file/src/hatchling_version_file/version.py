"""
Auto-generated version file from git-versioned
"""

from __future__ import annotations

from typing import NamedTuple

__all__ = [
    "__BUILD_METADATA__",
    "__GIT_METADATA__",
    "__VERSION_METADATA__",
    "BuildMetadata",
    "GitMetadata",
    "VersionMetadata",
    "__version__",
    "version",
]


class VersionMetadata(NamedTuple):
    major: int
    minor: int
    patch: int
    pre: tuple[str, int] | None
    post: int | None
    dev: int | None
    local: str | None


class GitMetadata(NamedTuple):
    hash: str
    branch: str
    tag: str
    dirty: list[str]
    commit_count: int


class BuildMetadata(NamedTuple):
    timestamp: str
    host: str
    python_version: str
    id: str


__version__ = "0.1.20260505+c260ca4"
version = __version__

__VERSION_METADATA__ = VersionMetadata(
    major=0,
    minor=1,
    patch=20260505,
    pre=None,
    post=None,
    dev=None,
    local="c260ca4",
)

__GIT_METADATA__ = GitMetadata(
    hash="c260ca441aa69bc0b2a13529783872e9bc96d306",
    branch="feature/init-funcionality",
    tag="",
    dirty=[
        "github/workflows/_tests.yml",
        ".gitignore",
        "AGENTS.md",
        "DEVELOPING.md",
        "README.md",
        "docs/getting-started/installation.md",
        "docs/getting-started/quickstart.md",
        "docs/getting-started/workflows.md",
        "docs/index.md",
        "docs/reference/index.md",
        "pyproject.toml",
        "src/gitversioned/__init__.py",
        "src/gitversioned/__main__.py",
        "src/gitversioned/plugins/setuptools_plugin.py",
        "tests/e2e/.gitkeep",
        "tests/e2e/conftest.py",
        "tests/e2e/test_builds.py",
        "tests/e2e/test_e2e.py",
        "tests/integration/.gitkeep",
        "tests/integration/test_integration.py",
        "tests/unit/.gitkeep",
        "tests/unit/test_unit.py",
        "examples/__init__.py",
        "examples/hatchling-hatch-vars/",
        "examples/hatchling-tool-table/",
        "examples/hatchling-version-branch/",
        "examples/hatchling-version-commits/",
        "examples/hatchling-version-file/",
        "examples/hatchling-version-function/",
        "examples/hatchling-version-tags/",
        "examples/setuptools-setup-cfg/",
        "examples/setuptools-setup-py/",
        "examples/setuptools-tool-table/",
        "examples/setuptools-version-branch/",
        "examples/setuptools-version-commits/",
        "examples/setuptools-version-file/",
        "examples/setuptools-version-function/",
        "examples/setuptools-version-tags/",
        "scripts/__init__.py",
        "src/gitversioned/compat.py",
        "src/gitversioned/logging.py",
        "src/gitversioned/plugins/__init__.py",
        "src/gitversioned/plugins/hatchling_plugin.py",
        "src/gitversioned/settings.py",
        "src/gitversioned/templates/",
        "src/gitversioned/utils/",
        "src/gitversioned/versioning.py",
        "tests/__init__.py",
        "tests/conftest.py",
        "tests/integration/conftest.py",
        "tests/integration/test_plugins.py",
        "tests/integration/test_versioning.py",
        "tests/unit/plugins/",
        "tests/unit/test_compat.py",
        "tests/unit/test_hatchling_plugin.py",
        "tests/unit/test_logging.py",
        "tests/unit/test_settings.py",
        "tests/unit/test_versioning.py",
        "tests/unit/utils/",
        "uv.lock",
        "version.py",
    ],
    commit_count=4,
)

__BUILD_METADATA__ = BuildMetadata(
    timestamp="2026-05-06 15:17:25.855800+00:00",
    host="Marks-MacBook-Pro-2.local",
    python_version="3.14.4",
    id="5f4b6775-97cf-4c26-8476-b63538acad9f",
)
