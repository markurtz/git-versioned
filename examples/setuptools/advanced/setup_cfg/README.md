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

# Setuptools setup.cfg Legacy Example

This example demonstrates how to integrate GitVersioned into projects using a legacy declarative `setup.cfg` configuration file instead of `pyproject.toml`.

## Overview

We define the configuration inside `setup.cfg` under the `[tool:gitversioned]` section. A minimal shim `setup.py` is used to invoke Setuptools' build commands, which automatically loads configuration values from `setup.cfg` via the custom settings parser.

## Prerequisites & Setup

Ensure you are in the virtual environment and have the python build frontends installed:

```bash
.venv/bin/pip install build
```

## Execution Blueprint

To build the package:

```bash
python -m build examples/setuptools/advanced/setup_cfg
```

## Expected Results

Upon completion, you will find a generated python wheel under `dist/` with the correct git tag version resolved:

```text
Successfully built setuptools_setup_cfg-0.2.5-py3-none-any.whl
```

## Troubleshooting

- **Shim setup.py Missing**: Declarative setups using `setup.cfg` still require a minimal `setup.py` importing `setup` to serve as the CLI hook for older build tools.
- **Colon Section Format**: Ensure you write `[tool:gitversioned]` with a colon, as this is the standard syntax for non-setuptools tools within `setup.cfg`.
