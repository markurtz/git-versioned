# Setuptools Integration Guide

`gitversioned` provides seamless, native integration with [Setuptools](https://setuptools.pypa.io/) by automatically registering as a plugin via standard Python entry points. This means that once it is installed and added to your build system requirements, Setuptools will automatically invoke it during builds.

This guide details how to configure `gitversioned` in a Setuptools project and highlights common usage patterns.

______________________________________________________________________

## 1. Enabling the Plugin

To use `gitversioned` with Setuptools, simply declare it as a build requirement in your `pyproject.toml`. Because `gitversioned` uses `setup_keywords` and `finalize_distribution_options` entry points, it will activate automatically without any explicit code hooks.

```toml
[build-system]
requires = ["setuptools", "gitversioned"]
build-backend = "setuptools.build_meta"

[project]
name = "my-package"
dynamic = ["version"]
```

When you run `python -m build` or `pip install .`, Setuptools will call `gitversioned` to dynamically resolve the package version and inject it into the built wheel and sdist!

______________________________________________________________________

## 2. Configuring GitVersioned

All settings for `gitversioned` are read natively from the `[tool.gitversioned]` table in your `pyproject.toml` (or `[tool:gitversioned]` in `setup.cfg`).

Here is a common configuration that prioritizes tags and writes the output directly to a file inside the package:

```toml
[tool.gitversioned]
source_type = ["tag"]
output_file = "src/my_package/version.py"

[tool.gitversioned.auto_increment]
pre = "minor"
dev = "patch"
```

If you prefer `setup.cfg`, the equivalent configuration looks like this:

```ini
[tool:gitversioned]
source_type = tag
output_file = src/my_package/version.py

[tool:gitversioned:auto_increment]
pre = minor
dev = patch
```

For a full list of configuration options, refer to the [Configuration Guide](configuration.md).

______________________________________________________________________

## 3. Common User Stories & Patterns

### Generating Stable vs. Dev Builds

By default, `gitversioned` is smart about determining what type of build you are creating based on the state of your Git repository.

**Scenario A: Clean Tagged Release**

- **State:** You check out `v1.5.0`. The working directory is clean.
- **Action:** You run `python -m build`.
- **Result:** `gitversioned` detects the clean tag and assigns the `release` version type. The generated version is `1.5.0`.

**Scenario B: Nightly Build**

- **State:** You are on the `main` branch, 3 commits ahead of `v1.5.0` in a clean CI environment.
- **Action:** You configure `pre = "minor"` under `[tool.gitversioned.auto_increment]` and run the build.
- **Result:** `gitversioned` resolves the `pre` version type (or you force it via `version_type = "pre"`). It auto-increments the minor segment, resulting in a pre-release like `1.6.0a20260507+<sha>`.

**Scenario C: Local Dirty Build**

- **State:** You have uncommitted changes.
- **Result:** Automatically resolved as `dev` and increments patch (if configured `dev = "patch"`), resulting in `1.5.1.devYYYYMMDD+<sha>`.

### Ensuring Sdist Portability

When you run `python -m build`, Setuptools creates a source distribution (sdist) containing your project files. However, the `.git` directory is not included in the sdist!

To ensure that downstream users (or pip) can still resolve the version when installing from the sdist, configure `gitversioned` to fall back to the generated version file:

```toml
[tool.gitversioned]
# Look at tags first. If the repo is missing, fall back to the generated file!
source_type = ["tag", "file"]
version_source_file = "src/my_package/version.py"
output_file = "src/my_package/version.py"

regex_file = [
    # Regex to extract the version string from the generated file
    '(?i)__version__\s*=\s*[\'"](?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)[\'"]'
]
```

With this configuration:

1. `python -m build` locally uses Git to build `1.6.0a...` and writes `version.py`.
1. The sdist packages `version.py` (provided it's tracked by Git or added to your manifest).
1. When a user runs `pip install my-package.tar.gz`, `gitversioned` fails to find `.git`, falls back to `file`, parses `version.py`, and successfully sets the version.

### Excluding the Version File from Git

If you add your generated `version.py` file to `.gitignore` so it isn't committed to your repository, Setuptools will natively ignore it during the build process if you are using `setuptools-scm` or native git file discovery, meaning it won't be included in your final wheel or sdist.

To ensure the ignored version file is correctly packaged, you must instruct Setuptools to explicitly include it by adding it to your `MANIFEST.in`:

```text
# MANIFEST.in
include src/my_package/version.py
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
