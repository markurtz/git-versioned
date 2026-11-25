# Polyglot example

One repository holding a Python package at the root, a Cargo workspace, an npm
package with its own release line, a Helm chart, a citation file, a Dockerfile
and a docs page that mentions the version.

```bash
git tag v1.4.0
gitversioned version --write --dry-run
```

One command stamps every manifest, each in the spelling its ecosystem expects:

| File                       | What is stamped                              |
| -------------------------- | -------------------------------------------- |
| `Cargo.toml` of each crate | `package.version`, and path-dependency pins  |
| `Cargo.lock`               | The entries of the workspace crates          |
| `charts/demo/Chart.yaml`   | `version` and `appVersion`                   |
| `CITATION.cff`             | `version`, and `date-released` on a release  |
| `Dockerfile`               | The `org.opencontainers.image.version` label |
| `docs/install.md`          | The listed pattern target                    |
| `src/demo/version.py`      | Generated, not committed                     |

`packages/web` has `tag = "web-v{version}"`, so it is versioned on its own:

```bash
git tag web-v0.9.0
gitversioned version -p web          # 0.9.0
gitversioned release -p web          # plans web-v0.9.1 from commits under packages/web
```

Settings live in `.config/gitversioned.toml`.
