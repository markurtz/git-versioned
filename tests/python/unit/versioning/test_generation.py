from __future__ import annotations

import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from packaging.version import Version

import gitversioned.versioning.generation as gen_mod
from gitversioned.settings import (
    OutputStrategy,
    RegexStrategy,
    Settings,
    TemplatePathStrategy,
    TemplateStrStrategy,
    VersionType,
)
from gitversioned.utils import BuildEnvironment, GitReference, GitRepository
from gitversioned.versioning.generation import (
    FormattedVersion,
    generate_from_template,
    generate_output_from_strategies,
)

if TYPE_CHECKING:
    from tests.conftest import GitRepoHelper


class TestFormattedVersion:
    @pytest.fixture(
        params=[
            (Version("1.2.3"), "release", "pep440"),
            (Version("1.2.3.dev4"), "dev", "pep440"),
            (Version("1.2.3.dev4"), "dev", "semver2"),
            (Version("1.2.3.post5"), "post", "semver2"),
            (Version("1.2.3a1"), "pre", "semver2"),
            (Version("1.2.3"), "post", "semver2"),
            (Version("1.2.3"), "dev", "semver2"),
            (Version("1.2.3.alpha2"), "pre", "semver2"),
            (Version("1.2.3+local"), "release", "semver2"),
        ]
    )
    def valid_instances(self, request: pytest.FixtureRequest) -> FormattedVersion:
        version_obj, version_type, version_standard = request.param
        return FormattedVersion(version_obj, version_type, version_standard)

    @pytest.mark.smoke
    def test_signature(self) -> None:
        assert issubclass(FormattedVersion, Version)

        signature = inspect.signature(FormattedVersion.__init__)
        assert "version" in signature.parameters
        assert "version_type" in signature.parameters
        assert "version_standard" in signature.parameters

        instance = FormattedVersion(Version("1.0.0"), "release")
        assert hasattr(instance, "release")
        assert hasattr(instance, "pre")
        assert hasattr(instance, "post")
        assert hasattr(instance, "dev")
        assert hasattr(instance, "local")

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: FormattedVersion) -> None:
        assert isinstance(valid_instances, FormattedVersion)
        assert valid_instances._version_type in (
            "release",
            "dev",
            "post",
            "pre",
            "alpha",
            "nightly",
        )
        assert valid_instances._version_standard in ("pep440", "semver2")

    @pytest.mark.sanity
    def test_invalid_initialization_values(self) -> None:
        version_obj = Version("1.2.3")
        invalid_instance = FormattedVersion(version_obj, "release", "invalid_standard")
        with pytest.raises(ValueError, match="Unsupported version standard"):
            str(invalid_instance)

    @pytest.mark.regression
    def test_invalid_initialization_missing(self) -> None:
        with pytest.raises(TypeError):
            FormattedVersion()  # type: ignore

        with pytest.raises(TypeError):
            FormattedVersion(Version("1.0.0"))  # type: ignore

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("version_str", "version_type", "version_standard", "expected_output"),
        [
            ("1.2.3", "release", "pep440", "1.2.3"),
            ("1.2.3.dev4", "dev", "pep440", "1.2.3.dev4"),
            ("1.2.3.dev4", "dev", "semver2", "1.2.3-dev4"),
            ("1.2.3.post5", "post", "semver2", "1.2.3-post5"),
            ("1.2.3a1", "pre", "semver2", "1.2.3a1"),
            ("1.2.3", "post", "semver2", "1.2.3-post0"),
            ("1.2.3", "dev", "semver2", "1.2.3-dev0"),
            ("1.2.3.alpha2", "pre", "semver2", "1.2.3a2"),
            ("1.2.3.alpha2", "alpha", "semver2", "1.2.3a2"),
            ("1.2.3.alpha2", "nightly", "semver2", "1.2.3a2"),
            ("1.2.3+local", "release", "semver2", "1.2.3+local"),
            ("1.2.3+local.dev4", "dev", "semver2", "1.2.3-dev0+local.dev4"),
        ],
    )
    def test_str_formatting(
        self,
        version_str: str,
        version_type: Any,
        version_standard: Any,
        expected_output: str,
    ) -> None:
        version_obj = Version(version_str)
        formatted_version = FormattedVersion(
            version_obj, version_type, version_standard
        )
        assert str(formatted_version) == expected_output

    @pytest.mark.sanity
    def test_repr_formatting(self) -> None:
        version_obj = Version("1.2.3")
        formatted_version = FormattedVersion(version_obj, "release", "pep440")
        assert repr(formatted_version) == repr("1.2.3")


class TestGenerateFromTemplate:
    @pytest.mark.smoke
    def test_signature(self) -> None:
        signature = inspect.signature(generate_from_template)
        assert "pattern" in signature.parameters
        assert "version" in signature.parameters
        assert "reference" in signature.parameters
        assert "settings" in signature.parameters
        assert "repository" in signature.parameters
        assert "environment" in signature.parameters

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("pattern", "expected_content"),
        [
            ("v{version}", "v1.2.3"),
            ("{ref.short_sha}", "abc1234"),
            ("{config.package_name}", "test_pkg"),
            ("{env.python_version}", "3.10"),
            ("", ""),
            (None, ""),
        ],
    )
    def test_invocation(
        self,
        pattern: str | None,
        expected_content: str,
    ) -> None:
        version_obj = Version("1.2.3")
        reference_obj = GitReference(short_sha="abc1234")
        settings_obj = Settings(package_name="test_pkg")
        repository_obj = GitRepository(settings_obj.project_root)
        environment_obj = BuildEnvironment(python_version="3.10")

        result = generate_from_template(
            pattern,
            version_obj,
            reference_obj,
            settings_obj,
            repository_obj,
            environment_obj,
        )
        assert result == expected_content

    @pytest.mark.regression
    @pytest.mark.parametrize(
        "invalid_pattern",
        [
            "{ref.nonexistent_field}",
            "{version.invalid_attr}",
            "{config.nonexistent}",
        ],
    )
    def test_invalid(self, invalid_pattern: str) -> None:
        version_obj = Version("1.2.3")
        reference_obj = GitReference(short_sha="abc1234")
        settings_obj = Settings(package_name="test_pkg")
        repository_obj = GitRepository(settings_obj.project_root)
        environment_obj = BuildEnvironment(python_version="3.10")

        with pytest.raises((AttributeError, NameError, Exception)):
            generate_from_template(
                invalid_pattern,
                version_obj,
                reference_obj,
                settings_obj,
                repository_obj,
                environment_obj,
            )


class TestGenerateOutputFromStrategies:
    @pytest.mark.smoke
    def test_signature(self) -> None:
        signature = inspect.signature(generate_output_from_strategies)
        assert "version" in signature.parameters
        assert "version_type" in signature.parameters
        assert "reference" in signature.parameters
        assert "settings" in signature.parameters
        assert "repository" in signature.parameters
        assert "environment" in signature.parameters

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        "strategy_type",
        [
            "template_str",
            "template_path",
            "regex",
            "regex_no_groups",
        ],
    )
    def test_invocation(
        self,
        temp_git_repo: GitRepoHelper,
        strategy_type: str,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        version_obj = Version("1.2.3")
        reference_obj = GitReference(short_sha="abc1234")
        repository_obj = GitRepository(helper.path)
        environment_obj = BuildEnvironment(project_root=helper.path)

        if strategy_type == "template_str":
            strategy = TemplateStrStrategy(content="__version__ = '{version}'")
            settings_obj = Settings(
                project_root=helper.path,
                output_strategies=strategy,
                dirty_ignore=["pyproject.toml", "target", "build", "dist"],
            )
            result = generate_output_from_strategies(
                version_obj,
                "release",
                reference_obj,
                settings_obj,
                repository_obj,
                environment_obj,
            )
            assert result == "__version__ = '1.2.3'"

        elif strategy_type == "template_path":
            temp_template = helper.path / "template.txt"
            temp_template.write_text("ver={version}", encoding="utf-8")
            strategy = TemplatePathStrategy(path=temp_template)
            settings_obj = Settings(
                project_root=helper.path,
                output_strategies=strategy,
                dirty_ignore=["pyproject.toml", "target", "build", "dist"],
            )
            result = generate_output_from_strategies(
                version_obj,
                "release",
                reference_obj,
                settings_obj,
                repository_obj,
                environment_obj,
            )
            assert result == "ver=1.2.3"

        elif strategy_type == "regex":
            output_file = helper.path / "version.py"
            output_file.write_text('__version__ = "0.0.0"', encoding="utf-8")
            strategy = RegexStrategy(pattern=r'__version__ = "(?P<version>.*?)"')
            settings_obj = Settings(
                project_root=helper.path,
                output="version.py",
                output_strategies=strategy,
                dirty_ignore=["pyproject.toml", "target", "build", "dist"],
            )
            result = generate_output_from_strategies(
                version_obj,
                "release",
                reference_obj,
                settings_obj,
                repository_obj,
                environment_obj,
            )
            assert result == '__version__ = "1.2.3"'

        elif strategy_type == "regex_no_groups":
            output_file = helper.path / "version.py"
            output_file.write_text("0.0.0", encoding="utf-8")
            strategy = RegexStrategy(pattern=r"\d+\.\d+\.\d+")
            settings_obj = Settings(
                project_root=helper.path,
                output="version.py",
                output_strategies=strategy,
                dirty_ignore=["pyproject.toml", "target", "build", "dist"],
            )
            result = generate_output_from_strategies(
                version_obj,
                "release",
                reference_obj,
                settings_obj,
                repository_obj,
                environment_obj,
            )
            assert result == "1.2.3"

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("version_type", "strategies_dict", "expected_result"),
        [
            (
                "dev",
                {"release": TemplateStrStrategy(content="single={version}")},
                "single=1.2.3",
            ),
            (
                "dev",
                {
                    "release": TemplateStrStrategy(content="rel={version}"),
                    "dev": TemplateStrStrategy(content="dev={version}"),
                },
                "dev=1.2.3",
            ),
            (
                "post",
                {
                    "release": TemplateStrStrategy(content="fallback={version}"),
                    "dev": TemplateStrStrategy(content="dev={version}"),
                },
                "fallback=1.2.3",
            ),
        ],
    )
    def test_dict_strategies(
        self,
        temp_git_repo: GitRepoHelper,
        version_type: VersionType,
        strategies_dict: dict[str, OutputStrategy],
        expected_result: str,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        version_obj = Version("1.2.3")
        reference_obj = GitReference()
        repository_obj = GitRepository(helper.path)
        environment_obj = BuildEnvironment(project_root=helper.path)

        settings_obj = Settings(
            project_root=helper.path,
            output_strategies=strategies_dict,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        result = generate_output_from_strategies(
            version_obj,
            version_type,
            reference_obj,
            settings_obj,
            repository_obj,
            environment_obj,
        )
        assert result == expected_result

    @pytest.mark.regression
    def test_invalid_strategy_type(self, temp_git_repo: GitRepoHelper) -> None:
        helper = temp_git_repo.setup_state("clean")
        version_obj = Version("1.2.3")
        reference_obj = GitReference()
        repository_obj = GitRepository(helper.path)
        environment_obj = BuildEnvironment(project_root=helper.path)

        settings_obj = Settings(
            project_root=helper.path,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        object.__setattr__(settings_obj, "output_strategies", "invalid_strategy")

        with pytest.raises(ValueError, match="Could not determine output strategy"):
            generate_output_from_strategies(
                version_obj,
                "release",
                reference_obj,
                settings_obj,
                repository_obj,
                environment_obj,
            )

    @pytest.mark.regression
    def test_invalid_dict_missing_release(self, temp_git_repo: GitRepoHelper) -> None:
        helper = temp_git_repo.setup_state("clean")
        version_obj = Version("1.2.3")
        reference_obj = GitReference()
        repository_obj = GitRepository(helper.path)
        environment_obj = BuildEnvironment(project_root=helper.path)

        settings_obj = Settings(
            project_root=helper.path,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        object.__setattr__(
            settings_obj,
            "output_strategies",
            {
                "alpha": TemplatePathStrategy(path=Path("alpha.py")),
                "beta": TemplatePathStrategy(path=Path("beta.py")),
            },
        )
        with pytest.raises(ValueError, match="Could not determine output strategy"):
            generate_output_from_strategies(
                version_obj,
                "dev",
                reference_obj,
                settings_obj,
                repository_obj,
                environment_obj,
            )

    @pytest.mark.regression
    def test_invalid_regex_missing_file(self, temp_git_repo: GitRepoHelper) -> None:
        helper = temp_git_repo.setup_state("clean")
        version_obj = Version("1.2.3")
        reference_obj = GitReference()
        repository_obj = GitRepository(helper.path)
        environment_obj = BuildEnvironment(project_root=helper.path)

        pattern_str = r'version = "(?P<version>.*?)"'
        settings_obj = Settings(
            project_root=helper.path,
            output="nonexistent_output.txt",
            output_strategies=RegexStrategy(pattern=pattern_str),
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        with pytest.raises(FileNotFoundError, match="Could not resolve content"):
            generate_output_from_strategies(
                version_obj,
                "release",
                reference_obj,
                settings_obj,
                repository_obj,
                environment_obj,
            )

    @pytest.mark.regression
    def test_invalid_regex_no_match(self, temp_git_repo: GitRepoHelper) -> None:
        helper = temp_git_repo.setup_state("clean")
        version_obj = Version("1.2.3")
        reference_obj = GitReference()
        repository_obj = GitRepository(helper.path)
        environment_obj = BuildEnvironment(project_root=helper.path)

        output_file = helper.path / "version.py"
        output_file.write_text("no version here", encoding="utf-8")
        pattern_str = r'version = "(?P<version>.*?)"'
        settings_obj = Settings(
            project_root=helper.path,
            output="version.py",
            output_strategies=RegexStrategy(pattern=pattern_str),
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        with pytest.raises(ValueError, match="Regex pattern .* not found"):
            generate_output_from_strategies(
                version_obj,
                "release",
                reference_obj,
                settings_obj,
                repository_obj,
                environment_obj,
            )

    @pytest.mark.regression
    def test_invalid_template_missing_file(self, temp_git_repo: GitRepoHelper) -> None:
        helper = temp_git_repo.setup_state("clean")
        version_obj = Version("1.2.3")
        reference_obj = GitReference()
        repository_obj = GitRepository(helper.path)
        environment_obj = BuildEnvironment(project_root=helper.path)

        strategy = TemplatePathStrategy(path=Path("nonexistent_template.txt"))
        settings_obj = Settings(
            project_root=helper.path,
            output_strategies=strategy,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        with pytest.raises(FileNotFoundError, match="Template path .* does not exist"):
            generate_output_from_strategies(
                version_obj,
                "release",
                reference_obj,
                settings_obj,
                repository_obj,
                environment_obj,
            )

    @pytest.mark.regression
    def test_invalid_strategy_obj(self, temp_git_repo: GitRepoHelper) -> None:
        helper = temp_git_repo.setup_state("clean")
        version_obj = Version("1.2.3")
        reference_obj = GitReference()
        repository_obj = GitRepository(helper.path)
        environment_obj = BuildEnvironment(project_root=helper.path)

        settings_obj = Settings(
            project_root=helper.path,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        object.__setattr__(settings_obj, "output_strategies", {"release": object()})
        with pytest.raises(ValueError, match="Unsupported strategy type"):
            generate_output_from_strategies(
                version_obj,
                "release",
                reference_obj,
                settings_obj,
                repository_obj,
                environment_obj,
            )

    @pytest.mark.regression
    def test_invalid_strategy_type_in_helpers(
        self,
        temp_git_repo: GitRepoHelper,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        version_obj = Version("1.2.3")
        reference_obj = GitReference()
        repository_obj = GitRepository(helper.path)
        environment_obj = BuildEnvironment(project_root=helper.path)

        settings_obj = Settings(
            project_root=helper.path,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        object.__setattr__(settings_obj, "output_strategies", "fake_strategy")
        original_isinstance = isinstance

        def mock_isinstance(obj: Any, class_or_tuple: Any) -> bool:
            if obj == "fake_strategy":
                return class_or_tuple in (
                    (
                        TemplatePathStrategy,
                        TemplateStrStrategy,
                        RegexStrategy,
                    ),
                    (TemplateStrStrategy, TemplatePathStrategy),
                )
            if isinstance(class_or_tuple, tuple):
                return any(original_isinstance(obj, item) for item in class_or_tuple)
            return original_isinstance(obj, class_or_tuple)

        with pytest.MonkeyPatch().context() as monkeypatch_context:
            monkeypatch_context.setattr(
                gen_mod, "isinstance", mock_isinstance, raising=False
            )
            with pytest.raises(ValueError, match="Invalid output strategy type"):
                generate_output_from_strategies(
                    version_obj,
                    "release",
                    reference_obj,
                    settings_obj,
                    repository_obj,
                    environment_obj,
                )

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("file_content", "pattern_str", "expected_output"),
        [
            (
                'version = "0.1.0"\nother_version = "0.2.0"',
                r'version = "(?P<version>.*?)"',
                'version = "1.2.3"\nother_version = "1.2.3"',
            ),
            (
                '__version__ = "0.0.0"',
                r'__version__ = "(?P<ref__short_sha>.*?)"',
                '__version__ = "abc1234"',
            ),
            (
                '__version__ = "0.0.0-dev"',
                r'__version__ = "(?P<version>.*?)-(?P<ref__short_sha>.*?)"',
                '__version__ = "1.2.3-abc1234"',
            ),
            (
                '__version__ = "0.0.0"',
                r'__version__ = "(?P<version>.*?)(?P<optional_group>optional)?"',
                '__version__ = "1.2.3"',
            ),
        ],
    )
    def test_regex_matching(
        self,
        temp_git_repo: GitRepoHelper,
        file_content: str,
        pattern_str: str,
        expected_output: str,
    ) -> None:
        helper = temp_git_repo.setup_state("clean")
        version_obj = Version("1.2.3")
        reference_obj = GitReference(short_sha="abc1234")
        repository_obj = GitRepository(helper.path)
        environment_obj = BuildEnvironment(project_root=helper.path)

        output_file = helper.path / "version.py"
        output_file.write_text(file_content, encoding="utf-8")

        strategy = RegexStrategy(pattern=pattern_str)
        settings_obj = Settings(
            project_root=helper.path,
            output="version.py",
            output_strategies=strategy,
            dirty_ignore=["pyproject.toml", "target", "build", "dist"],
        )
        result = generate_output_from_strategies(
            version_obj,
            "release",
            reference_obj,
            settings_obj,
            repository_obj,
            environment_obj,
        )
        assert result == expected_output
