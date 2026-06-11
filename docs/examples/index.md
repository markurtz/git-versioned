# Examples

This section contains runnable code examples that demonstrate real-world usage of GitVersioned. Each example is self-contained and can be copied directly into your own project.

> [!NOTE]
> All examples assume you have completed [Installation](../getting-started/installation.md).

## Example Index

Below is a curated list of available examples, categorized by build tool and use case:

### Hatchling Examples

| Example                                                                                                                          | Complexity   | Description                                                                               |
| :------------------------------------------------------------------------------------------------------------------------------- | :----------- | :---------------------------------------------------------------------------------------- |
| [Hatchling Root Example](https://github.com/markurtz/git-versioned/tree/main/examples/hatchling/)                                | Beginner     | Standard Hatchling configuration using `pyproject.toml` and `[tool.hatch.version]`.       |
| [Hatchling Docker Overrides](https://github.com/markurtz/git-versioned/tree/main/examples/hatchling/advanced/docker_overrides/)  | Intermediate | Dynamic versioning featuring external `Dockerfile` overrides during build.                |
| [Hatchling Custom Configuration](https://github.com/markurtz/git-versioned/tree/main/examples/hatchling/advanced/custom_config/) | Intermediate | Dynamic versioning showcasing custom pre-release templates and auto-increment strategies. |

### Setuptools Examples

| Example                                                                                                                                                  | Complexity   | Description                                                                                |
| :------------------------------------------------------------------------------------------------------------------------------------------------------- | :----------- | :----------------------------------------------------------------------------------------- |
| [Setuptools Root Example](https://github.com/markurtz/git-versioned/tree/main/examples/setuptools/)                                                      | Beginner     | Standard Setuptools configuration using `pyproject.toml` and `[tool.gitversioned]`.        |
| [Setuptools Configuration via setup.cfg](https://github.com/markurtz/git-versioned/tree/main/examples/setuptools/advanced/setup_cfg/)                    | Beginner     | Standard Setuptools configuration using a legacy `setup.cfg` file.                         |
| [Setuptools Configuration via setup.py](https://github.com/markurtz/git-versioned/tree/main/examples/setuptools/advanced/setup_py/)                      | Beginner     | Standard Setuptools configuration using a traditional legacy `setup.py` file.              |
| [Setuptools Configuration with Dockerfile Overrides](https://github.com/markurtz/git-versioned/tree/main/examples/setuptools/advanced/docker_overrides/) | Intermediate | Setuptools integration with external `Dockerfile` overrides via `pyproject.toml`.          |
| [Setuptools Custom Configuration](https://github.com/markurtz/git-versioned/tree/main/examples/setuptools/advanced/custom_config/)                       | Intermediate | Custom Setuptools config overrides featuring customized dirty ignoral rules and templates. |

### Maturin Examples

| Example                                                                                                                                            | Complexity   | Description                                                                                     |
| :------------------------------------------------------------------------------------------------------------------------------------------------- | :----------- | :---------------------------------------------------------------------------------------------- |
| [Maturin Root Example](https://github.com/markurtz/git-versioned/tree/main/examples/maturin/)                                                      | Beginner     | Minimal Rust/Python polyglot extension using Maturin and `gitversioned.plugins.maturin_plugin`. |
| [Maturin Polyglot Configuration with Overrides](https://github.com/markurtz/git-versioned/tree/main/examples/maturin/advanced/polyglot_overrides/) | Advanced     | Maturin build backend integration with multi-target overrides (`Cargo.toml` and `Dockerfile`).  |
| [Maturin Custom Configuration](https://github.com/markurtz/git-versioned/tree/main/examples/maturin/advanced/custom_config/)                       | Intermediate | Maturin configuration specifying custom tag formatting and Rust-specific settings.              |

### General (CLI & API) Examples

| Example                                                                                                                             | Complexity   | Description                                                                             |
| :---------------------------------------------------------------------------------------------------------------------------------- | :----------- | :-------------------------------------------------------------------------------------- |
| [General Web App (CI/CD) Example](https://github.com/markurtz/git-versioned/tree/main/examples/general/)                            | Beginner     | Python web app serving its dynamic Git-resolved version from an endpoint.               |
| [Docker Build Argument Injection](https://github.com/markurtz/git-versioned/tree/main/examples/general/advanced/docker_build_args/) | Beginner     | Sourcing and formatting dynamic versions to inject as Docker container build arguments. |
| [In-place File Update via Regex](https://github.com/markurtz/git-versioned/tree/main/examples/general/advanced/regex_replacement/)  | Beginner     | Direct, in-place version string replacement in non-python files using regex patterns.   |
| [Programmatic API Usage](https://github.com/markurtz/git-versioned/tree/main/examples/general/advanced/api_usage/)                  | Beginner     | Programmatic version resolution and output writing using the public python package API. |
| [Programmatic Custom Configuration](https://github.com/markurtz/git-versioned/tree/main/examples/general/advanced/custom_config/)   | Intermediate | Programmatic API usage applying custom dirty checks, formats, and auto-increment.       |

!!! tip "Contributing an Example"
Have a useful snippet or pattern to share? See the [Contributing Guide](../community/contributing.md) to learn how to add a new example to this section.
