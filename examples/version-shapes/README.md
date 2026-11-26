# Every version shape

Every version gitversioned prints, from one small Python project: releases,
development builds, dirty trees, nightlies and pre-releases, in PEP 440 and in
SemVer, with the settings and environment variables that shape them.

| Level    | Shows                                                       | Needs  |
| -------- | ----------------------------------------------------------- | ------ |
| Beginner | `version`, `--type`, `--standard`, `--json`, `-C`, `dev`, `nightly`, `date`, `local`, `fallback` | Python |

## Run

Copy this folder anywhere and run the commands below in it. The transcript is
checked on every test run, so it is exactly what you will see, apart from
hashes and dates.

### Before the first tag

A repository with no release tag yet uses the fallback, `0.1.0`, as the base of
a development version. `check` reports it.

```console
$ git init -q && git add -A && git commit -qm "feat: first version"
$ gitversioned version
0.1.0.dev20261125+d49ed04
$ gitversioned check | sed -n '1,2p'
ok    config        defaults
warn  git           no release tags match 'v{version}'; versions start from the fallback 0.1.0.
```

### A release

A clean checkout of a release tag is that release:

```console
$ git tag v1.2.0
$ gitversioned version
1.2.0
$ gitversioned version --standard semver
1.2.0
```

### Development builds

Each commit after a tag is a development build of the next patch release. The
number is the commit date, so two builds of one commit agree, and the local part
is the short commit hash. Python projects print PEP 440 by default; everything
else prints SemVer.

```console
$ echo "x = 1" > src/shapes/extra.py && git add -A && git commit -qm "feat: add extra"
$ gitversioned version
1.2.1.dev20261125+afe97a0
$ gitversioned version --standard semver
1.2.1-dev.20261125+afe97a0
```

Uncommitted changes add `.dirty` to the local part:

```console
$ echo "y = 2" >> src/shapes/extra.py
$ gitversioned version
1.2.1.dev20261125+afe97a0.dirty
$ git checkout -q -- src/shapes/extra.py
```

PyPI and npm refuse local parts, so a development upload turns them off:

```console
$ GITVERSIONED__LOCAL=false gitversioned version
1.2.1.dev20261125
```

The base of a development build is the next patch by default. `dev = "minor"`
or `"major"` moves it up, and `dev = "next"` asks the commits, here a `feat`:

```console
$ GITVERSIONED__DEV=minor gitversioned version
1.3.0.dev20261125+afe97a0
$ GITVERSIONED__DEV=next gitversioned version
1.3.0.dev20261125+afe97a0
```

`date = "build"` dates the number by the build instead of the commit
(`SOURCE_DATE_EPOCH` fixes the build time for reproducible builds):

```console
$ GITVERSIONED__DATE=build SOURCE_DATE_EPOCH=1798761600 gitversioned version
1.2.1.dev20270101+afe97a0
```

### Nightly builds

A nightly is based on the next release the commits ask for and never carries a
local part, so registries accept it:

```console
$ gitversioned version --type nightly
1.3.0.dev20261125
$ gitversioned version --type nightly --standard semver
1.3.0-nightly.20261125
```

`--type release` prints the version a release of this commit would get, and
`--type dev` forces a development version even on a tag.

```console
$ gitversioned version --type release
1.3.0
```

### Pre-releases

Release candidate tags are read in either spelling, `v1.3.0-rc.1` or
`v1.3.0rc1`. A checkout of one is that pre-release, and builds after it are
development builds of the next candidate, so they sort above it:

```console
$ git tag v1.3.0-rc.1
$ gitversioned version
1.3.0rc1
$ gitversioned version --standard semver
1.3.0-rc.1
$ echo "z = 3" >> src/shapes/extra.py && git commit -qam "fix: tweak extra"
$ gitversioned version
1.3.0rc2.dev20261125+95dd958
```

### For scripts

`--json` prints every field, and `-C` runs as if started in another folder:

```console
$ cd .. && gitversioned version -C version-shapes --json
{
  "version": "1.3.0rc2.dev20261125+95dd958",
  "pep440": "1.3.0rc2.dev20261125+95dd958",
  "semver": "1.3.0-rc.2.dev.20261125+95dd958",
  "type": "dev",
  "prerelease": true,
  "source": "tag",
  "tag": "v1.3.0-rc.1",
  "distance": 1,
  "sha": "95dd958",
  "dirty": false,
  "warnings": [],
  "written": [],
  "next": "1.3.0"
}
```

A tag that looks like a version but does not match the tag template is not
used silently:

```console
$ git init -q ../other && cd ../other && git commit -q --allow-empty -m "feat: start" && git tag 2.0.0
$ cd ../other && gitversioned version
WARNING tag 2.0.0 looks like a version but does not match the tag template 'v{version}'; using fallback 0.1.0. Set `tag` to match them.
0.1.0-dev.20261125+8fd1f5c
```

## How it works

- [`pyproject.toml`](pyproject.toml) is a Hatchling project, so the default
  spelling is PEP 440. There are no gitversioned settings; the variables above
  stand in for keys you could set in `[tool.gitversioned]` instead.
- The [concepts guide](https://markurtz.github.io/git-versioned/guides/concepts/)
  explains the order sources are read in and how bases are chosen.

## Next

- [next-version](../next-version/README.md) for how the next release is chosen.
- [ci-safety](../ci-safety/README.md) for what happens when the history is missing.
