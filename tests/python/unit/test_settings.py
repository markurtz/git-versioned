from __future__ import annotations

import configparser
import inspect
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError
from pydantic_settings import (
    BaseSettings,
    CliSettingsSource,
    PydanticBaseSettingsSource,
    PyprojectTomlConfigSettingsSource,
)

from gitversioned.settings import (
    IncrementLevel,
    JsonConfigSettingsSource,
    OutputStrategy,
    RegexStrategy,
    Settings,
    SetupCfgSettingsSource,
    TemplatePathStrategy,
    TemplateStrStrategy,
    TomlConfigSettingsSource,
    VersionStandard,
    VersionType,
)


class MockSettingsSource(PydanticBaseSettingsSource):
    """Mock settings source for testing customise_sources."""

    def __call__(self) -> dict[str, Any]:
        return {"project_root": Path("/test/tmp")}

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        return None, "", False


class TestTemplatePathStrategy:
    """Test suite for TemplatePathStrategy."""

    @pytest.fixture(
        params=[
            Path("templates/release.py.template"),
            Path("templates/dev.py.template"),
        ],
        ids=["release_template", "dev_template"],
    )
    def valid_instances(self, request: pytest.FixtureRequest) -> TemplatePathStrategy:
        """Fixture providing valid TemplatePathStrategy instances."""
        return TemplatePathStrategy(path=request.param)

    @pytest.mark.smoke
    def test_class_signatures(self) -> None:
        """Validate TemplatePathStrategy class signature."""
        assert issubclass(TemplatePathStrategy, BaseModel)
        assert "type" in TemplatePathStrategy.model_fields
        assert "path" in TemplatePathStrategy.model_fields
        methods = [
            name
            for name, val in TemplatePathStrategy.__dict__.items()
            if not name.startswith("_") and inspect.isfunction(val)
        ]
        assert not methods

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: TemplatePathStrategy) -> None:
        """Test TemplatePathStrategy initialization."""
        assert valid_instances.type == "template_path"
        assert isinstance(valid_instances.path, Path)

    @pytest.mark.parametrize(
        "invalid_path",
        [123, True, ["some", "path"]],
        ids=["int", "bool", "list"],
    )
    @pytest.mark.sanity
    def test_invalid_initialization_values(self, invalid_path: Any) -> None:
        """Test TemplatePathStrategy with invalid initialization values."""
        with pytest.raises(ValidationError):
            TemplatePathStrategy(path=invalid_path)

    @pytest.mark.sanity
    def test_invalid_initialization_missing(self) -> None:
        """Test TemplatePathStrategy with missing initialization arguments."""
        with pytest.raises(ValidationError):
            cast("Any", TemplatePathStrategy)()

    @pytest.mark.smoke
    def test_marshalling(self, valid_instances: TemplatePathStrategy) -> None:
        """Test marshalling of TemplatePathStrategy."""
        dumped = valid_instances.model_dump()
        assert dumped["type"] == "template_path"
        assert isinstance(dumped["path"], Path)
        validated = TemplatePathStrategy.model_validate(dumped)
        assert validated.type == valid_instances.type
        assert validated.path == valid_instances.path


class TestTemplateStrStrategy:
    """Test suite for TemplateStrStrategy."""

    @pytest.fixture(
        params=[
            "__version__ = '{version}'",
            "version = '{version}'",
        ],
        ids=["version_template", "simple_template"],
    )
    def valid_instances(self, request: pytest.FixtureRequest) -> TemplateStrStrategy:
        """Fixture providing valid TemplateStrStrategy instances."""
        return TemplateStrStrategy(content=request.param)

    @pytest.mark.smoke
    def test_class_signatures(self) -> None:
        """Validate TemplateStrStrategy class signature."""
        assert issubclass(TemplateStrStrategy, BaseModel)
        assert "type" in TemplateStrStrategy.model_fields
        assert "content" in TemplateStrStrategy.model_fields
        methods = [
            name
            for name, val in TemplateStrStrategy.__dict__.items()
            if not name.startswith("_") and inspect.isfunction(val)
        ]
        assert not methods

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: TemplateStrStrategy) -> None:
        """Test TemplateStrStrategy initialization."""
        assert valid_instances.type == "template_str"
        assert isinstance(valid_instances.content, str)

    @pytest.mark.parametrize(
        "invalid_content",
        [123, True, ["some", "content"]],
        ids=["int", "bool", "list"],
    )
    @pytest.mark.sanity
    def test_invalid_initialization_values(self, invalid_content: Any) -> None:
        """Test TemplateStrStrategy with invalid initialization values."""
        with pytest.raises(ValidationError):
            TemplateStrStrategy(content=invalid_content)

    @pytest.mark.sanity
    def test_invalid_initialization_missing(self) -> None:
        """Test TemplateStrStrategy with missing initialization arguments."""
        with pytest.raises(ValidationError):
            cast("Any", TemplateStrStrategy)()

    @pytest.mark.smoke
    def test_marshalling(self, valid_instances: TemplateStrStrategy) -> None:
        """Test marshalling of TemplateStrStrategy."""
        dumped = valid_instances.model_dump()
        assert dumped["type"] == "template_str"
        assert isinstance(dumped["content"], str)
        validated = TemplateStrStrategy.model_validate(dumped)
        assert validated.type == valid_instances.type
        assert validated.content == valid_instances.content


class TestRegexStrategy:
    """Test suite for RegexStrategy."""

    @pytest.fixture(
        params=[
            r'version = "(?P<version>.*?)"',
            r'__version__ = "(?P<version>[^"]+)"',
        ],
        ids=["pattern_version", "pattern_underscore"],
    )
    def valid_instances(self, request: pytest.FixtureRequest) -> RegexStrategy:
        """Fixture providing valid RegexStrategy instances."""
        return RegexStrategy(pattern=request.param)

    @pytest.mark.smoke
    def test_class_signatures(self) -> None:
        """Validate RegexStrategy class signature."""
        assert issubclass(RegexStrategy, BaseModel)
        assert "type" in RegexStrategy.model_fields
        assert "pattern" in RegexStrategy.model_fields
        methods = [
            name
            for name, val in RegexStrategy.__dict__.items()
            if not name.startswith("_") and inspect.isfunction(val)
        ]
        assert not methods

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: RegexStrategy) -> None:
        """Test RegexStrategy initialization."""
        assert valid_instances.type == "regex"
        assert isinstance(valid_instances.pattern, str)

    @pytest.mark.parametrize(
        "invalid_pattern",
        [123, True, ["some", "pattern"]],
        ids=["int", "bool", "list"],
    )
    @pytest.mark.sanity
    def test_invalid_initialization_values(self, invalid_pattern: Any) -> None:
        """Test RegexStrategy with invalid initialization values."""
        with pytest.raises(ValidationError):
            RegexStrategy(pattern=invalid_pattern)

    @pytest.mark.sanity
    def test_invalid_initialization_missing(self) -> None:
        """Test RegexStrategy with missing initialization arguments."""
        with pytest.raises(ValidationError):
            cast("Any", RegexStrategy)()

    @pytest.mark.smoke
    def test_marshalling(self, valid_instances: RegexStrategy) -> None:
        """Test marshalling of RegexStrategy."""
        dumped = valid_instances.model_dump()
        assert dumped["type"] == "regex"
        assert isinstance(dumped["pattern"], str)
        validated = RegexStrategy.model_validate(dumped)
        assert validated.type == valid_instances.type
        assert validated.pattern == valid_instances.pattern


class TestSetupCfgSettingsSource:
    """Test suite for SetupCfgSettingsSource."""

    @pytest.fixture(
        params=[
            ("test_package", {"version": "1.0.0"}, None),
            ("other_package", {}, None),
            ("missing_file", None, None),
            (
                "nested_package",
                {"version": "1.0.0"},
                {"auto_increment": {"dev": "minor"}},
            ),
        ],
        ids=["with_config", "empty_config", "no_file", "nested_config"],
    )
    def valid_instances(
        self, request: pytest.FixtureRequest, tmp_path: Path
    ) -> tuple[SetupCfgSettingsSource, dict[str, Any] | None]:
        """Fixture providing test data for SetupCfgSettingsSource."""
        package_name, original_config_dict, nested_config = request.param
        config_dict = (
            dict(original_config_dict) if original_config_dict is not None else None
        )

        if config_dict is not None:
            config = configparser.ConfigParser()
            config["tool:gitversioned"] = config_dict
            if nested_config:
                for key, val in nested_config.items():
                    config[f"tool:gitversioned:{key}"] = val
            with (tmp_path / "setup.cfg").open("w", encoding="utf-8") as target_file:
                config.write(target_file)

            if nested_config:
                config_dict.update(nested_config)

        return SetupCfgSettingsSource(Settings, tmp_path), config_dict

    @pytest.mark.smoke
    def test_class_signatures(self) -> None:
        """Test SetupCfgSettingsSource signatures and class hierarchy."""
        assert issubclass(SetupCfgSettingsSource, PydanticBaseSettingsSource)
        assert hasattr(SetupCfgSettingsSource, "get_field_value")
        assert callable(SetupCfgSettingsSource)
        signature = inspect.signature(SetupCfgSettingsSource.__init__)
        assert "settings_cls" in signature.parameters
        assert "project_root" in signature.parameters

    @pytest.mark.smoke
    def test_initialization(
        self,
        valid_instances: tuple[SetupCfgSettingsSource, dict[str, Any] | None],
        tmp_path: Path,
    ) -> None:
        """Test SetupCfgSettingsSource initialization."""
        instance, ignored_config = valid_instances
        assert instance.settings_cls == Settings
        assert instance.project_root == tmp_path

    @pytest.mark.sanity
    def test_invalid_initialization_values(self) -> None:
        """Test SetupCfgSettingsSource with invalid initialization values."""
        source_cls: Any = SetupCfgSettingsSource
        with pytest.raises(TypeError):
            source_cls(Settings, Path(), invalid_arg=True)

    @pytest.mark.sanity
    def test_invalid_initialization_missing(self) -> None:
        """Test SetupCfgSettingsSource with missing initialization arguments."""
        with pytest.raises(TypeError):
            cast("Any", SetupCfgSettingsSource)(*())

    @pytest.mark.smoke
    def test_get_field_value(
        self, valid_instances: tuple[SetupCfgSettingsSource, dict[str, Any] | None]
    ) -> None:
        """Test get_field_value retrieves correct configurations."""
        instance, config = valid_instances
        if config and "version" in config:
            field_value, field_key, flag = instance.get_field_value(None, "version")
            assert field_value == config["version"]
            assert field_key == "version"
            assert flag is False
        else:
            with pytest.raises(KeyError):
                instance.get_field_value(None, "version")

    @pytest.mark.sanity
    def test_get_field_value_invalid(
        self, valid_instances: tuple[SetupCfgSettingsSource, dict[str, Any] | None]
    ) -> None:
        """Test get_field_value handles invalid arguments properly."""
        instance, ignored_config = valid_instances
        with pytest.raises(TypeError):
            cast("Any", instance.get_field_value)(*())

    @pytest.mark.smoke
    def test_call(
        self, valid_instances: tuple[SetupCfgSettingsSource, dict[str, Any] | None]
    ) -> None:
        """Test __call__ reads the configuration correctly."""
        instance, config = valid_instances
        result = instance()
        if config:
            assert result == config
        else:
            assert result == {}

    @pytest.mark.sanity
    def test_call_invalid(
        self, valid_instances: tuple[SetupCfgSettingsSource, dict[str, Any] | None]
    ) -> None:
        """Test __call__ handles unexpected arguments properly."""
        instance, ignored_config = valid_instances
        callable_instance: Any = instance
        with pytest.raises(TypeError):
            callable_instance(invalid_arg=True)

    @pytest.mark.sanity
    def test_caching(self, tmp_path: Path) -> None:
        """Test that SetupCfgSettingsSource caches the configuration.

        This avoids redundant I/O on successive calls.
        """
        config = configparser.ConfigParser()
        config["tool:gitversioned"] = {"version": "2.0.0"}
        with (tmp_path / "setup.cfg").open("w", encoding="utf-8") as target_file:
            config.write(target_file)

        source = SetupCfgSettingsSource(Settings, tmp_path)
        first_call = source()
        assert first_call["version"] == "2.0.0"

        config["tool:gitversioned"]["version"] = "3.0.0"
        with (tmp_path / "setup.cfg").open("w", encoding="utf-8") as target_file:
            config.write(target_file)

        second_call = source()
        assert second_call["version"] == "2.0.0"

    @pytest.mark.regression
    def test_setup_cfg_nested_non_dict(self, tmp_path: Path) -> None:
        """Test parsing setup.cfg with a nested section.

        This handles the case when the parent key is a non-dict.
        """
        config = configparser.ConfigParser()
        config["tool:gitversioned"] = {"version": "1.0.0"}
        config["tool:gitversioned:version"] = {"nested_key": "nested_value"}
        with (tmp_path / "setup.cfg").open("w", encoding="utf-8") as target_file:
            config.write(target_file)

        source = SetupCfgSettingsSource(Settings, tmp_path)
        result = source()
        assert result["version"] == {"_": "1.0.0", "nested_key": "nested_value"}


class TestSettings:
    """Test suite for Settings."""

    @pytest.fixture(
        params=[
            {"package_name": "test"},
            {"package_name": "test", "version": "1.2.3"},
            {"package_name": "test", "output": "custom_version.py"},
            {"package_name": "test", "build_is_editable": True},
        ],
        ids=["minimal", "version", "output", "editable"],
    )
    def valid_instances(
        self, request: pytest.FixtureRequest
    ) -> tuple[Settings, dict[str, Any]]:
        """Fixture providing test data for Settings."""
        kwargs = request.param
        return Settings(**kwargs), kwargs

    @pytest.mark.smoke
    def test_class_signatures(self) -> None:
        """Test Settings signatures and class variables."""
        assert issubclass(Settings, BaseSettings)
        assert hasattr(Settings, "settings_customise_sources")
        signature = inspect.signature(Settings.settings_customise_sources)
        assert "init_settings" in signature.parameters

        for method_name in [
            "resolve_path_from_root",
            "resolve_path_from_project",
            "resolve_path_from_src",
        ]:
            assert hasattr(Settings, method_name)
            method_sig = inspect.signature(getattr(Settings, method_name))
            assert "path" in method_sig.parameters

    @pytest.mark.smoke
    def test_initialization(
        self, valid_instances: tuple[Settings, dict[str, Any]]
    ) -> None:
        """Test Settings initialization."""
        settings_instance, kwargs = valid_instances
        for key, val in kwargs.items():
            assert getattr(settings_instance, key) == val
        assert settings_instance.package_name == "test"

    @pytest.mark.sanity
    def test_invalid_initialization_values(self) -> None:
        """Test Settings with invalid initialization values."""
        invalid_data = {"package_name": ["not", "a", "string"]}
        with pytest.raises(ValidationError):
            Settings(**cast("Any", invalid_data))

    @pytest.mark.sanity
    def test_invalid_initialization_missing(self) -> None:
        """Test Settings with missing/default initialization values."""
        settings_instance = Settings()
        assert settings_instance.package_name in ("gitversioned", "git_versioned")

    @pytest.mark.regression
    def test_settings_customise_sources(self) -> None:
        """Test customization of settings sources."""
        init_source = MockSettingsSource(Settings)
        sources = Settings.settings_customise_sources(
            Settings, init_source, init_source, init_source, init_source
        )
        assert len(sources) == 10
        assert sources[0] is init_source
        assert isinstance(sources[1], SetupCfgSettingsSource)
        assert isinstance(sources[2], PyprojectTomlConfigSettingsSource)

        assert isinstance(sources[3], TomlConfigSettingsSource)
        assert isinstance(sources[4], TomlConfigSettingsSource)
        assert isinstance(sources[5], JsonConfigSettingsSource)
        assert isinstance(sources[6], JsonConfigSettingsSource)
        assert sources[7] is init_source
        assert sources[8] is init_source
        assert isinstance(sources[9], CliSettingsSource)

    @pytest.mark.sanity
    def test_settings_customise_sources_invalid(self) -> None:
        """Test settings_customise_sources handles unexpected arguments properly."""
        customise_sources: Any = Settings.settings_customise_sources
        with pytest.raises(TypeError):
            customise_sources(*())

    @pytest.mark.smoke
    def test_marshalling(
        self, valid_instances: tuple[Settings, dict[str, Any]]
    ) -> None:
        """Test marshalling of Settings to and from dictionaries."""
        settings_instance, kwargs = valid_instances
        dump = settings_instance.model_dump()
        for key, val in kwargs.items():
            if key == "output_strategies":
                continue
            assert dump[key] == val

        new_instance = Settings.model_validate(dump)
        assert new_instance.package_name == settings_instance.package_name

    @pytest.mark.smoke
    def test_str_and_repr(self) -> None:
        """Test __str__ and __repr__ return strings containing appropriate fields."""
        settings_instance = Settings(package_name="test")
        str_val = str(settings_instance)
        repr_val = repr(settings_instance)

        expected_str_fields = [
            "package_name",
            "version",
            "version_type",
            "project_root",
            "src_root",
            "source_type",
            "auto_increment",
            "output",
            "dirty_ignore",
        ]

        expected_repr_fields = [
            "package_name",
            "project_root",
            "src_root",
            "build_is_editable",
            "version",
            "source_type",
            "version_source_file",
            "version_source_archive",
            "version_source_function",
            "regex_version",
            "regex_tag",
            "regex_branch",
            "regex_commit",
            "regex_file",
            "regex_archive",
            "version_type",
            "version_standard",
            "auto_increment",
            "format_main",
            "format_dev",
            "format_pre",
            "format_post",
            "dirty_ignore",
            "output",
            "output_strategies",
        ]

        for field in expected_repr_fields:
            if field in expected_str_fields:
                assert f"{field}=" in str_val, f"__str__ missing field: {field}"
            else:
                assert f"{field}=" not in str_val, (
                    f"__str__ should not contain field: {field}"
                )
            assert f"{field}=" in repr_val, f"__repr__ missing field: {field}"

    @pytest.mark.smoke
    def test_output_strategies_default(self, tmp_path: Path) -> None:
        """Test that default output strategies are initialized correctly."""
        settings_instance = Settings(package_name="test", project_root=tmp_path)
        assert isinstance(settings_instance.output_strategies, dict)
        assert "release" in settings_instance.output_strategies
        assert "dev" in settings_instance.output_strategies
        release_strategy = settings_instance.output_strategies["release"]
        assert isinstance(release_strategy, TemplatePathStrategy)
        assert str(release_strategy.path).endswith("release.py.template")

        dev_strategy = settings_instance.output_strategies["dev"]
        assert isinstance(dev_strategy, TemplatePathStrategy)
        assert str(dev_strategy.path).endswith("dev.py.template")

    @pytest.mark.smoke
    def test_output_strategies_single(self) -> None:
        """Test configuring a single output strategy."""
        settings_instance = Settings(
            package_name="test",
            output_strategies=RegexStrategy(type="regex", pattern="my-pattern"),
        )
        assert isinstance(settings_instance.output_strategies, RegexStrategy)
        assert settings_instance.output_strategies.type == "regex"
        assert settings_instance.output_strategies.pattern == "my-pattern"

    @pytest.mark.smoke
    def test_resolve_path_from_project(self, tmp_path: Path) -> None:
        """Test resolve_path_from_project with various valid inputs."""
        settings_instance = Settings(package_name="test", project_root=tmp_path)

        assert settings_instance.resolve_path_from_project(None) is None

        existing_absolute = tmp_path / "absolute_file.txt"
        existing_absolute.touch()
        assert (
            settings_instance.resolve_path_from_project(existing_absolute)
            == existing_absolute
        )

        missing_absolute = tmp_path / "missing.txt"
        assert settings_instance.resolve_path_from_project(missing_absolute) is None

        relative_path = "relative_file.txt"
        existing_relative = tmp_path / relative_path
        existing_relative.touch()
        assert (
            settings_instance.resolve_path_from_project(relative_path)
            == existing_relative
        )

        assert (
            settings_instance.resolve_path_from_project("missing_relative.txt") is None
        )

    @pytest.mark.parametrize(
        "invalid_path",
        [123, True, ["some", "path"]],
        ids=["int", "bool", "list"],
    )
    @pytest.mark.sanity
    def test_resolve_path_from_project_invalid(
        self, tmp_path: Path, invalid_path: Any
    ) -> None:
        """Test resolve_path_from_project with invalid argument types."""
        settings_instance = Settings(package_name="test", project_root=tmp_path)
        with pytest.raises((AttributeError, TypeError)):
            settings_instance.resolve_path_from_project(invalid_path)

    @pytest.mark.smoke
    def test_resolve_path_from_src(self, tmp_path: Path) -> None:
        """Test resolve_path_from_src with various valid inputs."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        settings_instance = Settings(
            package_name="test", project_root=tmp_path, src_root=src_dir
        )

        assert settings_instance.resolve_path_from_src(None) is None

        existing_absolute = src_dir / "absolute_file.txt"
        existing_absolute.touch()
        assert (
            settings_instance.resolve_path_from_src(existing_absolute)
            == existing_absolute
        )

        missing_absolute = src_dir / "missing.txt"
        assert settings_instance.resolve_path_from_src(missing_absolute) is None

        relative_path = "relative_file.txt"
        existing_relative = src_dir / relative_path
        existing_relative.touch()
        assert (
            settings_instance.resolve_path_from_src(relative_path) == existing_relative
        )

        assert settings_instance.resolve_path_from_src("missing_relative.txt") is None

    @pytest.mark.parametrize(
        "invalid_path",
        [123, True, ["some", "path"]],
        ids=["int", "bool", "list"],
    )
    @pytest.mark.sanity
    def test_resolve_path_from_src_invalid(
        self, tmp_path: Path, invalid_path: Any
    ) -> None:
        """Test resolve_path_from_src with invalid argument types."""
        settings_instance = Settings(package_name="test", project_root=tmp_path)
        with pytest.raises((AttributeError, TypeError)):
            settings_instance.resolve_path_from_src(invalid_path)

    @pytest.mark.smoke
    def test_resolve_path_from_root(self, tmp_path: Path) -> None:
        """Test resolve_path_from_root resolves from project root first.

        If not found in project root, checks src root.
        """
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        settings_instance = Settings(
            package_name="test", project_root=tmp_path, src_root=src_dir
        )

        assert settings_instance.resolve_path_from_root(None) is None

        project_file = tmp_path / "file.txt"
        project_file.touch()
        assert settings_instance.resolve_path_from_root("file.txt") == project_file

        src_file = src_dir / "another_file.txt"
        src_file.touch()
        assert settings_instance.resolve_path_from_root("another_file.txt") == src_file

        assert settings_instance.resolve_path_from_root("missing.txt") is None
        assert (
            settings_instance.resolve_path_from_root(
                "missing.txt", enforce_existence=False
            )
            == src_dir / "missing.txt"
        )
        settings_same_root = Settings(
            package_name="test", project_root=tmp_path, src_root=tmp_path
        )
        assert (
            settings_same_root.resolve_path_from_root(
                "missing.txt", enforce_existence=False
            )
            == tmp_path / "missing.txt"
        )
        # Test enforce_existence=False when the file actually exists
        assert (
            settings_instance.resolve_path_from_root(
                "file.txt", enforce_existence=False
            )
            == project_file
        )

    @pytest.mark.parametrize(
        "invalid_path",
        [123, True, ["some", "path"]],
        ids=["int", "bool", "list"],
    )
    @pytest.mark.sanity
    def test_resolve_path_from_root_invalid(
        self, tmp_path: Path, invalid_path: Any
    ) -> None:
        """Test resolve_path_from_root with invalid argument types."""
        settings_instance = Settings(package_name="test", project_root=tmp_path)
        with pytest.raises((AttributeError, TypeError)):
            settings_instance.resolve_path_from_root(invalid_path)

    @pytest.mark.sanity
    def test_auto_detection(self, tmp_path: Path) -> None:
        """Test automatic detection of package name and source root."""
        setup_cfg = tmp_path / "setup.cfg"
        with setup_cfg.open("w", encoding="utf-8") as target_file:
            target_file.write("[metadata]\nname = cfg_package_name\n")

        settings_instance = Settings(
            project_root=tmp_path, src_root=tmp_path, package_name="auto"
        )
        assert settings_instance.package_name == "cfg_package_name"
        assert settings_instance.src_root == tmp_path

        src_pkg_dir = tmp_path / "src" / "cfg_package_name"
        src_pkg_dir.mkdir(parents=True)
        settings_instance = Settings(
            project_root=tmp_path, src_root=tmp_path, package_name="auto"
        )
        assert settings_instance.src_root == src_pkg_dir

        pyproject = tmp_path / "pyproject.toml"
        with pyproject.open("w", encoding="utf-8") as target_file:
            target_file.write('[project]\nname = "toml-package-name"\n')

        settings_instance = Settings(
            project_root=tmp_path, src_root=tmp_path, package_name="auto"
        )
        assert settings_instance.package_name == "toml_package_name"

    @pytest.mark.regression
    def test_auto_detection_no_files(self, tmp_path: Path) -> None:
        """Test package name and src_root detection when no config files exist.

        This forces fallback to project folder name and fallback in resolving src_root.
        """
        package_folder_name = tmp_path.name.replace("-", "_")
        pkg_dir = tmp_path / package_folder_name
        pkg_dir.mkdir()

        settings_instance = Settings(
            project_root=tmp_path, src_root=tmp_path, package_name="auto"
        )
        assert settings_instance.package_name == package_folder_name
        assert settings_instance.src_root == pkg_dir

    @pytest.mark.regression
    def test_auto_detection_invalid_toml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test package name detection when pyproject.toml is invalid.

        It should fallback and match the name via regex.
        """
        pyproject = tmp_path / "pyproject.toml"
        with pyproject.open("w", encoding="utf-8") as target_file:
            target_file.write(
                'name = "regex-detected-name"\ninvalid = [unclosed bracket\n'
            )

        monkeypatch.setattr(
            PyprojectTomlConfigSettingsSource,
            "_read_file",
            lambda *args, **kwargs: {},
        )

        settings_instance = Settings(
            project_root=tmp_path, src_root=tmp_path, package_name="auto"
        )
        assert settings_instance.package_name == "regex_detected_name"


@pytest.mark.smoke
def test_version_type() -> None:
    """Validate VersionType type and its allowed values."""
    adapter = TypeAdapter(VersionType)
    for valid_value in ["auto", "release", "dev", "pre", "alpha", "nightly", "post"]:
        assert adapter.validate_python(valid_value) == valid_value
    with pytest.raises(ValidationError):
        adapter.validate_python("invalid_type")


@pytest.mark.smoke
def test_version_standard() -> None:
    """Validate VersionStandard type and its allowed values."""
    adapter = TypeAdapter(VersionStandard)
    for valid_value in ["pep440", "semver2"]:
        assert adapter.validate_python(valid_value) == valid_value
    with pytest.raises(ValidationError):
        adapter.validate_python("invalid_standard")


@pytest.mark.smoke
def test_increment_level() -> None:
    """Validate IncrementLevel type and its allowed values."""
    adapter = TypeAdapter(IncrementLevel)
    for valid_value in ["major", "minor", "micro", "patch", "bug"]:
        assert adapter.validate_python(valid_value) == valid_value
    with pytest.raises(ValidationError):
        adapter.validate_python("invalid_level")


@pytest.mark.smoke
def test_output_strategy() -> None:
    """Validate OutputStrategy union type behavior."""
    adapter = TypeAdapter(OutputStrategy)

    path_strategy = adapter.validate_python(
        {"type": "template_path", "path": "templates/release.py.template"}
    )
    assert isinstance(path_strategy, TemplatePathStrategy)

    str_strategy = adapter.validate_python(
        {"type": "template_str", "content": "__version__ = '{version}'"}
    )
    assert isinstance(str_strategy, TemplateStrStrategy)

    regex_strategy = adapter.validate_python({"type": "regex", "pattern": ".*"})
    assert isinstance(regex_strategy, RegexStrategy)

    with pytest.raises(ValidationError):
        adapter.validate_python({"type": "invalid_type"})


class TestOverriddenSettings:
    """Test suite for overridden settings and overrides."""

    @pytest.mark.smoke
    def test_overrides_default(self) -> None:
        """Verify that overrides defaults to an empty dictionary."""
        settings = Settings(package_name="test")
        assert settings.overrides == {}

    @pytest.mark.smoke
    def test_get_overridden_settings_overrides(self) -> None:
        """Verify that get_overridden_settings correctly overrides root settings."""
        settings = Settings(
            package_name="test",
            version_type="dev",
            overrides={
                "cargo": {
                    "output": "Cargo.toml",
                    "version_type": "release",
                }
            },
        )
        assert settings.overrides["cargo"]["output"] == "Cargo.toml"
        assert settings.overrides["cargo"]["version_type"] == "release"

        override_settings = settings.get_overridden_settings("cargo")
        assert override_settings.package_name == "test"  # Inherited
        assert override_settings.output == "Cargo.toml"  # Overridden
        assert override_settings.version_type == "release"  # Overridden
        assert override_settings.overrides == {}  # Popped to prevent recursion

    @pytest.mark.sanity
    def test_get_overridden_settings_missing_raises_valueerror(self) -> None:
        """Verify get_overridden_settings raises ValueError for missing override."""
        settings = Settings(package_name="test")
        with pytest.raises(ValueError, match="not found in configuration"):
            settings.get_overridden_settings("missing")

    @pytest.mark.smoke
    def test_setup_cfg_overrides_parsing(self, tmp_path: Path) -> None:
        """Verify setup.cfg override sections are parsed into overrides."""
        config = configparser.ConfigParser()
        config["tool:gitversioned"] = {"package_name": "test"}
        config["tool:gitversioned:overrides:cargo"] = {
            "output": "Cargo.toml",
            "version_type": "release",
        }
        with (tmp_path / "setup.cfg").open("w", encoding="utf-8") as target_file:
            config.write(target_file)

        source = SetupCfgSettingsSource(Settings, tmp_path)
        result = source()
        assert "overrides" in result
        assert "cargo" in result["overrides"]
        assert result["overrides"]["cargo"]["output"] == "Cargo.toml"

        settings = Settings(project_root=tmp_path)
        assert "cargo" in settings.overrides
        assert settings.overrides["cargo"]["output"] == "Cargo.toml"
        assert settings.overrides["cargo"]["version_type"] == "release"

    @pytest.mark.smoke
    def test_pyproject_toml_overrides_parsing(self, tmp_path: Path) -> None:
        """Verify pyproject.toml nested overrides are parsed into overrides."""
        pyproject = tmp_path / "pyproject.toml"
        with pyproject.open("w", encoding="utf-8") as target_file:
            target_file.write(
                "[tool.gitversioned]\n"
                'package_name = "test"\n\n'
                "[tool.gitversioned.overrides.cargo]\n"
                'output = "Cargo.toml"\n'
                'version_type = "release"\n'
            )

        settings = Settings(project_root=tmp_path)
        assert "cargo" in settings.overrides
        assert settings.overrides["cargo"]["output"] == "Cargo.toml"
        assert settings.overrides["cargo"]["version_type"] == "release"
