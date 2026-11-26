# setuptools from setup.cfg and setup.py

Older setuptools projects keep their metadata in `setup.cfg` and call `setup()`
from `setup.py`, with no `pyproject.toml`. `setup(gitversioned=True)` turns the
integration on, and the `[tool:gitversioned]` table in `setup.cfg` holds the
settings.

| Level    | Build backend         | Needs                    |
| -------- | --------------------- | ------------------------ |
| Beginner | setuptools (setup.py) | Python, `build`, `setuptools` |

## Run

Copy this folder anywhere and run the commands below in it. The transcript is
checked on every test run, so it is exactly what you will see, apart from
hashes and dates.

```console
$ git init -q && git add -A && git commit -qm "feat: first version" && git tag v0.4.2
$ gitversioned version
0.4.2
$ python -m build --wheel --no-isolation >/dev/null 2>&1 && ls dist
legacy_app-0.4.2-py3-none-any.whl
$ gitversioned version --explain | tail -1
config    setup.cfg [tool:gitversioned]  (1 key set, 27 defaults)
```

Before the first tag, the fallback from `setup.cfg` is the base:

```console
$ git tag -d v0.4.2 >/dev/null && gitversioned version
0.0.1.dev20261125+34335b3
```

## How it works

- [`setup.py`](setup.py) passes `gitversioned=True` to `setup()`.
- [`setup.cfg`](setup.cfg) holds the metadata and a `[tool:gitversioned]` table.
- `version.py` is generated only for projects with a `pyproject.toml`; here
  the version is in the wheel's metadata (`importlib.metadata.version`).
- With no `pyproject.toml`, the build runs setuptools' legacy backend, which
  needs gitversioned installed where the build runs (pip's
  `--no-build-isolation`, or a `pyproject.toml` that lists it in
  `build-system.requires`).

## Next

- [setuptools](../setuptools/README.md) for the `pyproject.toml` form.
