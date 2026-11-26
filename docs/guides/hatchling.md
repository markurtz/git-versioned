# Hatchling Guide

gitversioned plugs into Hatchling as a version source and a build hook. The
version comes from git at build time and nothing is committed.

## Setup

```toml
# pyproject.toml
[build-system]
requires = ["hatchling", "gitversioned>=0.4"]
build-backend = "hatchling.build"

[project]
name = "my-package"
dynamic = ["version"]

[tool.hatch.version]
source = "gitversioned"

[tool.hatch.build.hooks.gitversioned]
```

| Piece                                   | What it does                                                      |
| --------------------------------------- | ----------------------------------------------------------------- |
| `gitversioned` in `requires`            | Makes the plugin available to the isolated build.                 |
| `dynamic = ["version"]`                 | Tells the build the version is not in the file.                   |
| `[tool.hatch.version] source`           | Resolves the version from git.                                    |
| `[tool.hatch.build.hooks.gitversioned]` | Writes `<package>/version.py` and adds it to the wheel and sdist. |

`gitversioned init` adds the `[tool.hatch.version]` table for you.

## Read the version at runtime

Add the generated file to `.gitignore`, then import from it:

```gitignore
src/my_package/version.py
```

<!--phmdoctest-skip-->

```python
# src/my_package/__init__.py
from my_package.version import __version__
```

The generated module holds `__version__`, `__version_semver__`,
`__version_tuple__`, `__tag__`, `__distance__`, `__commit__` and
`__commit_date__`. It has no build timestamp, so two builds of one commit are
identical.

## Build

```console
$ git tag v1.2.3
$ python -m build
Successfully built my_package-1.2.3.tar.gz and my_package-1.2.3-py3-none-any.whl
```

After the tag the same command builds `1.2.4.dev20261125+abc1234`. A wheel built
from the unpacked sdist keeps the sdist's version, because the version is read
from `PKG-INFO` when there is no git history.

## Publishing development builds

Package indexes reject versions with a local part (`+abc1234`). Build a nightly,
which has none, or turn the hash off:

```bash
GITVERSIONED__TYPE=nightly python -m build
GITVERSIONED__LOCAL=false python -m build
```

## Settings

Settings go under `[tool.gitversioned]`, never under the Hatch tables. See the
[Configuration Guide](configuration.md). A runnable project is in
[`examples/hatchling`](https://github.com/markurtz/git-versioned/tree/main/examples/hatchling).
