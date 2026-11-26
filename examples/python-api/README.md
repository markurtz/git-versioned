# The Python API

The command line is a thin layer over a small Python API: `load_config`,
`resolve`, `stamp`, `plan_release` and `get_version`, plus `Version` and the
error classes. [`main.py`](main.py) calls each one and asserts the answer, so it
exits non-zero if the API ever disagrees with this page.

| Level        | Shows                                                                   | Needs  |
| ------------ | ----------------------------------------------------------------------- | ------ |
| Intermediate | `load_config`, `resolve`, `stamp`, `plan_release`, `get_version`, `Version` | Python |

## Run

Copy this folder anywhere and run the commands below in it. The transcript is
checked on every test run, so it is exactly what you will see, apart from
hashes and dates.

```console
$ git init -q && git add -A && git commit -qm "feat: first version" && git tag v0.8.0
$ echo "x = 1" > src/apidemo/parse.py && git add -A && git commit -qm "fix(core): parse empty input"
$ python main.py
version  0.8.1.dev20261125+70c4d2b (dev, from tag)
semver   0.8.1-dev.20261125+70c4d2b
tag      v0.8.0, 1 commit(s) since, sha 70c4d2b
stamp    src/apidemo/version.py -> 0.8.1.dev20261125+70c4d2b (commit=False)
release  0.8.1 as v0.8.1 (patch, from commits, from 0.8.0)
## [0.8.1] - 2026-11-25

### Fixed

- **core**: parse empty input
```

The same answers from the command line:

```console
$ gitversioned version && gitversioned release | sed -n '1,2p'
0.8.1.dev20261125+70c4d2b
release   0.8.1  (patch, from commits, from 0.8.0)
tag       v0.8.1
```

## How it works

[`main.py`](main.py) in reading order:

1. `load_config(root)` finds the settings home (none here) and returns a
   `Config`.
1. `resolve(config)` returns a `Resolved`: the version, its type and source, the
   tag, the distance and the commit.
1. `stamp(config, resolved, dry_run=True)` returns one `Change` per target
   without writing; without `dry_run` it writes them.
1. `plan_release(config)` returns a `ReleasePlan`, or raises
   `NothingToReleaseError` when nothing is releasable.

The [API guide](https://markurtz.github.io/git-versioned/guides/api/) documents
every function.

## Next

- [release-local](../release-local/README.md) for the same plan from the command line.
