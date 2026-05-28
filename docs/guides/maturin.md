# Maturin Integration Guide

`gitversioned` provides seamless integration with [Maturin](https://github.com/PyO3/maturin), a PEP 517 build backend for Rust-based Python packages. This allows you to automatically calculate your package version using Git repository metadata and synchronize it across Python package definitions and your Rust `Cargo.toml` file dynamically during build operations.

There are two primary modes of integration: using the **Maturin Build Wrapper Plugin** (PEP 517 build hook integration) or using **Standalone Maturin** (direct CLI integration).

______________________________________________________________________

## 1. Maturin Build Wrapper Plugin (Recommended)

When building your package via Python frontends like `pip` or `build`, `gitversioned` can wrap Maturin to automatically intercept build hooks, calculate the version, synchronize files, and forward compilation to Maturin.

### Configuration

Declare `gitversioned` as a build requirement and specify it as the build backend wrapper in your `pyproject.toml` file.

**`pyproject.toml`**

```toml
[build-system]
requires = ["maturin>=1.0,<2.0", "gitversioned"]
build-backend = "gitversioned.plugins.maturin_plugin"

[project]
name = "my-package"
dynamic = ["version"]

[tool.gitversioned]
source_type = ["tag"]
output = "src/my_package/version.py"

[tool.gitversioned.auto_increment]
pre = "minor"
dev = "patch"
```

**`Cargo.toml`**
Ensure your Rust `Cargo.toml` has a placeholder version field under `[package]`. On build, the plugin will update this field automatically:

```toml
[package]
name = "my-rust-package"
version = "0.0.0"  # Will be dynamically synchronized during builds
```

### Dual-Artifact State Synchronization

When a build is initiated (e.g., via `pip install .` or `python -m build`), the wrapper plugin automatically detects if a `Cargo.toml` file is present in your project root.

If found, it auto-configures a configuration override matching your `Cargo.toml` structure. This executes a regex replacement strategy to update the `version` field under `[package]` in `Cargo.toml` before passing compilation over to Cargo.

The default `Cargo.toml` override configuration looks like this under the hood:

```toml
[tool.gitversioned.overrides.cargo]
output = "Cargo.toml"
output_strategies = { type = "regex", pattern = '(?ms)^\[package\].*?^(\s*version\s*=\s*)([\'\"])(?P<version>[^\'\"]+)\2' }
```

This ensures that the Rust compiler (`cargo`) and Python build tools agree on the exact version, avoiding compile-time version mismatch errors.

______________________________________________________________________

## 2. Standalone Maturin (CLI Integration)

If you compile or release your package using the `maturin` CLI directly (e.g., running `maturin build` or `maturin publish` in a Rust-only or hybrid CI pipeline) rather than using a Python PEP 517 frontend, you can run `gitversioned` standalone as a pre-build step.

In this setup, `gitversioned` runs before the `maturin` CLI, resolves the Git version, and writes it directly to `Cargo.toml`.

### Configuration

Add the override definition to your `pyproject.toml` to specify how the version is written to `Cargo.toml`:

```toml
# pyproject.toml
[tool.gitversioned]
source_type = ["tag"]
# Disables default Python file generation if you only need Cargo.toml updated
output = "" 

[tool.gitversioned.overrides.cargo]
output = "Cargo.toml"
output_strategies = { type = "regex", pattern = '(?ms)^\[package\].*?^(\s*version\s*=\s*)([\'\"])(?P<version>[^\'\"]+)\2' }
```

### Build Workflow

Run the `gitversioned` CLI to update `Cargo.toml` in-place before running the `maturin` compiler:

```bash
# 1. Resolve version and update Cargo.toml using the 'cargo' override
gitversioned overrides cargo write

# 2. Compile/package the Rust extension using Maturin
maturin build --release
```

______________________________________________________________________

## 3. Common User Stories & Patterns

### Sdist Portability & Fallbacks

When packaging an sdist (`.tar.gz`), Maturin does not package the `.git` directory. To ensure packaging and installation work properly from the built sdist, configure `gitversioned` to fall back to the generated Python file:

```toml
[tool.gitversioned]
source_type = ["tag", "file"]
version_source_file = "src/my_package/version.py"
output = "src/my_package/version.py"

regex_file = [
    '(?i)__version__\s*=\s*[\'"](?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)[\'"]'
]
```

### Advanced Layout Customizations

If your Rust crate's `Cargo.toml` is not located in the project root (e.g., in a workspace subdirectory like `rust/Cargo.toml`), you can declare a custom override path manually:

```toml
[tool.gitversioned.overrides.rust]
output = "rust/Cargo.toml"
output_strategies = { type = "regex", pattern = '(?ms)^\[package\].*?^(\s*version\s*=\s*)([\'\"])(?P<version>[^\'\"]+)\2' }
```

Then compile using the custom overrides context:

```bash
gitversioned overrides rust write
maturin build --manifest-path rust/Cargo.toml --release
```
