# Setuptools Guide

The setuptools integration is opt-in, so installing gitversioned next to an
unrelated setuptools project never changes that project's version.

## Setup

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=64", "gitversioned>=0.4"]
build-backend = "setuptools.build_meta"

[project]
name = "my-package"
dynamic = ["version"]

[tool.setuptools.packages.find]
where = ["src"]
```

Listing `gitversioned` in `build-system.requires` is the opt-in. A project that
still uses `setup.py` can opt in with a keyword instead:

<!--phmdoctest-skip-->

```python
# setup.py
from setuptools import setup

setup(gitversioned=True)
```

## What the build does

The build resolves the version from git, sets it as the distribution's version
and writes `<package>/version.py` so the installed package can report it. Add
that file to `.gitignore`:

```gitignore
src/my_package/version.py
```

<!--phmdoctest-skip-->

```python
# src/my_package/__init__.py
from my_package.version import __version__
```

```console
$ git tag v2.1.0
$ python -m build --wheel
Successfully built my_package-2.1.0-py3-none-any.whl
```

## Settings

Settings can live in `[tool.gitversioned]` in `pyproject.toml` or in
`[tool:gitversioned]` in `setup.cfg`:

```ini
# setup.cfg
[tool:gitversioned]
fallback = 0.1.0
scopes = ["core", "docs"]
```

See the [Configuration Guide](configuration.md). A runnable project is in
[`examples/setuptools`](https://github.com/markurtz/git-versioned/tree/main/examples/setuptools).

## Coming from setuptools-scm

- Tags are read the same way, so existing `v1.2.3` tags keep working.
- An existing `.git_archival.txt` is read as it is.
- `write_to` / `version_file` is replaced by the generated `version.py`.
- Remove `setuptools-scm` from `build-system.requires` and delete
  `[tool.setuptools_scm]`.
