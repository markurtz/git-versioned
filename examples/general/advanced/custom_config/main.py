# Copyright 2026 markurtz
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

"""
Runnable example demonstrating the programmatic use of custom settings in GitVersioned.

This script sets up a mock project workspace, initializes a Git repository,
and configures custom version formats and auto-increment strategies using
the python API.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from gitversioned import Settings, resolve_version
from gitversioned.utils import BuildEnvironment, GitRepository

__all__ = [
    "create_sandbox_repo",
    "main",
    "run_git_command",
]


def main() -> None:
    """
    Main entry point for running the custom configuration example.
    """
    print("=== GitVersioned Programmatic Custom Config Example ===")

    # Establish a local sandbox directory within this example folder
    sandbox_dir = tempfile.mkdtemp(prefix="gitversioned_custom_demo_")
    sandbox_path = Path(sandbox_dir)

    try:
        print(f"1. Creating sandbox repository at: {sandbox_path}")
        create_sandbox_repo(sandbox_path)

        # Step 2: Use programmatic API with custom settings
        print("\n2. Invoking resolve_version with customized Settings...")
        settings = Settings(
            project_root=sandbox_path,
            format_main="{version.major}.{version.minor}",
            format_dev="dev{ref.distance_from_head}",
            auto_increment={"dev": "minor"},
            dirty_ignore=["temp_ignored.txt"],
        )
        repository = GitRepository(settings.project_root)
        environment = BuildEnvironment(project_root=settings.project_root)

        # Run resolving tag build
        version_tag, _, _ = resolve_version(
            settings=settings,
            repository=repository,
            environment=environment,
        )
        print(f"Resolved Tagged Version (Custom Format): {version_tag}")

        # Make an extra commit to trigger dev version auto-increment minor settings
        print("\nMaking a commit to trigger dev version auto-increment...")
        run_git_command(sandbox_path, ["commit", "--allow-empty", "-m", "Commit ahead"])

        version_dev, _, _ = resolve_version(
            settings=settings,
            repository=repository,
            environment=environment,
        )
        print(f"Resolved Dev Version (Custom Format & Minor Increment): {version_dev}")

    finally:
        # Clean up the sandbox directory to ensure the workspace remains clean
        if sandbox_path.exists():
            shutil.rmtree(sandbox_path)
            print(f"\n3. Cleaned up sandbox directory: {sandbox_path}")

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

    # Create dummy file to commit
    dummy_file = sandbox_dir / "file.txt"
    dummy_file.write_text("dummy", encoding="utf-8")

    # Commit initial state
    run_git_command(sandbox_dir, ["add", "."])
    run_git_command(sandbox_dir, ["commit", "-m", "Initial commit"])

    # Tag version
    run_git_command(sandbox_dir, ["tag", "v1.2.3"])


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


if __name__ == "__main__":
    main()
