<!--
Copyright 2026 markurtz

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# Maturin Polyglot Overrides Example

This example demonstrates how to configure GitVersioned and Maturin to dynamically synchronize version metadata across python package settings, Rust's `Cargo.toml` package definition, and an external `Dockerfile` simultaneously.

## Overview

In Rust/Python polyglot repositories, multiple source files track versions. By specifying `tool.gitversioned.overrides.cargo` and `tool.gitversioned.overrides.docker` in `pyproject.toml`, GitVersioned automatically performs in-place version substitutions in both Rust package metadata and the container configuration file whenever a Maturin build is initiated.

## Prerequisites & Setup

Ensure you are in the virtual environment and have the python build frontends installed:

```bash
.venv/bin/pip install build
```

## Execution Blueprint

To trigger compilation:

```bash
python -m build examples/maturin/advanced/polyglot_overrides
```

## Expected Results

Upon completion, the python package version, `Cargo.toml` version key, and `Dockerfile` version argument will all align:

```text
# Excerpt from examples/maturin/advanced/polyglot_overrides/Cargo.toml
[package]
name = "maturin_polyglot_overrides"
version = "0.2.1.dev24"
```

## Troubleshooting

- **Rust Compilation Requirements**: Compiling this package requires the Cargo and Rustc build tools. If they are not present, you can test GitVersioned's integration hook behavior using our mock-backend automated pytest suite.
- **Cargo.toml Section Headers**: The default Cargo override pattern is designed to update the version key located immediately under the `[package]` header.
