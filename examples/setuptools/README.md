# setuptools from pyproject.toml

A setuptools package whose version comes from its git tags. Listing
`gitversioned` in `build-system.requires` is the opt-in; settings live in the
`[tool.gitversioned]` table of the same file.

| Level    | Build backend | Needs                             |
| -------- | ------------- | --------------------------------- |
| Beginner | setuptools    | Python, `build`, `setuptools>=64` |

## Run

Copy this folder anywhere and run the commands below in it. The transcript is
checked on every test run, so it is exactly what you will see, apart from
hashes and dates.

```console
$ git init -q && git add -A && git commit -qm "feat(core): first version" && git tag v2.1.0
$ gitversioned version
2.1.0
$ python -m build --wheel --no-isolation >/dev/null 2>&1 && ls dist
demo_setuptools-2.1.0-py3-none-any.whl
$ unzip -p dist/demo_setuptools-2.1.0-py3-none-any.whl demo_setuptools/version.py | grep "^__version__"
__version__ = version = "2.1.0"
$ git status --short
```

The settings in `pyproject.toml` limit commit scopes to `core` and `docs`:

```console
$ gitversioned check "feat(core): add a thing"
ok
$ gitversioned check "feat(web): add a page"
fail  title  unknown scope 'web'. Scopes: core, docs.
[exit 1]
$ gitversioned version --explain | tail -1
config    pyproject.toml [tool.gitversioned]  (1 key set, 27 defaults)
```

A commit after the tag builds a development version:

```console
$ echo "x = 1" > src/demo_setuptools/extra.py && git add -A && git commit -qm "fix(core): add extra"
$ rm -rf dist build && python -m build --wheel --no-isolation >/dev/null 2>&1 && ls dist
demo_setuptools-2.1.1.dev20261125+474e126-py3-none-any.whl
```

`--no-isolation` is only here because the test runs against the gitversioned
under test; a normal `python -m build` installs it from PyPI.

## How it works

- [`pyproject.toml`](pyproject.toml): `gitversioned` in `build-system.requires`,
  `dynamic = ["version"]`, and a `[tool.gitversioned]` table with `scopes`.
- The build writes `src/demo_setuptools/version.py`, which
  [`.gitignore`](.gitignore) keeps out of git.

## Next

- [setuptools-legacy](../setuptools-legacy/README.md) for `setup.cfg` and `setup.py`.
- [commit-checks](../commit-checks/README.md) for everything `check` does.
