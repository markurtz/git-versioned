# Installation

This page covers all supported installation methods for `{{ project_name }}`.

## Requirements

Before installing, ensure your system meets the following prerequisites:

| Requirement         | Minimum Version | Notes                                 |
| :------------------ | :-------------- | :------------------------------------ |
| **Python**          | 3.10+           | Required for all installation methods |
| **Package Manager** | pip or Hatch    | Required for dependencies             |
| **Git**             | 2.x             | Required for source installs          |
| **Docker**          | 24.x            | Optional — for containerized installs |

## Standard Installation

The recommended way to install `{{ project_name }}` for most users:

```bash
pip install project_name
```

### Verify the Installation

After installation, confirm it is working correctly:

```bash
{{ project_name }} --version
```

You should see output similar to:

```console
{{ project_name }} 0.1.0
```

## Install from Source

To install the latest unreleased code directly from the repository:

```bash
git clone https://github.com/{{ org_name }}/{{ project_name }}.git
cd {{ project_name }}

# Install dependencies for development
# If you are using hatch (recommended):
pipx install hatch
hatch shell

# Or using pip directly:
pip install -e .
```

> [!TIP]
> This is the recommended setup for contributors looking to make changes to the source code.

## Docker Installation

A pre-built Docker image is available for containerized environments:

```bash
# Pull the latest image
docker pull ghcr.io/{{ org_name }}/{{ project_name }}:latest

# Run a one-off command
docker run --rm ghcr.io/{{ org_name }}/{{ project_name }}:latest {{ project_name }} --version
```

For a persistent, volume-mounted setup using Docker Compose, see the `docker-compose.yml` in the root of the repository.

## Platform-Specific Notes

=== "macOS"

```
Python and `pip` or `hatch` work seamlessly on macOS. We recommend using `brew install python` if you need a base Python environment.
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

```bash
pip install --upgrade project_name
```

## Uninstalling

```bash
pip uninstall project_name
```

## Troubleshooting

| Problem                                 | Solution                                                          |
| :-------------------------------------- | :---------------------------------------------------------------- |
| `command not found: {{ project_name }}` | Ensure the binaries directory is on your `$PATH`.                 |
| Import errors after install             | Ensure you have the latest version installed.                     |
| Version conflicts                       | Isolate your dependencies using your language's recommended tool. |

If you continue to experience issues, please visit our [Support page](../community/support.md).

**Next:** [Quick Start →](quickstart.md)
