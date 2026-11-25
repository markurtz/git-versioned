# Setuptools example

Listing `gitversioned` in `build-system.requires` is the opt-in. The version is
dynamic, and the build writes `src/demo_setuptools/version.py`.

```bash
git tag v2.1.0
python -m build --wheel    # demo_setuptools-2.1.0-py3-none-any.whl
gitversioned check "feat(core): add a thing"
```

The `[tool.gitversioned]` table here shows the settings living in
`pyproject.toml` and limits commit scopes to `core` and `docs`.
