#!/usr/bin/env python3
"""Example demonstrating programmatic usage of the GitVersioned python API."""

from gitversioned import Settings, resolve_version
from gitversioned.utils import BuildEnvironment, GitRepository


def main():
    # 1. Initialize GitVersioned Settings
    # You can customize fields, e.g. project_root, output format, version_type, etc.
    settings = Settings(
        package_name="custom_pkg",
        version_type="auto",
    )
    print(f"Initialized Settings: {settings}\n")

    # 2. Instantiate GitRepository and BuildEnvironment helpers
    repository = GitRepository(settings.project_root)
    environment = BuildEnvironment(project_root=settings.project_root)

    print("Checking repository state:")
    print(f"  Is Git repository: {repository.is_available}")
    if repository.is_available:
        print(f"  Current Branch: {repository.current_branch}")
        print(f"  Last Tag: {repository.last_tag}")
        print(f"  Is Dirty: {repository.is_dirty}")
        print(f"  Commit Count: {repository.commit_count}\n")

    # 3. Resolve the PEP 440 version dynamically
    version, _, ref = resolve_version(settings, repository, environment)
    print(f"Resolved version: {version}")
    print(f"Resolved git reference details: {ref}")


if __name__ == "__main__":
    main()
