from __future__ import annotations

from distutils.errors import DistutilsSetupError
from pathlib import Path
from typing import Any

import pytest
from hatchling.version.source.plugin.interface import VersionSourceInterface

from gitversioned.plugins import setuptools_plugin
from gitversioned.plugins.hatchling_plugin import (
    GitVersionedVersionSource,
    hatch_register_version_source,
)
from gitversioned.plugins.setuptools_plugin import (
    finalize_distribution_options,
    setup_keywords,
)
from tests.conftest import GitRepoHelper


class MockSetuptoolsMetadata:
    def __init__(self) -> None:
        self.version: str | None = None
        self.name: str = "test_pkg"


class MockSetuptoolsDistribution:
    def __init__(self, root: str) -> None:
        self.src_root: str = root
        self.metadata: MockSetuptoolsMetadata = MockSetuptoolsMetadata()
        self.version: str | None = None
        self.gitversioned_config: dict[str, Any] = {}
        self.package_dir: dict[str, str] = {}
        self.packages: list[str] | None = None
        self.py_modules: list[str] = []
        self.package_data: dict[str, list[str]] = {}
        self.editable: bool = False
        self._mock_name: str | None = None

    def get_name(self) -> str:
        return self._mock_name if self._mock_name is not None else "test_pkg"


class TestGitVersionedVersionSource:
    @pytest.mark.sanity
    def test_interface_signature_validation(self) -> None:
        """Validate interface inheritance and plugin metadata."""
        assert issubclass(GitVersionedVersionSource, VersionSourceInterface)
        assert GitVersionedVersionSource.PLUGIN_NAME == "gitversioned"

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("repo_state", "expected_version_prefix"),
        [
            ("clean", "0.1"),
            ("tagged", "1.0"),
            ("dirty", "0.1"),
            ("tagged_dirty", "1.0"),
            ("detached", "1.0"),
            ("shallow", "1.0"),
            ("no_git", "0.1"),
        ],
    )
    def test_invocation(
        self,
        temp_git_repo: GitRepoHelper,
        repo_state: str,
        expected_version_prefix: str,
    ) -> None:
        """Test Hatchling plugin correctly resolves version across repository states."""
        temp_git_repo = temp_git_repo.setup_state(repo_state)

        # Call the plugin logic
        source = GitVersionedVersionSource(root=str(temp_git_repo.path), config={})
        version_data = source.get_version_data()
        assert version_data["version"].startswith(expected_version_prefix)

    @pytest.mark.smoke
    def test_get_version_data_env_override(
        self, temp_git_repo: GitRepoHelper, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test env override short circuits version resolution."""
        monkeypatch.setenv("GITVERSIONED_RESOLVED_VERSION", "3.5.7")
        source = GitVersionedVersionSource(root=str(temp_git_repo.path), config={})
        version_data = source.get_version_data()
        assert version_data == {"version": "3.5.7"}

    @pytest.mark.regression
    def test_set_version_with_source_file(self, temp_git_repo: GitRepoHelper) -> None:
        """Test set_version writes to source file if configured."""
        config_dict = {"version_source_file": "version.txt"}
        source = GitVersionedVersionSource(
            root=str(temp_git_repo.path), config=config_dict
        )
        source.set_version(version="2.4.6", version_data={})

        version_file = temp_git_repo.path / "version.txt"
        assert version_file.exists()
        assert version_file.read_text(encoding="utf-8") == "version=2.4.6\n"

    @pytest.mark.regression
    def test_set_version_no_source_file(
        self, temp_git_repo: GitRepoHelper, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test set_version logs a warning if no source file is configured."""
        source = GitVersionedVersionSource(
            root=str(temp_git_repo.path), config={"version_source_file": None}
        )
        source.set_version(version="2.4.6", version_data={})

        assert "version_source_file is not set; skipping manual update" in caplog.text

    @pytest.mark.sanity
    def test_get_src_root_config(self, temp_git_repo: GitRepoHelper) -> None:
        """Test src_root configuration overrides defaults."""
        config_dict = {"src_root": "custom_src"}
        source = GitVersionedVersionSource(
            root=str(temp_git_repo.path), config=config_dict
        )
        assert source.get_src_root() == temp_git_repo.path / "custom_src"

    @pytest.mark.regression
    def test_get_src_root_packages(self, temp_git_repo: GitRepoHelper) -> None:
        """Test src_root resolved from hatch packages list configuration."""
        pyproject_file = temp_git_repo.path / "pyproject.toml"
        pyproject_file.write_text(
            '[project]\nname = "test_pkg"\nversion = "0.1.0"\n'
            '[tool.hatch.build.targets.wheel]\npackages = ["my_pkg"]\n',
            encoding="utf-8",
        )
        source = GitVersionedVersionSource(root=str(temp_git_repo.path), config={})
        assert source.get_src_root() == temp_git_repo.path / "my_pkg"

    @pytest.mark.regression
    def test_get_src_root_sources(self, temp_git_repo: GitRepoHelper) -> None:
        """Test src_root resolved from hatch sources dict configuration."""
        pyproject_file = temp_git_repo.path / "pyproject.toml"
        pyproject_file.write_text(
            '[project]\nname = "test_pkg"\nversion = "0.1.0"\n'
            '[tool.hatch.build.targets.wheel]\nsources = {"pkg_dir" = ""}\n',
            encoding="utf-8",
        )
        source = GitVersionedVersionSource(root=str(temp_git_repo.path), config={})
        assert source.get_src_root() == temp_git_repo.path / "pkg_dir"

    @pytest.mark.smoke
    def test_get_src_root_default_src_pkg(self, temp_git_repo: GitRepoHelper) -> None:
        """Test src_root resolved using standard src/package_name convention."""
        src_pkg_dir = temp_git_repo.path / "src" / "test_pkg"
        src_pkg_dir.mkdir(parents=True, exist_ok=True)
        source = GitVersionedVersionSource(root=str(temp_git_repo.path), config={})
        assert source.get_src_root() == src_pkg_dir

    @pytest.mark.smoke
    def test_get_src_root_default_pkg(self, temp_git_repo: GitRepoHelper) -> None:
        """Test src_root resolved using standard package_name convention."""
        pkg_dir = temp_git_repo.path / "test_pkg"
        pkg_dir.mkdir(parents=True, exist_ok=True)
        source = GitVersionedVersionSource(root=str(temp_git_repo.path), config={})
        assert source.get_src_root() == pkg_dir

    @pytest.mark.sanity
    def test_get_src_root_fallback(self, temp_git_repo: GitRepoHelper) -> None:
        """Test src_root falls back to project root if no other configuration exists."""
        source = GitVersionedVersionSource(root=str(temp_git_repo.path), config={})
        assert source.get_src_root() == temp_git_repo.path.resolve()

    @pytest.mark.smoke
    def test_hook_registration(self) -> None:
        """Test Hatchling hook registration function returns the plugin class."""
        assert hatch_register_version_source() is GitVersionedVersionSource


class TestSetupKeywords:
    @pytest.mark.smoke
    def test_invocation(self) -> None:
        """Test valid setup_keywords invocation."""
        distribution: Any = MockSetuptoolsDistribution(root=".")
        setup_keywords(distribution, "gitversioned", {"foo": "bar"})
        assert hasattr(distribution, "gitversioned_config")
        assert distribution.gitversioned_config == {"foo": "bar"}

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("attribute", "value", "expected_error"),
        [
            ("wrong_attr", {}, "Unknown keyword argument: wrong_attr"),
            ("gitversioned", "not_a_dict", "gitversioned must be a dict"),
            ("gitversioned", [], "gitversioned must be a dict"),
            ("gitversioned", None, "gitversioned must be a dict"),
        ],
    )
    def test_invalid(self, attribute: str, value: Any, expected_error: str) -> None:
        """Test invalid setup_keywords configurations."""
        distribution: Any = MockSetuptoolsDistribution(root=".")
        with pytest.raises(DistutilsSetupError, match=expected_error):
            setup_keywords(distribution, attribute, value)


class TestFinalizeDistributionOptions:
    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("repo_state", "expected_version_prefix"),
        [
            ("clean", "0.1"),
            ("tagged", "1.0"),
            ("dirty", "0.1"),
            ("tagged_dirty", "1.0"),
            ("detached", "1.0"),
            ("shallow", "1.0"),
            ("no_git", "0.1"),
        ],
    )
    def test_invocation(
        self,
        temp_git_repo: GitRepoHelper,
        repo_state: str,
        expected_version_prefix: str,
    ) -> None:
        """Test Setuptools plugin correctly assigns version to distribution metadata."""
        temp_git_repo = temp_git_repo.setup_state(repo_state)

        distribution: Any = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        distribution.gitversioned_config = {}
        finalize_distribution_options(distribution)

        assert distribution.metadata.version is not None
        assert distribution.metadata.version.startswith(expected_version_prefix)

    @pytest.mark.sanity
    def test_unknown_package_name(self, temp_git_repo: GitRepoHelper) -> None:
        """Test error when package name cannot be determined."""
        distribution: Any = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        distribution.metadata.name = "UNKNOWN"
        distribution._mock_name = "UNKNOWN"
        with pytest.raises(
            DistutilsSetupError, match="Could not determine package name."
        ):
            finalize_distribution_options(distribution)

    @pytest.mark.sanity
    def test_package_dir_empty_string(self, temp_git_repo: GitRepoHelper) -> None:
        """Test rel_src_root extraction using empty string package_dir."""
        distribution: Any = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        distribution.package_dir = {"": "src"}
        finalize_distribution_options(distribution)
        assert distribution.metadata.version

    @pytest.mark.sanity
    def test_package_dir_package_name(self, temp_git_repo: GitRepoHelper) -> None:
        """Test rel_src_root extraction using package_name in package_dir."""
        distribution: Any = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        distribution.package_dir = {"test_pkg": "src/test_pkg"}
        finalize_distribution_options(distribution)
        assert distribution.metadata.version

    @pytest.mark.sanity
    def test_gitversioned_config(self, temp_git_repo: GitRepoHelper) -> None:
        """Test custom gitversioned_config updates kwargs."""
        distribution: Any = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        distribution.gitversioned_config = {"version": "2.0.0"}
        finalize_distribution_options(distribution)
        assert distribution.metadata.version is not None
        assert distribution.metadata.version.startswith("2.0")

    @pytest.mark.smoke
    def test_established_version_metadata(self, temp_git_repo: GitRepoHelper) -> None:
        """Test resolved version is retrieved from distribution metadata version."""
        distribution: Any = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        distribution.metadata.version = "1.2.3"
        finalize_distribution_options(distribution)
        assert distribution.metadata.version == "1.2.3"
        assert distribution.version == "1.2.3"

    @pytest.mark.smoke
    def test_established_version_distribution(
        self, temp_git_repo: GitRepoHelper
    ) -> None:
        """Test resolved version is retrieved from distribution version."""
        distribution: Any = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        distribution.version = "1.2.3"
        finalize_distribution_options(distribution)
        assert distribution.metadata.version == "1.2.3"
        assert distribution.version == "1.2.3"

    @pytest.mark.smoke
    def test_established_version_pkg_info(self, temp_git_repo: GitRepoHelper) -> None:
        """Test resolved version is retrieved from PKG-INFO file."""
        pkg_info_file = temp_git_repo.path / "PKG-INFO"
        pkg_info_file.write_text(
            "Metadata-Version: 2.1\nName: test_pkg\nVersion: 1.2.3\n", encoding="utf-8"
        )

        distribution: Any = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        finalize_distribution_options(distribution)
        assert distribution.metadata.version == "1.2.3"
        assert distribution.version == "1.2.3"

    @pytest.mark.regression
    def test_established_version_pkg_info_invalid_read(
        self,
        temp_git_repo: GitRepoHelper,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test error logged if PKG-INFO exists but cannot be read."""
        orig_is_file = Path.is_file
        orig_open = Path.open

        def mock_is_file(self_path: Path) -> bool:
            if self_path.name == "PKG-INFO":
                return True
            return orig_is_file(self_path)

        def mock_open(self_path: Path, *args: Any, **kwargs: Any) -> Any:
            if self_path.name == "PKG-INFO":
                raise PermissionError("Permission denied")
            return orig_open(self_path, *args, **kwargs)

        monkeypatch.setattr(Path, "is_file", mock_is_file)
        monkeypatch.setattr(Path, "open", mock_open)

        distribution: Any = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        finalize_distribution_options(distribution)
        # Should fallback to standard resolution, not raise error, but log a warning
        assert "Failed to read PKG-INFO" in caplog.text
        assert distribution.metadata.version is not None

    @pytest.mark.regression
    def test_established_version_invalid(self, temp_git_repo: GitRepoHelper) -> None:
        """Test invalid established versions are ignored, triggering Git resolution."""
        distribution: Any = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        distribution.version = "UNKNOWN"
        finalize_distribution_options(distribution)
        # Verify Git resolution ran (version string starts with 0.1 rather than UNKNOWN)
        assert distribution.metadata.version != "UNKNOWN"
        assert distribution.metadata.version.startswith("0.1")

    @pytest.mark.smoke
    def test_gitversioned_resolved_version_env(
        self, temp_git_repo: GitRepoHelper, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test GITVERSIONED_RESOLVED_VERSION overrides normal resolution."""
        monkeypatch.setenv("GITVERSIONED_RESOLVED_VERSION", "10.0.1")
        distribution: Any = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        finalize_distribution_options(distribution)
        assert distribution.metadata.version == "10.0.1"

    @pytest.mark.regression
    @pytest.mark.parametrize(
        ("mapping", "expected_src_path"),
        [
            ({"test_pkg": "src/test_pkg"}, "src/test_pkg"),
            ({"test-pkg": "src/test-pkg"}, "src/test-pkg"),
            ({"": "src"}, "src"),
        ],
    )
    def test_get_source_root_mapping(
        self,
        temp_git_repo: GitRepoHelper,
        mapping: dict[str, str],
        expected_src_path: str,
    ) -> None:
        """Test source root resolving matching different package_dir configurations."""
        distribution: Any = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        distribution.package_dir = mapping

        # Create folders so path exists
        src_path = temp_git_repo.path / expected_src_path
        src_path.mkdir(parents=True, exist_ok=True)

        finalize_distribution_options(distribution)
        assert distribution.metadata.version is not None

    @pytest.mark.smoke
    def test_probe_filesystem_context(self, temp_git_repo: GitRepoHelper) -> None:
        """Test probing locates package under src/ when name is UNKNOWN."""
        distribution: Any = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        distribution.metadata.name = "UNKNOWN"
        distribution._mock_name = "UNKNOWN"
        distribution.gitversioned_config = {"output": "src/my_probed_pkg/version.py"}

        probed_pkg_dir = temp_git_repo.path / "src" / "my_probed_pkg"
        probed_pkg_dir.mkdir(parents=True, exist_ok=True)
        (probed_pkg_dir / "__init__.py").write_text("", encoding="utf-8")

        finalize_distribution_options(distribution)
        assert distribution.metadata.version is not None
        # Verify it discovered the package name and version files would write to it
        assert "my_probed_pkg" in distribution.package_data

    @pytest.mark.smoke
    def test_inject_output_into_distribution_package_data(
        self, temp_git_repo: GitRepoHelper
    ) -> None:
        """Test writing inside package folder triggers package_data registration."""
        distribution: Any = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        distribution.gitversioned_config = {"output": "test_pkg/version.py"}

        # Create package dir
        pkg_dir = temp_git_repo.path / "test_pkg"
        pkg_dir.mkdir(exist_ok=True)

        finalize_distribution_options(distribution)
        assert "version.py" in distribution.package_data["test_pkg"]
        assert "test_pkg" in distribution.packages

    @pytest.mark.smoke
    def test_inject_output_into_distribution_py_modules(
        self, temp_git_repo: GitRepoHelper
    ) -> None:
        """Test flat module inside source root triggers py_modules registration."""
        distribution: Any = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        distribution.gitversioned_config = {"output": "version.py"}
        # Ensure no "test_pkg" directory to prevent package_data path detection
        finalize_distribution_options(distribution)
        assert "version" in distribution.py_modules

    @pytest.mark.regression
    def test_inject_output_into_distribution_outside_warning(
        self, temp_git_repo: GitRepoHelper, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test writing output outside package root logs a warning."""
        distribution: Any = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        # Absolute path outside source root (which is temp_git_repo.path)
        outside_path = temp_git_repo.path.parent / "outside_version.py"
        distribution.gitversioned_config = {"output": str(outside_path)}

        finalize_distribution_options(distribution)
        assert "is outside source root" in caplog.text

    @pytest.mark.regression
    def test_unexpected_failure(
        self, temp_git_repo: GitRepoHelper, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test resolution exception gets wrapped as DistutilsSetupError."""

        def mock_resolve(*args: Any, **kwargs: Any) -> Any:
            raise ValueError("Something unexpected broke")

        monkeypatch.setattr(
            setuptools_plugin, "resolve_version_output_to_stream", mock_resolve
        )

        distribution: Any = MockSetuptoolsDistribution(root=str(temp_git_repo.path))
        with pytest.raises(
            DistutilsSetupError,
            match="Failed to resolve version: Something unexpected broke",
        ):
            finalize_distribution_options(distribution)
