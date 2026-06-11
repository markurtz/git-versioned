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

# Programmatic Python API Usage

This example demonstrates how to integrate GitVersioned programmatically into custom Python scripts, build workflows, or developer orchestration tools.

## Overview

By importing the `gitversioned` package, you can bypass the command-line interface and invoke the version resolution functions directly:

- `resolve_version()` calculates and returns the semantic `Version` object, version type, and active `GitReference`.
- `resolve_version_output_to_stream()` calculates the version and writes the formatted version string to the target path specified in the `Settings`.

## Prerequisites & Setup

Ensure you are in the virtual environment and have `gitversioned` installed:

```bash
# Verify active environment has gitversioned
.venv/bin/pip show gitversioned
```

## Execution Blueprint

To run the self-contained demonstration:

```bash
python examples/general/advanced/api_usage/main.py
```

## Expected Results

The script will setup a sandbox git repository, calculate the version programmatically, write the output module, and display stdout logs:

```text
=== GitVersioned Programmatic API Example ===
1. Creating sandbox repository at: /tmp/gitversioned_api_demo_xyz

2. Invoking resolve_version API...
Resolved Version: 3.1.2
Version Type: release
Git Reference (Commit SHA): a1b2c3d4...

3. Invoking resolve_version_output_to_stream API...
Successfully wrote version file to: /tmp/gitversioned_api_demo_xyz/version_resolved.py
File Content:
# ...
__version__ = "3.1.2"
# ...

4. Cleaned up sandbox directory: /tmp/gitversioned_api_demo_xyz

=== Example Completed Successfully! ===
```

## Troubleshooting

- **Import Errors**: If you encounter `ImportError: cannot import name 'Settings' from 'gitversioned'`, verify that the parent package has been installed and is active in your current python search paths.
- **Pydantic Validation Warnings**: Ensure that you specify absolute paths for custom `project_root` fields inside the constructor when instantiating `Settings(project_root=...)` programmatically.
