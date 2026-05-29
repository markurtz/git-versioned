# Setuptools pyproject.toml Integration with Dockerfile Overrides

## Overview

This example demonstrates how to integrate GitVersioned as a setuptools versioning plugin, with configuration specified entirely within a project's `pyproject.toml` file under the `[tool.gitversioned]` section. It showcases how to dynamically calculate and update the standard package `version.py` file, as well as replace the version in an external `Dockerfile` using the `overrides` configuration.

## Prerequisites & Setup

Before running this example, ensure you have set up your environment using Hatch:

1. **Activate Environment:** Ensure you are using the active virtual environment containing `gitversioned` and `setuptools`.
   ```bash
   .venv/bin/hatch env create
   ```
1. **Navigate to the Example Directory:**
   ```bash
   cd examples/setuptools_pyproject_overrides
   ```

## Execution Blueprint

You can build the distribution package using Python's standard `build` module. Since the local `gitversioned` package is already installed in your virtual environment, execute the build command with `--no-isolation`:

```bash
python -m build --no-isolation
```

Alternatively, to install the package in editable mode and run its entrypoint script:

```bash
# Install the package locally
pip install --no-build-isolation -e .

# Execute the CLI entrypoint
python -m setuptools_pyproject_overrides.main
```

## Expected Results

When you run `python -m build --no-isolation`, Setuptools discovers the GitVersioned entry point, calculates the version using the repository's git tags/state, and performs the following updates:

1. Writes the calculated version to `src/setuptools_pyproject_overrides/version.py`.
1. Locates `Dockerfile` and updates the `ARG VERSION="0.0.0"` line with the calculated version.

Console build log output:

```text
* Getting build dependencies for wheel...
* Building wheel...
* Successfully built setuptools_pyproject_overrides-0.1.0-py3-none-any.whl
```

When you run the entrypoint script, it prints the resolved dynamic version:

```text
Setuptools Overrides Example Version: 0.1.0
```

And your `Dockerfile` will contain:

```dockerfile
# Simple Dockerfile demonstrating version replacement via GitVersioned overrides
FROM python:3.10-slim

# The version argument will be dynamically replaced by GitVersioned during builds
ARG VERSION="0.1.0"
...
```

## Troubleshooting

- **ModuleNotFoundError: No module named 'gitversioned'**
  Ensure you are executing inside the activated virtual environment `.venv` or have run the commands using `.venv/bin/python`.
- **DistutilsSetupError: Could not determine package name.**
  This occurs if the source layout cannot be parsed. Verify that the project structure exactly matches the `pyproject.toml` configuration and packages are situated inside the `src/` directory.
- **ValueError: Regex pattern not found in output content.**
  This occurs if the `Dockerfile` has been modified and the exact line `ARG VERSION="0.0.0"` (or the format targeted by the regex pattern) is no longer found.
