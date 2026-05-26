from __future__ import annotations

from distutils.errors import DistutilsSetupError
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from gitversioned.plugins.setuptools_plugin import (
    finalize_distribution_options,
    setup_keywords,
)
from gitversioned.settings import Settings
from gitversioned.utils import BuildEnvironment, GitRepository


class TestSetupKeywords:
    @pytest.fixture
    def valid_instances(self) -> list[tuple[MagicMock, str, dict[str, Any]]]:
        return [
            (MagicMock(), "gitversioned", {"some": "config"}),
        ]

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("attr", "value"),
        [
            ("gitversioned", {}),
            ("gitversioned", {"key": "val"}),
        ],
    )
    def test_invocation(self, attr: str, value: Any) -> None:
        dist_mock = MagicMock()
        setup_keywords(dist_mock, attr, value)
        assert dist_mock.gitversioned_config == value

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("attr", "value", "expected_error"),
        [
            ("wrong_attr", {}, "Unknown keyword argument: wrong_attr"),
            ("gitversioned", [], "gitversioned must be a dict"),
            ("gitversioned", "string", "gitversioned must be a dict"),
        ],
    )
    def test_invalid(self, attr: str, value: Any, expected_error: str) -> None:
        dist_mock = MagicMock()
        with pytest.raises(DistutilsSetupError, match=expected_error):
            setup_keywords(dist_mock, attr, value)


class TestFinalizeDistributionOptions:
    @pytest.fixture
    def mock_distribution(self) -> MagicMock:
        dist = MagicMock()
        dist.metadata = MagicMock()
        dist.metadata.name = "test-package"
        dist.get_name.return_value = "test-package"
        dist.version = None
        dist.src_root = "/mock/root"
        dist.package_dir = {}
        dist.editable = False
        dist.gitversioned_config = {}
        return dist

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        (
            "src_root",
            "package_dir",
            "gitversioned_config",
            "expected_project_root",
            "expected_src_root",
        ),
        [
            ("/mock/root", {}, {}, Path("/mock/root"), Path("/mock/root")),
            (None, {}, {}, Path.cwd(), Path.cwd()),
            ("/mock/root", {"": "src"}, {}, Path("/mock/root"), Path("/mock/root/src")),
            (
                "/mock/root",
                {"test-package": "lib"},
                {},
                Path("/mock/root"),
                Path("/mock/root/lib"),
            ),
            (
                "/mock/root",
                {"": "src", "test-package": "lib"},
                {"build_is_editable": True},
                Path("/mock/root"),
                Path("/mock/root/lib"),
            ),
            (
                "/mock/root",
                {},
                {"extra": "val"},
                Path("/mock/root"),
                Path("/mock/root"),
            ),
        ],
    )
    def test_invocation(
        self,
        mock_distribution: MagicMock,
        src_root: str | None,
        package_dir: dict[str, str],
        gitversioned_config: dict[str, Any],
        expected_project_root: Path,
        expected_src_root: Path,
    ) -> None:
        mock_distribution.src_root = src_root
        mock_distribution.package_dir = package_dir
        mock_distribution.gitversioned_config = gitversioned_config

        expected_version = "1.2.3"
        mock_settings = MagicMock(spec=Settings)
        mock_settings.project_root = expected_project_root
        mock_repo = MagicMock(spec=GitRepository)
        mock_env = MagicMock(spec=BuildEnvironment)

        with (
            patch(
                "gitversioned.plugins.setuptools_plugin.Settings",
                return_value=mock_settings,
            ) as mock_settings_cls,
            patch(
                "gitversioned.plugins.setuptools_plugin.GitRepository",
                return_value=mock_repo,
            ) as mock_repo_cls,
            patch(
                "gitversioned.plugins.setuptools_plugin.BuildEnvironment",
                return_value=mock_env,
            ) as mock_env_cls,
            patch(
                "gitversioned.plugins.setuptools_plugin.resolve_and_generate_version",
                return_value=(expected_version, MagicMock()),
            ) as mock_resolve,
        ):
            finalize_distribution_options(mock_distribution)

            mock_settings_cls.assert_called_once_with(
                package_name="test_package",
                project_root=expected_project_root,
                src_root=expected_src_root,
                build_is_editable=gitversioned_config.get("build_is_editable", False),
                **{
                    k: v
                    for k, v in gitversioned_config.items()
                    if k != "build_is_editable"
                },
            )
            mock_repo_cls.assert_called_once_with(mock_settings.project_root)
            mock_env_cls.assert_called_once_with(
                project_root=mock_settings.project_root
            )
            mock_resolve.assert_called_once_with(
                settings=mock_settings,
                repository=mock_repo,
                environment=mock_env,
            )

            assert mock_distribution.metadata.version == expected_version
            assert mock_distribution.version == expected_version

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("pkg_name", "fallback_name"),
        [
            ("UNKNOWN", "UNKNOWN"),
            (None, None),
            (None, "UNKNOWN"),
        ],
    )
    def test_invalid_package_name(
        self,
        mock_distribution: MagicMock,
        pkg_name: str | None,
        fallback_name: str | None,
    ) -> None:
        mock_distribution.metadata.name = pkg_name
        mock_distribution.get_name.return_value = fallback_name

        with pytest.raises(
            DistutilsSetupError, match="Could not determine package name."
        ):
            finalize_distribution_options(mock_distribution)

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        "pkg_name",
        [None, "UNKNOWN"],
    )
    def test_invocation_fallback_name(
        self, mock_distribution: MagicMock, pkg_name: str | None
    ) -> None:
        mock_distribution.metadata.name = pkg_name
        mock_distribution.get_name.return_value = "fallback_name"

        expected_version = "1.2.3"
        mock_settings = MagicMock(spec=Settings)
        mock_settings.project_root = Path("/mock/root")

        with (
            patch(
                "gitversioned.plugins.setuptools_plugin.Settings",
                return_value=mock_settings,
            ) as mock_settings_cls,
            patch("gitversioned.plugins.setuptools_plugin.GitRepository"),
            patch("gitversioned.plugins.setuptools_plugin.BuildEnvironment"),
            patch(
                "gitversioned.plugins.setuptools_plugin.resolve_and_generate_version",
                return_value=(expected_version, MagicMock()),
            ),
        ):
            finalize_distribution_options(mock_distribution)

            mock_settings_cls.assert_called_once_with(
                package_name="fallback_name",
                project_root=Path("/mock/root"),
                src_root=Path("/mock/root"),
                build_is_editable=False,
            )

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        "version_already_set",
        [
            "1.0.0",
            "1.2.3a1",
        ],
    )
    def test_version_already_set(
        self, mock_distribution: MagicMock, version_already_set: str
    ) -> None:
        mock_distribution.version = version_already_set
        with patch(
            "gitversioned.plugins.setuptools_plugin.resolve_and_generate_version",
            return_value=(version_already_set, MagicMock()),
        ) as mock_resolve:
            finalize_distribution_options(mock_distribution)
            mock_resolve.assert_not_called()
            assert mock_distribution.version == version_already_set
