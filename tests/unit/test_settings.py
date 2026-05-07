from __future__ import annotations

import configparser
import inspect
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from pydantic_settings import (
    BaseSettings,
    CliSettingsSource,
    PydanticBaseSettingsSource,
    PyprojectTomlConfigSettingsSource,
)

from gitversioned.settings import Settings, SetupCfgSettingsSource


class TestSetupCfgSettingsSource:
    """Test suite for SetupCfgSettingsSource."""

    @pytest.fixture(
        params=[
            ("test_package", {"version": "1.0.0"}),
            ("other_package", {}),
            ("missing_file", None),
        ],
        ids=["with_config", "empty_config", "no_file"],
    )
    def valid_instances(
        self, request: pytest.FixtureRequest, tmp_path: Path
    ) -> tuple[SetupCfgSettingsSource, dict[str, str] | None]:
        """Fixture providing test data for SetupCfgSettingsSource."""
        package_name, config_dict = request.param
        if config_dict is not None:
            config = configparser.ConfigParser()
            config["tool:gitversioned"] = config_dict
            with (tmp_path / "setup.cfg").open("w", encoding="utf-8") as file:
                config.write(file)
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
        valid_instances: tuple[SetupCfgSettingsSource, dict[str, str] | None],
        tmp_path: Path,
    ) -> None:
        """Test SetupCfgSettingsSource initialization."""
        instance, _ = valid_instances
        assert instance.settings_cls == Settings
        assert instance.project_root == tmp_path

    @pytest.mark.sanity
    def test_invalid_initialization_values(self) -> None:
        """Test SetupCfgSettingsSource with invalid initialization values."""
        with pytest.raises(TypeError):
            SetupCfgSettingsSource(Settings, Path(), invalid_arg=True)  # type: ignore[call-arg]

    @pytest.mark.sanity
    def test_invalid_initialization_missing(self) -> None:
        """Test SetupCfgSettingsSource with missing initialization arguments."""
        with pytest.raises(TypeError):
            SetupCfgSettingsSource()  # type: ignore[call-arg]

    @pytest.mark.smoke
    def test_get_field_value(
        self, valid_instances: tuple[SetupCfgSettingsSource, dict[str, str] | None]
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
        self, valid_instances: tuple[SetupCfgSettingsSource, dict[str, str] | None]
    ) -> None:
        """Test get_field_value handles invalid arguments properly."""
        instance, _ = valid_instances
        with pytest.raises(TypeError):
            instance.get_field_value()  # type: ignore[call-arg]

    @pytest.mark.smoke
    def test_call(
        self, valid_instances: tuple[SetupCfgSettingsSource, dict[str, str] | None]
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
        self, valid_instances: tuple[SetupCfgSettingsSource, dict[str, str] | None]
    ) -> None:
        """Test __call__ handles unexpected arguments properly."""
        instance, _ = valid_instances
        with pytest.raises(TypeError):
            instance(invalid_arg=True)  # type: ignore[call-arg]


class TestSettings:
    """Test suite for Settings."""

    @pytest.fixture(
        params=[
            {"package_name": "test"},
            {"package_name": "test", "version": "1.2.3"},
            {"package_name": "test", "output_file": "custom_version.py"},
            {"package_name": "test", "build_is_editable": True},
        ],
        ids=["minimal", "version", "output_file", "editable"],
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

    @pytest.mark.smoke
    def test_initialization(
        self, valid_instances: tuple[Settings, dict[str, Any]]
    ) -> None:
        """Test Settings initialization."""
        instance, kwargs = valid_instances
        for key, value in kwargs.items():
            assert getattr(instance, key) == value
        assert instance.package_name == "test"

    @pytest.mark.sanity
    def test_invalid_initialization_values(self) -> None:
        """Test Settings with invalid initialization values."""
        with pytest.raises(ValidationError):
            Settings(package_name=["not", "a", "string"])  # type: ignore[arg-type]

    @pytest.mark.sanity
    def test_invalid_initialization_missing(self) -> None:
        """Test Settings with missing initialization arguments."""
        with pytest.raises(ValidationError):
            Settings()  # type: ignore[call-arg]

    @pytest.mark.smoke
    def test_settings_customise_sources(self) -> None:
        """Test customization of settings sources."""

        class MockSource(PydanticBaseSettingsSource):
            """Mock settings source for testing."""

            def __call__(self) -> dict[str, Any]:
                return {"project_root": Path("/test/tmp")}

            def get_field_value(
                self, field: Any, field_name: str
            ) -> tuple[Any, str, bool]:
                return None, "", False

        init_source = MockSource(Settings)
        sources = Settings.settings_customise_sources(
            Settings, init_source, init_source, init_source, init_source
        )
        assert len(sources) == 6
        assert sources[0] is init_source
        assert isinstance(sources[1], SetupCfgSettingsSource)
        assert isinstance(sources[2], PyprojectTomlConfigSettingsSource)
        assert sources[3] is init_source
        assert sources[4] is init_source
        assert isinstance(sources[5], CliSettingsSource)

    @pytest.mark.sanity
    def test_settings_customise_sources_invalid(self) -> None:
        """Test settings_customise_sources handles unexpected arguments properly."""
        with pytest.raises(TypeError):
            Settings.settings_customise_sources()  # type: ignore[call-arg]

    @pytest.mark.smoke
    def test_marshalling(
        self, valid_instances: tuple[Settings, dict[str, Any]]
    ) -> None:
        """Test marshalling of Settings to and from dictionaries."""
        instance, kwargs = valid_instances
        dump = instance.model_dump()
        for key, value in kwargs.items():
            assert dump[key] == value

        new_instance = Settings.model_validate(dump)
        assert new_instance.package_name == instance.package_name
