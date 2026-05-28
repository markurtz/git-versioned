# Setuptools setup.py Integration Example

## Overview

This example demonstrates how to integrate GitVersioned as a setuptools versioning plugin using a traditional `setup.py` build pathway. It shows how configuration overrides can be passed directly as a keyword argument to setuptools' `setup()` function, allowing the build process to dynamically resolve, inject, and write the package version.

## Prerequisites & Setup

Before running this example, ensure you have set up your environment using Hatch:

1. **Activate Environment:** Ensure you are using the active virtual environment containing `gitversioned` and `setuptools`.
   ```bash
   .venv/bin/hatch env create
   ```
1. **Navigate to the Example Directory:**
   ```bash
   cd examples/setuptools_setup_py
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
python -m setuptools_setup_py.main
```

## Expected Results

When you run `python -m build --no-isolation`, Setuptools intercepts the `gitversioned` keyword argument in `setup.py`, calculates the version using the repository's git state, and writes the resolved version to `src/setuptools_setup_py/version.py`.

Console build log output:

```text
* Getting build dependencies for wheel...
* Building wheel...
* Successfully built setuptools_setup_py-0.1.0-py3-none-any.whl
```

When you run the entrypoint script, it prints the resolved dynamic version:

```text
Setuptools Setup.py Example Version: 0.1.0
```

## Troubleshooting

- **ModuleNotFoundError: No module named 'gitversioned'**
  Ensure you are executing inside the activated virtual environment `.venv` or have run the commands using `.venv/bin/python`.
- **DistutilsSetupError: Could not determine package name.**
  This occurs if the source layout cannot be parsed. Verify that the project structure matches the `setup.py` configuration and package modules are situated inside the `src/` directory.
