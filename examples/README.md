# GitVersioned Examples

This directory contains practical, runnable demonstrations of how to use GitVersioned in various scenarios. These examples are designed to help you quickly understand core concepts, advanced configurations, and best practices.

## Prerequisites

Before running the examples, ensure you have set up your environment correctly:

1. **Install Dependencies:** Make sure you have installed the core package for your environment and any example-specific requirements.
1. **Environment Variables:** Copy `.env.example` to `.env` if the examples require configuration (e.g., API keys or external services).

> [!NOTE]
> Some examples may require additional dependencies not included in the core `gitversioned` package. Please check the `README.md` within each specific example directory for details.

## Example Index

Below is a curated list of available examples, categorized by complexity:

| Example                                                            | Complexity  | Description                                                           |
| :----------------------------------------------------------------- | :---------- | :-------------------------------------------------------------------- |
| **`[setuptools-version-file/](setuptools-version-file/)`**         | ⭐ Beginner | Setuptools configuration using a version file source.                 |
| **`[setuptools-version-function/](setuptools-version-function/)`** | ⭐ Beginner | Setuptools configuration using a version function source.             |
| **`[setuptools-tool-table/](setuptools-tool-table/)`**             | ⭐ Beginner | Setuptools configuration using `[tool.gitversioned]` table.           |
| **`[setuptools-version-tags/](setuptools-version-tags/)`**         | ⭐ Beginner | Setuptools configuration using Git tags as the version source.        |
| **`[setuptools-version-branch/](setuptools-version-branch/)`**     | ⭐ Beginner | Setuptools configuration using Git branch as the version source.      |
| **`[setuptools-version-commits/](setuptools-version-commits/)`**   | ⭐ Beginner | Setuptools configuration using Git commits as the version source.     |
| **`[setuptools-setup-py/](setuptools-setup-py/)`**                 | ⭐ Beginner | Setuptools configuration using a traditional `setup.py` file.         |
| **`[setuptools-setup-cfg/](setuptools-setup-cfg/)`**               | ⭐ Beginner | Setuptools configuration using a `setup.cfg` file.                    |
| **`[hatchling-version-file/](hatchling-version-file/)`**           | ⭐ Beginner | Hatchling configuration using a version file source.                  |
| **`[hatchling-version-function/](hatchling-version-function/)`**   | ⭐ Beginner | Hatchling configuration using a version function source.              |
| **`[hatchling-hatch-vars/](hatchling-hatch-vars/)`**               | ⭐ Beginner | Hatchling configuration using `[tool.hatch.version]` table variables. |
| **`[hatchling-tool-table/](hatchling-tool-table/)`**               | ⭐ Beginner | Hatchling configuration using `[tool.gitversioned]` table.            |
| **`[hatchling-version-tags/](hatchling-version-tags/)`**           | ⭐ Beginner | Hatchling configuration using Git tags as the version source.         |
| **`[hatchling-version-branch/](hatchling-version-branch/)`**       | ⭐ Beginner | Hatchling configuration using Git branch as the version source.       |
| **`[hatchling-version-commits/](hatchling-version-commits/)`**     | ⭐ Beginner | Hatchling configuration using Git commits as the version source.      |
| **`[cli-stdout-injection/](cli-stdout-injection/)`**               | ⭐ Beginner | CLI version resolution outputting to stdout for Docker injection.     |
| **`[cli-file-injection/](cli-file-injection/)`**                   | ⭐ Beginner | CLI version resolution injecting into Cargo.toml & pyproject.toml.    |
| **`[python-api/](python-api/)`**                                   | ⭐ Beginner | Programmatic usage of the GitVersioned Python API.                    |

<!-- Add new examples to the table above as they are created. -->

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
