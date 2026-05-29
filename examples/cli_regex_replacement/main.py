"""
Runnable example demonstrating the use of the GitVersioned CLI regex strategy.

This script sets up a mock project workspace with custom configuration, initializes
a local Git repository, creates a version file and configuration files, and applies
the GitVersioned CLI with regex-based replacement rules to update version markers.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

__all__ = [
    "create_sandbox_repo",
    "main",
    "run_git_command",
    "run_gitversioned_cli",
]


def main() -> None:
    """
    Main entry point for running the CLI regex replacement example.
    """
    print("=== GitVersioned CLI Regex-Based Replacement Example ===")

    # Establish a local sandbox directory within this example folder
    example_root = Path(__file__).parent.resolve()
    sandbox_dir = example_root / "sandbox"

    try:
        # Clean up any residual sandbox directory
        if sandbox_dir.exists():
            shutil.rmtree(sandbox_dir)

        print(f"1. Creating sandbox repository at: {sandbox_dir}")
        create_sandbox_repo(sandbox_dir)

        # Verify initial files
        pyproject_file = sandbox_dir / "pyproject.toml"
        init_file = sandbox_dir / "src" / "my_app" / "__init__.py"

        print("\n=== Initial File States ===")
        print("pyproject.toml version line:")
        print(pyproject_file.read_text(encoding="utf-8").strip())
        print("src/my_app/__init__.py version line:")
        print(init_file.read_text(encoding="utf-8").strip())

        # Step 2: Run GitVersioned CLI to update pyproject.toml
        print("\n2. Executing GitVersioned CLI to update pyproject.toml...")
        pyproject_strategy = {
            "type": "regex",
            "pattern": r"(?m)^version\s*=\s*\"(?P<version>.*?)\"",
        }

        run_gitversioned_cli(
            project_root=sandbox_dir,
            output_file=Path("pyproject.toml"),
            strategy=pyproject_strategy,
            version_type="release",
        )

        # Step 3: Run GitVersioned CLI to update src/my_app/__init__.py
        print("\n3. Executing GitVersioned CLI to update src/my_app/__init__.py...")
        init_strategy = {
            "type": "regex",
            "pattern": r"(?m)^__version__\s*=\s*\"(?P<version>.*?)\"",
        }

        run_gitversioned_cli(
            project_root=sandbox_dir,
            output_file=Path("src/my_app/__init__.py"),
            strategy=init_strategy,
            version_type="release",
        )

        # Verify final files after updates
        print("\n=== Updated File States ===")
        print("pyproject.toml updated:")
        print(pyproject_file.read_text(encoding="utf-8").strip())
        print("src/my_app/__init__.py updated:")
        print(init_file.read_text(encoding="utf-8").strip())

    finally:
        # Clean up the sandbox directory to ensure the repository remains clean
        if sandbox_dir.exists():
            shutil.rmtree(sandbox_dir)
            print(f"\n4. Cleaned up sandbox directory: {sandbox_dir}")

    print("\n=== Example Completed Successfully! ===")


def create_sandbox_repo(sandbox_dir: Path) -> None:
    """
    Initialize a Git repository and write initial files within the sandbox.

    :param sandbox_dir: The path to the sandbox directory.
    """
    sandbox_dir.mkdir(parents=True, exist_ok=True)

    # Initialize git repo
    run_git_command(sandbox_dir, ["init"])
    run_git_command(sandbox_dir, ["config", "user.name", "Example Runner"])
    run_git_command(sandbox_dir, ["config", "user.email", "runner@example.com"])
    run_git_command(sandbox_dir, ["config", "init.defaultBranch", "main"])

    # Create initial directories
    app_dir = sandbox_dir / "src" / "my_app"
    app_dir.mkdir(parents=True, exist_ok=True)

    # Create pyproject.toml
    pyproject_content = '[project]\nname = "my-awesome-app"\nversion = "0.0.0"\n'
    pyproject_file = sandbox_dir / "pyproject.toml"
    pyproject_file.write_text(pyproject_content, encoding="utf-8")

    # Create __init__.py
    init_content = '"""My Awesome Application module."""\n__version__ = "0.0.0"\n'
    init_file = app_dir / "__init__.py"
    init_file.write_text(init_content, encoding="utf-8")

    # Commit initial state
    run_git_command(sandbox_dir, ["add", "."])
    run_git_command(sandbox_dir, ["commit", "-m", "Initial commit of project files"])

    # Tag version
    run_git_command(sandbox_dir, ["tag", "v2.5.4"])


def run_git_command(repo_path: Path, args: list[str]) -> None:
    """
    Helper to execute a Git command inside the sandbox repository.

    :param repo_path: Path to the target Git repository workspace.
    :param args: List of CLI arguments to pass to the git executable.
    """
    subprocess.run(
        ["git"] + args,
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )


def run_gitversioned_cli(
    project_root: Path,
    output_file: Path,
    strategy: dict[str, str],
    version_type: str,
) -> None:
    """
    Invoke the GitVersioned CLI write subcommand using subprocess.

    :param project_root: Root directory of the repository to update.
    :param output_file: Target relative path of the file to write/edit.
    :param strategy: Output replacement strategy dictionary.
    :param version_type: Target version resolution type (e.g., release, dev).
    """
    cli_args = [
        sys.executable,
        "-m",
        "gitversioned",
        "write",
        "--project-root",
        str(project_root),
        "--src-root",
        str(project_root),
        "--output",
        str(output_file),
        "--version-type",
        version_type,
        "--output-strategies",
        json.dumps(strategy),
    ]

    result = subprocess.run(
        cli_args,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        print(f"Error executing CLI: {result.stderr}")
        raise RuntimeError(
            f"GitVersioned CLI failed with exit code {result.returncode}"
        )

    print(result.stdout.strip())


if __name__ == "__main__":
    main()
