# Workflows

This page walks through the most common end-to-end usage patterns for `gitversioned`. Each workflow is a self-contained user story — pick the one that matches your use case.

## Workflow 1 — CI/CD Integration

**Goal:** Integrate `gitversioned` into a GitHub Actions pipeline.

```yaml
# .github/workflows/run.yml
name: Run gitversioned

on: [push]

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up environment
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"

      - name: Install gitversioned
        run: |
          # Or optionally using uv: uv pip install gitversioned
          pip install gitversioned

      - name: Generate version metadata
        run: gitversioned generate

```

**Need more?** See the [Guides](../guides/index.md) section for in-depth task-specific documentation or browse the [Examples](../examples/index.md) for runnable code.
