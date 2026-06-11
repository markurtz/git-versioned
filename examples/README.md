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

Unless otherwise noted, all files in this directory and its subdirectories
are licensed under the Apache License, Version 2.0.
-->

# GitVersioned Examples

This directory contains practical, runnable demonstrations of how to use GitVersioned in various scenarios. These examples are designed to help you quickly understand core concepts, advanced configurations, and best practices.

## Prerequisites

Before running the examples, ensure you have set up your environment correctly:

1. **Install Dependencies:** Make sure you have installed the core `gitversioned` package in your environment.
1. **Setup virtualenv:** We recommend running inside the project's virtual environment (`.venv`).

## Example Index

Below is a curated list of available examples, categorized by entrypoint type and use case:

### 1. [Hatchling Examples](./hatchling/)

| Location                                                                             | Type     | Complexity   | Description                                                                               |
| :----------------------------------------------------------------------------------- | :------- | :----------- | :---------------------------------------------------------------------------------------- |
| **`[hatchling/](./hatchling/)`**                                                     | Root     | Beginner     | Standard Hatchling configuration using `pyproject.toml` with version source hooks.        |
| **`[hatchling/advanced/docker_overrides/](./hatchling/advanced/docker_overrides/)`** | Advanced | Intermediate | Dynamic versioning featuring external `Dockerfile` overrides during build.                |
| **`[hatchling/advanced/custom_config/](./hatchling/advanced/custom_config/)`**       | Advanced | Intermediate | Dynamic versioning showcasing custom pre-release templates and auto-increment strategies. |

### 2. [Setuptools Examples](./setuptools/)

| Location                                                                               | Type     | Complexity   | Description                                                                                |
| :------------------------------------------------------------------------------------- | :------- | :----------- | :----------------------------------------------------------------------------------------- |
| **`[setuptools/](./setuptools/)`**                                                     | Root     | Beginner     | Standard Setuptools configuration using `pyproject.toml` and `[tool.gitversioned]`.        |
| **`[setuptools/advanced/setup_cfg/](./setuptools/advanced/setup_cfg/)`**               | Advanced | Beginner     | Declarative Setuptools configuration using legacy `setup.cfg` parameters.                  |
| **`[setuptools/advanced/setup_py/](./setuptools/advanced/setup_py/)`**                 | Advanced | Beginner     | Imperative Setuptools configuration using legacy `setup.py` parameter dictionary passing.  |
| **`[setuptools/advanced/docker_overrides/](./setuptools/advanced/docker_overrides/)`** | Advanced | Intermediate | Setuptools integration featuring external `Dockerfile` overrides via `pyproject.toml`.     |
| **`[setuptools/advanced/custom_config/](./setuptools/advanced/custom_config/)`**       | Advanced | Intermediate | Custom Setuptools config overrides featuring customized dirty ignoral rules and templates. |

### 3. [Maturin Examples](./maturin/)

| Location                                                                             | Type     | Complexity   | Description                                                                                         |
| :----------------------------------------------------------------------------------- | :------- | :----------- | :-------------------------------------------------------------------------------------------------- |
| **`[maturin/](./maturin/)`**                                                         | Root     | Beginner     | Minimal Rust/Python polyglot extension using Maturin and `gitversioned.plugins.maturin_plugin`.     |
| **`[maturin/advanced/polyglot_overrides/](./maturin/advanced/polyglot_overrides/)`** | Advanced | Advanced     | Maturin build backend integration featuring multi-target overrides (`Cargo.toml` and `Dockerfile`). |
| **`[maturin/advanced/custom_config/](./maturin/advanced/custom_config/)`**           | Advanced | Intermediate | Maturin configuration specifying custom tag formatting and Rust-specific settings.                  |

### 4. [General (CLI & API) Examples](./general/)

| Location                                                                           | Type     | Complexity   | Description                                                                                       |
| :--------------------------------------------------------------------------------- | :------- | :----------- | :------------------------------------------------------------------------------------------------ |
| **`[general/](./general/)`**                                                       | Root     | Beginner     | Python web app (CI/CD) serving its dynamic Git-resolved version from an endpoint.                 |
| **`[general/advanced/docker_build_args/](./general/advanced/docker_build_args/)`** | Advanced | Beginner     | Sourcing and formatting dynamic versions to inject as Docker container build arguments.           |
| **`[general/advanced/regex_replacement/](./general/advanced/regex_replacement/)`** | Advanced | Beginner     | In-place version string replacements in non-Python config files using the CLI and regex patterns. |
| **`[general/advanced/api_usage/](./general/advanced/api_usage/)`**                 | Advanced | Beginner     | Programmatic version resolution and output writing using the public python package API.           |
| **`[general/advanced/custom_config/](./general/advanced/custom_config/)`**         | Advanced | Intermediate | Programmatic API usage applying custom dirty checks, formats, and auto-increment.                 |

______________________________________________________________________

## Running the Examples

Each example directory contains standard build configurations. You can build and package the example projects (which automatically triggers version calculation) using standard frontends:

```bash
# Example: Build an example package using the build frontend
python -m build examples/setuptools
```

You can also run the E2E verification test suite, which automatically validates that all examples build and execute correctly:

```bash
# Run E2E verification tests for all examples
.venv/bin/hatch run project:tests-e2e
```

> [!TIP]
> **Always run example commands from the repository root.** This ensures that relative paths, python modules, and configurations resolve correctly.
