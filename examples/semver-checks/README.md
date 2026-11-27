# API checks for Rust releases

`semver_checks = true` runs
[cargo-semver-checks](https://github.com/obi1kenobi/cargo-semver-checks)
against the last release tag whenever a release is planned. A breaking change
to the public API makes the release a major one, even when the commits only
asked for a patch, the way release-plz does.

| Level    | Shows                                       | Needs                           |
| -------- | ------------------------------------------- | ------------------------------- |
| Advanced | `semver_checks`, the level from an API diff | git, cargo, cargo-semver-checks |

## Run

Copy this folder anywhere and run the commands below in it. Install the checker
first with `cargo install cargo-semver-checks --locked`.

```console
$ git init -q && git add -A && git commit -qm "feat: first release" && gitversioned release 1.0.0 --write | tail -1 && git commit -qam "release: v1.0.0" && gitversioned release --tag
Wrote CHANGELOG.md, Cargo.toml, Cargo.lock.
tag       v1.0.0 at ..., created locally
$ printf '//! The beam API.\n\n/// Parse a beam definition.\npub fn parse(text: &str) -> usize {\n    text.len()\n}\n' > src/lib.rs && git commit -qam "fix: tidy the API"
$ gitversioned release | head -1
release   2.0.0  (major, from cargo semver-checks, from 1.0.0)
$ GITVERSIONED__SEMVER_CHECKS=false gitversioned release | head -1
release   1.0.1  (patch, from commits, from 1.0.0)
```

The commit called removing `render` a fix; the API diff says it breaks callers,
so the release is 2.0.0.

## How it works

- The check runs `cargo semver-checks --workspace --baseline-rev <last tag>`
  from the project root. It only raises the level: a release the commits
  already make major is not checked.
- Below 1.0.0 the major is shifted to a minor, like any breaking change, unless
  `zero_shift = false`.
- Without cargo-semver-checks installed the plan stops with exit 3 and the
  install command.

## Next

- [rust-workspace](../rust-workspace/README.md) for versions in a Cargo workspace.
- [next-version](../next-version/README.md) for the other ways the level is chosen.
