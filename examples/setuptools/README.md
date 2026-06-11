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

# Setuptools Integration Example

This example demonstrates the minimal recommended setup for integrating GitVersioned with the [Setuptools](https://setuptools.pypa.io/en/latest/) build backend. It dynamically resolves the package version from Git metadata (tags) and writes the calculated version to a python module (`src/setuptools_example/version.py`) at build time using the standard `[tool.gitversioned]` configuration block in `pyproject.toml`.

## Advanced Pathways

We also provide the following advanced and legacy setups under the `advanced/` directory:

1. **[Docker Overrides (`advanced/docker_overrides/`)](./advanced/docker_overrides/)**: Illustrates updating version metadata in both the python package and an external `Dockerfile` during the Setuptools build process.
1. **[Custom Configuration Settings (`advanced/custom_config/`)](./advanced/custom_config/)**: Showcases using customized configurations (e.g. customized formats, auto-increment, dirty ignore paths) within `pyproject.toml` for Setuptools.
1. **[Setup.cfg Legacy Setup (`advanced/setup_cfg/`)](./advanced/setup_cfg/)**: Demonstrates declarative packaging integration using a legacy `setup.cfg` configuration file.
1. **[Setup.py Legacy Setup (`advanced/setup_py/`)](./advanced/setup_py/)**: Illustrates imperative packaging integration using a legacy `setup.py` build script.

______________________________________________________________________

## Prerequisites & Setup

Ensure you are in the virtual environment and have the python build frontends installed:

```bash
.venv/bin/pip install build
```

## Execution Blueprint

To build the example package:

```bash
python -m build examples/setuptools
```

## Expected Results

When building the package, Setuptools dynamically invokes GitVersioned to calculate the version and write it to `examples/setuptools/src/setuptools_example/version.py`. You will see output resembling:

```text
* Creating venv isolated environment...
* Installing packages in isolated environment...
* Getting dependencies for wheel...
* Building wheel...
Successfully built setuptools_example-0.2.1-py3-none-any.whl
```

## Troubleshooting

- **ImportError: No module named 'gitversioned'**: Ensure the parent `gitversioned` package is installed in your active environment, or that you are using `--no-isolation` when building locally.
- **Git Repository Not Initialized**: If this folder is built outside of a git repository context, GitVersioned will fall back to a default version of `0.1.0`.
