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

# Setuptools Custom Configuration Example

This example demonstrates how to configure customized version templates and automatic minor segment incrementing when using Setuptools.

## Overview

By adding custom keys to the `[tool.gitversioned]` section in `pyproject.toml`, we control version generation:

- `format_main` dictates the base release segment layout (e.g. `{version.major}.{version.minor}`).
- `format_dev` dictates the suffix for development builds.
- `auto_increment` governs which semantic version level increments for development builds (e.g. `minor`).

## Prerequisites & Setup

Ensure you are in the virtual environment and have the python build frontends installed:

```bash
.venv/bin/pip install build
```

## Execution Blueprint

To build the package:

```bash
python -m build examples/setuptools/advanced/custom_config
```

## Expected Results

If you are 1 commit ahead of tag `v1.2.3`, you will see a generated python wheel under `dist/` with the version string `1.3.dev1` resolved:

```text
Successfully built setuptools_custom_config-1.3.dev1-py3-none-any.whl
```

## Troubleshooting

- **Configuration Key Typos**: Ensure setting names conform to the Pydantic settings schema properties (e.g. `auto_increment`, `dirty_ignore`).
- **Build Isolation Issues**: When testing locally, make sure you use `--no-isolation` to reference the active local repository installation of `gitversioned`.
