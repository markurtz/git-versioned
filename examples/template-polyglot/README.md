# A template polyglot repository

The manifests of a [markurtz/template](https://github.com/markurtz/template)
polyglot render, Python primary, copied from the generator's snapshot: the root
hatchling package, a virtual Cargo workspace with `workspace.package` and
`workspace.dependencies`, the maturin binding, the wasm npm package, a pnpm
workspace with private apps, the desktop app's own Tauri workspace, the API's
private `pyproject.toml`, a cargo-fuzz harness, the example legs and
`CITATION.cff`. The lockfiles are trimmed to a few entries, and the source files
are left out.

`gitversioned version --write` replaces the template's `release:stamp` task, and
`release --write` its release pull request contents.

| Level    | Shows                                                                     | Needs  |
| -------- | ------------------------------------------------------------------------- | ------ |
| Advanced | discovery across every block, scopes from `.config/blocks.toml`, what is never stamped, builds that stay clean | Python |

## Run

Copy this folder anywhere and run the commands below in it. The transcript is
checked on every test run, so it is exactly what you will see, apart from
hashes and dates.

```console
$ git init -q && git add -A && git commit -qm "feat: first release" && git tag v0.3.0
$ git init -q --bare ../origin.git && git remote add origin ../origin.git && git push -q -u origin main v0.3.0
$ gitversioned check
ok    config        pyproject.toml [tool.gitversioned]
ok    git           full history, 1 release tag, latest v0.3.0
ok    targets       CITATION.cff, Cargo.toml, apps/desktop/package.json, apps/desktop/src-tauri/Cargo.toml, apps/web/package.json, crates/wasm/package.json, packages/client/package.json, src/template_polyglot/version.py, Cargo.lock, apps/desktop/src-tauri/Cargo.lock
ok    scopes        core, oci, python, api, rust, cli, node, contract, db, web, desktop, docs, notebooks, python-ext, wasm, deps, deps-dev, ci, release
warn  archive file  .git_archival.txt is not set up, so source tarballs lose the version. Run `gitversioned init`.
warn  github        gh is missing or not signed in: release --pr, GitHub releases and pull request titles in the changelog are unavailable.
```

### Pull request titles

`pr.yml` checks the title with `gitversioned check "$PR_TITLE"`. The scopes are
the block names in `.config/blocks.toml` plus `deps`, `deps-dev`, `ci` and
`release`:

```console
$ gitversioned check "feat(wasm): export count_words"
ok
$ gitversioned check "chore(deps-dev): bump vitest"
ok
$ gitversioned check "feat(frontend): dark mode"
fail  title  unknown scope 'frontend'. Scopes: core, oci, python, api, rust, cli, node, contract, db, web, desktop, docs, notebooks, python-ext, wasm, deps, deps-dev, ci, release.
[exit 1]
```

### Stamp a build

A build or publish job between releases stamps the development version where
`release:stamp` did. Every manifest that ships gets it, each in its own
spelling; the workspace's path dependency follows; `Cargo.lock` changes only the
workspace's own crates:

```console
$ echo "x = 1" > src/template_polyglot/stats.py && git add -A && git commit -qm "feat(web): word cloud (#21)"
$ gitversioned version --write
0.3.1.dev20261125+5a80275
  CITATION.cff                       0.3.1-dev.20261125+5a80275
  Cargo.toml                         0.3.1-dev.20261125+5a80275
  apps/desktop/package.json          0.3.1-dev.20261125+5a80275
  apps/desktop/src-tauri/Cargo.toml  0.3.1-dev.20261125+5a80275
  apps/web/package.json              0.3.1-dev.20261125+5a80275
  crates/wasm/package.json           0.3.1-dev.20261125+5a80275
  packages/client/package.json       0.3.1-dev.20261125+5a80275
  src/template_polyglot/version.py   0.3.1.dev20261125+5a80275
  Cargo.lock                         0.3.1-dev.20261125+5a80275
  apps/desktop/src-tauri/Cargo.lock  0.3.1-dev.20261125+5a80275
$ git diff Cargo.toml Cargo.lock | grep '^[-+][^-+]'
-version = "0.0.0"
+version = "0.3.1-dev.20261125+5a80275"
-version = "0.0.0"
+version = "0.3.1-dev.20261125+5a80275"
-version = "0.0.0"
+version = "0.3.1-dev.20261125+5a80275"
-version = "0.0.0"
+version = "0.3.1-dev.20261125+5a80275"
-version = "0.0.0"
+version = "0.3.1-dev.20261125+5a80275"
-template-polyglot-core = { path = "crates/core", version = "0.0.0" }
+template-polyglot-core = { path = "crates/core", version = "0.3.1-dev.20261125" }
```

Some manifests are left alone: the example legs under `examples/`, the fuzz
harness (`cargo-fuzz = true`), and the API, whose `Private :: Do Not Upload`
classifier says it never ships. The stamped files do not make the tree dirty,
so the build that follows still gets a clean version:

```console
$ git status --short
 M CITATION.cff
 M Cargo.lock
 M Cargo.toml
 M apps/desktop/package.json
 M apps/desktop/src-tauri/Cargo.lock
 M apps/desktop/src-tauri/Cargo.toml
 M apps/web/package.json
 M crates/wasm/package.json
 M packages/client/package.json
$ grep -c '"0.0.0"' Cargo.lock && grep '^version' apps/api/pyproject.toml crates/core/fuzz/Cargo.toml examples/text-stats/rust/Cargo.toml
1
apps/api/pyproject.toml:version = "0.0.0"
crates/core/fuzz/Cargo.toml:version = "0.0.0"
examples/text-stats/rust/Cargo.toml:version = "0.0.0"
$ gitversioned version
0.3.1.dev20261125+5a80275
$ git checkout -q . && git status --short
```

### Release

`release --write` writes the same files at the release version, folds the
`[Unreleased]` lines into the new section, and adds `version` and
`date-released` to `CITATION.cff`. Committing them means the tagged commit names
its own version in every manifest, so `cargo publish`, `npm publish` and
maturin need no stamp step on the tag:

```console
$ gitversioned release --write | sed -n '1,3p'
release   0.3.1  (minor, a patch below 1.0.0, from commits, from 0.3.0)
tag       v0.3.1
files     CHANGELOG.md, CITATION.cff, Cargo.toml, apps/desktop/package.json, apps/desktop/src-tauri/Cargo.toml, apps/web/package.json, crates/wasm/package.json, packages/client/package.json, Cargo.lock, apps/desktop/src-tauri/Cargo.lock
$ sed -n '/^## \[0.3.1\]/,/^## \[0.3.0\]/p' CHANGELOG.md
## [0.3.1] - 2026-11-25

### Added

- **core**: Initial repository generated from [markurtz/template](https://github.com/markurtz/template).
- **web**: word cloud (#21)
$ git diff CITATION.cff | grep '^+[^+]'
+version: "0.3.1"
+date-released: "2026-11-25"
$ git commit -qam "release: v0.3.1" && git push -q && gitversioned release --tag
tag       v0.3.1 at d09b581, pushed
$ gitversioned version && gitversioned check --tag v0.3.1 | sed -n '1p'
0.3.1
ok    tag        0.3.1 at HEAD, newer than v0.3.0
```

## How it works

- [`pyproject.toml`](pyproject.toml) adds one table to the rendered file:
  `[tool.gitversioned] scopes = [".config/blocks.toml", "deps", "deps-dev",
  "ci", "release"]`. The build requirement is `gitversioned>=0.4`.
- Discovery reads every tracked manifest except those under `examples/`,
  `tests/` and other fixture folders, a nested `CITATION.cff`, a cargo-fuzz
  harness and a Python project marked `Private :: Do Not Upload`.
- `crates/*` inherit `version.workspace = true`, so only the root `Cargo.toml`
  changes. The maturin binding in `crates/python-ext` reads that version.
- The desktop app's `src-tauri` is its own workspace with its own `Cargo.lock`;
  Tauri names the installers after its `version`.
- The root `package.json` is private and has no version, so it is left alone.
- The changelog in the render groups entries by scope first; gitversioned reads
  those entries and writes the new section by type, with the scope in bold.

## What the template changes

- `release:stamp` becomes `gitversioned version --write`, and `release:verify`
  becomes `gitversioned check --tag`; see
  [template-python](../template-python/README.md).
- Manifests hold the last release's version between releases instead of
  `0.0.0`, since `release --write` commits them.
- `pr.yml`'s title check becomes `gitversioned check "$PR_TITLE"`.

## Next

- [template-python](../template-python/README.md) for the release tasks.
- [polyglot](../polyglot/README.md) for Helm, Docker and `[packages]`.
