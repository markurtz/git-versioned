import os
import shutil
import subprocess
import sys
from pathlib import Path
from gitversioned.settings import Settings
from gitversioned.utils import GitRepository, BuildEnvironment
from gitversioned.versioning import resolve_version_output_to_stream

def main():
    test_dir = Path("scratch/test_repo")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)

    # Initialize git repo
    subprocess.check_call(["git", "init", "-b", "main"], cwd=test_dir)
    subprocess.check_call(["git", "config", "user.name", "Test User"], cwd=test_dir)
    subprocess.check_call(["git", "config", "user.email", "test@example.com"], cwd=test_dir)

    # Setup dummy project files
    pyproject_path = test_dir / "pyproject.toml"
    pyproject_path.write_text('[project]\nname = "test_pkg"\nversion = "0.1.0"\n', encoding="utf-8")

    setup_py = test_dir / "setup.py"
    setup_py.write_text("from setuptools import setup\n\nsetup()\n", encoding="utf-8")

    setup_cfg = test_dir / "setup.cfg"
    setup_cfg.write_text(
        "[metadata]\n"
        "name = test_pkg\n"
        "version = 0.0.0\n\n"
        "[options]\n"
        "packages = find:\n"
        "package_dir =\n"
        "    = src\n\n"
        "[options.packages.find]\n"
        "where = src\n\n"
        "[tool:gitversioned]\n"
        "output = src/test_pkg/version.py\n",
        encoding="utf-8",
    )

    # Create source structure
    src_dir = test_dir / "src" / "test_pkg"
    src_dir.mkdir(parents=True, exist_ok=True)
    init_file = src_dir / "__init__.py"
    init_file.write_text("from .version import __version__\n", encoding="utf-8")

    gitignore = test_dir / ".gitignore"
    gitignore.write_text(
        "dist/*\n*.egg-info/\n*.egg-info\n__pycache__/\n*.pyc\nbuild/\n",
        encoding="utf-8",
    )

    # Add and commit
    subprocess.check_call(["git", "add", "pyproject.toml", "setup.py", "setup.cfg", "src", ".gitignore"], cwd=test_dir)
    subprocess.check_call(["git", "commit", "-m", "Initial commit"], cwd=test_dir)

    # Tag
    subprocess.check_call(["git", "tag", "v1.5.0"], cwd=test_dir)

    # Run build
    build_env = os.environ.copy()
    build_env.pop("HATCH_ENV", None)
    build_env.pop("HATCH_ENV_ACTIVE", None)
    venv_bin = str(Path(sys.executable).parent)
    build_env["PATH"] = os.pathsep.join([venv_bin, build_env.get("PATH", "")])
    build_env["PIP_NO_CACHE_DIR"] = "1"
    build_env["PIP_BREAK_SYSTEM_PACKAGES"] = "1"
    
    print("--- RUNNING BUILD ---")
    res = subprocess.run(
        [sys.executable, "-m", "build", "--no-isolation"],
        cwd=test_dir,
        capture_output=True,
        text=True,
        env=build_env,
    )
    print("exit code:", res.returncode)
    print("stdout:")
    print(res.stdout)
    print("stderr:")
    print(res.stderr)

    # Check git status
    print("--- GIT STATUS AFTER BUILD ---")
    print(subprocess.check_output(["git", "status", "--porcelain"], cwd=test_dir, text=True))

    # Now check what resolution says
    config_overrides = {}
    kwargs = {
        "package_name": "test_pkg",
        "project_root": test_dir.resolve(),
        "src_root": (test_dir / "src").resolve(),
        "build_is_editable": False,
    }
    kwargs.update(config_overrides)
    settings = Settings(**kwargs)

    repository = GitRepository(settings.project_root)
    environment = BuildEnvironment(project_root=settings.project_root)

    ignore_paths = [
        path
        for raw_path in (
            settings.output,
            settings.version_source_file,
            *settings.dirty_ignore,
        )
        if (path := settings.resolve_path_from_root(raw_path)) is not None
    ]
    print("--- RESOLUTION INFO ---")
    print("ignore_paths:", ignore_paths)
    print("dirty_files:", repository.dirty_files)
    print("filtered_dirty_files:", repository.filtered_dirty_files(ignore_paths=ignore_paths))

if __name__ == "__main__":
    main()
