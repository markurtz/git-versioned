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

# Hatchling Docker Overrides Example

This example demonstrates how to configure GitVersioned and Hatchling to dynamically inject and update version metadata in non-python files, specifically updating a `Dockerfile`'s build arguments in sync with python packaging versions.

## Overview

During the packaging process, Hatchling executes GitVersioned's version resolution. By defining the `tool.gitversioned.overrides.docker` block in `pyproject.toml`, GitVersioned matches target regex patterns in the specified `Dockerfile` to automatically synchronize version strings in-place.

## Prerequisites & Setup

Ensure you are in the virtual environment and have the python build frontends installed:

```bash
.venv/bin/pip install build
```

## Execution Blueprint

To trigger the version override calculation and package compilation:

```bash
python -m build examples/hatchling/advanced/docker_overrides
```

## Expected Results

Upon completion, you will find a generated python wheel under `dist/` and a modified `Dockerfile` with the correct git version injected:

```text
# Excerpt from examples/hatchling/advanced/docker_overrides/Dockerfile
ARG VERSION="0.2.1.dev24"
```

## Troubleshooting

- **Regex Misalignment**: Ensure the regex pattern in `pyproject.toml` matches the exact string structure of `ARG VERSION="..."` in your `Dockerfile` (including quotes and spaces).
- **File Not Written**: Double check that the path in `tool.gitversioned.overrides.docker.output` resolves correctly relative to the project root.
