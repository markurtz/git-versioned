# Maturin through the wrapper backend

A Rust extension for Python, built by Maturin. Maturin reads the version from
`Cargo.toml`, which stays at the placeholder `0.0.0` in git. The
`gitversioned.plugins.maturin` backend stamps the resolved version into
`Cargo.toml` for the length of the build, hands over to Maturin, and puts the
file back, so the tree stays clean.

| Level        | Build backend                  | Needs                                        |
| ------------ | ------------------------------ | -------------------------------------------- |
| Intermediate | `gitversioned.plugins.maturin` | Python, `build`, `maturin`, a Rust toolchain |

## Run

Copy this folder anywhere and run the commands below in it. The transcript is
checked on every test run, so it is exactly what you will see, apart from
hashes and dates. The first build compiles PyO3 and takes a minute.

```console
$ git init -q && git add -A && git commit -qm "feat: first version" && git tag v0.3.0
$ python -m build --wheel --no-isolation >/dev/null 2>&1 && ls dist
demo_maturin-0.3.0-...whl
$ git status --short
$ grep '^version' Cargo.toml
version = "0.0.0"
```

The extension reports the version Cargo compiled into it, and the Python
package the one in its generated `version.py`; both are the tag's:

```console
$ unzip -q dist/*.whl -d ../site
$ PYTHONPATH=../site python -c "import demo_maturin, demo_maturin.version as v; print(demo_maturin.__version__, v.__version__, demo_maturin.add(2, 3))"
0.3.0 0.3.0 5
```

A release candidate tag is spelled for each ecosystem: SemVer in `Cargo.toml`,
PEP 440 in the wheel name.

```console
$ git commit -q --allow-empty -m "feat: add more" && git tag v0.4.0-rc.1
$ gitversioned version --write --dry-run | sed -n '1,8p'
0.4.0rc1
--- a/Cargo.toml
+++ b/Cargo.toml
@@ -1,6 +1,6 @@
 [package]
 name = "demo-maturin"
-version = "0.0.0"
+version = "0.4.0-rc.1"
$ rm -rf dist && python -m build --wheel --no-isolation >/dev/null 2>&1 && ls dist
demo_maturin-0.4.0rc1-...whl
```

`gitversioned version --write` stamps `Cargo.toml` for a plain `cargo build`
too. The edit does not make the tree dirty, so the version stays clean:

```console
$ gitversioned version --write >/dev/null && git status --short && gitversioned version
 M Cargo.toml
0.4.0rc1
$ git checkout -q Cargo.toml
```

## How it works

- [`pyproject.toml`](pyproject.toml) sets
  `build-backend = "gitversioned.plugins.maturin"` and lists both `maturin` and
  `gitversioned` in `build-system.requires`.
- [`Cargo.toml`](Cargo.toml) keeps `version = "0.0.0"` in git.
- [`src/lib.rs`](src/lib.rs) exposes `CARGO_PKG_VERSION` as `__version__`.
- The [template-polyglot](../template-polyglot/README.md) example shows the
  other way: the plain `maturin` backend reading a workspace version that
  `version --write` stamped.

## Next

- [rust-workspace](../rust-workspace/README.md) for a Cargo workspace without Python.
