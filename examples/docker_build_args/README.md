# Docker Build Arguments Example

## Overview

This example demonstrates how to integrate the `gitversioned` CLI within Docker container build pipelines. It showcases how to dynamically calculate version strings directly from git reference metadata (such as releases/tags or commit histories) and supply them as `--build-arg` parameters during image builds, keeping Dockerfiles decoupled from hardcoded version tags.

## Prerequisites & Setup

Before running the example, ensure you have Python 3.10+ and Git installed on your system.

Install `gitversioned` inside a virtual environment:

```bash
# Activate your virtual environment and install the package
pip install gitversioned
```

Ensure `gitversioned` is available in your path:

```bash
gitversioned --version
```

## Execution Blueprint

You can execute the automated demo orchestration script directly:

```bash
python examples/docker_build_args/main.py
```

To run this workflow manually in your own repository:

1. Define a build-time argument `APP_VERSION` inside your `Dockerfile`:
   ```dockerfile
   FROM python:3.11-slim
   ARG APP_VERSION
   ENV APP_VERSION=${APP_VERSION}
   LABEL version="${APP_VERSION}"
   ```
1. Configure custom version formats inside your `pyproject.toml`:
   ```toml
   [tool.gitversioned]
   source_type = ["tag"]
   format_main = "{version.major}.{version.minor}.{version.micro}"
   format_dev = "dev{ref.total_commits}"
   ```
1. Dynamically inject the version when building your Docker image via shell command substitution:
   ```bash
   docker build --build-arg APP_VERSION=$(gitversioned calculate) -t my-app:latest .
   ```

## Expected Results

Running the simulation script `main.py` will produce the following console output:

```text
=== GitVersioned Docker Build Args Example ===

Creating sandbox files in: /tmp/gitversioned_docker_demo_xxxxxx
Created: Dockerfile
Created: pyproject.toml

Initializing Git repository...

[Scenario 1] Resolving version with no tags...
Calculated Version: '0.1.0'

[Scenario 2] Tagging repository with v1.2.0...
Calculated Version: '1.2.0'
Docker Build command blueprint:
  docker build --build-arg APP_VERSION=1.2.0 -t dummy-app:1.2.0 .

[Scenario 3] Making a commit after the tag (Development State)...
Calculated Version (Dev): '1.2.0.dev2'
Docker Build command blueprint:
  docker build --build-arg APP_VERSION=1.2.0.dev2 -t dummy-app:dev .

Demo completed successfully!

Cleaned up sandbox: /tmp/gitversioned_docker_demo_xxxxxx
```

## Troubleshooting

- **No Git Repository Found:** If you get a Git repository validation error, ensure the command is run from within a valid git repository or specify the path explicitly using `--project-root`.
- **Untagged Repository Fallbacks:** If the repository has no tags, the output defaults to the PEP 440 default value `0.1.0` or configuration presets. Use tags (e.g. `git tag v1.0.0`) to define release anchor versions.
- **Dirty Working Tree suffix:** If your git status is dirty (uncommitted changes), `gitversioned` might append a dev tag suffix. Use `--dirty-ignore` or clean your working tree before resolving versions.
