# A Rust workspace

A Cargo workspace with no Python at all: three crates on one version, an
inherited `version.workspace = true`, internal dependencies pinned by version,
and a committed `Cargo.lock`. The manifests stay at `0.0.0` in git, and
`gitversioned version --write` stamps the tag's version before a build, as
cargo-release and release-plz do when they cut a release.

| Level        | Shows                                                                     | Needs       |
| ------------ | ------------------------------------------------------------------------- | ----------- |
| Intermediate | `version --write`, `[workspace.package]`, `[workspace.dependencies]`, `Cargo.lock` | git, Cargo  |

## Run

Copy this folder anywhere and run the commands below in it. The transcript is
checked on every test run, so it is exactly what you will see, apart from
hashes and dates.

With no Python project in the folder, versions print in SemVer:

```console
$ git init -q && git add -A && git commit -qm "feat: first version" && git tag v1.4.0
$ gitversioned version
1.4.0
$ gitversioned version --write
1.4.0
  Cargo.toml               1.4.0
  crates/extra/Cargo.toml  1.4.0
  Cargo.lock               1.4.0
$ git diff --stat
 Cargo.lock              | 6 +++---
 Cargo.toml              | 4 ++--
 crates/extra/Cargo.toml | 4 ++--
 3 files changed, 7 insertions(+), 7 deletions(-)
```

Every value Cargo checks moved together, so a locked, offline build works and
each crate reports the release:

```console
$ git diff crates/extra/Cargo.toml Cargo.toml | grep '^[-+][^-+]'
-version = "0.0.0"
+version = "1.4.0"
-demo-core = { path = "crates/core", version = "0.0.0" }
+demo-core = { path = "crates/core", version = "1.4.0" }
-version = "0.0.0"
+version = "1.4.0"
-demo-core = { path = "../core", version = "0.0.0" }
+demo-core = { path = "../core", version = "1.4.0" }
$ cargo run -q --locked --offline -p demo-cli
demo-cli 1.4.0 (core 1.4.0)
```

The stamp is not a change to the source: the version is still the clean
release, not a dirty development build.

```console
$ gitversioned version
1.4.0
$ git checkout -q .
```

A development build gets a SemVer pre-release with the commit hash as build
metadata. Requirements on sibling crates leave the build metadata out, which
Cargo would otherwise warn about:

```console
$ git commit -q --allow-empty -m "fix(core): tighten checks"
$ gitversioned version --write >/dev/null && grep -h 'version = ' Cargo.toml crates/extra/Cargo.toml
version = "1.4.1-dev.20261125+ea5ecdd"
demo-core = { path = "crates/core", version = "1.4.1-dev.20261125" }
version = "1.4.1-dev.20261125+ea5ecdd"
demo-core = { path = "../core", version = "1.4.1-dev.20261125" }
$ cargo run -q --locked --offline -p demo-cli
demo-cli 1.4.1-dev.20261125+ea5ecdd (core 1.4.1-dev.20261125+ea5ecdd)
```

## How it works

- [`Cargo.toml`](Cargo.toml) holds `[workspace.package] version` and the
  `[workspace.dependencies]` entry for the core. Both are found by discovery.
- [`crates/extra/Cargo.toml`](crates/extra/Cargo.toml) spells its version out
  and depends on the core by path and version; both values are stamped.
- `Cargo.lock` entries of the workspace's own crates are rewritten in place;
  entries of other crates are never touched.
- [cargo-release](https://github.com/crate-ci/cargo-release) and
  [release-plz](https://release-plz.dev) edit the same fields; gitversioned
  does it from the tag on every build, so nothing is committed between
  releases.

## Next

- [maturin](../maturin/README.md) for a Rust crate built as a Python extension.
- [monorepo-packages](../monorepo-packages/README.md) for crates with their own tags.
