# Command-Line Interface (CLI) Guide

The `gitversioned` CLI provides a standalone utility to calculate versions, test output formatting, and generate version files. It is useful for integration with languages other than Python, custom build pipelines, and containerized deployments.

______________________________________________________________________

## Subcommands Reference

The CLI is structured into four primary subcommands, which accept any settings field as a command-line parameter (e.g., `--output`, `--version-type`).

### 1. `calculate`

Resolves the project version and outputs only the calculated version string to `stdout`.

```bash
gitversioned calculate [OPTIONS]
```

- **Output:** E.g., `1.0.1.dev4+gabc1234`
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

### 4. `overrides`

Runs nested commands under the context of a specific override profile configured under `[tool.gitversioned.overrides.<name>]`. The nested command will merge the override-specific properties on top of your default configuration.

```bash
gitversioned overrides [OVERRIDES_NAME] [SUBCOMMAND] [OPTIONS]
```

- **Positional Argument:** `OVERRIDES_NAME` — The name of the override configuration context to load (e.g., `cargo`).
- **Subcommands:** `calculate`, `format`, or `write`.
- **Use Case:** Executing multi-artifact generation pipelines from a single CLI command structure.

For example, to write the version to a target configured under the `cargo` override block:

```bash
gitversioned overrides cargo write
```

______________________________________________________________________

## Detailed User Stories & Workflows

### 1. Sourcing and Getting the Current Version

This user story covers retrieving the dynamically resolved version for logging, environment tagging, or local diagnostics.

To fetch the raw calculated version for your repository based on its Git state:

```bash
gitversioned calculate
```

Output:

```console
1.0.1.dev5+g9a1e3a1
```

You can customize the calculation on the fly by passing configuration overrides as command-line options. For example, if you want to preview what the version string would look like if you forced a `release` version type instead of the dynamically resolved `dev` version type:

```bash
gitversioned calculate --version-type release
```

Output:

```console
1.1.0
```

You can also test custom formatting styles directly via the command line:

```bash
gitversioned calculate --format-main "{version.major}.{version.minor}"
```

Output:

```console
1.1
```

### 2. Injecting Custom Formats for Docker Build (Format Setup)

When building Docker container images, you often want to inject the dynamically resolved version as a build argument or tag the container with a custom format (e.g., a version string combined with a timestamp or commit hash).

By using the `format` subcommand, you can render custom formats directly to `stdout` and capture them in shell variables.

#### Example: Tagging a Docker Image

You want to tag your Docker image with a custom format: `my-app:<major>.<minor>-dev<commits_distance>`.

1. Run the `format` command to resolve and print the custom format, using the inline `template_str` strategy:
   ```bash
   # Capture the custom version string
   IMAGE_TAG=$(gitversioned format \
     --output-strategies '{"type": "template_str", "content": "{version.major}.{version.minor}-dev{ref.distance_from_head}"}')
   ```
1. Build the Docker container, passing the resolved version to the tag:
   ```bash
   docker build -t "my-app:$IMAGE_TAG" .
   ```

#### Example: Passing the Version as a Build Argument

Alternatively, you can pass the version directly into the build environment:

```bash
# Capture the PEP 440 version
VERSION=$(gitversioned calculate)

# Build and pass the version argument
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

# Run your application, which prints the embedded version
CMD ["python", "-c", "import os; print(f'Starting app v{os.environ[\"APP_VERSION\"]}')"]
```

### 3. Writing Version Strings with Custom Regex (Write Setup)

In many multi-language or polyglot repositories, you need to update version strings inline within non-Python files (such as `Cargo.toml` for Rust, `package.json` for Node, or a legacy config file) before packaging or compilation.

The `write` subcommand supports a `regex` strategy that parses an existing file, finds the version string via a regular expression pattern containing a `(?P<version>...)` named capture group, updates that group inline, and writes the file back.

#### Example: Updating `Cargo.toml` Version In-Place

Suppose you have a Rust package in your repository and need its `Cargo.toml` version field updated to match the dynamically calculated Git version:

```toml
# Cargo.toml (Before)
[package]
name = "my_rust_package"
version = "0.0.0"
```

You can execute a regex-based search-and-replace using the CLI `write` subcommand:

```bash
gitversioned write \
  --output Cargo.toml \
  --output-strategies '{"type": "regex", "pattern": "(?ms)^(?P<prefix>\\[package\\].*?^version\\s*=\\s*[\'\"])(?P<version>[^\'\"]+)(?P<suffix>[\'\"])"}'
```

After running this command:

1. `gitversioned` resolves the version (e.g., `1.0.1.dev5+g9a1e3a1`).
1. It reads `Cargo.toml` and locates the version pattern.
1. It replaces the version string inside the `(?P<version>...)` capture group with the resolved version.
1. It writes the updated contents back to `Cargo.toml` in-place.

```toml
# Cargo.toml (After)
[package]
name = "my_rust_package"
version = "1.0.1.dev5+g9a1e3a1"
```

This ensures that the Rust and Python components of a package are perfectly synchronized under the exact same VCS version without requiring manual file edits.
