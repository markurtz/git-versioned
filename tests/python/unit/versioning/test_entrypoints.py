from __future__ import annotations

import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest

from gitversioned.settings import (
    RegexStrategy,
    Settings,
    TemplatePathStrategy,
    TemplateStrStrategy,
)
from gitversioned.utils import BuildEnvironment, GitRepository
from gitversioned.versioning.entrypoints import (
    resolve_version,
    resolve_version_output,
    resolve_version_output_to_stream,
)

if TYPE_CHECKING:
    import pytest_mock

    from tests.conftest import GitRepoHelper


class TestResolveVersion:
    @pytest.mark.smoke
    def test_signature(self) -> None:
        sig = inspect.signature(resolve_version)
        assert "settings" in sig.parameters
        assert "repository" in sig.parameters
        assert "environment" in sig.parameters

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("repo_state", "expected_prefix", "auto_inc", "ver_type"),
        [
            ("clean", "0.1", None, "auto"),
            ("commit_no_tag", "0.1", None, "auto"),
            ("lightweight_tag", "1.0", None, "auto"),
            ("annotated_tag", "1.0", None, "auto"),
            ("tagged_plus_commit", "1.0", None, "auto"),
            ("dirty", "0.1", None, "auto"),
            ("tagged_dirty", "1.0", None, "auto"),
            ("detached", "1.0", None, "auto"),
            ("shallow", "1.0", None, "auto"),
            ("no_git", "0.1", None, "auto"),
            ("lightweight_tag", "2.0", {"release": "major"}, "auto"),
            ("lightweight_tag", "1.1", {"release": "minor"}, "auto"),
            ("lightweight_tag", "1.0", {"dev": "patch"}, "auto"),
            ("tagged_plus_commit", "1.0", {"dev": "patch"}, "auto"),
            ("tagged_plus_commit", "2.0", {"dev": "major"}, "auto"),
            ("clean", "0.1", None, "release"),
            ("dirty", "0.1", None, "dev"),
        ],
    )
    def test_invocation(
        self,
        temp_git_repo: GitRepoHelper,
        repo_state: str,
        expected_prefix: str,
        auto_inc: dict[Any, Any] | None,
        ver_type: Any,
    ) -> None:
        helper = temp_git_repo.setup_state(repo_state)
        settings = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            auto_increment=auto_inc,
            version_type=ver_type,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository = GitRepository(helper.path)
        environment = BuildEnvironment(project_root=helper.path)

        version, resolved_type, reference = resolve_version(
            settings=settings,
            repository=repository,
            environment=environment,
        )

        assert str(version).startswith(expected_prefix)
        assert isinstance(resolved_type, str)
        assert reference is not None

    @pytest.mark.sanity
    def test_default_repo_and_env(
        self,
        temp_git_repo: GitRepoHelper,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        settings = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        version, resolved_type, reference = resolve_version(
            settings=settings,
            repository=None,
            environment=None,
        )
        assert version is not None
        assert resolved_type is not None
        assert reference is not None

    @pytest.mark.regression
    @pytest.mark.parametrize(
        "source_types",
        [
            ["tag"],
            ["file"],
        ],
    )
    def test_invalid(
        self,
        temp_git_repo: GitRepoHelper,
        source_types: list[str],
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        settings = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            source_type=source_types,
            version_source_file="nonexistent_source_file.txt",
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository = GitRepository(helper.path)
        environment = BuildEnvironment(project_root=helper.path)

        version, resolved_type, reference = resolve_version(
            settings=settings,
            repository=repository,
            environment=environment,
        )

        assert str(version).startswith("0.1.0")
        assert resolved_type == "release"
        assert reference is not None

    @pytest.mark.regression
    def test_auto_increment_invalid(
        self,
        temp_git_repo: GitRepoHelper,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        settings = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            auto_increment={"release": "major"},
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        # Bypassing validation to check fallback handling
        if settings.auto_increment is not None:
            settings.auto_increment["release"] = cast("Any", "invalid_level")

        repository = GitRepository(helper.path)
        environment = BuildEnvironment(project_root=helper.path)

        version, resolved_type, reference = resolve_version(
            settings=settings,
            repository=repository,
            environment=environment,
        )
        assert version is not None
        assert resolved_type is not None


class TestResolveVersionOutput:
    @pytest.mark.smoke
    def test_signature(self) -> None:
        sig = inspect.signature(resolve_version_output)
        assert "settings" in sig.parameters
        assert "repository" in sig.parameters
        assert "environment" in sig.parameters

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("template_format", "expected_content"),
        [
            ("version={version}", "version="),
            ("hash={ref.short_sha}", "hash="),
        ],
    )
    def test_invocation(
        self,
        temp_git_repo: GitRepoHelper,
        template_format: str,
        expected_content: str,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")

        settings = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            output_strategies=TemplateStrStrategy(content=template_format),
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository = GitRepository(helper.path)
        environment = BuildEnvironment(project_root=helper.path)

        output, version, resolved_type, reference = resolve_version_output(
            settings=settings,
            repository=repository,
            environment=environment,
        )

        assert expected_content in output
        assert version is not None
        assert resolved_type is not None
        assert reference is not None

    @pytest.mark.sanity
    def test_regex_strategy_happy_path(
        self,
        temp_git_repo: GitRepoHelper,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        output_file = Path(helper.path) / "version_file.py"
        output_file.write_text(
            "__version__ = '0.0.0'\nother_info = 'info'", encoding="utf-8"
        )

        strategy = RegexStrategy(pattern=r"__version__ = '(?P<version>.*?)'")
        settings = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            output="version_file.py",
            output_strategies=strategy,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository = GitRepository(helper.path)
        environment = BuildEnvironment(project_root=helper.path)

        output, version, resolved_type, reference = resolve_version_output(
            settings=settings,
            repository=repository,
            environment=environment,
        )
        assert "__version__ = '" in output
        assert "other_info = 'info'" in output

    @pytest.mark.sanity
    def test_regex_strategy_no_groups(
        self,
        temp_git_repo: GitRepoHelper,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        output_file = Path(helper.path) / "version_file.py"
        output_file.write_text("version_string = '0.0.0'\n", encoding="utf-8")

        strategy = RegexStrategy(pattern=r"'0.0.0'")
        settings = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            output="version_file.py",
            output_strategies=strategy,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository = GitRepository(helper.path)
        environment = BuildEnvironment(project_root=helper.path)

        output, version, resolved_type, reference = resolve_version_output(
            settings=settings,
            repository=repository,
            environment=environment,
        )
        assert "version_string = " in output
        assert "0.1" in output

    @pytest.mark.regression
    @pytest.mark.parametrize(
        ("bad_strategies", "expected_err", "err_match"),
        [
            (123, ValueError, "Could not determine output strategy"),
            ({}, ValueError, "Could not determine output strategy"),
            (
                {
                    "release_only": TemplateStrStrategy(content="foo"),
                    "another_only": TemplateStrStrategy(content="bar"),
                },
                ValueError,
                "Could not determine output strategy",
            ),
        ],
    )
    def test_invalid_strategies(
        self,
        temp_git_repo: GitRepoHelper,
        bad_strategies: Any,
        expected_err: type[Exception],
        err_match: str,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        settings = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        object.__setattr__(settings, "output_strategies", bad_strategies)

        repository = GitRepository(helper.path)
        environment = BuildEnvironment(project_root=helper.path)

        with pytest.raises(expected_err, match=err_match):
            resolve_version_output(
                settings=settings,
                repository=repository,
                environment=environment,
            )

    @pytest.mark.regression
    def test_nonexistent_template_path(
        self,
        temp_git_repo: GitRepoHelper,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        strategy = TemplatePathStrategy(path=Path("nonexistent_template.txt"))
        settings = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            output_strategies=strategy,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository = GitRepository(helper.path)
        environment = BuildEnvironment(project_root=helper.path)

        with pytest.raises(FileNotFoundError, match="does not exist in project root"):
            resolve_version_output(
                settings=settings,
                repository=repository,
                environment=environment,
            )

    @pytest.mark.regression
    def test_regex_strategy_nonexistent_file(
        self,
        temp_git_repo: GitRepoHelper,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        strategy = RegexStrategy(pattern=r"__version__ = '(?P<version>.*?)'")
        settings = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            output="nonexistent_file.py",
            output_strategies=strategy,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository = GitRepository(helper.path)
        environment = BuildEnvironment(project_root=helper.path)

        with pytest.raises(FileNotFoundError, match="Could not resolve content from"):
            resolve_version_output(
                settings=settings,
                repository=repository,
                environment=environment,
            )

    @pytest.mark.regression
    def test_regex_strategy_pattern_not_found(
        self,
        temp_git_repo: GitRepoHelper,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        output_file = Path(helper.path) / "version_file.py"
        output_file.write_text("no_version_here = '1.0.0'", encoding="utf-8")

        strategy = RegexStrategy(pattern=r"__version__ = '(?P<version>.*?)'")
        settings = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            output="version_file.py",
            output_strategies=strategy,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository = GitRepository(helper.path)
        environment = BuildEnvironment(project_root=helper.path)

        with pytest.raises(
            ValueError, match="Regex pattern .* not found in output content"
        ):
            resolve_version_output(
                settings=settings,
                repository=repository,
                environment=environment,
            )


class TestResolveVersionOutputToStream:
    @pytest.mark.smoke
    def test_signature(self) -> None:
        sig = inspect.signature(resolve_version_output_to_stream)
        assert "settings" in sig.parameters
        assert "repository" in sig.parameters
        assert "environment" in sig.parameters

    @pytest.mark.sanity
    def test_invocation(
        self,
        temp_git_repo: GitRepoHelper,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        settings = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            output="file.txt",
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository = GitRepository(helper.path)
        environment = BuildEnvironment(project_root=helper.path)

        output_path, content, version, resolved_type, reference = (
            resolve_version_output_to_stream(
                settings=settings,
                repository=repository,
                environment=environment,
            )
        )

        assert content is not None
        assert version is not None
        assert output_path is not None
        assert output_path.exists()
        assert output_path.read_text(encoding="utf-8") == content
        assert resolved_type is not None
        assert reference is not None

    @pytest.mark.sanity
    @pytest.mark.parametrize("output_val", ["", None])
    def test_no_output_target(
        self,
        temp_git_repo: GitRepoHelper,
        output_val: str | None,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        settings = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            output="",
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        if output_val is None:
            object.__setattr__(settings, "output", None)
        else:
            settings.output = output_val

        repository = GitRepository(helper.path)
        environment = BuildEnvironment(project_root=helper.path)

        output_path, content, version, resolved_type, reference = (
            resolve_version_output_to_stream(
                settings=settings,
                repository=repository,
                environment=environment,
            )
        )
        assert output_path is None
        assert content is not None
        assert version is not None

    @pytest.mark.regression
    def test_path_resolution_failure(
        self,
        temp_git_repo: GitRepoHelper,
        mocker: pytest_mock.MockerFixture,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        settings = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            output="some_file.txt",
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        repository = GitRepository(helper.path)
        environment = BuildEnvironment(project_root=helper.path)

        original_resolve = Settings.resolve_path_from_root

        def side_effect(path: Any, enforce_existence: bool = True) -> Any:
            if path == "some_file.txt":
                return None
            return original_resolve(settings, path, enforce_existence)

        mocker.patch.object(Settings, "resolve_path_from_root", side_effect=side_effect)
        mocker.patch.object(Settings, "resolve_path_from_src", return_value=None)

        with pytest.raises(ValueError, match="Could not resolve output path"):
            resolve_version_output_to_stream(
                settings=settings,
                repository=repository,
                environment=environment,
            )

    @pytest.mark.regression
    @pytest.mark.parametrize(
        "bad_output",
        [
            "mocked_invalid_path",
        ],
    )
    def test_invalid(
        self,
        temp_git_repo: GitRepoHelper,
        mocker: pytest_mock.MockerFixture,
        bad_output: str,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        settings = Settings(
            package_name="test_pkg",
            project_root=helper.path,
            output=bad_output,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        mocker.patch.object(Path, "write_text", side_effect=OSError("Write failed"))
        repository = GitRepository(helper.path)
        environment = BuildEnvironment(project_root=helper.path)

        with pytest.raises(ValueError, match="Invalid output target"):
            resolve_version_output_to_stream(
                settings=settings,
                repository=repository,
                environment=environment,
            )
