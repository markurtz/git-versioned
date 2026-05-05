from __future__ import annotations

import ast
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from tests.integration.conftest import GitRepoHelper


def _write_hatch_config(repo: GitRepoHelper) -> None:
    pkg_dir = repo.path / "src" / "test_pkg"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "__init__.py").touch()
    (repo.path / "version.txt").write_text("0.1.0")
    pyproject_path = repo.path / "pyproject.toml"
    
    # Get the project root of gitversioned
    project_root = Path(__file__).resolve().parent.parent.parent
    
    pyproject_path.write_text(
        f"""[build-system]
requires = ["hatchling", "gitversioned @ file://{project_root}"]
build-backend = "hatchling.build"

[project]
name = "test_pkg"
dynamic = ["version"]

[tool.hatch.version]
source = "gitversioned"
""",
        encoding="utf-8",
    )


def _write_setuptools_config(repo: GitRepoHelper) -> None:
    pkg_dir = repo.path / "src" / "test_pkg"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "__init__.py").touch()
    (repo.path / "version.txt").write_text("0.1.0")
    pyproject_path = repo.path / "pyproject.toml"
    
    # Get the project root of gitversioned
    project_root = Path(__file__).resolve().parent.parent.parent
    
    pyproject_path.write_text(
        f"""[build-system]
requires = ["setuptools>=61.0.0", "wheel", "gitversioned @ file://{project_root}"]
build-backend = "setuptools.build_meta"

[project]
name = "test_pkg"
dynamic = ["version"]
""",
        encoding="utf-8",
    )


@pytest.mark.regression
class TestBuilds:
    """E2E Tests for GitVersioned build processes."""

    @pytest.mark.parametrize(
        ("repo_state", "expected_version_prefix"),
        [
            ("clean", "0.1.0"),
            ("tagged", "1.0.0"),
            ("dirty", "0.1.0"),
            ("detached", "1.0.0"),
            ("shallow", "1.0.0"),
        ],
    )
    @pytest.mark.parametrize("builder", ["hatchling", "setuptools"])
    def test_build_version_generation(
        self,
        e2e_git_repo: GitRepoHelper,
        repo_state: str,
        expected_version_prefix: str,
        builder: str,
    ) -> None:
        """Test the end-to-end build process generates the correct version in the wheel."""
        # Setup builder specific config
        if builder == "hatchling":
            _write_hatch_config(e2e_git_repo)
        else:
            _write_setuptools_config(e2e_git_repo)

        # Setup git state
        if repo_state != "clean":
            e2e_git_repo.commit("First commit")
        if repo_state in {"tagged", "detached", "shallow"}:
            e2e_git_repo.tag("v1.0.0")
        if repo_state == "dirty":
            e2e_git_repo.dirty()
        if repo_state == "detached":
            e2e_git_repo.checkout_detached()
        if repo_state == "shallow":
            clone_path = e2e_git_repo.path.with_name(
                e2e_git_repo.path.name + "_shallow"
            )
            e2e_git_repo = e2e_git_repo.shallow_clone(clone_path)
            if builder == "hatchling":
                _write_hatch_config(e2e_git_repo)
            else:
                _write_setuptools_config(e2e_git_repo)

        # Ensure git identity is available to gitversioned if needed
        # (Though GitRepoHelper already sets it during init)

        # Run the build process
        # We use python -m build --wheel
        # The build environment will be isolated and will install gitversioned from the source tree
        result = subprocess.run(
            [sys.executable, "-m", "build", "--wheel"],
            cwd=str(e2e_git_repo.path),
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, f"Build failed: {result.stdout}\n{result.stderr}"

        # Find the generated wheel
        dist_dir = e2e_git_repo.path / "dist"
        wheels = list(dist_dir.glob("*.whl"))
        assert len(wheels) == 1, f"Expected 1 wheel, found {len(wheels)}.\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        wheel_path = wheels[0]

        # The wheel filename contains the version: test_pkg-VERSION-py3-none-any.whl
        wheel_name = wheel_path.name
        version_part = wheel_name.split("-")[1]
        
        assert version_part.startswith(expected_version_prefix), f"Expected version {expected_version_prefix}, got {version_part}.\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"

        # Verify the version file was created and contains correct data if we expect it to
        # By default gitversioned creates src/test_pkg/version.py
        version_file = e2e_git_repo.path / "src" / "test_pkg" / "version.py"
        assert version_file.exists(), f"Version file not found at {version_file}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"

        # Introspect the version file safely
        tree = ast.parse(version_file.read_text(encoding="utf-8"))
        version_dict = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name):
                    if isinstance(node.value, ast.Constant):
                        version_dict[target.id] = node.value.value
                    elif isinstance(node.value, ast.Tuple):
                        version_dict[target.id] = tuple(
                            elt.value for elt in node.value.elts if isinstance(elt, ast.Constant)
                        )

        assert "__version__" in version_dict, f"__version__ not found in version_dict: {version_dict}"
        assert version_dict["__version__"].startswith(expected_version_prefix), f"Expected __version__ to start with {expected_version_prefix}, got {version_dict['__version__']}"
