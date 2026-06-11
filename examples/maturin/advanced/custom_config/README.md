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

# Maturin Custom Configuration Example

This example demonstrates how to configure customized version string formatting templates and minor segment auto-incrementing when packaging a Rust/Python polyglot extension using Maturin.

## Overview

By customizing keys in the `[tool.gitversioned]` section in `pyproject.toml`, we control version generation:

- `format_main` dictates the base release segment layout (e.g. `{version.major}.{version.minor}`).
- `format_dev` dictates the suffix for development builds.
- `auto_increment` governs which semantic version level increments for development builds (e.g. `minor`).

## Prerequisites & Setup

Ensure you are in the virtual environment and have the python build frontends installed:

```bash
.venv/bin/pip install build
```

## Execution Blueprint

To compile the package:

```bash
python -m build examples/maturin/advanced/custom_config
```

## Expected Results

If you are 1 commit ahead of tag `v1.2.3`, you will see a generated python wheel under `dist/` with the version string `1.3.dev1` resolved:

```text
Successfully built maturin_custom_config-1.3.dev1-py3-none-any.whl
```

## Troubleshooting

- **Rust Compilation Failures**: Building this package requires Rust compiler toolchains (`cargo`/`rustc`). Make sure they are installed on your path.
- **Pydantic Validation Errors**: Ensure properties specified under `[tool.gitversioned]` conform exactly to the settings parameters.
