# Maturin Guide

Maturin takes the version of a Rust extension from `Cargo.toml`. gitversioned
wraps Maturin's build backend: it stamps the resolved version into `Cargo.toml`
for the length of the build, hands over to Maturin, then restores the file.

## Setup

```toml
# pyproject.toml
[build-system]
requires = ["maturin>=1.0,<2.0", "gitversioned>=0.4"]
build-backend = "gitversioned.plugins.maturin"

[project]
name = "my-extension"
dynamic = ["version"]

[tool.maturin]
python-source = "python"
module-name = "my_extension._native"
```

```toml
# Cargo.toml
[package]
name = "my-extension"
version = "0.0.0"        # a placeholder; never edited by hand
```

Everything under `[tool.maturin]` is passed through untouched. To ship the
generated `version.py` in a mixed Rust and Python project, list it, because
Maturin leaves out files that git ignores:

```toml
[tool.maturin]
include = [{ path = "python/my_extension/version.py", format = ["sdist", "wheel"] }]
```

## Build

```console
$ git tag v0.3.0
$ python -m build --wheel
$ git status --short
```

The wheel is `my_extension-0.3.0-...whl` and the working tree is clean
afterwards. Release candidates are spelled for each side: a tag `v0.3.0-rc.1`
gives the wheel version `0.3.0rc1` and the crate version `0.3.0-rc.1`.

## Cargo on its own

For `cargo build`, `cargo publish` or `maturin develop` outside a PEP 517
build, stamp the manifests first:

```bash
gitversioned version --write
cargo build --release
```

In a workspace this also updates the version of every path dependency on a
workspace crate (the operator, such as `=` or `^`, is kept) and the matching
`Cargo.lock` entries, so `cargo build --locked` keeps working. The stamped
files do not make the tree count as dirty.

A runnable project is in
[`examples/maturin`](https://github.com/markurtz/git-versioned/tree/main/examples/maturin).
