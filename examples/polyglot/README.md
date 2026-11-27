# One version for every manifest

One repository holding a Python package at the root, a Cargo workspace, a Helm
chart, a citation file, a Dockerfile, a docs page that names the version, and an
npm package with its own release line. One command stamps them all, each in the
spelling its ecosystem expects.

| Level    | Shows                                                                                               | Needs  |
| -------- | --------------------------------------------------------------------------------------------------- | ------ |
| Advanced | discovery, `version --write`, `--dry-run`, `[[targets]]`, `[packages]`, `.config/gitversioned.toml` | Python |

## Run

Copy this folder anywhere and run the commands below in it. The transcript is
checked on every test run, so it is exactly what you will see, apart from
hashes and dates.

```console
$ git init -q && git add -A && git commit -qm "feat: first version" && git tag v1.4.0 && git tag web-v0.9.0
$ gitversioned check | sed -n '1,3p'
ok    config        .config/gitversioned.toml
ok    git           full history, 1 release tag, latest v1.4.0
ok    targets       CITATION.cff, Dockerfile, charts/demo/Chart.yaml, crates/cli/Cargo.toml, crates/core/Cargo.toml, src/demo/version.py, Cargo.lock, docs/install.md, packages/web/package.json
```

### Preview, then write

`--dry-run` prints the diff and changes nothing:

```console
$ gitversioned version --write --dry-run | sed -n '1,12p'
1.4.0
--- a/CITATION.cff
+++ b/CITATION.cff
@@ -4,5 +4,5 @@
 type: software
 authors:
   - name: "The demo authors"
-version: 0.0.0
-date-released: "2026-01-01"
+version: 1.4.0
+date-released: "2026-11-25"
--- a/Dockerfile
$ git status --short
```

Without it, every target is stamped:

```console
$ gitversioned version --write
1.4.0
  CITATION.cff            1.4.0
  Dockerfile              1.4.0
  charts/demo/Chart.yaml  1.4.0
  crates/cli/Cargo.toml   1.4.0
  crates/core/Cargo.toml  1.4.0
  src/demo/version.py     1.4.0
  Cargo.lock              1.4.0
  docs/install.md         1.4.0
$ grep -h -E '^version|version = "=|appVersion|image.version|demo-cli@' Cargo.toml crates/*/Cargo.toml charts/demo/Chart.yaml Dockerfile docs/install.md
version = "1.4.0"
demo-core = { path = "../core", version = "=1.4.0" }
version = "1.4.0"
version: 1.4.0
appVersion: "1.4.0"
      org.opencontainers.image.version="1.4.0"
cargo install demo-cli@1.4.0
$ grep -E '^(version|date-released)' CITATION.cff
version: 1.4.0
date-released: "2026-11-25"
$ grep '"version"' packages/web/package.json
  "version": "0.0.0",
```

The web package was left at `0.0.0`: it has its own tag, so the repository's
version is not its version. Stamping it is a separate run:

```console
$ gitversioned version -p web --write
0.9.0
  packages/web/package.json  0.9.0
```

The stamped files do not make the tree dirty, so the version is still the
release:

```console
$ gitversioned version
1.4.0
$ git checkout -q .
```

### Its own release line

Commits under `packages/web` belong to the web package, and the rest of the
repository does not see them:

```console
$ echo 'export const name = "web";' > packages/web/index.js && git add -A && git commit -qm "fix(web): shorter name"
$ gitversioned version -p web --next
0.9.1
$ gitversioned version --next
fail  Nothing to release since 1.4.0: no commit since is a feat, a fix or another releasable type.
[exit 1]
$ gitversioned release -p web | sed -n '1,3p'
release   0.9.1  (patch, from commits, from 0.9.0)
tag       web-v0.9.1
files     packages/web/CHANGELOG.md, packages/web/package.json
```

## How it works

- Discovery finds `src/demo/version.py` (generated, never committed), each
  crate's `Cargo.toml` with its path-dependency pins, `Cargo.lock`,
  `charts/demo/Chart.yaml` (`version` and `appVersion`), `CITATION.cff`
  (`version`, and `date-released` on a release), the OCI version label in the
  `Dockerfile`, and `packages/web/package.json`.
- [`.config/gitversioned.toml`](.config/gitversioned.toml) adds the docs page
  as a `pattern` target, limits scopes, and gives `packages/web` its own tag.

## Next

- [template-polyglot](../template-polyglot/README.md) for the full layout markurtz/template renders.
- [monorepo-packages](../monorepo-packages/README.md) for more on `[packages]`.
