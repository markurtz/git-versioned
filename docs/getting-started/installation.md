# Installation

This page covers all supported installation methods for `gitversioned`.

## Requirements

Before installing, ensure your system meets the following prerequisites:

| Requirement         | Minimum Version   | Notes                                 |
| :------------------ | :---------------- | :------------------------------------ |
| **Python**          | 3.10+             | Required for all installation methods |
| **Package Manager** | pip, uv, or Hatch | Required for dependencies             |
| **Git**             | 2.x               | Required for source installs          |
| **Docker**          | 24.x              | Optional — for containerized installs |

## Build Setup (Core Workflow)

`gitversioned` is primarily used as a build plugin. The preferred pathway is to configure it in your `pyproject.toml` utilizing Hatchling or Setuptools.

=== "Hatchling (Preferred)"

````
```toml
[build-system]
requires = ["hatchling", "gitversioned"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "gitversioned"
```
````

=== "Setuptools (pyproject.toml)"

````
```toml
[build-system]
requires = ["setuptools>=61.0", "gitversioned"]
build-backend = "setuptools.build_meta"

[project]
dynamic = ["version"]
```
````

=== "Setuptools (setup.py)"

````
```python
from setuptools import setup

setup(
    setup_requires=["gitversioned"],
    # ...
)
```
````

=== "Setuptools (setup.cfg)"

````
```ini
[options]
setup_requires = gitversioned
```
````

## Standard Installation

To install the standalone CLI for local generation, use `pip` or `uv`:

=== "pip (Standard)"

````
```bash
pip install gitversioned
```
````

=== "uv (Alternative)"

````
```bash
uv pip install gitversioned
```
````

### Verify the Installation

After installation, confirm it is working correctly:

```bash
gitversioned --version
```

You should see output similar to:

```console
gitversioned 0.1.0
```

## Install from Source

To install the latest unreleased code directly from the repository and set up a local development environment:

```bash
git clone https://github.com/markurtz/git-versioned.git
cd git-versioned

# Sync the development environment (installs all groups and extras)
uv sync --all-groups --all-extras

# Or, optionally install specific groups/extras:
uv sync --group dev --extra some_extra
```

> [!TIP]
> This is the recommended setup for contributors looking to make changes to the source code.

## Docker Installation

A pre-built Docker image is available for containerized environments:

```bash
# Pull the latest image
docker pull ghcr.io/markurtz/git-versioned:latest

# Run a one-off command
docker run --rm ghcr.io/markurtz/git-versioned:latest gitversioned --version
```

For a persistent, volume-mounted setup using Docker Compose, see the `docker-compose.yml` in the root of the repository.

## Platform-Specific Notes

=== "macOS"

```
Python, `pip`, and `uv` work seamlessly on macOS. We recommend using `brew install uv` to get started.
```

=== "Linux"

```
Use your distribution's package manager to install Python 3.10+ (e.g., `sudo apt install python3`).
```

=== "Windows"

```
Ensure Python is added to your PATH during the Windows installer setup.
```

## Upgrading

To upgrade an existing installation to the latest release:

=== "pip"

````
```bash
pip install --upgrade gitversioned
```
````

=== "uv"

````
```bash
uv pip install --upgrade gitversioned
```
````

## Uninstalling

=== "pip"

````
```bash
pip uninstall gitversioned
```
````

=== "uv"

````
```bash
uv pip uninstall gitversioned
```
````

## Troubleshooting

| Problem                           | Solution                                                          |
| :-------------------------------- | :---------------------------------------------------------------- |
| `command not found: gitversioned` | Ensure the binaries directory is on your `$PATH`.                 |
| Import errors after install       | Ensure you have the latest version installed.                     |
| Version conflicts                 | Isolate your dependencies using your language's recommended tool. |

If you continue to experience issues, please visit our [Support page](../community/support.md).

**Next:** [Quick Start →](quickstart.md)
