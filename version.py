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
    commit_message: str
    distance_from_head: int
    is_head_commit: bool


class BuildMetadata(NamedTuple):
    timestamp: str
    host: str
    python_version: str
    id: str


__version__ = "0.1.2.dev20260514+9eea393"
version = __version__

__VERSION_METADATA__ = VersionMetadata(
    major=0,
    minor=1,
    patch=2,
    pre=None,
    post=None,
    dev=20260514,
    local='9eea393',
)

__GIT_METADATA__ = GitMetadata(
    hash="9eea393943e4504913e6508c89fb99e11aef5f5e",
    branch="",
    tag="v0.1.2",
    dirty=['editorconfig', '.github/workflows/_build_container.yml', '.github/workflows/_build_package.yml', '.github/workflows/_docs.yml', '.github/workflows/_link-check.yml', '.github/workflows/_pr_comment.yml', '.github/workflows/_quality.yml', '.github/workflows/_security.yml', '.github/workflows/_tests.yml', '.github/workflows/development.yml', '.github/workflows/development_cleanup.yml', '.github/workflows/main.yml', '.github/workflows/nightly.yml', '.github/workflows/release.yml', '.github/workflows/weekly.yml', '.gitignore', '.pre-commit-config.yaml', 'AGENTS.md', 'DEVELOPING.md', 'Dockerfile', 'README.md', 'docker-compose.yml', 'docs/getting-started/installation.md', 'docs/guides/hatchling.md', 'docs/guides/setuptools.md', 'docs/index.md', 'docs/reference/index.md', 'docs/scripts/extra.js', 'docs/scripts/gen_ref_pages.py', 'docs/stylesheets/extra.css', 'examples/hatchling-hatch-vars/src/hatchling_hatch_vars/main.py', 'examples/hatchling-tool-table/src/hatchling_tool_table/main.py', 'examples/hatchling-version-branch/src/hatchling_version_branch/main.py', 'examples/hatchling-version-commits/src/hatchling_version_commits/main.py', 'examples/hatchling-version-file/src/hatchling_version_file/main.py', 'examples/hatchling-version-function/src/hatchling_version_function/main.py', 'examples/hatchling-version-tags/src/hatchling_version_tags/main.py', 'examples/setuptools-setup-cfg/src/setuptools_setup_cfg/main.py', 'examples/setuptools-setup-py/src/setuptools_setup_py/main.py', 'examples/setuptools-tool-table/src/setuptools_tool_table/main.py', 'examples/setuptools-version-branch/src/setuptools_version_branch/main.py', 'examples/setuptools-version-commits/src/setuptools_version_commits/main.py', 'examples/setuptools-version-file/src/setuptools_version_file/main.py', 'examples/setuptools-version-function/src/setuptools_version_function/main.py', 'examples/setuptools-version-tags/src/setuptools_version_tags/main.py', 'mkdocs.yml', 'pyproject.toml', 'src/gitversioned/__init__.py', 'src/gitversioned/compat.py', 'src/gitversioned/logging.py', 'src/gitversioned/plugins/hatchling_plugin.py', 'src/gitversioned/plugins/setuptools_plugin.py', 'src/gitversioned/settings.py', 'src/gitversioned/utils/git.py', 'src/gitversioned/versioning.py', 'tests/README.md', 'tests/conftest.py', 'tests/e2e/conftest.py', 'tests/e2e/test_builds.py', 'tests/integration/__init__.py', 'tests/integration/conftest.py', 'tests/integration/test_plugins.py', 'tests/integration/test_versioning.py', 'tests/unit/__init__.py', 'tests/unit/plugins/__init__.py', 'tests/unit/plugins/test_setuptools_plugin.py', 'tests/unit/test_compat.py', 'tests/unit/test_hatchling_plugin.py', 'tests/unit/test_logging.py', 'tests/unit/test_settings.py', 'tests/unit/test_versioning.py', 'tests/unit/utils/__init__.py', 'tests/unit/utils/test_environment.py', 'tests/unit/utils/test_git.py', 'tests/unit/utils/test_pydantic.py', 'uv.lock', '.detect-secrets.scan.json', '.devcontainer/', '.github/actions/', '.github/paths-filter.yml', '.github/workflows/pipeline-development.yml', '.github/workflows/pipeline-main.yml', '.github/workflows/pipeline-nightly.yml', '.github/workflows/pipeline-release.yml', '.github/workflows/pipeline-weekly.yml', '.github/workflows/util-development-cleanup.yml', '.github/workflows/util-pr-comment.yml', '.yamllint', 'cst.yaml', 'docs/reference/cli.md', 'docs/reference/python_api.md', 'docs/reference/python_coverage.md', 'docs/scripts/macros.py', 'scripts/check_links.py', 'scripts/generate_doc_tests.py', 'scripts/run_oci.py', 'src/gitversioned/__main__.py', 'src/gitversioned/build.py', 'taplo.toml', 'tests/e2e/test___main__.py', 'tests/python/', 'version.py', 'zensical.toml'],
    commit_count=9,
    commit_message="",
    distance_from_head=0,
    is_head_commit=False,
)

__BUILD_METADATA__ = BuildMetadata(
    timestamp="2026-05-26 11:54:53.921454+00:00",
    host="Marks-MacBook-Pro-2.local",
    python_version="3.13.13",
    id="9e11f8a5-006a-4e8b-925d-0938f9e63822",
)
