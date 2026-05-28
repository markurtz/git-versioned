# Examples

This section contains runnable code examples that demonstrate real-world usage of GitVersioned. Each example is self-contained and can be copied directly into your own project.

> [!NOTE]
> All examples assume you have completed [Installation](../getting-started/installation.md).

## Example Index

Below is a curated list of available examples, categorized by build tool and use case:

### Setuptools Examples

| Example                                                                                                                                            | Complexity   | Description                                                                         |
| :------------------------------------------------------------------------------------------------------------------------------------------------- | :----------- | :---------------------------------------------------------------------------------- |
| [Setuptools Configuration via pyproject.toml](https://github.com/markurtz/git-versioned/tree/main/examples/setuptools_pyproject_toml/)             | Beginner     | Standard Setuptools configuration using `pyproject.toml` and `[tool.gitversioned]`. |
| [Setuptools Configuration via setup.cfg](https://github.com/markurtz/git-versioned/tree/main/examples/setuptools_setup_cfg/)                       | Beginner     | Standard Setuptools configuration using a `setup.cfg` file.                         |
| [Setuptools Configuration via setup.py](https://github.com/markurtz/git-versioned/tree/main/examples/setuptools_setup_py/)                         | Beginner     | Standard Setuptools configuration using a traditional `setup.py` file.              |
| [Setuptools Configuration with Dockerfile Overrides](https://github.com/markurtz/git-versioned/tree/main/examples/setuptools_pyproject_overrides/) | Intermediate | Setuptools integration with external `Dockerfile` overrides via `pyproject.toml`.   |

### Hatchling Examples

| Example                                                                                                                          | Complexity | Description                                                                |
| :------------------------------------------------------------------------------------------------------------------------------- | :--------- | :------------------------------------------------------------------------- |
| [Hatchling Configuration via pyproject.toml](https://github.com/markurtz/git-versioned/tree/main/examples/hatch_pyproject_toml/) | Beginner   | Hatchling configuration using `pyproject.toml` and `[tool.hatch.version]`. |

### Maturin Examples

| Example                                                                                                                                   | Complexity | Description                                                                                    |
| :---------------------------------------------------------------------------------------------------------------------------------------- | :--------- | :--------------------------------------------------------------------------------------------- |
| [Maturin Polyglot Configuration with Overrides](https://github.com/markurtz/git-versioned/tree/main/examples/maturin_polyglot_overrides/) | Advanced   | Maturin build backend integration with multi-target overrides (`Cargo.toml` and `Dockerfile`). |

### Command-Line Interface (CLI) Examples

| Example                                                                                                               | Complexity | Description                                                                           |
| :-------------------------------------------------------------------------------------------------------------------- | :--------- | :------------------------------------------------------------------------------------ |
| [Docker Build Argument Injection](https://github.com/markurtz/git-versioned/tree/main/examples/docker_build_args/)    | Beginner   | Sourcing and formatting versions for Docker build arguments.                          |
| [In-place File Update via Regex](https://github.com/markurtz/git-versioned/tree/main/examples/cli_regex_replacement/) | Beginner   | Direct, in-place version string replacement in non-python files using regex patterns. |

!!! tip "Contributing an Example"
Have a useful snippet or pattern to share? See the [Contributing Guide](../community/contributing.md) to learn how to add a new example to this section.
