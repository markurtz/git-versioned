# Command-Line Interface (CLI) Guide

The `gitversioned` CLI provides a standalone utility to calculate versions, test output formatting, and generate version files. It is useful for integration with languages other than Python, custom build pipelines, and containerized deployments.

______________________________________________________________________

## Subcommands Reference

The CLI is structured into three primary subcommands, which accept any settings field as a command-line parameter (e.g., `--output`, `--version-type`).

### 1. `calculate`

Resolves the project version and outputs only the calculated version string to `stdout`.

```bash
gitversioned calculate [OPTIONS]
```

- **Output:** E.g., `1.0.1.dev20260528+abc1234`
- **Use Case:** Extracting a dynamic version for use in shell scripts.

### 2. `format`

Resolves the version and outputs the rendered text of the configured output strategies to `stdout`. It does not write any files.

```bash
gitversioned format [OPTIONS]
```

- **Output:** Rendered template content.
- **Use Case:** Debugging custom template strings or verifying output format patterns.

### 3. `write`

Resolves the version and writes the rendered output strategy directly to the designated file path (defaults to `version.py`).

```bash
gitversioned write [OPTIONS]
```

- **Output:** Confirmation message printed to `stdout`, and the file written to disk.
- **Use Case:** Generating version files in CI/CD pipelines before packaging.

______________________________________________________________________

## Common CLI Workflows

### Pre-Build Version File Generation

If your project utilizes a build tool that does not natively integrate with Python packaging plugins (e.g., Rust, Go, or a legacy backend), you can run `gitversioned` before starting your compile phase to dump the resolved version into a file:

```bash
# Generate the version file before building the package
gitversioned write --output src/my_package/__version__.py

# Run your build tool
python -m build --wheel
```

To update a version string directly inside a configuration file (like `Cargo.toml` or `pyproject.toml`) in-place before compiling:

```bash
# Inline replace the version in Cargo.toml using the regex strategy
gitversioned write \
  --output Cargo.toml \
  --output-strategies '{"type": "regex", "pattern": "(?s)(\\[package\\].*?^version\\s*=\\s*)\"([^\"]*)\""}'
```

### Docker Build Versioning Integration

When building Docker container images, you can pass the dynamically resolved version as a build argument or environment variable:

```bash
# 1. Resolve version using calculate subcommand
VERSION=$(gitversioned calculate)

# 2. Build the Docker container, passing the version as a build argument
docker build --build-arg APP_VERSION="$VERSION" -t my-app:latest .
```

Inside your `Dockerfile`, you can receive and embed this version metadata:

```dockerfile
FROM python:3.11-slim

# Define build argument
ARG APP_VERSION

# Set environment variable
ENV APP_VERSION=${APP_VERSION}

WORKDIR /app
COPY . .

# Run your application
CMD ["python", "-c", "import os; print(f'Starting app v{os.environ[\"APP_VERSION\"]}')"]
```
