# Static versions for uv_build

uv_build, like Flit's core backend and Poetry's, reads a static
`[project].version` and has no plugin hook. gitversioned writes the version
into `pyproject.toml` before the build, then the build names everything for it.

| Level        | Build backend | Needs                                    |
| ------------ | ------------- | ---------------------------------------- |
| Intermediate | uv_build      | Python, [uv](https://docs.astral.sh/uv/) |

## Run

Copy this folder anywhere and run the commands below in it. The transcript is
checked on every test run, so it is exactly what you will see, apart from
hashes and dates.

```console
$ git init -q && git add -A && git commit -qm "feat: first version" && git tag v1.4.0
$ echo '"""Parsing."""' > src/demo_uv/parse.py && git add -A && git commit -qm "feat: parse input"
$ gitversioned check
ok    config        defaults
ok    git           full history, 1 release tag, latest v1.4.0
ok    targets       pyproject.toml
warn  archive file  .git_archival.txt is not set up, so source tarballs lose the version. Run `gitversioned init`.
warn  github        gh is missing or not signed in: release --pr, GitHub releases and pull request titles in the changelog are unavailable.
```

A nightly or a test build stamps the development version, builds, and puts the
file back, so nothing is committed:

```console
$ gitversioned version --write
1.4.1.dev20261125+bd86c17
  pyproject.toml  1.4.1.dev20261125+bd86c17
$ uv build -q 2>&1; ls dist
demo_uv-1.4.1.dev20261125+bd86c17-py3-none-any.whl
demo_uv-1.4.1.dev20261125+bd86c17.tar.gz
$ git checkout -q pyproject.toml && rm -rf dist && git status --short
```

A release writes the next version and the changelog. Commit them and tag that
commit, so the tag holds the released number and builds without gitversioned:

```console
$ gitversioned release --write
release   1.5.0  (minor, from commits, from 1.4.0)
tag       v1.5.0
files     CHANGELOG.md, pyproject.toml

## [1.5.0] - 2026-11-25

### Added

- parse input

Wrote CHANGELOG.md, pyproject.toml.
$ git add -A && git commit -qm "release: v1.5.0" && git tag v1.5.0 && grep '^version' pyproject.toml
version = "1.5.0"
$ uv build -q 2>&1; ls dist
demo_uv-1.5.0-py3-none-any.whl
demo_uv-1.5.0.tar.gz
$ gitversioned version && git status --short
1.5.0
```

## How it works

- [`pyproject.toml`](pyproject.toml) has a static `version = "0.0.0"`, which is
  only a placeholder: gitversioned finds it because `version` is not listed in
  `dynamic`, and lists `pyproject.toml` as a target.
- `version --write` writes the version and leaves the file changed, so run it in
  a throwaway checkout or restore the file after the build.
- `release --write` writes the same file and the changelog, and you commit
  them. The tag on that commit then matches the version in the file, so the
  sdist and anyone building from the tag get 1.5.0 without gitversioned.
- On a development checkout, `version --write` gives one patch above the tag
  whatever the commits are; `version --write --next` stamps the next release
  number instead.
- [`src/demo_uv/__init__.py`](src/demo_uv/__init__.py) reads `__version__` from
  the installed metadata, since uv_build writes no version module.

## Next

- [hatchling](../hatchling/README.md) for a backend with a build hook, where
  nothing is written to the tree.
- [release-local](../release-local/README.md) for the release commit in detail.
