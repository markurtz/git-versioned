# Setuptools Integration Guide

`gitversioned` provides seamless, native integration with [Setuptools](https://setuptools.pypa.io/) by automatically registering as a plugin via standard Python packaging entry points. This means once it is added to your project's build requirements, Setuptools will automatically invoke it during packaging operations to resolve your project's version.

______________________________________________________________________

## 1. Setup Configurations

Depending on your project's layout and preference, you can configure Setuptools using modern `pyproject.toml`, declarative `setup.cfg`, or legacy `setup.py`.

=== "pyproject.toml (Modern)"

````
Declare `gitversioned` under `build-system` requirements, specify `version` as dynamic, and configure it under `[tool.gitversioned]`:

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=61.0", "gitversioned"]
build-backend = "setuptools.build_meta"

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
````

=== "setup.cfg (Declarative)"

````
If you define your package metadata in `setup.cfg`, ensure `gitversioned` is in `setup_requires` and declare your settings under `[tool:gitversioned]`:

```ini
# setup.cfg
[metadata]
name = my-package

[options]
# Keep version dynamic so Setuptools hooks can inject it
setup_requires =
    gitversioned

[tool:gitversioned]
source_type = tag
output = src/my_package/version.py

[tool:gitversioned:auto_increment]
pre = minor
dev = patch
```
````

=== "setup.py (Legacy/Imperative)"

````
If your project uses an imperative `setup.py` file, pass configuration overrides directly to `setup()` via the `gitversioned` dictionary keyword argument:

```python
# setup.py
# Copyright 2026 Mark Kurtz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from setuptools import setup

setup(
    name="my-package",
    setup_requires=["gitversioned"],
    # Configure settings directly in python
    gitversioned={
        "source_type": ["tag"],
        "output": "src/my_package/version.py",
        "auto_increment": {
            "pre": "minor",
            "dev": "patch",
        },
    },
)
```
````

______________________________________________________________________

## 2. Common User Stories & Patterns

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
output = "src/my_package/version.py"

regex_file = [
    # Regex to extract the version string from the generated file
    '(?i)__version__\s*=\s*[\'"](?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)[\'"]'
]
```

With this configuration:

1. `python -m build` locally uses Git to build `1.6.0a...` and writes `version.py`.
1. The sdist packages `version.py` (provided it's tracked by Git or added to your manifest).
1. When a user runs `pip install my-package.tar.gz`, `gitversioned` fails to find `.git`, falls back to `file`, parses `version.py`, and successfully sets the version.

> [!TIP]
> **GitHub ZIP Downloads vs. sdists**
> If a user downloads your repository as a ZIP directly from GitHub, there is no `.git` directory and no pre-generated `version.py` file! For this scenario, `gitversioned` provides an **Archive Fallback** mechanism that parses a substituted `.git_archival.txt` file. See the [Quick Start](../getting-started/quickstart.md#configure-archive-support-recommended) for setup instructions.

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
# Copyright 2026 Mark Kurtz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

try:
    from .version import __version__
except ImportError:
    # Fallback if the build hasn't run yet or failed
    __version__ = "0.0.0"

__all__ = ["__version__"]
```
