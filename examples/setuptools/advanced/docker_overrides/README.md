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

# Setuptools Docker Overrides Example

This example demonstrates how to configure GitVersioned and Setuptools to dynamically update version metadata inside a `Dockerfile` during standard packaging.

## Overview

We define the `tool.gitversioned.overrides.docker` block in `pyproject.toml` targeting the project's `Dockerfile`. During version calculation, GitVersioned updates `ARG VERSION="..."` inside the `Dockerfile` with the resolved PEP 440 version.

## Prerequisites & Setup

Ensure you are in the virtual environment and have the python build frontends installed:

```bash
.venv/bin/pip install build
```

## Execution Blueprint

To build the project:

```bash
python -m build examples/setuptools/advanced/docker_overrides
```

## Expected Results

Upon completion, you will find a generated python wheel under `dist/` and a modified `Dockerfile` with the correct git version injected:

```text
# Excerpt from examples/setuptools/advanced/docker_overrides/Dockerfile
ARG VERSION="0.2.1.dev24"
```

## Troubleshooting

- **Pattern Matching Failures**: Ensure the pattern under `[tool.gitversioned.overrides.docker]` matches exactly the string layout inside `Dockerfile`.
- **Target File Relative Resolving**: The output file path is relative to the directory containing the `pyproject.toml` file.
