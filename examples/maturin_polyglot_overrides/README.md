# Maturin Polyglot Overrides Example

## Overview

This example demonstrates how to configure and use `gitversioned` with the Maturin build backend in a polyglot Python and Rust repository. It highlights the use of config-level overrides to target and update the version inside `Cargo.toml` and a `Dockerfile`, while concurrently generating the standard `version.py` module to keep the entire codebase synchronized.

## Prerequisites & Setup

Make sure you have `cargo` (Rust toolchain) and `pip`/`build` (Python ecosystem) installed.

To set up the environment and install dependencies:

```bash
# Set up/update dependencies via Hatch inside virtualenv wrapper
.venv/bin/hatch env create

# Activate project environment
source .venv/bin/activate
```

## Execution Blueprint

Build the wheel package dynamically using the `gitversioned` Maturin wrapper backend plugin:

```bash
python -m build --no-isolation
```

## Expected Results

When building the project in a git repository tagged at `v1.2.3`, the build output will show version synchronization across all targets:

```
$ python -m build --no-isolation
* Creating venv isolated environment...
* Installing packages in isolated environment...
* Getting build dependencies for wheel...
* Building wheel...
...
Maturin plugin resolved version: 1.2.3 (wrote to: src/maturin_polyglot_overrides/version.py)
...
Successfully built maturin_polyglot_overrides-1.2.3-py3-none-any.whl
```

Verifying that the Cargo.toml version was updated:

```toml
[package]
name = "maturin_polyglot_overrides"
version = "1.2.3"
edition = "2021"
```

Verifying that the Dockerfile version argument was updated:

```dockerfile
# Use a slim Python image
FROM python:3.10-slim

# Version build argument to be injected via GitVersioned overrides
ARG VERSION="1.2.3"
ENV APP_VERSION=${VERSION}
```

## Troubleshooting

- **Rust compiler not found**: Ensure that Rust/Cargo is installed and available in your environment path.
- **Maturin build error**: Maturin requires pyo3 dependency versions to be compatible with Python. Ensure python-dev header files are present in your OS distribution if compiling manually.
