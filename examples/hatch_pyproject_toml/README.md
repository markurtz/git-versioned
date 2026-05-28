# Hatchling pyproject.toml Integration Example

## Overview

This example demonstrates how to integrate GitVersioned as a Hatchling versioning plugin, with configuration specified entirely within a project's `pyproject.toml` file under the `[tool.hatch.version]` section. It shows how the Hatchling build backend dynamically resolves and updates the package version during standard packaging lifecycles (like building a wheel or installing the package).

## Prerequisites & Setup

Before running this example, ensure you have set up your environment using Hatch:

1. **Activate Environment:** Ensure you are using the active virtual environment containing `gitversioned` and `hatchling`.
   ```bash
   .venv/bin/hatch env create
   ```
1. **Navigate to the Example Directory:**
   ```bash
   cd examples/hatch_pyproject_toml
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
python -m hatch_pyproject_toml.main
```

## Expected Results

When you run `python -m build --no-isolation`, Hatchling discovers the GitVersioned entry point, calculates the version using the repository's git tags/state, and writes the calculated version to `src/hatch_pyproject_toml/version.py`.

Console build log output:

```text
* Getting build dependencies for wheel...
* Building wheel...
* Successfully built hatch_pyproject_toml-0.1.0-py3-none-any.whl
```

When you run the entrypoint script, it prints the resolved dynamic version:

```text
Hatchling Example Version: 0.1.0
```

## Troubleshooting

- **ModuleNotFoundError: No module named 'gitversioned'**
  Ensure you are executing inside the activated virtual environment `.venv` or have run the commands using `.venv/bin/python`.
- **Hatchling version calculation failure**
  This occurs if the source layout cannot be parsed or the Git repository has no commits/tags to resolve. Verify that the project structure exactly matches the `pyproject.toml` configuration and packages are situated inside the `src/` directory.
