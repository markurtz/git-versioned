# Hatchling example

A pure Python project whose version comes from git tags at build time.

```bash
git tag v1.2.3
python -m build            # demo_hatch-1.2.3-py3-none-any.whl
gitversioned version       # 1.2.3
```

`pyproject.toml` needs three things: `gitversioned` in `build-system.requires`,
`source = "gitversioned"` under `[tool.hatch.version]`, and the
`[tool.hatch.build.hooks.gitversioned]` table, which adds the generated
`version.py` to the wheel and sdist. There is no `[tool.gitversioned]` table
because every default fits.
