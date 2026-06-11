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

# Hatchling Integration Example

This example demonstrates the minimal recommended setup for integrating GitVersioned with the [Hatchling](https://hatch.pypa.io/latest/) build backend. It dynamically resolves the package version from Git metadata (tags) and writes the calculated version to a python module (`src/hatchling_example/version.py`) at build time.

## Advanced Pathways

We also provide the following advanced setups under the `advanced/` directory:

1. **[Docker Overrides (`advanced/docker_overrides/`)](./advanced/docker_overrides/)**: Demonstrates using Hatchling to update version information in both python packages and external files, such as a `Dockerfile`, during the build lifecycle.
1. **[Custom Configuration Settings (`advanced/custom_config/`)](./advanced/custom_config/)**: Illustrates customizing GitVersioned configuration (e.g. customized pre-release format templates, tag prefixes, and dirty file ignores) inside the `pyproject.toml` file.

______________________________________________________________________

## Prerequisites & Setup

Ensure you have initialized the project environment dependencies:

```bash
# Verify you are in the virtual environment
.venv/bin/pip install build
```

## Execution Blueprint

To build the example package:

```bash
python -m build examples/hatchling
```

## Expected Results

When building the package, the Hatchling backend dynamically invokes GitVersioned to calculate the version and write it to `examples/hatchling/src/hatchling_example/version.py`. You will see output resembling:

```text
* Creating venv isolated environment...
* Installing packages in isolated environment...
* Getting dependencies for wheel...
* Building wheel...
Successfully built hatchling_example-0.2.1.dev24-py3-none-any.whl
```

## Troubleshooting

- **ImportError: No module named 'gitversioned'**: Make sure the parent `gitversioned` package is installed in your active environment, or that you are using `--no-isolation` when building locally if you want to use the local development packages.
- **Git Repository Not Initialized**: If this folder is built outside of a git repository context, GitVersioned will fall back to a default version of `0.1.0`.
