# Settings, homes and the environment

A repository needs no settings at all. When it does have some, they live in
exactly one of six homes, unknown keys are errors that name the nearest valid
one, and every root key can come from the environment instead.

| Level        | Shows                                                               | Needs |
| ------------ | ------------------------------------------------------------------- | ----- |
| Intermediate | the six homes, `GITVERSIONED__KEY`, `tag`, `fallback`, `-v`, `-q`, exit code 2 | git   |

## Run

Copy this folder anywhere and run the commands below in it. The transcript is
checked on every test run, so it is exactly what you will see, apart from
hashes and dates.

### Defaults

`--explain` names where the settings came from:

```console
$ git init -q && git add -A && git commit -qm "feat: first version" && git tag v1.0.0
$ gitversioned version --explain | tail -1
config    defaults  (0 keys set, 14 defaults)
```

### One home

The first home found wins: `.config/gitversioned.toml`, `gitversioned.toml`,
`[tool.gitversioned]` in `pyproject.toml`, `[workspace.metadata.gitversioned]`
in `Cargo.toml`, `"gitversioned"` in `package.json`, then
`[tool:gitversioned]` in `setup.cfg`.

```console
$ printf 'annotated = true\n' > gitversioned.toml && gitversioned version --explain | tail -1
config    gitversioned.toml  (1 key set, 13 defaults)
$ printf '{"name": "demo", "version": "0.0.0", "gitversioned": {"branch": "trunk"}}\n' > package.json
$ gitversioned version
fail  settings found in two homes: gitversioned.toml and package.json "gitversioned". Keep them in one file.
[exit 2]
$ rm gitversioned.toml && gitversioned version --explain | tail -1
config    package.json "gitversioned"  (1 key set, 13 defaults)
$ rm package.json
```

### Mistakes are errors

An unknown key names the nearest valid one, and so does a 0.3 key that no
longer exists. Bad configuration exits with code 2:

```console
$ printf 'tga = "v{version}"\n' > gitversioned.toml && gitversioned version
fail  unknown key `tga` in gitversioned.toml. Did you mean `tag`? Valid keys: version, fallback, tag, annotated, branch, dev, nightly, date, local, changelog, types, scopes, targets, packages.
[exit 2]
$ printf 'version_type = "dev"\n' > gitversioned.toml && gitversioned version
fail  unknown key `version_type` in gitversioned.toml. `version_type` was removed in 0.4: pass --type on the command line. Valid keys: version, fallback, tag, annotated, branch, dev, nightly, date, local, changelog, types, scopes, targets, packages.
[exit 2]
$ printf 'dev = "huge"\n' > gitversioned.toml && gitversioned version
fail  invalid config in gitversioned.toml: dev: Input should be 'patch', 'minor', 'major' or 'next'
[exit 2]
$ rm gitversioned.toml
```

### Tag names

`tag` is both how release tags are named and how they are recognised. A
repository that tags `release-2.1.0` says so once:

```console
$ git tag release-2.1.0 && git commit -q --allow-empty -m "fix: after the release"
$ printf 'tag = "release-{version}"\n' > gitversioned.toml && gitversioned version --explain | sed -n '1,3p'
version   2.1.1-dev.20261125+2914331
type      dev
current   2.1.0  (tag release-2.1.0, 2914331, 1 commit since)
$ gitversioned check --tag release-2.2.0
ok    tag  2.2.0, newer than release-2.1.0
$ rm gitversioned.toml
```

### The environment

Any root key can be set as `GITVERSIONED__KEY`, which wins over the file. A
build job pins the version once and passes it on with `GITVERSIONED__VERSION`:

```console
$ GITVERSIONED__TAG='release-{version}' gitversioned version
2.1.1-dev.20261125+2914331
$ GITVERSIONED__VERSION=9.9.9 gitversioned version --explain
version   9.9.9
type      release
current   none (version given by the pin)
note      pinned to 9.9.9
config    defaults  (1 key set, 13 defaults)
```

A misspelled variable is not silently ignored:

```console
$ GITVERSIONED__TAGG='release-{version}' gitversioned version
WARNING ignoring unknown environment override GITVERSIONED__TAGG. Did you mean `tag`?
1.0.1-dev.20261125+2914331
```

`fallback` is the base before the first matching tag:

```console
$ GITVERSIONED__TAG='pkg-v{version}' GITVERSIONED__FALLBACK=0.0.1 gitversioned version
WARNING tags release-2.1.0, v1.0.0 look like versions but do not match the tag template 'pkg-v{version}'; using fallback 0.0.1. Set `tag` to match them.
0.0.1-dev.20261125+2914331
```

### How much it says

Results go to stdout and everything else to stderr. `-v` adds detail, `-vv`
debug output, and `-q` keeps only errors:

```console
$ gitversioned version -v
INFO    settings from defaults: all defaults
INFO    version 1.0.1.dev20261125+2914331 (dev, from tag); tag v1.0.0, 1 commit since
1.0.1-dev.20261125+2914331
$ GITVERSIONED__TAG='pkg-v{version}' gitversioned version -q
0.1.0-dev.20261125+2914331
```

## How it works

- The [configuration guide](https://markurtz.github.io/git-versioned/guides/configuration/)
  lists every key and its default.
- Two homes with settings in them are an error that names both files, so the
  answer never depends on which file was read first.

## Next

- [custom-targets](../custom-targets/README.md) for `[[targets]]`.
- [monorepo-packages](../monorepo-packages/README.md) for `[packages]`.
