# GitVersioned Examples

This directory contains practical, runnable demonstrations of how to use GitVersioned in various scenarios. These examples are designed to help you quickly understand core concepts, advanced configurations, and best practices.

## Prerequisites

Before running the examples, ensure you have set up your environment correctly:

1. **Install Dependencies:** Make sure you have installed the core package for your environment and any example-specific requirements.
1. **Environment Variables:** Copy `.env.example` to `.env` if the examples require configuration (e.g., API keys or external services).

> [!NOTE]
> Some examples may require additional dependencies not included in the core `gitversioned` package. Please check the `README.md` within each specific example directory for details.

## Example Index

Below is a curated list of available examples, categorized by build tool and use case:

### Setuptools Examples

| Example                                                                  | Complexity   | Description                                                                         |
| :----------------------------------------------------------------------- | :----------- | :---------------------------------------------------------------------------------- |
| **`[setuptools_pyproject_toml/](setuptools_pyproject_toml/)`**           | Beginner     | Standard Setuptools configuration using `pyproject.toml` and `[tool.gitversioned]`. |
| **`[setuptools_setup_cfg/](setuptools_setup_cfg/)`**                     | Beginner     | Standard Setuptools configuration using a `setup.cfg` file.                         |
| **`[setuptools_setup_py/](setuptools_setup_py/)`**                       | Beginner     | Standard Setuptools configuration using a traditional `setup.py` file.              |
| **`[setuptools_pyproject_overrides/](setuptools_pyproject_overrides/)`** | Intermediate | Setuptools integration with external `Dockerfile` overrides via `pyproject.toml`.   |

### Hatchling Examples

| Example                                              | Complexity | Description                                                                |
| :--------------------------------------------------- | :--------- | :------------------------------------------------------------------------- |
| **`[hatch_pyproject_toml/](hatch_pyproject_toml/)`** | Beginner   | Hatchling configuration using `pyproject.toml` and `[tool.hatch.version]`. |

### Maturin Examples

| Example                                                          | Complexity | Description                                                                                    |
| :--------------------------------------------------------------- | :--------- | :--------------------------------------------------------------------------------------------- |
| **`[maturin_polyglot_overrides/](maturin_polyglot_overrides/)`** | Advanced   | Maturin build backend integration with multi-target overrides (`Cargo.toml` and `Dockerfile`). |

### Command-Line Interface (CLI) Examples

| Example                                                | Complexity | Description                                                                           |
| :----------------------------------------------------- | :--------- | :------------------------------------------------------------------------------------ |
| **`[docker_build_args/](docker_build_args/)`**         | Beginner   | Sourcing and formatting versions for Docker build arguments.                          |
| **`[cli_regex_replacement/](cli_regex_replacement/)`** | Beginner   | Direct, in-place version string replacement in non-python files using regex patterns. |

<!-- Add new examples to the tables above as they are created. -->

## Running the Examples

Most examples can be executed directly from the command line. Navigate to the root of the repository and run the desired script:

```bash
# Example: Running a generic example script
python examples/example_name/main.py
```

> [!TIP]
> **Always run examples from the repository root.** This ensures that all relative paths, environment variables, and module imports resolve correctly.

## Contributing New Examples

We welcome community contributions! If you have a use case that isn't covered, please consider submitting a new example:

1. Create a new directory under `examples/` with a descriptive name.
1. Include a focused, easily digestible script or application.
1. Add a local `README.md` within your example directory explaining what it does and how to run it.
1. Update the **Example Index** table above.

For more details on contributing, please review our [Contributing Guide](../CONTRIBUTING.md).
