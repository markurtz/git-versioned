from __future__ import annotations

import inspect
import io
import os
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
    @pytest.mark.smoke
    def test_signature(self) -> None:
        sig = inspect.signature(setup_keywords)
        assert "distribution" in sig.parameters
        assert "attribute" in sig.parameters
        assert "value" in sig.parameters

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("attribute", "value"),
        [
            ("gitversioned", {}),
            ("gitversioned", {"key": "val"}),
        ],
    )
    def test_invocation(self, attribute: str, value: dict[str, Any]) -> None:
        dist_mock = MagicMock()
        setup_keywords(dist_mock, attribute, value)
        assert dist_mock.gitversioned_config == value

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("attribute", "value", "expected_error"),
        [
            ("wrong_attr", {}, "Unknown keyword argument: wrong_attr"),
            ("gitversioned", [], "gitversioned must be a dict"),
            ("gitversioned", "string", "gitversioned must be a dict"),
        ],
    )
    def test_invalid(self, attribute: str, value: Any, expected_error: str) -> None:
        dist_mock = MagicMock()
        with pytest.raises(DistutilsSetupError, match=expected_error):
            setup_keywords(dist_mock, attribute, value)


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
    def test_signature(self) -> None:
        sig = inspect.signature(finalize_distribution_options)
        assert "distribution" in sig.parameters

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
        mock_settings.src_root = expected_src_root
        mock_settings.output = None
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
                "gitversioned.plugins.setuptools_plugin.resolve_version_output_to_stream",
                return_value=(
                    None,
                    "mock_content",
                    expected_version,
                    "mock_type",
                    "mock_ref",
                ),
            ) as mock_resolve,
        ):
            finalize_distribution_options(mock_distribution)

            mock_settings_cls.assert_called_once_with(
                package_name="test_package",
                project_root=expected_project_root,
                src_root=expected_src_root,
                build_is_editable=gitversioned_config.get("build_is_editable", False),
                **{
                    key: val
                    for key, val in gitversioned_config.items()
                    if key != "build_is_editable"
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

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "version_already_set",
        [
            "1.0.0",
            "1.2.3a1",
        ],
    )
    def test_established_version_attributes(
        self, mock_distribution: MagicMock, version_already_set: str
    ) -> None:
        mock_distribution.version = version_already_set
        with patch(
            "gitversioned.plugins.setuptools_plugin.resolve_version_output_to_stream"
        ) as mock_resolve:
            finalize_distribution_options(mock_distribution)
            mock_resolve.assert_not_called()
            assert mock_distribution.version == version_already_set

    @pytest.mark.smoke
    def test_established_version_env_var(self, mock_distribution: MagicMock) -> None:
        expected_version = "2.3.4"
        with (
            patch.dict(os.environ, {"GITVERSIONED_RESOLVED_VERSION": expected_version}),
            patch(
                "gitversioned.plugins.setuptools_plugin.resolve_version_output_to_stream"
            ) as mock_resolve,
        ):
            finalize_distribution_options(mock_distribution)
            mock_resolve.assert_not_called()
            assert mock_distribution.version == expected_version
            assert mock_distribution.metadata.version == expected_version

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        "invalid_candidate",
        ["None", "0.0.0", "UNKNOWN"],
    )
    def test_established_version_invalid_candidates(
        self, mock_distribution: MagicMock, invalid_candidate: str
    ) -> None:
        mock_distribution.version = invalid_candidate
        mock_distribution.metadata.version = invalid_candidate
        expected_version = "1.2.3"
        with (
            patch(
                "gitversioned.plugins.setuptools_plugin.resolve_version_output_to_stream",
                return_value=(
                    None,
                    "mock_content",
                    expected_version,
                    "mock_type",
                    "mock_ref",
                ),
            ) as mock_resolve,
            patch("gitversioned.plugins.setuptools_plugin.Settings"),
            patch("gitversioned.plugins.setuptools_plugin.GitRepository"),
            patch("gitversioned.plugins.setuptools_plugin.BuildEnvironment"),
        ):
            finalize_distribution_options(mock_distribution)
            mock_resolve.assert_called_once()
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
        mock_distribution.packages = None

        def mock_is_dir(self_path: Path) -> bool:
            return False

        with (
            patch("gitversioned.plugins.setuptools_plugin.Path.is_dir", mock_is_dir),
            pytest.raises(
                DistutilsSetupError, match="Could not determine package name."
            ),
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
        mock_settings.src_root = Path("/mock/root")
        mock_settings.output = None

        with (
            patch(
                "gitversioned.plugins.setuptools_plugin.Settings",
                return_value=mock_settings,
            ) as mock_settings_cls,
            patch("gitversioned.plugins.setuptools_plugin.GitRepository"),
            patch("gitversioned.plugins.setuptools_plugin.BuildEnvironment"),
            patch(
                "gitversioned.plugins.setuptools_plugin.resolve_version_output_to_stream",
                return_value=(
                    None,
                    "mock_content",
                    expected_version,
                    "mock_type",
                    "mock_ref",
                ),
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
    def test_packages_list_fallback(self, mock_distribution: MagicMock) -> None:
        mock_distribution.metadata.name = "UNKNOWN"
        mock_distribution.get_name.return_value = "UNKNOWN"
        mock_distribution.packages = ["pkg_from_packages", "other_pkg"]

        expected_version = "1.2.3"
        mock_settings = MagicMock(spec=Settings)
        mock_settings.project_root = Path("/mock/root")
        mock_settings.src_root = Path("/mock/root")
        mock_settings.output = None

        with (
            patch(
                "gitversioned.plugins.setuptools_plugin.Settings",
                return_value=mock_settings,
            ) as mock_settings_cls,
            patch("gitversioned.plugins.setuptools_plugin.GitRepository"),
            patch("gitversioned.plugins.setuptools_plugin.BuildEnvironment"),
            patch(
                "gitversioned.plugins.setuptools_plugin.resolve_version_output_to_stream",
                return_value=(
                    None,
                    "mock_content",
                    expected_version,
                    "mock_type",
                    "mock_ref",
                ),
            ),
        ):
            finalize_distribution_options(mock_distribution)

            mock_settings_cls.assert_called_once_with(
                package_name="pkg_from_packages",
                project_root=Path("/mock/root"),
                src_root=Path("/mock/root"),
                build_is_editable=False,
            )

    @pytest.mark.sanity
    def test_filesystem_probe_fallback(self, mock_distribution: MagicMock) -> None:
        mock_distribution.metadata.name = "UNKNOWN"
        mock_distribution.get_name.return_value = "UNKNOWN"
        mock_distribution.packages = None

        expected_version = "1.2.3"
        mock_settings = MagicMock(spec=Settings)
        mock_settings.project_root = Path("/mock/root")
        mock_settings.src_root = Path("/mock/root")
        mock_settings.output = None

        with (
            patch(
                "gitversioned.plugins.setuptools_plugin.Settings",
                return_value=mock_settings,
            ) as mock_settings_cls,
            patch("gitversioned.plugins.setuptools_plugin.GitRepository"),
            patch("gitversioned.plugins.setuptools_plugin.BuildEnvironment"),
            patch(
                "gitversioned.plugins.setuptools_plugin.resolve_version_output_to_stream",
                return_value=(
                    None,
                    "mock_content",
                    expected_version,
                    "mock_type",
                    "mock_ref",
                ),
            ),
            patch(
                "gitversioned.plugins.setuptools_plugin._probe_filesystem_context",
                return_value=(Path("/mock/root/src/probed_pkg"), "probed_pkg"),
            ) as mock_probe,
        ):
            finalize_distribution_options(mock_distribution)

            mock_probe.assert_called_once_with(Path("/mock/root"))
            mock_settings_cls.assert_called_once_with(
                package_name="probed_pkg",
                project_root=Path("/mock/root"),
                src_root=Path("/mock/root/src/probed_pkg"),
                build_is_editable=False,
            )

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("raised_exception", "expected_exception_class", "expected_match"),
        [
            (
                DistutilsSetupError("Specific setuptools error"),
                DistutilsSetupError,
                "Specific setuptools error",
            ),
            (
                ValueError("Some value error"),
                DistutilsSetupError,
                "Failed to resolve version: Some value error",
            ),
        ],
    )
    def test_invalid_exceptions(
        self,
        mock_distribution: MagicMock,
        raised_exception: Exception,
        expected_exception_class: type[Exception],
        expected_match: str,
    ) -> None:
        with (
            patch(
                "gitversioned.plugins.setuptools_plugin.Settings",
                side_effect=raised_exception,
            ),
            pytest.raises(expected_exception_class, match=expected_match),
        ):
            finalize_distribution_options(mock_distribution)

    @pytest.mark.regression
    def test_probe_filesystem_context_success_src(
        self, mock_distribution: MagicMock
    ) -> None:
        mock_distribution.metadata.name = "UNKNOWN"
        mock_distribution.get_name.return_value = "UNKNOWN"
        mock_distribution.packages = None
        mock_distribution.src_root = "/mock/root"

        mock_src_dir = Path("/mock/root/src")
        mock_pkg_dir = Path("/mock/root/src/my_package")

        def mock_is_dir(self_path: Path) -> bool:
            return self_path in (Path("/mock/root"), mock_src_dir, mock_pkg_dir)

        def mock_iterdir(self_path: Path) -> list[Path]:
            if self_path == mock_src_dir:
                return [mock_pkg_dir]
            return []

        def mock_exists(self_path: Path) -> bool:
            return self_path == Path("/mock/root/src/my_package/__init__.py")

        with (
            patch("gitversioned.plugins.setuptools_plugin.Path.is_dir", mock_is_dir),
            patch("gitversioned.plugins.setuptools_plugin.Path.iterdir", mock_iterdir),
            patch("gitversioned.plugins.setuptools_plugin.Path.exists", mock_exists),
            patch(
                "gitversioned.plugins.setuptools_plugin.Settings"
            ) as mock_settings_cls,
            patch("gitversioned.plugins.setuptools_plugin.GitRepository"),
            patch("gitversioned.plugins.setuptools_plugin.BuildEnvironment"),
            patch(
                "gitversioned.plugins.setuptools_plugin.resolve_version_output_to_stream",
                return_value=(None, "", "1.0.0", "", ""),
            ),
        ):
            finalize_distribution_options(mock_distribution)
            mock_settings_cls.assert_called_once()
            assert mock_settings_cls.call_args[1]["package_name"] == "my_package"
            assert mock_settings_cls.call_args[1]["src_root"] == mock_pkg_dir

    @pytest.mark.regression
    def test_probe_filesystem_context_success_root(
        self, mock_distribution: MagicMock
    ) -> None:
        mock_distribution.metadata.name = "UNKNOWN"
        mock_distribution.get_name.return_value = "UNKNOWN"
        mock_distribution.packages = None
        mock_distribution.src_root = "/mock/root"

        mock_pkg_dir = Path("/mock/root/my_package")

        def mock_is_dir(self_path: Path) -> bool:
            return self_path in (Path("/mock/root"), mock_pkg_dir)

        def mock_iterdir(self_path: Path) -> list[Path]:
            if self_path == Path("/mock/root"):
                return [mock_pkg_dir]
            return []

        def mock_exists(self_path: Path) -> bool:
            return self_path == Path("/mock/root/my_package/__init__.py")

        with (
            patch("gitversioned.plugins.setuptools_plugin.Path.is_dir", mock_is_dir),
            patch("gitversioned.plugins.setuptools_plugin.Path.iterdir", mock_iterdir),
            patch("gitversioned.plugins.setuptools_plugin.Path.exists", mock_exists),
            patch(
                "gitversioned.plugins.setuptools_plugin.Settings"
            ) as mock_settings_cls,
            patch("gitversioned.plugins.setuptools_plugin.GitRepository"),
            patch("gitversioned.plugins.setuptools_plugin.BuildEnvironment"),
            patch(
                "gitversioned.plugins.setuptools_plugin.resolve_version_output_to_stream",
                return_value=(None, "", "1.0.0", "", ""),
            ),
        ):
            finalize_distribution_options(mock_distribution)
            mock_settings_cls.assert_called_once()
            assert mock_settings_cls.call_args[1]["package_name"] == "my_package"
            assert mock_settings_cls.call_args[1]["src_root"] == mock_pkg_dir

    @pytest.mark.regression
    @pytest.mark.parametrize(
        ("file_content", "expected_version", "should_resolve"),
        [
            (
                "Metadata-Version: 2.1\nName: test-package\nVersion: 4.5.6\n",
                "4.5.6",
                False,
            ),
            (
                "Metadata-Version: 2.1\nName: test-package\nVersion: UNKNOWN\n",
                "1.2.3",
                True,
            ),
            (
                "Metadata-Version: 2.1\nName: test-package\n",
                "1.2.3",
                True,
            ),
        ],
    )
    def test_established_version_pkg_info(
        self,
        mock_distribution: MagicMock,
        file_content: str,
        expected_version: str,
        should_resolve: bool,
    ) -> None:
        mock_distribution.src_root = "/mock/root"

        def mock_is_file(self_path: Path) -> bool:
            return self_path == Path("/mock/root/PKG-INFO")

        mock_file = io.StringIO(file_content)
        original_open = Path.open

        def mock_open(self_path: Path, *args: Any, **kwargs: Any) -> Any:
            if self_path == Path("/mock/root/PKG-INFO"):
                return mock_file
            return original_open(self_path, *args, **kwargs)

        with (
            patch("gitversioned.plugins.setuptools_plugin.Path.is_file", mock_is_file),
            patch("gitversioned.plugins.setuptools_plugin.Path.open", mock_open),
            patch(
                "gitversioned.plugins.setuptools_plugin.resolve_version_output_to_stream",
                return_value=(
                    None,
                    "mock_content",
                    "1.2.3",
                    "mock_type",
                    "mock_ref",
                ),
            ) as mock_resolve,
            patch("gitversioned.plugins.setuptools_plugin.Settings"),
            patch("gitversioned.plugins.setuptools_plugin.GitRepository"),
            patch("gitversioned.plugins.setuptools_plugin.BuildEnvironment"),
        ):
            finalize_distribution_options(mock_distribution)
            if should_resolve:
                mock_resolve.assert_called_once()
            else:
                mock_resolve.assert_not_called()
            assert mock_distribution.version == expected_version

    @pytest.mark.regression
    @pytest.mark.parametrize(
        "exception_class",
        [OSError, ValueError],
    )
    def test_established_version_pkg_info_failure(
        self,
        mock_distribution: MagicMock,
        exception_class: type[Exception],
    ) -> None:
        mock_distribution.src_root = "/mock/root"

        def mock_is_file(self_path: Path) -> bool:
            return self_path == Path("/mock/root/PKG-INFO")

        def mock_open(self_path: Path, *args: Any, **kwargs: Any) -> Any:
            if self_path == Path("/mock/root/PKG-INFO"):
                raise exception_class("Failed to read")
            raise FileNotFoundError

        expected_version = "1.2.3"
        with (
            patch("gitversioned.plugins.setuptools_plugin.Path.is_file", mock_is_file),
            patch("gitversioned.plugins.setuptools_plugin.Path.open", mock_open),
            patch(
                "gitversioned.plugins.setuptools_plugin.resolve_version_output_to_stream",
                return_value=(
                    None,
                    "mock_content",
                    expected_version,
                    "mock_type",
                    "mock_ref",
                ),
            ) as mock_resolve,
            patch("gitversioned.plugins.setuptools_plugin.Settings"),
            patch("gitversioned.plugins.setuptools_plugin.GitRepository"),
            patch("gitversioned.plugins.setuptools_plugin.BuildEnvironment"),
        ):
            finalize_distribution_options(mock_distribution)
            mock_resolve.assert_called_once()
            assert mock_distribution.version == expected_version

    @pytest.mark.regression
    @pytest.mark.parametrize(
        ("output_setting", "exists_value", "is_absolute", "expected_result"),
        [
            (None, False, False, None),
            ("/mock/root/version.txt", True, True, Path("/mock/root/version.txt")),
            ("/mock/root/version.txt", False, True, None),
            ("version.txt", True, False, Path("/mock/root/version.txt")),
            ("version.txt", False, False, None),
        ],
    )
    def test_find_existing_version_file(
        self,
        mock_distribution: MagicMock,
        output_setting: str | None,
        exists_value: bool,
        is_absolute: bool,
        expected_result: Path | None,
    ) -> None:
        mock_distribution.src_root = "/mock/root"
        mock_distribution.version = "1.0.0"

        mock_settings = MagicMock(spec=Settings)
        mock_settings.project_root = Path("/mock/root")
        mock_settings.src_root = Path("/mock/root")
        mock_settings.output = output_setting

        def mock_exists(self_path: Path) -> bool:
            return exists_value and self_path == Path("/mock/root/version.txt")

        with (
            patch(
                "gitversioned.plugins.setuptools_plugin.Settings",
                return_value=mock_settings,
            ),
            patch("gitversioned.plugins.setuptools_plugin.Path.exists", mock_exists),
            patch(
                "gitversioned.plugins.setuptools_plugin._inject_output_into_distribution"
            ) as mock_inject,
        ):
            finalize_distribution_options(mock_distribution)
            if expected_result:
                mock_inject.assert_called_once_with(
                    distribution=mock_distribution,
                    output_path=expected_result,
                    source_root=mock_settings.src_root,
                    package_name="test_package",
                )
            else:
                mock_inject.assert_not_called()

    @pytest.mark.regression
    @pytest.mark.parametrize(
        (
            "output_path",
            "source_root",
            "package_name",
            "initial_packages",
            "initial_package_data",
            "initial_py_modules",
            "expected_packages",
            "expected_package_data",
            "expected_py_modules",
            "expect_warning",
        ),
        [
            (
                Path("/mock/root/src/my_pkg/version.py"),
                Path("/mock/root/src"),
                "my_pkg",
                None,
                None,
                None,
                ["my_pkg"],
                {"my_pkg": ["version.py"]},
                None,
                False,
            ),
            (
                Path("/mock/root/src/my_pkg/version.py"),
                Path("/mock/root/src"),
                "my_pkg",
                ["my_pkg", "other_pkg"],
                {"my_pkg": ["other_file.py"]},
                None,
                ["my_pkg", "other_pkg"],
                {"my_pkg": ["other_file.py", "version.py"]},
                None,
                False,
            ),
            (
                Path("/mock/root/src/my_pkg/version.py"),
                Path("/mock/root/src"),
                "my_pkg",
                ["other_pkg"],
                None,
                None,
                ["other_pkg", "my_pkg"],
                {"my_pkg": ["version.py"]},
                None,
                False,
            ),
            (
                Path("/mock/root/src/version.py"),
                Path("/mock/root/src"),
                "my_pkg",
                None,
                None,
                None,
                None,
                None,
                ["version"],
                False,
            ),
            (
                Path("/mock/root/src/version.py"),
                Path("/mock/root/src"),
                "my_pkg",
                None,
                None,
                ["other_mod"],
                None,
                None,
                ["other_mod", "version"],
                False,
            ),
            (
                Path("/mock/root/src/version.py"),
                Path("/mock/root/src"),
                "my_pkg",
                None,
                None,
                ["version"],
                None,
                None,
                ["version"],
                False,
            ),
            (
                Path("/different/path/version.py"),
                Path("/mock/root/src"),
                "my_pkg",
                None,
                None,
                None,
                None,
                None,
                None,
                True,
            ),
        ],
    )
    def test_inject_output_into_distribution(
        self,
        mock_distribution: MagicMock,
        output_path: Path,
        source_root: Path,
        package_name: str,
        initial_packages: list[str] | None,
        initial_package_data: dict[str, list[str]] | None,
        initial_py_modules: list[str] | None,
        expected_packages: list[str] | None,
        expected_package_data: dict[str, list[str]] | None,
        expected_py_modules: list[str] | None,
        expect_warning: bool,
    ) -> None:
        mock_distribution.metadata.name = package_name
        mock_distribution.src_root = "/mock/root"
        mock_distribution.packages = initial_packages
        mock_distribution.package_data = initial_package_data
        mock_distribution.py_modules = initial_py_modules

        mock_settings = MagicMock(spec=Settings)
        mock_settings.project_root = Path("/mock/root")
        mock_settings.src_root = source_root
        mock_settings.output = None

        with (
            patch(
                "gitversioned.plugins.setuptools_plugin.Settings",
                return_value=mock_settings,
            ),
            patch("gitversioned.plugins.setuptools_plugin.GitRepository"),
            patch("gitversioned.plugins.setuptools_plugin.BuildEnvironment"),
            patch(
                "gitversioned.plugins.setuptools_plugin.resolve_version_output_to_stream",
                return_value=(
                    output_path,
                    "mock_content",
                    "1.2.3",
                    "mock_type",
                    "mock_ref",
                ),
            ),
            patch(
                "gitversioned.plugins.setuptools_plugin._get_source_root",
                return_value=source_root,
            ),
            patch("gitversioned.plugins.setuptools_plugin.logger.warning") as mock_warn,
        ):
            finalize_distribution_options(mock_distribution)

            if expected_packages is not None:
                assert mock_distribution.packages == expected_packages
            if expected_package_data is not None:
                assert mock_distribution.package_data == expected_package_data
            if expected_py_modules is not None:
                assert mock_distribution.py_modules == expected_py_modules

            if expect_warning:
                mock_warn.assert_called_once()
            else:
                mock_warn.assert_not_called()
