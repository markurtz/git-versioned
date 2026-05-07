from __future__ import annotations

import os
import typing
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import BaseModel, ValidationError

from gitversioned.utils.environment import (
    BuildEnvironment,
    get_ci_info,
    get_ram_gb,
    get_user,
)


class TestGetUser:
    """Test suite for the get_user function."""

    @pytest.mark.smoke
    def test_function_signatures(self) -> None:
        """Test get_user signature."""
        assert callable(get_user)

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("env_vars", "getlogin_side_effect", "getlogin_return", "expected_user"),
        [
            ({}, None, "login_user", "login_user"),
            ({"USER": "env_user", "USERNAME": ""}, OSError, None, "env_user"),
            ({"USER": "", "USERNAME": "env_username"}, OSError, None, "env_username"),
            ({}, OSError, None, "unknown"),
        ],
        ids=["getlogin", "env_user", "env_username", "unknown"],
    )
    def test_invocation(
        self,
        env_vars: dict[str, str],
        getlogin_side_effect: type[Exception] | None,
        getlogin_return: str | None,
        expected_user: str,
    ) -> None:
        """Test get_user invocation across different scenarios."""
        with patch("gitversioned.utils.environment.os.getlogin") as mock_getlogin:
            if getlogin_side_effect:
                mock_getlogin.side_effect = getlogin_side_effect
            else:
                mock_getlogin.return_value = getlogin_return

            with patch.dict(os.environ, env_vars, clear=True):
                assert get_user() == expected_user


class TestGetCiInfo:
    """Test suite for the get_ci_info function."""

    @pytest.mark.smoke
    def test_function_signatures(self) -> None:
        """Test get_ci_info signature."""
        assert callable(get_ci_info)

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("env_vars", "expected_is_ci", "expected_provider"),
        [
            ({"GITHUB_ACTIONS": "true"}, True, "GitHub Actions"),
            ({"GITLAB_CI": "true"}, True, "GitLab CI"),
            ({"CIRCLECI": "true"}, True, "CircleCI"),
            ({"TRAVIS": "true"}, True, "Travis CI"),
            ({"JENKINS_URL": "http://jenkins"}, True, "Jenkins"),
            ({"BITBUCKET_COMMIT": "abc1234"}, True, "Bitbucket Pipelines"),
            ({"CI": "true"}, True, "Unknown CI"),
            ({"CI": "1"}, True, "Unknown CI"),
            ({"CI": "True"}, True, "Unknown CI"),
            ({}, False, None),
        ],
    )
    def test_invocation(
        self,
        env_vars: dict[str, str],
        expected_is_ci: bool,
        expected_provider: str | None,
    ) -> None:
        """Test get_ci_info invocation across different CI environments."""
        with patch.dict(os.environ, env_vars, clear=True):
            is_ci, provider = get_ci_info()
            assert is_ci == expected_is_ci
            assert provider == expected_provider


class TestGetRamGb:
    """Test suite for the get_ram_gb function."""

    @pytest.mark.smoke
    def test_function_signatures(self) -> None:
        """Test get_ram_gb signature."""
        assert callable(get_ram_gb)

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("has_psutil", "ram_bytes", "expected_gb"),
        [
            (True, 16 * (1024**3), 16.0),
            (False, None, 0.0),
        ],
    )
    def test_invocation(
        self, has_psutil: bool, ram_bytes: int | None, expected_gb: float
    ) -> None:
        """Test get_ram_gb invocation with and without psutil."""
        if has_psutil:
            with patch("gitversioned.utils.environment.psutil") as mock_psutil:
                mock_psutil.virtual_memory.return_value.total = ram_bytes
                assert get_ram_gb() == expected_gb
        else:
            with patch("gitversioned.utils.environment.psutil", None):
                assert get_ram_gb() == expected_gb


class TestBuildEnvironment:
    """Test suite for the BuildEnvironment model."""

    @pytest.fixture(
        params=[
            {
                "hostname": "test-host",
                "user": "test-user",
                "os_system": "Linux",
                "os_release": "5.10",
                "os_version": "#1 SMP",
                "cpu_arch": "x86_64",
                "cpu_cores": 8,
                "total_ram_gb": 16.0,
                "python_version": "3.10.0",
                "python_implementation": "CPython",
                "python_compiler": "GCC",
                "project_root": Path("/test/cwd"),
                "timestamp": datetime(2023, 1, 1, tzinfo=timezone.utc),
                "is_ci": True,
                "ci_provider": "GitHub Actions",
                "build_id": "test-id-1",
            },
            {
                "hostname": "local-mac",
                "user": "dev",
                "os_system": "Darwin",
                "os_release": "21.6.0",
                "os_version": "Darwin Kernel",
                "cpu_arch": "arm64",
                "cpu_cores": 10,
                "total_ram_gb": 32.0,
                "python_version": "3.11.2",
                "python_implementation": "CPython",
                "python_compiler": "Clang",
                "project_root": Path("/Users/dev/project"),
                "timestamp": datetime(2023, 5, 1, 12, tzinfo=timezone.utc),
                "is_ci": False,
                "ci_provider": None,
                "build_id": "test-id-2",
            },
        ],
        ids=["ci_linux", "local_mac"],
    )
    def valid_instances(
        self, request: pytest.FixtureRequest
    ) -> tuple[BuildEnvironment, dict[str, typing.Any]]:
        """Fixture providing test data for BuildEnvironment."""
        constructor_args = request.param
        instance = BuildEnvironment(**constructor_args)
        return instance, constructor_args

    @pytest.mark.smoke
    def test_class_signatures(self) -> None:
        """Test BuildEnvironment signature and fields."""
        assert issubclass(BuildEnvironment, BaseModel)
        expected_fields = {
            "hostname",
            "user",
            "os_system",
            "os_release",
            "os_version",
            "cpu_arch",
            "cpu_cores",
            "total_ram_gb",
            "python_version",
            "python_implementation",
            "python_compiler",
            "project_root",
            "timestamp",
            "is_ci",
            "ci_provider",
            "build_id",
        }
        assert set(BuildEnvironment.model_fields.keys()) == expected_fields

    @pytest.mark.smoke
    def test_initialization(
        self,
        valid_instances: tuple[BuildEnvironment, dict[str, typing.Any]],
    ) -> None:
        """Test BuildEnvironment initialization."""
        instance, constructor_args = valid_instances
        assert isinstance(instance, BuildEnvironment)
        assert instance.hostname == constructor_args["hostname"]
        assert instance.user == constructor_args["user"]
        assert instance.os_system == constructor_args["os_system"]
        assert instance.is_ci == constructor_args["is_ci"]

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("cpu_cores", "not an int"),
            ("total_ram_gb", "not a float"),
        ],
    )
    def test_invalid_initialization_values(
        self,
        valid_instances: tuple[BuildEnvironment, dict[str, typing.Any]],
        field: str,
        value: str,
    ) -> None:
        """Test BuildEnvironment with invalid field values."""
        _instance, constructor_args = valid_instances
        invalid_args = {**constructor_args, field: value}
        with pytest.raises(ValidationError):
            BuildEnvironment(**invalid_args)

    @pytest.mark.sanity
    def test_invalid_initialization_missing(self) -> None:
        """Test BuildEnvironment initialization without required fields.

        Since all fields have default_factories, this should succeed.
        """
        env_instance = BuildEnvironment()
        assert isinstance(env_instance, BuildEnvironment)
        assert env_instance.hostname
        assert env_instance.user
        assert env_instance.os_system

    @pytest.mark.smoke
    def test_marshalling(
        self,
        valid_instances: tuple[BuildEnvironment, dict[str, typing.Any]],
    ) -> None:
        """Test BuildEnvironment marshalling."""
        instance, constructor_args = valid_instances
        dumped_data = instance.model_dump()
        assert dumped_data["hostname"] == constructor_args["hostname"]

        validated_instance = BuildEnvironment.model_validate(dumped_data)
        assert validated_instance == instance
