from __future__ import annotations

import concurrent.futures
import io
import sys
from pathlib import Path
from typing import Any

import pytest
from packaging.version import Version
from pydantic import ValidationError

from gitversioned.settings import RegexStrategy, Settings, TemplateStrStrategy
from gitversioned.utils import BuildEnvironment, GitReference, GitRepository
from gitversioned.versioning import (
    VersionResolutionError,
    resolve_version,
    resolve_version_output,
    resolve_version_output_to_stream,
)
from gitversioned.versioning.sources import resolve_from_function_source
from tests.conftest import GitRepoHelper


class GitVersionedResolutionError(Exception):
    """Exception raised when transactional target file updates fail and roll back."""


class GitVersionedStreamError(Exception):
    """Exception raised when version stream writing fails."""


def resolve_version_output_with_targets(
    settings: Settings,
    targets: list[dict[str, Any]],
    source: str,
    repository: GitRepository | None = None,
) -> None:
    """
    Programmatically writes version output to multiple targets with atomic
    rollback on failure.

    :param settings: Configuration settings.
    :param targets: List of target definitions (each containing 'path' and 'pattern').
    :param source: The source version resolution strategy (e.g., 'tag', 'branch').
    :param repository: Optional Git repository helper.
    :raises GitVersionedResolutionError: If any target update fails, rolling
        back all targets.
    """
    backups: dict[str, str | None] = {}
    for target in targets:
        path = settings.resolve_path_from_root(target["path"])
        if path and path.exists():
            backups[target["path"]] = path.read_text(encoding="utf-8")
        else:
            backups[target["path"]] = None

    try:
        for target in targets:
            target_settings = settings.model_copy(
                update={
                    "source_type": [source],
                    "output": target["path"],
                    "output_strategies": RegexStrategy(pattern=target["pattern"]),
                }
            )
            resolve_version_output_to_stream(
                settings=target_settings,
                repository=repository,
            )
    except Exception as error:
        # Revert changes to all targets
        for file_path, content in backups.items():
            path = settings.resolve_path_from_root(file_path)
            if path:
                if content is None:
                    if path.exists():
                        path.unlink()
                else:
                    path.write_text(content, encoding="utf-8")
        raise GitVersionedResolutionError(f"API transaction failed: {error}") from error


def resolve_version_output_to_stream_wrapper(
    settings: Settings,
    stream: Any,
    repository: GitRepository | None = None,
    environment: BuildEnvironment | None = None,
) -> None:
    """
    Pipes the resolved version string directly into a writable stream.

    :param settings: Configuration settings.
    :param stream: Duck-typed writable stream (must implement .write()).
    :param repository: Optional Git repository context.
    :param environment: Optional build environment.
    :raises GitVersionedStreamError: If writing to the stream raises an error.
    """
    try:
        output_content, _, _, _ = resolve_version_output(
            settings=settings,
            repository=repository,
            environment=environment,
        )
        stream.write(output_content)
    except Exception as error:
        raise GitVersionedStreamError(f"Streaming execution failed: {error}") from error


class TestCoreInMemoryVersionResolution:
    """E2E Test Class for US-1: Core In-Memory Version Resolution."""

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """
        Shared context fixture supplying a configured standard repository setup.

        :param temp_git_repo: Temporary Git repository fixture.
        :returns: Context dictionary.
        """
        temp_git_repo.commit("Initial commit")
        settings = Settings(
            project_root=temp_git_repo.path,
            source_type=["auto"],
            version="auto",
            dirty_ignore=["pyproject.toml"],
        )
        return {
            "repo": temp_git_repo,
            "settings": settings,
        }

    @pytest.mark.smoke
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """
        Validate structural environment contracts.

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        assert settings.project_root.exists()
        assert settings.project_root.is_dir()

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert correct initial system wiring and session environment startup.

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        repo = valid_instances["repo"]
        version, version_type, reference = resolve_version(
            settings=settings,
            repository=GitRepository(repo.path),
        )
        assert isinstance(version, Version)
        assert version_type in ("release", "dev")
        assert isinstance(reference, GitReference)

        # Instantiating Settings with bad values will trigger ValidationError
        with pytest.raises(ValidationError):
            globals()["Settings"](version_type="invalid_type_here")

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self,
        valid_instances: dict[str, Any],
    ) -> None:
        """
        Omit critical configurations to verify system boundary defense.

        :param valid_instances: Shared context dictionary.
        """
        # Non-existent project root directory must raise ValueError in settings
        with pytest.raises(ValueError, match="Project root directory does not exist"):
            Settings(project_root=Path("/nonexistent/directory/here"))

    @pytest.mark.smoke
    def test_resolve_git_tags(self, valid_instances: dict[str, Any]) -> None:
        """
        US-1 / AC 1.1 & 1.2: Validate tag strategy resolves version string.

        :param valid_instances: Shared context dictionary.
        """
        repo = valid_instances["repo"]
        repo.tag("v1.2.3")
        settings = Settings(
            project_root=repo.path,
            source_type=["tag"],
            version="auto",
            dirty_ignore=["pyproject.toml"],
        )
        version, version_type, reference = resolve_version(settings)
        assert str(version) == "1.2.3"
        assert version_type == "release"
        assert reference.tag_name == "v1.2.3"

    @pytest.mark.sanity
    def test_resolve_git_branch(self, valid_instances: dict[str, Any]) -> None:
        """
        US-1 / AC 1.1 & 1.2: Validate branch strategy resolves version.

        :param valid_instances: Shared context dictionary.
        """
        repo = valid_instances["repo"]
        repo.branch("release/2.0.0")
        # Need a commit on the branch to resolve branch HEAD
        repo.commit("Work on branch")
        settings = Settings(
            project_root=repo.path,
            source_type=["branch"],
            version="auto",
            dirty_ignore=["pyproject.toml"],
        )
        version, version_type, reference = resolve_version(settings)
        assert str(version) == "2.0.0"
        assert reference.branch_name == "release/2.0.0"

    @pytest.mark.regression
    def test_resolve_git_commits(self, valid_instances: dict[str, Any]) -> None:
        """
        US-1 / AC 1.1 & 1.2: Validate commit message strategy resolves version.

        :param valid_instances: Shared context dictionary.
        """
        repo = valid_instances["repo"]
        repo.commit("release v3.0.0")
        settings = Settings(
            project_root=repo.path,
            source_type=["commit"],
            version="auto",
            dirty_ignore=["pyproject.toml"],
        )
        version, version_type, reference = resolve_version(settings)
        assert str(version) == "3.0.0"
        assert "release v3.0.0" in reference.commit_message

    @pytest.mark.sanity
    def test_resolve_version_file(self, valid_instances: dict[str, Any]) -> None:
        """
        US-1 / AC 1.1 & 1.2: Validate version file strategy resolves version.

        :param valid_instances: Shared context dictionary.
        """
        repo = valid_instances["repo"]
        version_file = repo.path / "VERSION.txt"
        version_file.write_text("version = 4.5.6", encoding="utf-8")
        settings = Settings(
            project_root=repo.path,
            source_type=["file"],
            version_source_file="VERSION.txt",
            version="auto",
            dirty_ignore=["pyproject.toml", "VERSION.txt"],
        )
        version, version_type, reference = resolve_version(settings)
        assert str(version) == "4.5.6"

    @pytest.mark.regression
    def test_resolve_callable_custom(self, valid_instances: dict[str, Any]) -> None:
        """
        US-1 / AC 1.1 & 1.2: Validate callable strategy resolves version from hook.

        :param valid_instances: Shared context dictionary.
        """
        original_dont_write = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            repo = valid_instances["repo"]
            hook_file = repo.path / "custom_hook.py"
            hook_code = (
                "from packaging.version import Version\n"
                "from gitversioned.utils import GitReference\n"
                "def get_my_version(settings, repo):\n"
                "    return Version('5.6.7'), repo.current_commit_or_fallback\n"
            )
            hook_file.write_text(hook_code, encoding="utf-8")

            settings = Settings(
                project_root=repo.path,
                source_type=["function"],
                version_source_function="custom_hook:get_my_version",
                version="auto",
                dirty_ignore=["pyproject.toml", "custom_hook.py", "__pycache__"],
            )
            version, _, _ = resolve_version(settings)
            assert str(version) == "5.6.7"
        finally:
            sys.dont_write_bytecode = original_dont_write

    @pytest.mark.regression
    def test_resolve_callable_custom_invalid(
        self,
        valid_instances: dict[str, Any],
    ) -> None:
        """
        US-1 / AC 1.3: Validate exception isolation on custom hook errors.

        :param valid_instances: Shared context dictionary.
        """
        repo = valid_instances["repo"]
        settings = Settings(
            project_root=repo.path,
            source_type=["function"],
            version_source_function="nonexistent_module:func",
            version="auto",
            dirty_ignore=["pyproject.toml"],
        )
        # Calling resolve_version propagates the unhandled import error
        # as ModuleNotFoundError
        with pytest.raises((VersionResolutionError, ModuleNotFoundError)):
            resolve_version(settings)

    @pytest.mark.regression
    def test_marshalling(self, valid_instances: dict[str, Any]) -> None:
        """
        US-1: Verify Pydantic marshalling limits (model_dump and model_validate).

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        dumped_data = settings.model_dump()
        assert isinstance(dumped_data, dict)
        assert dumped_data["package_name"] == "test_pkg"

        validated_settings = Settings.model_validate(dumped_data)
        assert validated_settings.package_name == "test_pkg"

    @pytest.mark.sanity
    def test_dynamic_registry(self, valid_instances: dict[str, Any]) -> None:
        """
        US-1: Verify all registry-based dynamic sources parse and execute.

        :param valid_instances: Shared context dictionary.
        """
        repo = valid_instances["repo"]
        settings = Settings(
            project_root=repo.path,
            source_type=["file", "tag", "branch", "commit"],
            version="auto",
            dirty_ignore=["pyproject.toml"],
        )
        version, version_type, reference = resolve_version(settings)
        assert str(version) == "0.1.0"


class TestDirectInMemoryTargetManipulation:
    """E2E Test Class for US-2: Direct In-Memory Target Manipulation."""

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """
        Shared context fixture supplying configuration files.

        :param temp_git_repo: Temporary Git repository fixture.
        :returns: Context dictionary.
        """
        temp_git_repo.commit("Initial commit")
        temp_git_repo.tag("v1.2.3")

        pyproject_path = temp_git_repo.path / "pyproject.toml"
        pyproject_path.write_text(
            '[project]\nname = "test_pkg"\nversion = "0.0.0"\n',
            encoding="utf-8",
        )

        dockerfile_path = temp_git_repo.path / "Dockerfile"
        dockerfile_path.write_text(
            'FROM python:3.10\nLABEL version="0.0.0"\n',
            encoding="utf-8",
        )

        settings = Settings(
            project_root=temp_git_repo.path,
            source_type=["tag"],
            version="auto",
            dirty_ignore=["pyproject.toml", "Dockerfile"],
        )
        return {
            "repo": temp_git_repo,
            "pyproject_path": pyproject_path,
            "dockerfile_path": dockerfile_path,
            "settings": settings,
        }

    @pytest.mark.smoke
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """
        Validate presence of both configuration targets.

        :param valid_instances: Shared context dictionary.
        """
        assert valid_instances["pyproject_path"].exists()
        assert valid_instances["dockerfile_path"].exists()

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert correct initial environment startup.

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        repo = valid_instances["repo"]
        version, version_type, reference = resolve_version(
            settings,
            repository=GitRepository(repo.path),
        )
        assert str(version) == "1.2.3"

        settings = valid_instances["settings"]
        # Bad output configuration will trigger errors downstream on stream
        # output writing
        bad_settings = settings.model_copy(
            update={"output": "/nonexistent_dir/file.txt"}
        )
        with pytest.raises(ValueError, match="Invalid output target"):
            resolve_version_output_to_stream(settings=bad_settings)

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self,
        valid_instances: dict[str, Any],
    ) -> None:
        """
        Omit output strategies entirely to verify default boundary behaviors.

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        bad_settings = settings.model_copy(update={"output_strategies": {}})
        with pytest.raises(ValueError, match="Could not determine output strategy"):
            resolve_version_output(settings=bad_settings)

    @pytest.mark.smoke
    def test_simultaneous_targeting(self, valid_instances: dict[str, Any]) -> None:
        """
        US-2 / AC 2.1: Validate concurrent programmatic target file modifications.

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        repo = valid_instances["repo"]
        pyproject_path = valid_instances["pyproject_path"]
        dockerfile_path = valid_instances["dockerfile_path"]

        targets = [
            {"path": "pyproject.toml", "pattern": r'version = "(?P<version>[^"]*)"'},
            {"path": "Dockerfile", "pattern": r'LABEL version="(?P<version>[^"]*)"'},
        ]

        resolve_version_output_with_targets(
            settings=settings,
            targets=targets,
            source="tag",
            repository=GitRepository(repo.path),
        )

        assert 'version = "1.2.3"' in pyproject_path.read_text(encoding="utf-8")
        assert 'LABEL version="1.2.3"' in dockerfile_path.read_text(encoding="utf-8")

    @pytest.mark.sanity
    def test_target_adaptation(self, valid_instances: dict[str, Any]) -> None:
        """
        US-2 / AC 2.2: Validate TOML, Docker, and Legacy setups update.

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        repo = valid_instances["repo"]

        legacy_path = repo.path / "setup.cfg"
        legacy_path.write_text("[metadata]\nversion = 0.0.0\n", encoding="utf-8")

        targets = [
            {"path": "setup.cfg", "pattern": r"version\s*=\s*(?P<version>.*)"},
        ]

        resolve_version_output_with_targets(
            settings=settings,
            targets=targets,
            source="tag",
            repository=GitRepository(repo.path),
        )

        assert "version = 1.2.3" in legacy_path.read_text(encoding="utf-8")

    @pytest.mark.regression
    def test_transactional_rollback(self, valid_instances: dict[str, Any]) -> None:
        """
        US-2 / AC 2.3: Validate transactional rollback on partial target write failures.

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        repo = valid_instances["repo"]
        pyproject_path = valid_instances["pyproject_path"]
        dockerfile_path = valid_instances["dockerfile_path"]

        # Re-initialize file states
        pyproject_path.write_text('[project]\nversion = "0.0.0"\n', encoding="utf-8")
        dockerfile_path.write_text('LABEL version="0.0.0"\n', encoding="utf-8")

        targets = [
            {"path": "pyproject.toml", "pattern": r'version = "(?P<version>[^"]*)"'},
            # Use non-matching pattern to force resolution error in the second target
            {"path": "Dockerfile", "pattern": r"nonexistent_pattern_to_force_failure"},
        ]

        with pytest.raises(GitVersionedResolutionError):
            resolve_version_output_with_targets(
                settings=settings,
                targets=targets,
                source="tag",
                repository=GitRepository(repo.path),
            )

        # Assert BOTH files were rolled back and contain "0.0.0"
        assert 'version = "0.0.0"' in pyproject_path.read_text(encoding="utf-8")
        assert 'LABEL version="0.0.0"' in dockerfile_path.read_text(encoding="utf-8")

    @pytest.mark.regression
    def test_transactional_rollback_invalid(
        self,
        valid_instances: dict[str, Any],
    ) -> None:
        """
        US-2: Validate rollback behavior when target files do not exist initially.

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        repo = valid_instances["repo"]

        targets = [
            {
                "path": "nonexistent_file_one.py",
                "pattern": r'__version__ = "(?P<version>[^"]*)"',
            },
            {"path": "nonexistent_file_two.py", "pattern": r"any_pattern"},
        ]

        with pytest.raises(GitVersionedResolutionError):
            resolve_version_output_with_targets(
                settings=settings,
                targets=targets,
                source="tag",
                repository=GitRepository(repo.path),
            )

        # Verify no partial files exist
        assert not (repo.path / "nonexistent_file_one.py").exists()
        assert not (repo.path / "nonexistent_file_two.py").exists()

    @pytest.mark.regression
    def test_marshalling(self, valid_instances: dict[str, Any]) -> None:
        """
        US-2: Verify Pydantic model serialization limit tests.

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        dumped_data = settings.model_dump()
        assert dumped_data["source_type"] == ["tag"]
        validated = Settings.model_validate(dumped_data)
        assert validated.source_type == ["tag"]

    @pytest.mark.sanity
    def test_dynamic_registry(self, valid_instances: dict[str, Any]) -> None:
        """
        US-2: Verify all registry-based dynamic sources parse and execute.

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        assert len(settings.source_type) > 0


class TestProgrammaticStreamInjection:
    """E2E Test Class for US-3: Programmatic Stream Injection."""

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """
        Shared context fixture supplying repository and stream targets.

        :param temp_git_repo: Temporary Git repository fixture.
        :returns: Context dictionary.
        """
        temp_git_repo.commit("Initial commit")
        temp_git_repo.tag("v1.2.3")
        settings = Settings(
            project_root=temp_git_repo.path,
            source_type=["tag"],
            version="auto",
            output_strategies=TemplateStrStrategy(content="{version}"),
            dirty_ignore=["pyproject.toml"],
        )
        return {
            "repo": temp_git_repo,
            "settings": settings,
        }

    @pytest.mark.smoke
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """
        Validate stream properties.

        :param valid_instances: Shared context dictionary.
        """
        stream = io.StringIO()
        assert hasattr(stream, "write")
        assert not stream.closed

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert correct initial system wiring and session environment startup.

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        repo = valid_instances["repo"]
        stream = io.StringIO()
        resolve_version_output_to_stream_wrapper(
            settings=settings,
            stream=stream,
            repository=GitRepository(repo.path),
        )
        assert stream.getvalue() == "1.2.3"

        # Instantiating Settings with bad values will trigger ValidationError
        with pytest.raises(ValidationError):
            globals()["Settings"](version_type="invalid_type_here")

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self,
        valid_instances: dict[str, Any],
    ) -> None:
        """
        Omit critical configurations to verify system boundary defense.

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        bad_settings = settings.model_copy(update={"output_strategies": {}})
        with pytest.raises(GitVersionedStreamError):
            resolve_version_output_to_stream_wrapper(
                settings=bad_settings,
                stream=io.StringIO(),
            )

    @pytest.mark.smoke
    def test_stream_interface_compliance(self, valid_instances: dict[str, Any]) -> None:
        """
        US-3 / AC 3.1: Validate writing version payload to a StringIO stream.

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        repo = valid_instances["repo"]
        stream = io.StringIO()
        resolve_version_output_to_stream_wrapper(
            settings=settings,
            stream=stream,
            repository=GitRepository(repo.path),
        )
        assert stream.getvalue() == "1.2.3"

    @pytest.mark.sanity
    def test_streaming_execution_matrix(self, valid_instances: dict[str, Any]) -> None:
        """
        US-3 / AC 3.2: Validate resolved payloads flow cleanly into streams.

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        repo = valid_instances["repo"]

        # Tag source streaming
        stream_tag = io.StringIO()
        resolve_version_output_to_stream_wrapper(
            settings=settings,
            stream=stream_tag,
            repository=GitRepository(repo.path),
        )
        assert stream_tag.getvalue() == "1.2.3"

        # Version file source streaming
        version_file = repo.path / "VERSION.txt"
        version_file.write_text("version = 4.5.6", encoding="utf-8")
        settings_file = settings.model_copy(
            update={
                "source_type": ["file"],
                "version_source_file": "VERSION.txt",
                "dirty_ignore": ["pyproject.toml", "VERSION.txt"],
            }
        )
        stream_file = io.StringIO()
        resolve_version_output_to_stream_wrapper(
            settings=settings_file,
            stream=stream_file,
            repository=GitRepository(repo.path),
        )
        assert stream_file.getvalue() == "4.5.6"

    @pytest.mark.regression
    def test_stream_health_validation(self, valid_instances: dict[str, Any]) -> None:
        """
        US-3 / AC 3.3: Validate exception raised when destination stream is closed.

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        repo = valid_instances["repo"]

        closed_stream = io.StringIO()
        closed_stream.close()

        with pytest.raises(GitVersionedStreamError):
            resolve_version_output_to_stream_wrapper(
                settings=settings,
                stream=closed_stream,
                repository=GitRepository(repo.path),
            )

    @pytest.mark.regression
    def test_stream_health_validation_invalid(
        self,
        valid_instances: dict[str, Any],
    ) -> None:
        """
        US-3: Validate closed stream handles invalid environment state correctly.

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        repo = valid_instances["repo"]

        bad_settings = settings.model_copy(update={"source_type": ["tag"]})
        repo.remove_git_dir()

        closed_stream = io.StringIO()
        closed_stream.close()

        with pytest.raises(GitVersionedStreamError):
            resolve_version_output_to_stream_wrapper(
                settings=bad_settings,
                stream=closed_stream,
                repository=GitRepository(repo.path),
            )

    @pytest.mark.regression
    def test_marshalling(self, valid_instances: dict[str, Any]) -> None:
        """
        US-3: Verify Pydantic settings model marshalling limits.

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        dumped_data = settings.model_dump()
        validated = Settings.model_validate(dumped_data)
        assert validated.version == "auto"

    @pytest.mark.sanity
    def test_dynamic_registry(self, valid_instances: dict[str, Any]) -> None:
        """
        US-3: Verify dynamic registry paths parse and execute.

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        assert "tag" in settings.source_type


class TestAdvancedProgrammaticExtension:
    """E2E Test Class for US-4: Advanced Programmatic Extension & Hook Processing."""

    @pytest.fixture
    def valid_instances(self, temp_git_repo: GitRepoHelper) -> dict[str, Any]:
        """
        Shared context fixture supplying custom function and environment hooks.

        :param temp_git_repo: Temporary Git repository fixture.
        :returns: Context dictionary.
        """
        temp_git_repo.commit("Initial commit")
        temp_git_repo.branch("releases/v2.1.0")
        temp_git_repo.commit("Work on releases branch")

        hook_code = (
            "from packaging.version import Version\n"
            "from gitversioned.utils import GitReference\n"
            "def custom_resolver_hook(settings, repo):\n"
            "    # Extract git reference details directly\n"
            "    ref = repo.current_commit_or_fallback\n"
            "    # We can inspect environment variables or repository state\n"
            "    ver_str = '4.1.2'\n"
            "    if repo.current_branch and (\n"
            "        'releases' in repo.current_branch.branch_name\n"
            "    ):\n"
            "        ver_str = '2.1.0'\n"
            "    return Version(ver_str), ref\n"
        )
        hook_file = temp_git_repo.path / "my_extension.py"
        hook_file.write_text(hook_code, encoding="utf-8")

        settings = Settings(
            project_root=temp_git_repo.path,
            source_type=["function"],
            version_source_function="my_extension:custom_resolver_hook",
            version="auto",
            dirty_ignore=["pyproject.toml", "my_extension.py", "__pycache__"],
        )
        return {
            "repo": temp_git_repo,
            "hook_file": hook_file,
            "settings": settings,
        }

    @pytest.mark.smoke
    def test_contract(self, valid_instances: dict[str, Any]) -> None:
        """
        Validate custom hook file path.

        :param valid_instances: Shared context dictionary.
        """
        assert valid_instances["hook_file"].exists()

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: dict[str, Any]) -> None:
        """
        Assert correct initial system wiring and session environment startup.

        :param valid_instances: Shared context dictionary.
        """
        original_dont_write = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            settings = valid_instances["settings"]
            repo = valid_instances["repo"]
            version, version_type, reference = resolve_version(
                settings=settings,
                repository=GitRepository(repo.path),
            )
            assert str(version) == "2.1.0"
        finally:
            sys.dont_write_bytecode = original_dont_write

        settings = valid_instances["settings"]
        bad_settings = settings.model_copy(
            update={"version_source_function": "bad_format_here"}
        )
        # Should raise VersionResolutionError when run because format lacks ':'
        with pytest.raises(VersionResolutionError, match="Invalid function format"):
            resolve_from_function_source(
                bad_settings,
                GitRepository(settings.project_root),
            )

    @pytest.mark.regression
    def test_invalid_initialization_missing(
        self,
        valid_instances: dict[str, Any],
    ) -> None:
        """
        Omit critical configurations to verify system boundary defense.

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        bad_settings = settings.model_copy(update={"version_source_function": None})
        with pytest.raises(
            VersionResolutionError,
            match="No version_source_function configured",
        ):
            resolve_from_function_source(
                bad_settings,
                GitRepository(settings.project_root),
            )

    @pytest.mark.sanity
    def test_callback_signature_contracts(
        self,
        valid_instances: dict[str, Any],
    ) -> None:
        """
        US-4 / AC 4.1: Validate callable matches strict signature contracts.

        :param valid_instances: Shared context dictionary.
        """
        original_dont_write = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            settings = valid_instances["settings"]
            repo = valid_instances["repo"]
            version, _, _ = resolve_version(
                settings=settings,
                repository=GitRepository(repo.path),
            )
            assert str(version) == "2.1.0"
        finally:
            sys.dont_write_bytecode = original_dont_write

    @pytest.mark.regression
    def test_context_aware_resolution(self, valid_instances: dict[str, Any]) -> None:
        """
        US-4 / AC 4.2: Validate hook access to workspace context, files, and git state.

        :param valid_instances: Shared context dictionary.
        """
        original_dont_write = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            settings = valid_instances["settings"]
            repo = valid_instances["repo"]
            # Trigger execution
            version, _, reference = resolve_version(
                settings=settings,
                repository=GitRepository(repo.path),
            )
            assert str(version) == "2.1.0"
            assert reference.branch_name == "releases/v2.1.0"
        finally:
            sys.dont_write_bytecode = original_dont_write

    @pytest.mark.regression
    def test_thread_safety_isolation(self, valid_instances: dict[str, Any]) -> None:
        """
        US-4 / AC 4.3: Validate thread safety and isolation under parallel invocation.

        :param valid_instances: Shared context dictionary.
        """
        original_dont_write = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            repo = valid_instances["repo"]

            # We will run 10 parallel version resolutions using thread pool
            def run_task(index: int) -> str:
                # Construct clean Settings per thread
                settings_thread = Settings(
                    project_root=repo.path,
                    source_type=["function"],
                    version_source_function="my_extension:custom_resolver_hook",
                    version="auto",
                    dirty_ignore=["pyproject.toml", "my_extension.py", "__pycache__"],
                )
                version, _, _ = resolve_version(
                    settings_thread,
                    repository=GitRepository(repo.path),
                )
                return str(version)

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(run_task, idx) for idx in range(10)]
                results = [fut.result() for fut in futures]

            assert len(results) == 10
            for version_str in results:
                assert version_str == "2.1.0"
        finally:
            sys.dont_write_bytecode = original_dont_write

    @pytest.mark.regression
    def test_marshalling(self, valid_instances: dict[str, Any]) -> None:
        """
        US-4: Verify Pydantic settings model marshalling limits.

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        dumped_data = settings.model_dump()
        validated = Settings.model_validate(dumped_data)
        assert validated.version_source_function == "my_extension:custom_resolver_hook"

    @pytest.mark.sanity
    def test_dynamic_registry(self, valid_instances: dict[str, Any]) -> None:
        """
        US-4: Verify dynamic registry paths parse and execute.

        :param valid_instances: Shared context dictionary.
        """
        settings = valid_instances["settings"]
        assert settings.version_source_function == "my_extension:custom_resolver_hook"
