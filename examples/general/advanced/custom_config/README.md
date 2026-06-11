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

# Programmatic Custom Configuration

This example demonstrates how to supply custom Settings parameters to the GitVersioned programmatic API dynamically.

## Overview

When creating a new `Settings` instance inside your python code, you can pass custom fields directly to the constructor (e.g., `format_main`, `format_dev`, `auto_increment`, `dirty_ignore`). This changes the calculation behavior of the version resolver engine dynamically for that specific execution context.

## Prerequisites & Setup

Ensure you are in the virtual environment and have `gitversioned` installed:

```bash
# Verify active environment has gitversioned
.venv/bin/pip show gitversioned
```

## Execution Blueprint

To run the self-contained demonstration:

```bash
python examples/general/advanced/custom_config/main.py
```

## Expected Results

The script will setup a sandbox git repository, configure custom parameters, commit ahead of the tag, and display stdout logs:

```text
=== GitVersioned Programmatic Custom Config Example ===
1. Creating sandbox repository at: /tmp/gitversioned_custom_demo_xyz

2. Invoking resolve_version with customized Settings...
Resolved Tagged Version (Custom Format): 1.2

Making a commit to trigger dev version auto-increment...
Resolved Dev Version (Custom Format & Minor Increment): 1.3.dev1

3. Cleaned up sandbox directory: /tmp/gitversioned_custom_demo_xyz

=== Example Completed Successfully! ===
```

## Troubleshooting

- **Format String Syntax**: Ensure templates match python's `.format()` format (e.g. `{version.major}`).
- **Pydantic Validation**: Supplying invalid dictionary structures to properties like `auto_increment` will raise Pydantic validation exceptions at runtime.
