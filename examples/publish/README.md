# Publishing to PyPI, crates.io and npm

`release --publish` builds the tagged release and uploads it to every registry
the project has a manifest for: PyPI, crates.io and npm. `--dry-run` runs each
tool's own dry run, which is what the transcript below shows.

| Level        | Shows                                                    | Needs              |
| ------------ | -------------------------------------------------------- | ------------------ |
| Intermediate | `release --publish`, `--dry-run`, `publish`, `--json`     | git, uv, cargo, npm |

## Run

Copy this folder anywhere and run the commands below in it. The dry runs reach
PyPI, crates.io and npm to check the packages, so they need the network.

```console
$ git init -q && git add -A && git commit -qm "feat: first release"
$ gitversioned release --publish --dry-run
fail  HEAD has no release tag. Publish from the tagged release commit, or run release --tag first.
[exit 1]
$ gitversioned release 1.0.0 --write | tail -1 && git commit -qam "release: v1.0.0" && gitversioned release --tag
Wrote CHANGELOG.md, Cargo.toml, package.json, pyproject.toml, Cargo.lock.
tag       v1.0.0 at 0da3f23, created locally
$ gitversioned release --publish --dry-run
publish   cargo publish --workspace --locked --dry-run
publish   npm publish --dry-run
publish   uv build --out-dir dist
publish   uv publish --dry-run dist/beam_gv-1.0.0-py3-none-any.whl dist/beam_gv-1.0.0.tar.gz
Dry run: nothing was uploaded.
$ gitversioned release --publish --dry-run --json | grep -A5 commands
    "commands": [
      "cargo publish --workspace --locked --dry-run",
      "npm publish --dry-run",
      "uv build --out-dir dist",
      "uv publish --dry-run dist/beam_gv-1.0.0-py3-none-any.whl dist/beam_gv-1.0.0.tar.gz"
    ],
$ GITVERSIONED__PUBLISH='["crates"]' gitversioned release --publish --dry-run
publish   cargo publish --workspace --locked --dry-run
Dry run: nothing was uploaded.
```

Without `--dry-run` the same commands upload. `release --tag --publish` tags,
pushes, publishes and then, with `forge_release = true`, creates the GitHub
release with the built files attached.

## How it works

- `publish` lists the registries; unset, a public `pyproject.toml` means PyPI,
  `Cargo.toml` crates.io and a `package.json` that is not private npm. A
  `Private :: Do Not Upload` classifier keeps a Python project off PyPI.
- PyPI uses `uv build` and `uv publish` when uv is installed, otherwise
  `python -m build` and `twine upload`. crates.io gets
  `cargo publish --workspace --locked`, which orders a workspace's crates, and
  npm gets `npm publish`, with `--tag next` for a pre-release and
  `--workspaces` for a workspace.
- Each tool reads its own credentials: `UV_PUBLISH_TOKEN` or trusted publishing
  in CI, `CARGO_REGISTRY_TOKEN` and `NODE_AUTH_TOKEN`. Publishing only runs on
  a commit with a release tag.
- `-p NAME` publishes one package from its own folder.

## Next

- [forges](../forges/README.md) for the GitHub release the files attach to.
- [github-actions](../github-actions/README.md) for the release workflow.
