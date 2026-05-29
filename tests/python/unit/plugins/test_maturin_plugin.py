# Copyright 2026 The GitVersioned Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for the Maturin build backend plugin wrapper."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from gitversioned.plugins import maturin_plugin


@pytest.fixture
def mock_maturin(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock the maturin module and its hooks."""
    mock = MagicMock()
    monkeypatch.setattr(maturin_plugin, "maturin", mock)
    return mock


@pytest.fixture
def mock_resolve_version(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock the resolve_version_output_to_stream entry point."""
    mock = MagicMock(
        return_value=(Path("version.py"), "content", "1.0.0", "release", None)
    )
    monkeypatch.setattr(maturin_plugin, "resolve_version_output_to_stream", mock)
    return mock


@pytest.fixture
def mock_configure_logger(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock the configure_logger function."""
    mock_func = MagicMock()
    monkeypatch.setattr(maturin_plugin, "configure_logger", mock_func)
    return mock_func


@pytest.fixture(autouse=True)
def reset_logging_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset the internal logging configured flag for each test."""
    monkeypatch.setattr(maturin_plugin, "_logging_configured", False)


class TestBuildWheel:
    """Test suite for the build_wheel function."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("wheel_directory", "config_settings", "metadata_directory"),
        [
            ("dist_dir", {"opt": "val"}, "meta_dir"),
            ("dist_dir", None, None),
        ],
    )
    def test_invocation(
        self,
        wheel_directory: str,
        config_settings: dict[str, Any] | None,
        metadata_directory: str | None,
        mock_maturin: MagicMock,
        mock_resolve_version: MagicMock,
    ) -> None:
        """Verify build_wheel correctly invokes maturin.build_wheel."""
        mock_maturin.build_wheel.return_value = "built_wheel_path"

        result = maturin_plugin.build_wheel(
            wheel_directory,
            config_settings=config_settings,
            metadata_directory=metadata_directory,
        )

        assert result == "built_wheel_path"
        mock_maturin.build_wheel.assert_called_once_with(
            wheel_directory,
            config_settings=config_settings,
            metadata_directory=metadata_directory,
        )
        mock_resolve_version.assert_called_once()

    @pytest.mark.sanity
    def test_invalid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify build_wheel raises ImportError when maturin is missing."""
        monkeypatch.setattr(maturin_plugin, "maturin", None)
        with pytest.raises(
            ImportError, match="The 'maturin' package must be installed"
        ):
            maturin_plugin.build_wheel("dist_dir")


class TestBuildSdist:
    """Test suite for the build_sdist function."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("sdist_directory", "config_settings"),
        [
            ("dist_dir", {"opt": "val"}),
            ("dist_dir", None),
        ],
    )
    def test_invocation(
        self,
        sdist_directory: str,
        config_settings: dict[str, Any] | None,
        mock_maturin: MagicMock,
        mock_resolve_version: MagicMock,
    ) -> None:
        """Verify build_sdist correctly invokes maturin.build_sdist."""
        mock_maturin.build_sdist.return_value = "built_sdist_path"

        result = maturin_plugin.build_sdist(
            sdist_directory,
            config_settings=config_settings,
        )

        assert result == "built_sdist_path"
        mock_maturin.build_sdist.assert_called_once_with(
            sdist_directory,
            config_settings=config_settings,
        )
        mock_resolve_version.assert_called_once()

    @pytest.mark.sanity
    def test_invalid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify build_sdist raises ImportError when maturin is missing."""
        monkeypatch.setattr(maturin_plugin, "maturin", None)
        with pytest.raises(
            ImportError, match="The 'maturin' package must be installed"
        ):
            maturin_plugin.build_sdist("dist_dir")


class TestGetRequiresForBuildWheel:
    """Test suite for the get_requires_for_build_wheel function."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "config_settings",
        [
            {"opt": "val"},
            None,
        ],
    )
    def test_invocation(
        self,
        config_settings: dict[str, Any] | None,
        mock_maturin: MagicMock,
        mock_resolve_version: MagicMock,
    ) -> None:
        """Verify get_requires_for_build_wheel invokes maturin counterpart."""
        mock_maturin.get_requires_for_build_wheel.return_value = ["req1", "req2"]

        result = maturin_plugin.get_requires_for_build_wheel(
            config_settings=config_settings,
        )

        assert result == ["req1", "req2"]
        mock_maturin.get_requires_for_build_wheel.assert_called_once_with(
            config_settings=config_settings,
        )
        mock_resolve_version.assert_called_once()

    @pytest.mark.sanity
    def test_invalid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify get_requires_for_build_wheel raises ImportError if missing."""
        monkeypatch.setattr(maturin_plugin, "maturin", None)
        with pytest.raises(
            ImportError, match="The 'maturin' package must be installed"
        ):
            maturin_plugin.get_requires_for_build_wheel()


class TestGetRequiresForBuildSdist:
    """Test suite for the get_requires_for_build_sdist function."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "config_settings",
        [
            {"opt": "val"},
            None,
        ],
    )
    def test_invocation(
        self,
        config_settings: dict[str, Any] | None,
        mock_maturin: MagicMock,
        mock_resolve_version: MagicMock,
    ) -> None:
        """Verify get_requires_for_build_sdist invokes maturin counterpart."""
        mock_maturin.get_requires_for_build_sdist.return_value = ["req1", "req2"]

        result = maturin_plugin.get_requires_for_build_sdist(
            config_settings=config_settings,
        )

        assert result == ["req1", "req2"]
        mock_maturin.get_requires_for_build_sdist.assert_called_once_with(
            config_settings=config_settings,
        )
        mock_resolve_version.assert_called_once()

    @pytest.mark.sanity
    def test_invalid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify get_requires_for_build_sdist raises ImportError if missing."""
        monkeypatch.setattr(maturin_plugin, "maturin", None)
        with pytest.raises(
            ImportError, match="The 'maturin' package must be installed"
        ):
            maturin_plugin.get_requires_for_build_sdist()


class TestPrepareMetadataForBuildWheel:
    """Test suite for the prepare_metadata_for_build_wheel function."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("metadata_directory", "config_settings"),
        [
            ("meta_dir", {"opt": "val"}),
            ("meta_dir", None),
        ],
    )
    def test_invocation(
        self,
        metadata_directory: str,
        config_settings: dict[str, Any] | None,
        mock_maturin: MagicMock,
        mock_resolve_version: MagicMock,
    ) -> None:
        """Verify prepare_metadata_for_build_wheel invokes maturin counterpart."""
        mock_maturin.prepare_metadata_for_build_wheel.return_value = "metadata_path"

        result = maturin_plugin.prepare_metadata_for_build_wheel(
            metadata_directory,
            config_settings=config_settings,
        )

        assert result == "metadata_path"
        mock_maturin.prepare_metadata_for_build_wheel.assert_called_once_with(
            metadata_directory,
            config_settings=config_settings,
        )
        mock_resolve_version.assert_called_once()

    @pytest.mark.sanity
    def test_invalid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify prepare_metadata_for_build_wheel raises ImportError if missing."""
        monkeypatch.setattr(maturin_plugin, "maturin", None)
        with pytest.raises(
            ImportError, match="The 'maturin' package must be installed"
        ):
            maturin_plugin.prepare_metadata_for_build_wheel("meta_dir")


class TestBuildEditable:
    """Test suite for the build_editable function."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("wheel_directory", "config_settings", "metadata_directory"),
        [
            ("dist_dir", {"opt": "val"}, "meta_dir"),
            ("dist_dir", None, None),
        ],
    )
    def test_invocation(
        self,
        wheel_directory: str,
        config_settings: dict[str, Any] | None,
        metadata_directory: str | None,
        mock_maturin: MagicMock,
        mock_resolve_version: MagicMock,
    ) -> None:
        """Verify build_editable correctly invokes maturin.build_editable."""
        mock_maturin.build_editable.return_value = "built_editable_path"

        result = maturin_plugin.build_editable(
            wheel_directory,
            config_settings=config_settings,
            metadata_directory=metadata_directory,
        )

        assert result == "built_editable_path"
        mock_maturin.build_editable.assert_called_once_with(
            wheel_directory,
            config_settings=config_settings,
            metadata_directory=metadata_directory,
        )
        mock_resolve_version.assert_called_once()

    @pytest.mark.sanity
    def test_invalid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify build_editable raises ImportError when maturin is missing."""
        monkeypatch.setattr(maturin_plugin, "maturin", None)
        with pytest.raises(
            ImportError, match="The 'maturin' package must be installed"
        ):
            maturin_plugin.build_editable("dist_dir")


class TestGetRequiresForBuildEditable:
    """Test suite for the get_requires_for_build_editable function."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "config_settings",
        [
            {"opt": "val"},
            None,
        ],
    )
    def test_invocation(
        self,
        config_settings: dict[str, Any] | None,
        mock_maturin: MagicMock,
        mock_resolve_version: MagicMock,
    ) -> None:
        """Verify get_requires_for_build_editable invokes maturin counterpart."""
        mock_maturin.get_requires_for_build_editable.return_value = ["req1", "req2"]

        result = maturin_plugin.get_requires_for_build_editable(
            config_settings=config_settings,
        )

        assert result == ["req1", "req2"]
        mock_maturin.get_requires_for_build_editable.assert_called_once_with(
            config_settings=config_settings,
        )
        mock_resolve_version.assert_called_once()

    @pytest.mark.sanity
    def test_invalid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify get_requires_for_build_editable raises ImportError if missing."""
        monkeypatch.setattr(maturin_plugin, "maturin", None)
        with pytest.raises(
            ImportError, match="The 'maturin' package must be installed"
        ):
            maturin_plugin.get_requires_for_build_editable()


class TestPrepareMetadataForBuildEditable:
    """Test suite for the prepare_metadata_for_build_editable function."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("metadata_directory", "config_settings"),
        [
            ("meta_dir", {"opt": "val"}),
            ("meta_dir", None),
        ],
    )
    def test_invocation(
        self,
        metadata_directory: str,
        config_settings: dict[str, Any] | None,
        mock_maturin: MagicMock,
        mock_resolve_version: MagicMock,
    ) -> None:
        """Verify prepare_metadata_for_build_editable invokes maturin counterpart."""
        mock_maturin.prepare_metadata_for_build_editable.return_value = "metadata_path"

        result = maturin_plugin.prepare_metadata_for_build_editable(
            metadata_directory,
            config_settings=config_settings,
        )

        assert result == "metadata_path"
        mock_maturin.prepare_metadata_for_build_editable.assert_called_once_with(
            metadata_directory,
            config_settings=config_settings,
        )
        mock_resolve_version.assert_called_once()

    @pytest.mark.sanity
    def test_invalid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify prepare_metadata_for_build_editable raises ImportError if missing."""
        monkeypatch.setattr(maturin_plugin, "maturin", None)
        with pytest.raises(
            ImportError, match="The 'maturin' package must be installed"
        ):
            maturin_plugin.prepare_metadata_for_build_editable("meta_dir")


class TestLoggingConfiguration:
    """Test suite for the logging configuration within the Maturin plugin."""

    @pytest.mark.regression
    def test_logging_not_previously_configured(
        self,
        mock_maturin: MagicMock,
        mock_resolve_version: MagicMock,
        mock_configure_logger: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify that logging is configured if it has not been previously."""
        monkeypatch.setattr(maturin_plugin, "_logging_configured", False)
        maturin_plugin.build_wheel("wheel_dir")

        mock_configure_logger.assert_called_once()
        call_args = mock_configure_logger.call_args[0][0]
        assert call_args.enabled is True
        assert maturin_plugin._logging_configured is True

    @pytest.mark.regression
    def test_logging_previously_configured(
        self,
        mock_maturin: MagicMock,
        mock_resolve_version: MagicMock,
        mock_configure_logger: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify that logging is not reconfigured if it was already configured."""
        monkeypatch.setattr(maturin_plugin, "_logging_configured", True)
        maturin_plugin.build_wheel("wheel_dir")

        mock_configure_logger.assert_not_called()
        assert maturin_plugin._logging_configured is True


class TestCargoTomlOverrides:
    """Test suite for the Cargo.toml auto-injection behavior."""

    @pytest.mark.regression
    def test_overrides_injected_when_toml_exists(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_maturin: MagicMock,
        mock_resolve_version: MagicMock,
    ) -> None:
        """Verify cargo override injection when Cargo.toml exists and is empty."""
        monkeypatch.chdir(tmp_path)
        cargo_toml = tmp_path / "Cargo.toml"
        cargo_toml.touch()

        maturin_plugin.build_wheel("wheel_dir")

        assert mock_resolve_version.call_count == 1
        settings_passed = mock_resolve_version.call_args[1]["settings"]
        assert "cargo" in settings_passed.overrides
        assert settings_passed.overrides["cargo"]["output"] == "Cargo.toml"
        assert (
            settings_passed.overrides["cargo"]["output_strategies"]["type"] == "regex"
        )

    @pytest.mark.regression
    def test_overrides_not_injected_when_toml_missing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_maturin: MagicMock,
        mock_resolve_version: MagicMock,
    ) -> None:
        """Verify cargo override is not injected when Cargo.toml does not exist."""
        monkeypatch.chdir(tmp_path)

        maturin_plugin.build_wheel("wheel_dir")

        assert mock_resolve_version.call_count == 1
        settings_passed = mock_resolve_version.call_args[1]["settings"]
        assert not settings_passed.overrides

    @pytest.mark.regression
    def test_overrides_not_injected_when_overrides_exist(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_maturin: MagicMock,
        mock_resolve_version: MagicMock,
    ) -> None:
        """Verify cargo override is not injected if overrides already configured."""
        monkeypatch.chdir(tmp_path)
        cargo_toml = tmp_path / "Cargo.toml"
        cargo_toml.touch()

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[project]\n"
            'name = "mock_pkg"\n'
            'dynamic = ["version"]\n\n'
            "[tool.gitversioned.overrides.docker]\noutput = 'Dockerfile'\n",
            encoding="utf-8",
        )

        maturin_plugin.build_wheel("wheel_dir")

        assert mock_resolve_version.call_count == 1
        settings_passed = mock_resolve_version.call_args[1]["settings"]
        assert "cargo" not in settings_passed.overrides
        assert "docker" in settings_passed.overrides


class TestModuleExports:
    """Test suite for validating module-level constants and parameters."""

    @pytest.mark.regression
    def test_all_exports(self) -> None:
        """Verify the __all__ exports list matches expectations."""
        expected_exports = [
            "build_editable",
            "build_sdist",
            "build_wheel",
            "get_requires_for_build_editable",
            "get_requires_for_build_sdist",
            "get_requires_for_build_wheel",
            "prepare_metadata_for_build_editable",
            "prepare_metadata_for_build_wheel",
        ]
        assert sorted(maturin_plugin.__all__) == sorted(expected_exports)
