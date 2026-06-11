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

# Hatchling Custom Configuration Example

This example demonstrates how to configure customized version segments and dynamic auto-increment behaviors in GitVersioned via the `[tool.gitversioned]` section in `pyproject.toml`.

## Overview

We configure custom version templates in `pyproject.toml` to modify the resolved version formatting:

- `format_main = "{version.major}.{version.minor}"` restricts the core release segment to two digits (e.g. `1.3`).
- `format_dev = "dev{ref.distance_from_head}"` formats development segments as a simple commit distance count (e.g. `dev1`).
- `auto_increment = { dev = "minor" }` forces the package minor version number to increment for development builds when ahead of the tag.

## Prerequisites & Setup

Ensure you are in the virtual environment and have the python build frontends installed:

```bash
.venv/bin/pip install build
```

## Execution Blueprint

To trigger the version calculation and package compilation:

```bash
python -m build examples/hatchling/advanced/custom_config
```

## Expected Results

If you are 1 commit ahead of tag `v1.2.3`, you will see a generated python wheel under `dist/` with the version string `1.3.dev1` resolved:

```text
Successfully built hatchling_custom_config-1.3.dev1-py3-none-any.whl
```

## Troubleshooting

- **Malformed Format String**: Ensure format variables (like `{version.major}` or `{ref.distance_from_head}`) match valid fields on the underlying Version and GitReference models.
- **Pydantic Validation Error**: Ensure properties under `[tool.gitversioned]` match the expected Pydantic settings schema.
