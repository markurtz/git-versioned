import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import subprocess
import shutil
from tests.conftest import GitRepoHelper

def main():
    # Setup temp path
    temp_dir = Path("scratch/temp_build_test")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Initialize repo helper
    repo = GitRepoHelper(temp_dir)

    # Write pyproject.toml
    pyproject_toml = temp_dir / "pyproject.toml"
    pyproject_toml.write_text(
        "[build-system]\n"
        'requires = ["maturin>=1.0,<2.0", "gitversioned"]\n'
        'build-backend = "gitversioned.integrations.maturin"\n\n'
        "[project]\n"
        'name = "test_pkg"\n'
        'dynamic = ["version"]\n\n'
        "[tool.maturin]\n"
        'bindings = "bin"\n\n'
        "[tool.gitversioned]\n"
        'output = "version.py"\n',
        encoding="utf-8",
    )
    repo.add("pyproject.toml")

    # Write Cargo.toml
    cargo_toml = temp_dir / "Cargo.toml"
    cargo_toml.write_text(
        '[package]\nname = "test_pkg"\nversion = "0.0.0"\nedition = "2021"\n',
        encoding="utf-8",
    )
    repo.add("Cargo.toml")

    # Write main.rs
    src_dir = temp_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    main_rs = src_dir / "main.rs"
    main_rs.write_text('fn main() { println!("Hello!"); }\n', encoding="utf-8")
    repo.add("src/main.rs")

    # Write gitignore
    gitignore = temp_dir / ".gitignore"
    gitignore.write_text(
        "dist/*\ntarget/*\n*.egg-info/\n*.egg-info\n__pycache__/\n*.pyc\n",
        encoding="utf-8",
    )
    repo.add(".gitignore")

    # Commit
    repo.commit("Initial commit")

    # Run build
    build_env = {}
    import os
    build_env.update(os.environ)
    build_env.pop("HATCH_ENV", None)
    build_env.pop("HATCH_ENV_ACTIVE", None)
    venv_bin = str(Path(sys.executable).parent)
    build_env["PATH"] = os.pathsep.join([venv_bin, build_env.get("PATH", "")])

    build_env["PIP_NO_CACHE_DIR"] = "1"
    build_env["PIP_BREAK_SYSTEM_PACKAGES"] = "1"

    print("Running python -m build --no-isolation...")
    res = subprocess.run(
        [sys.executable, "-m", "build", "--no-isolation"],
        cwd=temp_dir,
        capture_output=True,
        text=True,
        env=build_env,
    )

    print(f"Return code: {res.returncode}")
    print("\n--- STDOUT ---")
    print(res.stdout)
    print("\n--- STDERR ---")
    print(res.stderr)

if __name__ == "__main__":
    main()
