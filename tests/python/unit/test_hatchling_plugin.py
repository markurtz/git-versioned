from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from hatchling.version.source.plugin.interface import VersionSourceInterface

from gitversioned.plugins.hatchling_plugin import (
    GitVersionedVersionSource,
    hatch_register_version_source,
)


class TestGitVersionedVersionSource:
    @pytest.fixture(
        params=[
            ("/mock/project", {"plugin_config": "val"}),
            (str(Path("/mock/project")), {}),
        ]
    )
    def valid_instances(
        self, request: pytest.FixtureRequest
    ) -> GitVersionedVersionSource:
        root, config = request.param
        return GitVersionedVersionSource(root=root, config=config)

    @pytest.mark.smoke
    def test_signature(self) -> None:
        assert issubclass(GitVersionedVersionSource, VersionSourceInterface)
        assert hasattr(GitVersionedVersionSource, "PLUGIN_NAME")
        assert GitVersionedVersionSource.PLUGIN_NAME == "gitversioned"

        methods = [
            "get_version_data",
            "set_version",
            "get_settings_kwargs",
            "get_project_root",
            "get_package_name",
            "get_src_root",
        ]
        for method in methods:
            assert hasattr(GitVersionedVersionSource, method)
            assert callable(getattr(GitVersionedVersionSource, method))

    @pytest.mark.smoke
    def test_initialization(self, valid_instances: GitVersionedVersionSource) -> None:
        assert valid_instances is not None
        assert hasattr(valid_instances, "root")
        assert hasattr(valid_instances, "config")

    @pytest.mark.sanity
    @patch("gitversioned.plugins.hatchling_plugin.resolve_and_generate_version")
    @patch("gitversioned.plugins.hatchling_plugin.BuildEnvironment")
    @patch("gitversioned.plugins.hatchling_plugin.GitRepository")
    @patch("gitversioned.plugins.hatchling_plugin.Settings")
    @patch("gitversioned.plugins.hatchling_plugin.configure_logger")
    def test_get_version_data(
        self,
        mock_configure_logger: MagicMock,
        mock_settings_cls: MagicMock,
        mock_git_repo_cls: MagicMock,
        mock_build_env_cls: MagicMock,
        mock_resolve_generate: MagicMock,
        valid_instances: GitVersionedVersionSource,
    ) -> None:
        mock_settings = MagicMock()
        mock_settings.project_root = Path("/mock/mock_root")
        mock_settings_cls.return_value = mock_settings
        mock_resolve_generate.return_value = (
            "1.2.3",
            Path("/mock/mock_root/version.py"),
        )

        with patch.object(
            valid_instances, "get_settings_kwargs", return_value={"mock": "kwargs"}
        ):
            result = valid_instances.get_version_data()

        assert result == {"version": "1.2.3"}
        mock_configure_logger.assert_called_once()
        mock_settings_cls.assert_called_once_with(mock="kwargs")
        mock_git_repo_cls.assert_called_once_with(mock_settings.project_root)
        mock_build_env_cls.assert_called_once_with(
            project_root=mock_settings.project_root
        )
        mock_resolve_generate.assert_called_once_with(
            settings=mock_settings,
            repository=mock_git_repo_cls.return_value,
            environment=mock_build_env_cls.return_value,
        )

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("version_source_file", "expected_call_count"),
        [
            ("version.txt", 1),
            (None, 0),
            ("", 0),
        ],
    )
    @patch("gitversioned.plugins.hatchling_plugin.Settings")
    @patch("pathlib.Path.write_text")
    def test_set_version(
        self,
        mock_write_text: MagicMock,
        mock_settings_cls: MagicMock,
        version_source_file: str | None,
        expected_call_count: int,
        valid_instances: GitVersionedVersionSource,
    ) -> None:
        mock_settings = MagicMock()
        mock_settings.project_root = Path("/mock/mock_root")
        mock_settings.version_source_file = version_source_file
        mock_settings_cls.return_value = mock_settings

        with patch.object(
            valid_instances, "get_settings_kwargs", return_value={"mock": "kwargs"}
        ):
            valid_instances.set_version("1.2.4", {"some": "data"})

        assert mock_write_text.call_count == expected_call_count
        if expected_call_count > 0:
            mock_write_text.assert_called_once_with("version=1.2.4\n", encoding="utf-8")

    @pytest.mark.sanity
    def test_get_settings_kwargs(
        self, valid_instances: GitVersionedVersionSource
    ) -> None:
        with (
            patch.object(
                valid_instances, "get_project_root", return_value=Path("/mock/root")
            ),
            patch.object(valid_instances, "get_package_name", return_value="my_pkg"),
            patch.object(
                valid_instances,
                "get_src_root",
                return_value=Path("/mock/root/src/my_pkg"),
            ),
        ):
            kwargs = valid_instances.get_settings_kwargs()

        assert kwargs["package_name"] == "my_pkg"
        assert kwargs["project_root"] == Path("/mock/root")
        assert kwargs["src_root"] == Path("/mock/root/src/my_pkg")
        assert kwargs["build_is_editable"] is False
        for key, value in valid_instances.config.items():
            assert kwargs[key] == value

    @pytest.mark.sanity
    def test_get_project_root(self, valid_instances: GitVersionedVersionSource) -> None:
        root = valid_instances.get_project_root()
        assert isinstance(root, Path)
        assert root == Path(valid_instances.root).resolve()

    @pytest.mark.sanity
    @patch("gitversioned.plugins.hatchling_plugin.ProjectMetadata")
    def test_get_package_name(
        self,
        mock_metadata_cls: MagicMock,
        valid_instances: GitVersionedVersionSource,
    ) -> None:
        mock_metadata = MagicMock()
        mock_metadata.name = "my-awesome-package"
        mock_metadata_cls.return_value = mock_metadata

        name = valid_instances.get_package_name()

        assert name == "my_awesome_package"
        mock_metadata_cls.assert_called_once_with(
            str(valid_instances.get_project_root()), None
        )

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("config_kwargs", "hatch_build_targets", "dir_to_create", "expected_rel_path"),
        [
            ({"src_root": "explicit_src"}, {}, None, "explicit_src"),
            ({}, {"packages": ["pkg_from_hatch"]}, None, "pkg_from_hatch"),
            ({}, {"sources": {"src_from_hatch": "xyz"}}, None, "src_from_hatch"),
            ({}, {}, "src/my_pkg", "src/my_pkg"),
            ({}, {}, "my_pkg", "my_pkg"),
            ({}, {}, None, ""),
        ],
    )
    @patch("gitversioned.plugins.hatchling_plugin.ProjectMetadata")
    def test_get_src_root(
        self,
        mock_metadata_cls: MagicMock,
        config_kwargs: dict[str, Any],
        hatch_build_targets: dict[str, Any],
        dir_to_create: str | None,
        expected_rel_path: str,
        tmp_path: Path,
    ) -> None:
        mock_metadata = MagicMock()
        mock_metadata.config = {
            "tool": {"hatch": {"build": {"targets": {"wheel": hatch_build_targets}}}}
        }
        mock_metadata_cls.return_value = mock_metadata

        if dir_to_create:
            (tmp_path / dir_to_create).mkdir(parents=True)

        instance = GitVersionedVersionSource(root=str(tmp_path), config=config_kwargs)
        with patch.object(instance, "get_package_name", return_value="my_pkg"):
            src_root = instance.get_src_root()

        expected_path = tmp_path / expected_rel_path if expected_rel_path else tmp_path
        assert src_root == expected_path


class TestHatchRegisterVersionSource:
    @pytest.mark.smoke
    def test_invocation(self) -> None:
        result = hatch_register_version_source()
        assert result is GitVersionedVersionSource
