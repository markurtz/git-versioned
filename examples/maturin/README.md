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

# Maturin Integration Example

This example demonstrates the minimal recommended setup for integrating GitVersioned with the [Maturin](https://maturin.rs/) build backend for Rust/Python polyglot projects. It dynamically calculates versions from Git tag information and writes the results to a python module (`src/maturin_example/version.py`) during compile time using the custom Maturin wrapper backend `gitversioned.plugins.maturin_plugin`.

## Advanced Pathways

We also provide the following advanced setups under the `advanced/` directory:

1. **[Polyglot Overrides (`advanced/polyglot_overrides/`)](./advanced/polyglot_overrides/)**: Illustrates updating version metadata in both `Cargo.toml` and a local `Dockerfile` via regex replacements during Maturin builds.
1. **[Custom Configuration Settings (`advanced/custom_config/`)](./advanced/custom_config/)**: Illustrates customizing GitVersioned configuration (such as custom templates, auto-increment, and tag regex structures) specifically for Rust packaging.

______________________________________________________________________

## Prerequisites & Setup

Ensure you are in the virtual environment and have the python build frontends installed:

```bash
.venv/bin/pip install build
```

## Execution Blueprint

To compile the polyglot extension package:

```bash
python -m build examples/maturin
```

## Expected Results

When compiling the package, Maturin hooks into GitVersioned to calculate the version and write it to `examples/maturin/src/maturin_example/version.py`. You will see output resembling:

```text
* Creating venv isolated environment...
* Installing packages in isolated environment...
* Getting dependencies for wheel...
* Building wheel...
Successfully built maturin_example-0.2.1-py3-none-any.whl
```

## Troubleshooting

- **Cargo/Rustc Missing**: Building this package locally requires Rust compiler tooling (`rustup`, `cargo`) to be installed on your development machine. If you want to check testing integration without compilation, run the test suite using pytest, which uses a mock Maturin build strategy.
- **ImportError: No module named 'gitversioned'**: Make sure the parent `gitversioned` package is installed in your active environment, or that you are using `--no-isolation` when building locally.
