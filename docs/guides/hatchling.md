# Hatchling Integration Guide

`gitversioned` provides a native version source plugin for [Hatchling](https://hatch.pypa.io/). This allows Hatchling to automatically determine your package version based on your Git repository state during builds, installs, and environment setups.

This guide walks you through the configuration and common user stories for using `gitversioned` with Hatchling.

______________________________________________________________________

## 1. Enabling the Plugin

To use `gitversioned` as a version source, you need to declare it as a build dependency and configure Hatch to use it in your `pyproject.toml`.

```toml
[build-system]
requires = ["hatchling", "gitversioned"]
build-backend = "hatchling.build"

[project]
name = "my-package"
dynamic = ["version"]

[tool.hatch.version]
source = "gitversioned"
```

With this minimal setup, running `hatch build` will dynamically determine the version (e.g., from your latest Git tag or commit) and inject it into the built wheel and sdist!

______________________________________________________________________

## 2. Configuring GitVersioned

When using the `gitversioned` Hatchling plugin, all configurations are read from the `[tool.gitversioned]` table in your `pyproject.toml`.

Here is an example configuring it to read from tags, output a `version.py` file, and auto-increment the patch segment for development builds:

```toml
[tool.gitversioned]
source_type = ["tag"]
output_file = "src/my_package/version.py"

[tool.gitversioned.auto_increment]
dev = "patch"
pre = "minor"
```

For a full list of configuration options, refer to the [Configuration Guide](configuration.md).

______________________________________________________________________

## 3. Common User Stories & Patterns

### Auto-Incrementing Nightly Builds

Many projects push nightly builds to a registry. You can configure `gitversioned` to automatically bump the version based on your release strategy and generate a `.dev` or `a` (alpha) suffix with the date and commit hash.

**Goal:** Treat commits on the `main` branch as pre-release builds that increment the minor version from the last tag, while keeping `dev` strict to dirty local builds.

```toml
[tool.gitversioned]
source_type = ["tag"]
version_type = "auto" # Automatically determined based on clean/dirty state

[tool.gitversioned.auto_increment]
# If we are ahead of the last tag in a clean CI environment, increment the minor segment for 'pre'.
pre = "minor"
# Local dirty builds will be evaluated as 'dev' and can increment 'patch'.
dev = "patch"
```

*Result:* If the last tag was `v1.2.0`, a clean CI build on `main` will build as `1.3.0a20260507+<sha>` (if `version_type` resolves or is forced to `pre`), while a local dirty build resolves to `dev` and increments patch: `1.2.1.dev...`.

### Differentiated Dev Versions

Sometimes you want local builds (with dirty files) to look different from CI builds. While `gitversioned` handles this dynamically via the `template_dev` setting (see [Templates](templates.md)), you can also enforce a strict format for all development builds.

**Goal:** Ensure local dirty builds always append a `+dirty` metadata tag, while clean pre-releases do not.

This is handled seamlessly by default! When `gitversioned` detects uncommitted changes, it automatically resolves the `version_type` to `dev`, evaluating the `format_dev` string (which defaults to `dev{ref.timestamp:%Y%m%d}+{ref.short_sha}` showing dirty state).

### Fallback to Static Files

If a user installs your package from a source distribution (sdist) rather than a Git clone, the `.git` directory won't exist. You can tell `gitversioned` to fall back to a generated file.

```toml
[tool.gitversioned]
# Try tags first, then fall back to reading the generated file.
source_type = ["tag", "file"]
version_source_file = "src/my_package/version.py"
output_file = "src/my_package/version.py"

regex_file = [
    # Match the __version__ assignment inside version.py
    '(?i)__version__\s*=\s*[\'"](?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)[\'"]'
]
```

This ensures `hatch build` works perfectly in both local clones and downstream source installations.

> [!TIP]
> "GitHub ZIP Downloads vs. sdists"
> If a user downloads your repository as a ZIP directly from GitHub, there is no `.git` directory and no pre-generated `version.py` file! For this scenario, `gitversioned` provides an **Archive Fallback** mechanism that parses a substituted `.git_archival.txt` file. See the [Quick Start](../getting-started/quickstart.md#configure-archive-support-recommended) for setup instructions.

### Excluding the Version File from Git

If you add your generated `version.py` file to `.gitignore` so it isn't committed to your repository, Hatchling will natively ignore it during the build process, meaning it won't be included in your final wheel or sdist.

To ensure the ignored version file is correctly packaged, you must instruct Hatchling to explicitly include it via `artifacts`:

```toml
[tool.hatch.build]
artifacts = [
    "src/my_package/version.py"
]
```

You can then cleanly expose this version in your package's `__init__.py`:

```python
# src/my_package/__init__.py
try:
    from .version import __version__
except ImportError:
    # Fallback if the build hasn't run yet or failed
    __version__ = "0.0.0"

__all__ = ["__version__"]
```
