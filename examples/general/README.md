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

# General CLI & API Integration Examples

This directory contains examples of using the GitVersioned CLI, programmatic Python API, and general packaging configurations for applications, web apps, and custom workflows.

## Root Example: Dynamic Web Application Versioning

The root folder of this example is a Python web application that exposes a `/version` JSON endpoint. This demonstrates a standard CI/CD workflow: when the web application is built and packaged (using Hatchling in this case), GitVersioned calculates the version and writes it to `src/webapp/version.py`, which is imported by the web app at runtime to serve the active version.

## Advanced Pathways

We also provide the following advanced setups under the `advanced/` directory:

1. **[Docker Build Arguments (`advanced/docker_build_args/`)](./advanced/docker_build_args/)**: Showcases using the GitVersioned CLI to retrieve and format the version string in CI/CD to pass it into Docker image builds as a build argument.
1. **[Regex File Replacement (`advanced/regex_replacement/`)](./advanced/regex_replacement/)**: Demonstrates using the GitVersioned CLI to search-and-replace version markers in arbitrary non-python configuration files in-place using regular expressions.
1. **[Programmatic API Usage (`advanced/api_usage/`)](./advanced/api_usage/)**: Details importing the `gitversioned` package and invoking functions like `resolve_version()` and `resolve_version_output_to_stream()` programmatically in scripts or tooling.
1. **[Custom Configurations (`advanced/custom_config/`)](./advanced/custom_config/)**: Illustrates advanced programmatically loaded CLI setups featuring custom dirty checks, formats, and tags regex mapping.

______________________________________________________________________

## Prerequisites & Setup

Ensure you are in the virtual environment and have the python build frontends installed:

```bash
.venv/bin/pip install build
```

## Execution Blueprint

1. **Build the Webapp Package**:

   ```bash
   python -m build examples/general
   ```

1. **Run the Webapp**:
   To start the server:

   ```bash
   # Run the server from the source tree (the version will fallback to unknown if not built yet)
   PYTHONPATH=examples/general/src python examples/general/src/webapp/main.py
   ```

1. **Query the Version Endpoint**:
   Open a separate shell and request:

   ```bash
   curl http://localhost:8000/version
   ```

## Expected Results

The curl response will return JSON metadata:

```json
{"version": "0.2.1.dev24+02d93d4"}
```

## Troubleshooting

- **Server Already in Use**: If port `8000` is already in use by another service on your system, modify the port parameter inside `main.py` or stop the competing process.
- **Import Error for `webapp`**: Ensure you specify `PYTHONPATH=examples/general/src` so python can locate the local package directory.
