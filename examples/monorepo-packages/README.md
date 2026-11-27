# Packages with their own tags

A repository with a main Python package at the root and two packages under
`packages/`. `packages/core` has its own tags (`core-v0.5.0`) and its own
release line, like a release-please manifest entry or a release-plz crate.
`packages/web` has no tag, so it always ships with the repository's version.

| Level    | Shows                                                               | Needs  |
| -------- | ------------------------------------------------------------------- | ------ |
| Advanced | `[packages]`, `-p`, package tags, per-package changelogs and builds | Python |

## Run

Copy this folder anywhere and run the commands below in it. The transcript is
checked on every test run, so it is exactly what you will see, apart from
hashes and dates.

```console
$ git init -q && git add -A && git commit -qm "feat: first version" && git tag v1.0.0 && git tag core-v0.5.0
$ gitversioned version
1.0.0
$ gitversioned version -p core
0.5.0
$ gitversioned version -p web
1.0.0
```

### Commits belong to one line

A commit under `packages/core` moves only the core's line. The repository is
still on its release, because the core's folder is not part of it:

```console
$ echo "x = 1" > packages/core/src/mono_core/fast.py && git add -A && git commit -qm "fix(core): faster parsing"
$ gitversioned version
1.0.0
$ gitversioned version -p core
0.5.1.dev20261125+7a3f4c7
$ gitversioned version -p core --next
0.5.1
$ gitversioned version --next
fail  Nothing to release since 1.0.0: no commit since is a feat, a fix or another releasable type.
[exit 1]
```

A commit under `packages/web` belongs to the repository, since web follows it:

```console
$ echo '<h1>hi</h1>' > packages/web/index.html && git add -A && git commit -qm "feat(web): add a page"
$ gitversioned version --next
1.1.0
$ gitversioned version --write | grep web
  packages/web/package.json  1.0.1-dev.20261125+44b8223
$ git checkout -q packages/web
```

### Release the core on its own

`-p core` plans, writes and tags the core's release, with its own changelog in
its folder:

```console
$ gitversioned release -p core
release   0.5.1  (patch, from commits, from 0.5.0)
tag       core-v0.5.1
files     packages/core/CHANGELOG.md

## [0.5.1] - 2026-11-25

### Fixed

- **core**: faster parsing

Nothing changed. Run with --write, --pr or --tag.
$ gitversioned release -p core --write >/dev/null && git add -A && git commit -qm "release(core): core-v0.5.1"
$ gitversioned release -p core --tag
tag       core-v0.5.1 at 997d17e, created locally
$ git tag --list
core-v0.5.0
core-v0.5.1
v1.0.0
```

A build from the package's folder follows the package's tag:

```console
$ cd packages/core && python -m build --wheel --no-isolation >/dev/null 2>&1 && ls dist
mono_core-0.5.1-py3-none-any.whl
```

Packages without their own tag are released with the repository, and
`check --tag` validates package tags too:

```console
$ gitversioned release -p web
fail  package 'web' has no `tag` of its own, so it is released with the repository. Run the release without -p, or give the package a `tag` such as "web-v{version}".
[exit 2]
$ gitversioned check --tag core-v0.5.1 -p core
ok    tag        0.5.1 at HEAD, newer than core-v0.5.0
ok    changelog  packages/core/CHANGELOG.md has the section
```

## How it works

- [`gitversioned.toml`](gitversioned.toml) lists both packages; only `core` has
  a `tag`.
- Each package's targets, commits and changelog are scoped to its `path`.
  Folders of packages with their own tag are left out of the repository's.
- A build plugin finds the package a build folder belongs to, so
  `packages/core/pyproject.toml` needs no settings of its own.

## Next

- [polyglot](../polyglot/README.md) for a package with its own tag among many manifests.
- [release-pr](../release-pr/README.md) for release pull requests per package.
