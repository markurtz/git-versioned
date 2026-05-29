from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest
from packaging.version import Version

import gitversioned.versioning as versioning_mod
from gitversioned.settings import (
    RegexStrategy,
    Settings,
    TemplatePathStrategy,
    TemplateStrStrategy,
)
from gitversioned.utils import BuildEnvironment, GitReference, GitRepository
from gitversioned.versioning import (
    VersionResolutionError,
    resolve_version,
    resolve_version_output,
    resolve_version_output_to_stream,
)
from gitversioned.versioning.generation import (
    FormattedVersion,
    _generate_output_from_template_strategy,
    generate_output_from_strategies,
)
from gitversioned.versioning.sources import (
    _extract_versions,
    resolve_from_file_source,
    resolve_from_function_source,
    resolve_from_git_source,
    resolve_sources_from_archive,
)
from tests.conftest import GitRepoHelper


@pytest.mark.sanity
def test_versioning_exports() -> None:
    """Validate public variables, constants, and module-level exports."""
    assert hasattr(versioning_mod, "__all__")
    expected_exports = [
        "VersionResolutionError",
        "resolve_version",
        "resolve_version_output",
        "resolve_version_output_to_stream",
    ]
    assert sorted(versioning_mod.__all__) == sorted(expected_exports)
    assert versioning_mod.VersionResolutionError is VersionResolutionError
    assert versioning_mod.resolve_version is resolve_version
    assert versioning_mod.resolve_version_output is resolve_version_output
    assert (
        versioning_mod.resolve_version_output_to_stream
        is resolve_version_output_to_stream
    )


@pytest.mark.sanity
def test_interface_signature_validation() -> None:
    """Validate structural contracts across integrated boundaries."""
    # Check inheritance lineage
    assert issubclass(FormattedVersion, Version)

    # Check method signatures and parameter names
    res_ver_sig = inspect.signature(resolve_version)
    assert "settings" in res_ver_sig.parameters
    assert "repository" in res_ver_sig.parameters
    assert "environment" in res_ver_sig.parameters

    res_out_sig = inspect.signature(resolve_version_output)
    assert "settings" in res_out_sig.parameters
    assert "repository" in res_out_sig.parameters
    assert "environment" in res_out_sig.parameters

    res_stream_sig = inspect.signature(resolve_version_output_to_stream)
    assert "settings" in res_stream_sig.parameters
    assert "repository" in res_stream_sig.parameters
    assert "environment" in res_stream_sig.parameters


class TestFormattedVersion:
    """Integration test suite for FormattedVersion class."""

    @pytest.fixture
    def valid_instances(self, request: pytest.FixtureRequest) -> FormattedVersion:
        """Fixture supplying properly initialized FormattedVersion instances."""
        params = request.param
        return FormattedVersion(
            version=params["version"],
            version_type=params["version_type"],
            version_standard=params.get("version_standard", "pep440"),
        )

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "valid_instances",
        [
            {"version": Version("1.0.0.dev1"), "version_type": "dev"},
            {"version": Version("2.1.0"), "version_type": "release"},
        ],
        indirect=True,
    )
    def test_initialization(self, valid_instances: FormattedVersion) -> None:
        """Test initialization with valid inputs."""
        assert isinstance(valid_instances, FormattedVersion)
        assert isinstance(valid_instances, Version)

    @pytest.mark.sanity
    def test_invalid_initialization_values(self) -> None:
        """Test that invalid values trigger ValueError when formatted."""
        version_obj = FormattedVersion(
            Version("1.0.0"), "release", version_standard="semver3"
        )
        with pytest.raises(ValueError, match="Unsupported version standard: semver3"):
            str(version_obj)

    @pytest.mark.sanity
    def test_invalid_initialization_missing(self) -> None:
        """Test missing parameter types raise TypeError."""
        with pytest.raises(TypeError):
            FormattedVersion()  # type: ignore

        with pytest.raises(TypeError):
            FormattedVersion(Version("1.0.0"))  # type: ignore

    @pytest.mark.regression
    @pytest.mark.parametrize(
        ("version_str", "version_type", "version_standard", "expected"),
        [
            ("1.0.0", "release", "pep440", "1.0.0"),
            ("1.0.0.post1", "post", "semver2", "1.0.0-post1"),
            ("2.0.0a1", "pre", "semver2", "2.0.0a1"),
            ("3.0.0.dev4", "dev", "semver2", "3.0.0-dev4"),
            ("1.2.3.post0+local.info", "post", "semver2", "1.2.3-post0+local.info"),
        ],
    )
    def test___str__(
        self,
        version_str: str,
        version_type: str,
        version_standard: str,
        expected: str,
    ) -> None:
        """Test PEP 440 vs SemVer 2 string formatting pipelines."""
        version_obj = FormattedVersion(
            version=Version(version_str),
            version_type=version_type,  # type: ignore
            version_standard=version_standard,
        )
        assert str(version_obj) == expected

    @pytest.mark.regression
    def test___repr__(self) -> None:
        """Test developer representation formatting."""
        version_obj = FormattedVersion(Version("1.0.0"), "release")
        assert repr(version_obj) == "'1.0.0'"


class TestResolveVersion:
    """Integration test suite for resolve_version orchestrator."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        (
            "repo_state",
            "source_type",
            "version_override",
            "expected_version",
            "expected_type",
        ),
        [
            ("tagged", ["tag"], "auto", "1.0.0", "release"),
            ("clean", ["auto"], "2.3.4", "2.3.4", "release"),
        ],
    )
    def test_invocation_smoke(
        self,
        temp_git_repo: GitRepoHelper,
        repo_state: str,
        source_type: list[str],
        version_override: str,
        expected_version: str,
        expected_type: str,
    ) -> None:
        """Test basic successful version resolutions."""
        temp_git_repo.setup_state(repo_state)
        settings = Settings(
            project_root=temp_git_repo.path,
            source_type=source_type,
            version=version_override,
            dirty_ignore=["pyproject.toml"],
        )
        version, version_type, reference = resolve_version(settings)
        assert str(version) == expected_version
        assert version_type == expected_type
        assert isinstance(reference, GitReference)

    @pytest.mark.sanity
    def test_invocation_sanity_branch(self, temp_git_repo: GitRepoHelper) -> None:
        """Test version resolution from current branch name."""
        temp_git_repo.commit("Initial commit")
        temp_git_repo.branch("releases/v1.2.0")
        settings = Settings(
            project_root=temp_git_repo.path,
            source_type=["branch"],
            version="auto",
            dirty_ignore=["pyproject.toml"],
        )
        version, version_type, reference = resolve_version(settings)
        assert str(version) == "1.2.0"
        assert version_type == "release"
        assert reference.branch_name == "releases/v1.2.0"

    @pytest.mark.sanity
    def test_invocation_sanity_commit(self, temp_git_repo: GitRepoHelper) -> None:
        """Test version resolution from commit message."""
        temp_git_repo.commit("Initial commit")
        temp_git_repo.commit("release v1.3.0")
        settings = Settings(
            project_root=temp_git_repo.path,
            source_type=["commit"],
            version="auto",
            dirty_ignore=["pyproject.toml"],
        )
        version, version_type, reference = resolve_version(settings)
        assert str(version) == "1.3.0"
        assert version_type == "release"
        assert "release v1.3.0" in reference.commit_message

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("auto_inc", "expected_version"),
        [
            ({"release": "major"}, "2.0.0"),
            ({"release": "minor"}, "1.1.0"),
            ({"release": "patch"}, "1.0.1"),
        ],
    )
    def test_invocation_sanity_increment(
        self,
        temp_git_repo: GitRepoHelper,
        auto_inc: dict[str, str],
        expected_version: str,
    ) -> None:
        """Test auto-increment functionality after resolving base version."""
        temp_git_repo.setup_state("tagged")
        settings = Settings(
            project_root=temp_git_repo.path,
            source_type=["tag"],
            auto_increment=auto_inc,  # type: ignore
            dirty_ignore=["pyproject.toml"],
        )
        version, version_type, reference = resolve_version(settings)
        assert str(version) == expected_version
        assert version_type == "release"

    @pytest.mark.sanity
    def test_invalid_sanity_fallback(self, temp_git_repo: GitRepoHelper) -> None:
        """Test fallback to 0.1.0 when no version source resolves a version."""
        temp_git_repo.setup_state("clean")
        settings = Settings(
            project_root=temp_git_repo.path,
            source_type=["tag"],
            version="auto",
            dirty_ignore=["pyproject.toml"],
        )
        version, version_type, reference = resolve_version(settings)
        assert str(version) == "0.1.0"
        assert version_type == "release"
        assert isinstance(reference, GitReference)

    @pytest.mark.regression
    def test_invocation_regression_function(self, temp_git_repo: GitRepoHelper) -> None:
        """Test version resolution calling a custom Python function."""
        # Disable bytecode writing to prevent __pycache__ dirtying the repository
        original_dont_write = sys.dont_write_bytecode
        sys.dont_write_bytecode = True

        try:
            temp_git_repo.commit("Initial commit")
            function_code = (
                "from packaging.version import Version\n"
                "from gitversioned.utils import GitReference\n"
                "def get_version(settings, repo):\n"
                "    return Version('4.5.6'), repo.current_commit_or_fallback\n"
            )
            (temp_git_repo.path / "version_func.py").write_text(
                function_code, encoding="utf-8"
            )

            settings = Settings(
                project_root=temp_git_repo.path,
                source_type=["function"],
                version_source_function="version_func:get_version",
                version="auto",
                dirty_ignore=["pyproject.toml", "version_func.py", "__pycache__"],
            )
            version, version_type, reference = resolve_version(settings)
            assert str(version) == "4.5.6"
            assert version_type == "release"
        finally:
            sys.dont_write_bytecode = original_dont_write

    @pytest.mark.regression
    def test_invocation_regression_archive(self, temp_git_repo: GitRepoHelper) -> None:
        """Test version resolution from an archival export file."""
        archive_content = (
            "commit_sha: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
            "short_sha: aaaaaaa\n"
            "timestamp: 2026-05-28T07:00:21Z\n"
            "author_name: Test User\n"
            "author_email: test@example.com\n"
            "ref_names: tag: v1.5.0\n"
            "distance_from_head: 0\n"
            "is_head_commit: true\n"
            "total_commits: 1\n"
            "is_current_branch: true\n"
            "commit_message:\n"
            "Initial release\n"
        )
        (temp_git_repo.path / ".git_archival.txt").write_text(
            archive_content, encoding="utf-8"
        )

        settings = Settings(
            project_root=temp_git_repo.path,
            source_type=["tag"],
            version="auto",
            version_source_archive=".git_archival.txt",
            dirty_ignore=["pyproject.toml"],
        )
        # Simulate non-git environment by using a setting or no git directory
        temp_git_repo.remove_git_dir()

        version, version_type, reference = resolve_version(settings)
        assert str(version) == "1.5.0"
        assert version_type == "release"
        assert reference.tag_name == "v1.5.0"

    @pytest.mark.regression
    def test_invalid_regression_unknown_source(
        self, temp_git_repo: GitRepoHelper
    ) -> None:
        """Test ValueError when source_type is unknown."""
        settings = Settings(
            project_root=temp_git_repo.path,
            source_type=["invalid_source"],
        )
        with pytest.raises(ValueError, match="Unknown source type: invalid_source"):
            resolve_version(settings)


class TestResolveVersionOutput:
    """Integration test suite for resolve_version_output orchestrator."""

    @pytest.mark.smoke
    def test_invocation_smoke(self, temp_git_repo: GitRepoHelper) -> None:
        """Test formatting using TemplateStrStrategy."""
        temp_git_repo.setup_state("tagged")
        settings = Settings(
            project_root=temp_git_repo.path,
            source_type=["tag"],
            version="auto",
            output_strategies=TemplateStrStrategy(content="__version__ = '{version}'"),
            dirty_ignore=["pyproject.toml"],
        )
        output_content, version, version_type, reference = resolve_version_output(
            settings
        )
        assert output_content == "__version__ = '1.0.0'"
        assert str(version) == "1.0.0"

    @pytest.mark.sanity
    def test_invocation_sanity_path(self, temp_git_repo: GitRepoHelper) -> None:
        """Test formatting using TemplatePathStrategy."""
        temp_git_repo.setup_state("tagged")
        template_file = temp_git_repo.path / "template.txt"
        template_file.write_text("Version is: {version}", encoding="utf-8")

        settings = Settings(
            project_root=temp_git_repo.path,
            source_type=["tag"],
            version="auto",
            output_strategies=TemplatePathStrategy(path=Path("template.txt")),
            dirty_ignore=["pyproject.toml", "template.txt"],
        )
        output_content, version, version_type, reference = resolve_version_output(
            settings
        )
        assert output_content == "Version is: 1.0.0"

    @pytest.mark.regression
    def test_invocation_regression_regex(self, temp_git_repo: GitRepoHelper) -> None:
        """Test replacing version string inline using RegexStrategy."""
        temp_git_repo.setup_state("tagged")
        target_file = temp_git_repo.path / "version.py"
        target_file.write_text('__version__ = "0.0.0"', encoding="utf-8")

        settings = Settings(
            project_root=temp_git_repo.path,
            source_type=["tag"],
            version="auto",
            output="version.py",
            output_strategies=RegexStrategy(
                pattern=r'__version__ = "(?P<version>.*?)"'
            ),
            dirty_ignore=["pyproject.toml"],
        )
        output_content, version, version_type, reference = resolve_version_output(
            settings
        )
        assert output_content == '__version__ = "1.0.0"'

    @pytest.mark.sanity
    def test_invalid_sanity_missing_path(self, temp_git_repo: GitRepoHelper) -> None:
        """Test missing template path raises FileNotFoundError."""
        settings = Settings(
            project_root=temp_git_repo.path,
            output_strategies=TemplatePathStrategy(path=Path("nonexistent.txt")),
        )
        with pytest.raises(FileNotFoundError):
            resolve_version_output(settings)

    @pytest.mark.regression
    def test_invalid_regression_regex_mismatch(
        self, temp_git_repo: GitRepoHelper
    ) -> None:
        """Test RegexStrategy raises ValueError if pattern not found in output file."""
        temp_git_repo.setup_state("tagged")
        target_file = temp_git_repo.path / "version.py"
        target_file.write_text('__version__ = "0.0.0"', encoding="utf-8")

        settings = Settings(
            project_root=temp_git_repo.path,
            source_type=["tag"],
            version="auto",
            output="version.py",
            output_strategies=RegexStrategy(pattern=r"non_matching_pattern"),
        )
        with pytest.raises(ValueError, match="Regex pattern .* not found"):
            resolve_version_output(settings)


class TestResolveVersionOutputToStream:
    """Integration test suite for resolve_version_output_to_stream orchestrator."""

    @pytest.mark.smoke
    def test_invocation_smoke(
        self,
        temp_git_repo: GitRepoHelper,
    ) -> None:
        """Test writing generated output to a file."""
        temp_git_repo.setup_state("tagged")
        settings = Settings(
            project_root=temp_git_repo.path,
            source_type=["tag"],
            version="auto",
            output="version.py",
            output_strategies=TemplateStrStrategy(content="{version}"),
            dirty_ignore=["pyproject.toml"],
        )
        output_path, content, version, version_type, reference = (
            resolve_version_output_to_stream(settings)
        )
        assert output_path is not None
        assert output_path.name == "version.py"
        assert content == "1.0.0"
        assert output_path.read_text(encoding="utf-8") == "1.0.0"

    @pytest.mark.sanity
    def test_invocation_sanity_nested_file(self, temp_git_repo: GitRepoHelper) -> None:
        """Test writing generated output to a nested file path."""
        temp_git_repo.setup_state("tagged")
        settings = Settings(
            project_root=temp_git_repo.path,
            source_type=["tag"],
            version="auto",
            output="nested/dirs/output.py",
            output_strategies=TemplateStrStrategy(content="__version__ = '{version}'"),
            dirty_ignore=["pyproject.toml"],
        )
        output_path, content, version, version_type, reference = (
            resolve_version_output_to_stream(settings)
        )
        assert isinstance(output_path, Path)
        assert output_path.exists()
        assert output_path.read_text(encoding="utf-8") == "__version__ = '1.0.0'"

    @pytest.mark.regression
    def test_invalid_regression_dir_write_fail(
        self, temp_git_repo: GitRepoHelper
    ) -> None:
        """Test ValueError is raised when writing to a directory instead of a file."""
        settings = Settings(
            project_root=temp_git_repo.path,
            output=str(temp_git_repo.path),  # Attempting to write to directory path
            output_strategies=TemplateStrStrategy(content="{version}"),
        )
        with pytest.raises(ValueError, match="Invalid output target"):
            resolve_version_output_to_stream(settings)


@pytest.mark.sanity
def test_registry_integration(temp_git_repo: GitRepoHelper) -> None:
    """Validate resolver registry integration across different priority keys."""
    # Ensure all registered resolver keys are processed or fall back
    # to VersionResolutionError.
    temp_git_repo.setup_state("clean")

    # Mock settings with various source types
    settings = Settings(
        project_root=temp_git_repo.path,
        source_type=["file", "tag", "branch", "commit"],
        version_source_file="nonexistent.txt",
        version="auto",
        dirty_ignore=["pyproject.toml"],
    )

    # Calling resolve_version will execute the registry resolvers in sequence.
    # Since they all fail, it falls back to 0.1.0 rather than raising unexpected errors.
    version, version_type, reference = resolve_version(settings)
    assert str(version) == "0.1.0"


@pytest.mark.regression
def test_strategy_marshalling(temp_git_repo: GitRepoHelper) -> None:
    """Test strategy dict mapping based on version_type."""
    temp_git_repo.setup_state("tagged")
    settings = Settings(
        project_root=temp_git_repo.path,
        source_type=["tag"],
        version="auto",
        output_strategies={
            "release": TemplateStrStrategy(content="Release: {version}"),
            "dev": TemplateStrStrategy(content="Dev: {version}"),
        },
        dirty_ignore=["pyproject.toml"],
    )

    # Validate output for 'release'
    settings.version_type = "release"
    output_content, version, version_type, reference = resolve_version_output(settings)
    assert output_content == "Release: 1.0.0"

    # Validate output for 'dev'
    settings.version_type = "dev"
    output_content, version, version_type, reference = resolve_version_output(settings)
    assert output_content.startswith("Dev: 1.0.0.dev")


class TestCoverageEdgeCases:
    """Test cases to ensure complete code path coverage in versioning package."""

    @pytest.mark.sanity
    def test_resolve_version_output_to_stream_no_output(
        self, temp_git_repo: GitRepoHelper
    ) -> None:
        """Test resolve_version_output_to_stream when output setting is empty."""
        temp_git_repo.setup_state("tagged")
        settings = Settings(
            project_root=temp_git_repo.path,
            source_type=["tag"],
            version="auto",
            output="",
            dirty_ignore=["pyproject.toml"],
        )
        output_path, content, version, version_type, reference = (
            resolve_version_output_to_stream(settings)
        )
        assert output_path is None
        assert content != ""

    @pytest.mark.regression
    def test_resolve_version_output_to_stream_resolve_none(
        self, temp_git_repo: GitRepoHelper
    ) -> None:
        """Test ValueError when output path cannot be resolved from root."""
        temp_git_repo.setup_state("tagged")

        class SettingsWithResolveNone(Settings):
            """Subclass overriding resolve_path_from_root to return None for output."""

            def resolve_path_from_root(
                self, path: str | Path | None, enforce_existence: bool = True
            ) -> Path | None:
                if path == self.output:
                    return None
                return super().resolve_path_from_root(path, enforce_existence)

        settings = SettingsWithResolveNone(
            project_root=temp_git_repo.path,
            source_type=["tag"],
            version="auto",
            output="some_output.txt",
            dirty_ignore=["pyproject.toml"],
        )

        with pytest.raises(
            ValueError, match="Could not resolve output path for target"
        ):
            resolve_version_output_to_stream(settings)

    @pytest.mark.sanity
    def test_dict_strategies_edge_cases(self, temp_git_repo: GitRepoHelper) -> None:
        """Test various dict strategy resolution pathways."""
        temp_git_repo.setup_state("tagged")
        repository = GitRepository(temp_git_repo.path)
        environment = BuildEnvironment(project_root=temp_git_repo.path)

        # 1. Dict of length 1 (uses the single value regardless of version_type)
        settings_single = Settings(
            project_root=temp_git_repo.path,
            output_strategies={
                "other_type": TemplateStrStrategy(content="Single: {version}")
            },
        )
        output_content = generate_output_from_strategies(
            Version("1.0.0"),
            "release",
            GitReference(short_sha="abcdefg"),
            settings_single,
            repository,
            environment,
        )
        assert output_content == "Single: 1.0.0"

        # 2. Dict missing matching version type but containing 'release'
        settings_fallback = Settings(
            project_root=temp_git_repo.path,
            output_strategies={
                "release": TemplateStrStrategy(content="Fallback: {version}"),
                "dev": TemplateStrStrategy(content="Dev: {version}"),
            },
        )
        output_content = generate_output_from_strategies(
            Version("1.0.0"),
            "alpha",
            GitReference(short_sha="abcdefg"),
            settings_fallback,
            repository,
            environment,
        )
        assert output_content == "Fallback: 1.0.0"

        # 3. Dict missing both matching version type and 'release' -> raises ValueError
        settings_invalid = Settings(
            project_root=temp_git_repo.path,
            output_strategies={
                "dev": TemplateStrStrategy(content="Dev: {version}"),
                "pre": TemplateStrStrategy(content="Pre: {version}"),
            },
        )
        with pytest.raises(ValueError, match="Could not determine output strategy"):
            generate_output_from_strategies(
                Version("1.0.0"),
                "release",
                GitReference(short_sha="abcdefg"),
                settings_invalid,
                repository,
                environment,
            )

        # 4. Invalid strategy configuration type -> raises ValueError
        settings_bad_type = Settings(
            project_root=temp_git_repo.path,
            dirty_ignore=["pyproject.toml"],
        )
        # Use object.__setattr__ to bypass Pydantic validate_assignment
        # during test setup
        object.__setattr__(
            settings_bad_type,
            "output_strategies",
            [TemplateStrStrategy(content="...")],
        )
        with pytest.raises(ValueError, match="Could not determine output strategy"):
            generate_output_from_strategies(
                Version("1.0.0"),
                "release",
                GitReference(short_sha="abcdefg"),
                settings_bad_type,
                repository,
                environment,
            )

        # 5. Unsupported strategy class type inside dictionary -> raises ValueError
        settings_unsupported = Settings(
            project_root=temp_git_repo.path,
            dirty_ignore=["pyproject.toml"],
        )
        object.__setattr__(
            settings_unsupported,
            "output_strategies",
            {"release": "unsupported_str_value"},
        )
        with pytest.raises(ValueError, match="Unsupported strategy type"):
            generate_output_from_strategies(
                Version("1.0.0"),
                "release",
                GitReference(short_sha="abcdefg"),
                settings_unsupported,
                repository,
                environment,
            )

    @pytest.mark.regression
    def test_regex_strategy_missing_file(self, temp_git_repo: GitRepoHelper) -> None:
        """Test RegexStrategy raises FileNotFoundError when target output file does

        not exist.
        """
        temp_git_repo.setup_state("tagged")
        repository = GitRepository(temp_git_repo.path)
        environment = BuildEnvironment(project_root=temp_git_repo.path)
        settings = Settings(
            project_root=temp_git_repo.path,
            output="nonexistent_output.py",
            output_strategies=RegexStrategy(pattern="version"),
            dirty_ignore=["pyproject.toml"],
        )
        with pytest.raises(FileNotFoundError, match="Could not resolve content"):
            generate_output_from_strategies(
                Version("1.0.0"),
                "release",
                GitReference(short_sha="abcdefg"),
                settings,
                repository,
                environment,
            )

    @pytest.mark.regression
    def test_regex_strategy_no_named_groups(self, temp_git_repo: GitRepoHelper) -> None:
        """Test RegexStrategy works when pattern has no named capture groups."""
        temp_git_repo.setup_state("tagged")
        repository = GitRepository(temp_git_repo.path)
        environment = BuildEnvironment(project_root=temp_git_repo.path)
        output_file = temp_git_repo.path / "version.py"
        output_file.write_text("VERSION_STR = '0.0.0'", encoding="utf-8")

        settings = Settings(
            project_root=temp_git_repo.path,
            output="version.py",
            output_strategies=RegexStrategy(pattern=r"\d+\.\d+\.\d+"),
            dirty_ignore=["pyproject.toml"],
        )
        output_content = generate_output_from_strategies(
            Version("1.2.3"),
            "release",
            GitReference(short_sha="abcdefg"),
            settings,
            repository,
            environment,
        )
        assert output_content == "VERSION_STR = '1.2.3'"

    @pytest.mark.regression
    def test_resolve_from_file_source_none(self, temp_git_repo: GitRepoHelper) -> None:
        """Test resolve_from_file_source raises VersionResolutionError when file is

        None.
        """
        temp_git_repo.setup_state("clean")
        settings = Settings(
            project_root=temp_git_repo.path,
            version_source_file=None,
        )
        repository = GitRepository(temp_git_repo.path)
        with pytest.raises(
            VersionResolutionError, match="No version_source_file configured"
        ):
            resolve_from_file_source(settings, repository)

    @pytest.mark.regression
    def test_resolve_from_file_source_directory(
        self, temp_git_repo: GitRepoHelper
    ) -> None:
        """Test resolve_from_file_source raises VersionResolutionError when source

        path is a directory.
        """
        temp_git_repo.setup_state("clean")
        settings = Settings(
            project_root=temp_git_repo.path,
            # Point to a directory instead of a file
            version_source_file="subfolder",
            dirty_ignore=["pyproject.toml"],
        )
        (temp_git_repo.path / "subfolder").mkdir(exist_ok=True)
        repository = GitRepository(temp_git_repo.path)
        with pytest.raises(VersionResolutionError, match="Failed to read version file"):
            resolve_from_file_source(settings, repository)

    @pytest.mark.regression
    def test_resolve_from_file_source_no_match(
        self, temp_git_repo: GitRepoHelper
    ) -> None:
        """Test resolve_from_file_source raises VersionResolutionError when regex

        pattern does not match content.
        """
        temp_git_repo.setup_state("clean")
        version_file = temp_git_repo.path / "version.txt"
        version_file.write_text("no version here", encoding="utf-8")
        settings = Settings(
            project_root=temp_git_repo.path,
            version_source_file="version.txt",
            dirty_ignore=["pyproject.toml", "version.txt"],
        )
        repository = GitRepository(temp_git_repo.path)
        with pytest.raises(
            VersionResolutionError, match="No version found for patterns"
        ):
            resolve_from_file_source(settings, repository)

    @pytest.mark.smoke
    def test_resolve_from_file_source_success(
        self, temp_git_repo: GitRepoHelper
    ) -> None:
        """Test resolve_from_file_source successfully extracts version."""
        temp_git_repo.setup_state("clean")
        version_file = temp_git_repo.path / "version.txt"
        version_file.write_text("__version__ = '3.4.5'", encoding="utf-8")
        settings = Settings(
            project_root=temp_git_repo.path,
            version_source_file="version.txt",
            dirty_ignore=["pyproject.toml", "version.txt"],
        )
        repository = GitRepository(temp_git_repo.path)
        version, reference = resolve_from_file_source(settings, repository)
        assert str(version) == "3.4.5"
        assert isinstance(reference, GitReference)

    @pytest.mark.regression
    def test_resolve_from_function_source_invalid_format(
        self, temp_git_repo: GitRepoHelper
    ) -> None:
        """Test resolve_from_function_source raises VersionResolutionError when

        format is wrong.
        """
        temp_git_repo.setup_state("clean")
        settings = Settings(
            project_root=temp_git_repo.path,
            version_source_function="invalid_format_no_colon",
        )
        repository = GitRepository(temp_git_repo.path)
        with pytest.raises(VersionResolutionError, match="Invalid function format"):
            resolve_from_function_source(settings, repository)

    @pytest.mark.regression
    def test_resolve_from_function_source_invalid_returns(
        self, temp_git_repo: GitRepoHelper
    ) -> None:
        """Test resolve_from_function_source raises ValueError when function

        returns wrong types.
        """
        temp_git_repo.setup_state("clean")
        function_code = (
            "def get_version(settings, repo):\n    return 'not-a-Version', None\n"
        )
        (temp_git_repo.path / "bad_func.py").write_text(function_code, encoding="utf-8")
        settings = Settings(
            project_root=temp_git_repo.path,
            version_source_function="bad_func:get_version",
            dirty_ignore=["pyproject.toml", "bad_func.py"],
        )
        repository = GitRepository(temp_git_repo.path)
        with pytest.raises(ValueError, match="did not return a valid version"):
            resolve_from_function_source(settings, repository)

        function_code_no_ref = (
            "from packaging.version import Version\n"
            "def get_version(settings, repo):\n"
            "    return Version('1.0.0'), 'not-a-GitReference'\n"
        )
        (temp_git_repo.path / "bad_func2.py").write_text(
            function_code_no_ref, encoding="utf-8"
        )
        settings.version_source_function = "bad_func2:get_version"
        settings.dirty_ignore = ["pyproject.toml", "bad_func.py", "bad_func2.py"]
        with pytest.raises(ValueError, match="did not return a valid reference"):
            resolve_from_function_source(settings, repository)

    @pytest.mark.regression
    def test_resolve_from_git_source_invalid_type(
        self, temp_git_repo: GitRepoHelper
    ) -> None:
        """Test resolve_from_git_source raises ValueError when git type is invalid."""
        temp_git_repo.setup_state("clean")
        repository = GitRepository(temp_git_repo.path)
        settings = Settings(project_root=temp_git_repo.path)
        with pytest.raises(ValueError, match="Invalid git type"):
            resolve_from_git_source("invalid_type", settings, repository)  # type: ignore

    @pytest.mark.regression
    def test_resolve_sources_from_archive_directory(
        self, temp_git_repo: GitRepoHelper
    ) -> None:
        """Test resolve_sources_from_archive raises VersionResolutionError when

        path is a directory.
        """
        temp_git_repo.setup_state("clean")
        (temp_git_repo.path / "archive_dir").mkdir(exist_ok=True)
        settings = Settings(
            project_root=temp_git_repo.path,
            version_source_archive="archive_dir",
            dirty_ignore=["pyproject.toml"],
        )
        with pytest.raises(VersionResolutionError, match="Failed to read archive file"):
            resolve_sources_from_archive(["tag"], settings)

    @pytest.mark.regression
    def test_resolve_sources_from_archive_missing(
        self, temp_git_repo: GitRepoHelper
    ) -> None:
        """Test resolve_sources_from_archive raises VersionResolutionError when

        file is missing.
        """
        settings = Settings(
            project_root=temp_git_repo.path,
            version_source_archive="nonexistent_archive_file.txt",
        )
        with pytest.raises(
            VersionResolutionError, match="Version file not found for source"
        ):
            resolve_sources_from_archive(["tag"], settings)

    @pytest.mark.regression
    def test_resolve_sources_from_archive_no_match(
        self, temp_git_repo: GitRepoHelper
    ) -> None:
        """Test resolve_sources_from_archive raises VersionResolutionError when no

        match is found.
        """
        temp_git_repo.setup_state("clean")
        (temp_git_repo.path / "archive.txt").write_text(
            "commit_sha: abc\n", encoding="utf-8"
        )
        settings = Settings(
            project_root=temp_git_repo.path,
            version_source_archive="archive.txt",
            dirty_ignore=["pyproject.toml", "archive.txt"],
        )
        with pytest.raises(
            VersionResolutionError, match="No version found for archive"
        ):
            resolve_sources_from_archive(["tag"], settings)

    @pytest.mark.regression
    def test_resolve_sources_from_archive_fallback_loop(
        self, temp_git_repo: GitRepoHelper
    ) -> None:
        """Test archive resolution loops to fallback source when first source fails

        to extract version.
        """
        archive_content = (
            "commit_sha: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
            "short_sha: aaaaaaa\n"
            "timestamp: 2026-05-28T07:00:21Z\n"
            "author_name: Test User\n"
            "author_email: test@example.com\n"
            "ref_names: tag: bad_tag_val, releases/v2.1.0\n"
            "distance_from_head: 0\n"
            "is_head_commit: true\n"
            "total_commits: 1\n"
            "is_current_branch: true\n"
            "commit_message:\n"
            "Initial release\n"
        )
        (temp_git_repo.path / ".git_archival.txt").write_text(
            archive_content, encoding="utf-8"
        )
        settings = Settings(
            project_root=temp_git_repo.path,
            source_type=["tag", "branch"],
            version="auto",
            version_source_archive=".git_archival.txt",
            dirty_ignore=["pyproject.toml"],
        )
        version, reference = resolve_sources_from_archive(["tag", "branch"], settings)
        assert str(version) == "2.1.0"
        assert isinstance(reference, GitReference)

    @pytest.mark.regression
    def test_extract_versions_missing_segments(self) -> None:
        """Test _extract_versions logs warning when major/minor/micro group matches

        are missing.
        """
        patterns = [r"(?P<major>\d+)"]  # Missing minor/micro named groups
        text = "1"
        with pytest.raises(
            VersionResolutionError, match="No version found for patterns"
        ):
            _extract_versions(patterns, text)

    @pytest.mark.regression
    def test_generate_output_from_template_strategy_invalid(
        self, temp_git_repo: GitRepoHelper
    ) -> None:
        """Test _generate_output_from_template_strategy raises ValueError for

        invalid strategy type.
        """
        repository = GitRepository(temp_git_repo.path)
        environment = BuildEnvironment(project_root=temp_git_repo.path)
        settings = Settings(project_root=temp_git_repo.path)
        with pytest.raises(ValueError, match="Invalid output strategy type"):
            _generate_output_from_template_strategy(
                "invalid_strategy_type",  # type: ignore
                Version("1.0.0"),
                "release",
                GitReference(short_sha="abcdefg"),
                settings,
                repository,
                environment,
            )
