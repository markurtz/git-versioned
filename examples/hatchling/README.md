# Hatchling, zero config

A pure Python package built with Hatchling whose version comes from its git
tags. Nothing is configured: there is no `[tool.gitversioned]` table.

| Level    | Build backend | Needs                     |
| -------- | ------------- | ------------------------- |
| Beginner | Hatchling     | Python, `build`, `hatchling` |

## Run

Copy this folder anywhere and run the commands below in it. The transcript is
checked on every test run, so it is exactly what you will see, apart from
hashes and dates.

```console
$ git init -q && git add -A && git commit -qm "feat: first version"
$ git tag v1.2.3
$ gitversioned version
1.2.3
$ gitversioned check
ok    config        defaults
ok    git           full history, 1 release tag, latest v1.2.3
ok    targets       src/demo_hatch/version.py
warn  archive file  .git_archival.txt is not set up, so source tarballs lose the version. Run `gitversioned init`.
warn  github        gh is missing or not signed in: release --pr, GitHub releases and pull request titles in the changelog are unavailable.
```

Build a wheel and an sdist. Both are named for the tag, and the wheel carries a
generated `version.py`:

```console
$ python -m build --no-isolation >/dev/null 2>&1 && ls dist
demo_hatch-1.2.3-py3-none-any.whl
demo_hatch-1.2.3.tar.gz
$ unzip -p dist/demo_hatch-1.2.3-py3-none-any.whl demo_hatch/version.py | grep -E "^__(version|tag|distance)__"
__version__ = version = "1.2.3"
__tag__ = "v1.2.3"
__distance__ = 0
$ git status --short
```

A commit after the tag gives a development version, one patch above the tag,
dated by the commit and carrying the commit hash as a local part:

```console
$ echo '"""A demo package."""' > src/demo_hatch/extra.py && git add -A && git commit -qm "fix: add a module"
$ gitversioned version
1.2.4.dev20261125+488b5b3
$ gitversioned version --standard semver
1.2.4-dev.20261125+488b5b3
```

The sdist builds again without git, from the version recorded in its
`PKG-INFO`, which is how pip installs it:

```console
$ mkdir ../unpacked && tar -xzf dist/demo_hatch-1.2.3.tar.gz -C ../unpacked
$ cd ../unpacked/demo_hatch-1.2.3 && python -m build --wheel --no-isolation >/dev/null 2>&1 && ls dist
demo_hatch-1.2.3-py3-none-any.whl
```

## How it works

- [`pyproject.toml`](pyproject.toml) has three gitversioned lines:
  `gitversioned` in `build-system.requires`, `source = "gitversioned"` under
  `[tool.hatch.version]`, and the `[tool.hatch.build.hooks.gitversioned]` table,
  which writes `src/demo_hatch/version.py` into the wheel and the sdist.
- [`.gitignore`](.gitignore) ignores `version.py`, so it is never committed and
  builds never make the tree dirty.
- [`src/demo_hatch/__init__.py`](src/demo_hatch/__init__.py) re-exports
  `__version__` from the generated module.

## Next

- [setuptools](../setuptools/README.md) for the same with setuptools.
- [version-shapes](../version-shapes/README.md) for every version gitversioned prints.
