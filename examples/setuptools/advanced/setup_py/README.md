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

# Setuptools setup.py Legacy Example

This example demonstrates how to integrate GitVersioned directly into legacy imperative `setup.py` scripts by passing configuration parameters inline.

## Overview

We define the configuration keys inside the argument dictionary supplied to Setuptools' `setup()` command under the `gitversioned` parameter. The build system hooks into GitVersioned dynamically during compilation to calculate and write version files.

## Prerequisites & Setup

Ensure you are in the virtual environment and have the python build frontends installed:

```bash
.venv/bin/pip install build
```

## Execution Blueprint

To build the package:

```bash
python -m build examples/setuptools/advanced/setup_py
```

## Expected Results

Upon completion, you will find a generated python wheel under `dist/` with the correct version name matching the git tag:

```text
Successfully built setuptools_setup_py-0.2.5-py3-none-any.whl
```

## Troubleshooting

- **Legacy CLI Deprecation Warnings**: Setuptools may emit deprecation warnings when invoking `setup.py` directly; we recommend building via standard build frontends like `python -m build` rather than executing `python setup.py sdist`.
- **Requires-Dist Misalignment**: When passing custom dictionaries, make sure dictionary keys conform to the standard Pydantic schema parameters.
