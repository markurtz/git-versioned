# Apache 2.0 License Copyright Notice (per AGENTS.md requirement)
#
# Copyright 2026 Mark Kurtz
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

"""A self-contained example demonstrating GitVersioned Docker build argument usage."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

__all__ = ["main"]


def main() -> None:
    """Run the end-to-end Docker build argument integration demo.

    This function sets up a sandbox environment containing a dummy repository,
    creates a Dockerfile and a pyproject.toml configuration with custom
    version formats, and executes the gitversioned CLI to resolve version
    strings under different git scenarios (e.g., tagged release vs development).
    """
    print("=== GitVersioned Docker Build Args Example ===")

    # 1. Create a temporary directory for the sandbox
    sandbox_dir = tempfile.mkdtemp(prefix="gitversioned_docker_demo_")
    sandbox_path = Path(sandbox_dir)

    try:
        # 2. Setup the dummy files (Dockerfile and pyproject.toml)
        dockerfile_path = sandbox_path / "Dockerfile"
        pyproject_path = sandbox_path / "pyproject.toml"

        print(f"\nCreating sandbox files in: {sandbox_path}")

        # Write Dockerfile using ARG APP_VERSION
        dockerfile_content = (
            "FROM python:3.11-slim\n\n"
            "# The version of the application passed as a build argument\n"
            "ARG APP_VERSION\n"
            "ENV APP_VERSION=${APP_VERSION}\n\n"
            'LABEL version="${APP_VERSION}"\n\n'
            'CMD ["python", "-c", "import os; '
            'print(f\'Running version {os.environ.get("APP_VERSION")}\')"]\n'
        )
        dockerfile_path.write_text(dockerfile_content, encoding="utf-8")
        print("Created: Dockerfile")

        # Write pyproject.toml with custom gitversioned formatting
        # Here we specify that tag is the source, and define a custom dev format
        pyproject_content = (
            "[project]\n"
            'name = "dummy-app"\n'
            'version = "0.0.0"\n\n'
            "[tool.gitversioned]\n"
            'source_type = ["tag"]\n'
            'format_main = "{version.major}.{version.minor}.{version.micro}"\n'
            'format_dev = "dev{ref.total_commits}"\n'
        )
        pyproject_path.write_text(pyproject_content, encoding="utf-8")
        print("Created: pyproject.toml")

        # 3. Initialize Git repository
        print("\nInitializing Git repository...")
        _run_cmd(["git", "init"], cwd=sandbox_path)
        _run_cmd(
            ["git", "config", "--local", "user.name", "Test User"],
            cwd=sandbox_path,
        )
        _run_cmd(
            ["git", "config", "--local", "user.email", "test@example.com"],
            cwd=sandbox_path,
        )
        # Avoid issues with default branch names (e.g. master vs main)
        _run_cmd(["git", "checkout", "-b", "main"], cwd=sandbox_path)

        # Commit initial files
        _run_cmd(["git", "add", "Dockerfile", "pyproject.toml"], cwd=sandbox_path)
        _run_cmd(["git", "commit", "-m", "Initial commit"], cwd=sandbox_path)

        # 4. Resolve version when no tags exist (default fallback)
        print("\n[Scenario 1] Resolving version with no tags...")
        version_no_tags = _run_gitversioned(["calculate"], cwd=sandbox_path)
        print(f"Calculated Version: '{version_no_tags}'")

        # 5. Tag with a release version
        print("\n[Scenario 2] Tagging repository with v1.2.0...")
        _run_cmd(["git", "tag", "v1.2.0"], cwd=sandbox_path)

        version_tagged = _run_gitversioned(["calculate"], cwd=sandbox_path)
        print(f"Calculated Version: '{version_tagged}'")
        print("Docker Build command blueprint:")
        print(
            f"  docker build --build-arg APP_VERSION={version_tagged} "
            f"-t dummy-app:{version_tagged} .",
        )

        # 6. Make a commit ahead of tag to show dev format
        print("\n[Scenario 3] Making a commit after the tag (Development State)...")
        # Modify Dockerfile slightly
        updated_dockerfile = dockerfile_content + "\n# Extra layer metadata\n"
        dockerfile_path.write_text(updated_dockerfile, encoding="utf-8")
        _run_cmd(["git", "add", "Dockerfile"], cwd=sandbox_path)
        _run_cmd(["git", "commit", "-m", "Update dockerfile comment"], cwd=sandbox_path)

        version_dev = _run_gitversioned(["calculate"], cwd=sandbox_path)
        print(f"Calculated Version (Dev): '{version_dev}'")
        print("Docker Build command blueprint:")
        print(
            f"  docker build --build-arg APP_VERSION={version_dev} -t dummy-app:dev .",
        )

        print("\nDemo completed successfully!")

    finally:
        # Clean up temporary sandbox directory
        shutil.rmtree(sandbox_path)
        print(f"\nCleaned up sandbox: {sandbox_path}")


def _run_cmd(command: list[str], cwd: Path) -> None:
    """Execute a shell command in the specified directory.

    :param command: List of command arguments.
    :param cwd: Directory to run the command in.
    """
    subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        check=True,
    )


def _run_gitversioned(args: list[str], cwd: Path) -> str:
    """Execute the local gitversioned CLI using the current sys.executable.

    :param args: Subcommand and flags for gitversioned.
    :param cwd: Directory to run the command in.
    :return: Stripped stdout output from the CLI execution.
    """
    # Execute as a module to guarantee the current virtualenv's package is utilized
    command = [sys.executable, "-m", "gitversioned.__main__"] + args
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


if __name__ == "__main__":
    main()
