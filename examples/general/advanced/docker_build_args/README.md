<!--
Copyright 2026 markurtz

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# Docker Build Argument Version Injection

This example demonstrates how to use the GitVersioned CLI to dynamically calculate the package version and inject it as a build argument (`--build-arg`) during a Docker image build.

## Overview

In CI/CD pipelines, you can run the GitVersioned CLI subcommand `gitversioned calculate` to get the resolved semantic version. You can then pipe or assign this string directly into a shell variable and pass it to your Docker daemon to tag the image and build metadata.

## Prerequisites & Setup

Ensure you are in the virtual environment and have `gitversioned` installed:

```bash
# Verify active environment has gitversioned
.venv/bin/gitversioned --help
```

## Execution Blueprint

To run the self-contained demonstration:

```bash
python examples/general/advanced/docker_build_args/main.py
```

## Expected Results

The demo script runs a full mock sequence (initializing a repository, committing files, tagging, and running `calculate`). The script will output logs like:

```text
=== GitVersioned Docker Build Args Example ===

Creating sandbox files in: /tmp/gitversioned_docker_demo_xyz

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
```

## Troubleshooting

- **Tag Format Issues**: By default, GitVersioned expects tags to start with `v` (e.g. `v1.0.0`). If your tags do not contain a `v`, adjust the `regex_tag` settings inside `pyproject.toml`.
- **Dirty Tree Warnings**: If files are modified but uncommitted, GitVersioned will detect a dirty workspace and resolve version as a development (`dev`) release.
