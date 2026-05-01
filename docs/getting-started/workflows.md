# Workflows

This page walks through the most common end-to-end usage patterns for `gitversioned`. Each workflow is a self-contained user story — pick the one that matches your use case.

## Workflow 1 — Basic Usage

**Goal:** Perform the most common, standard operation with `gitversioned`.

### Steps

1. **Initialize the repository**

```bash
gitversioned init
```

2. **Configure your project**

Update the generated `pyproject.toml` or `gitversioned.toml` configuration as needed.

3. **Generate the version**

```bash
gitversioned generate
```

4. **Verify the output**

Check the generated `version.py` for correctness.

## Workflow 2 — Docker-Based Execution

**Goal:** Run `gitversioned` in a containerized environment without any local setup.

### Steps

1. **Pull the image**

   ```bash
   docker pull ghcr.io/markurtz/git-versioned:latest
   ```

1. **Run with environment variables**

   ```bash
   docker run --rm \
     -v $(pwd):/workspace \
     ghcr.io/markurtz/git-versioned:latest \
     gitversioned generate
   ```

1. **Inspect the output**

   ```bash
   cat version.py
   ```

## Workflow 3 — CI/CD Integration

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
          pip install gitversioned

      - name: Generate version metadata
        run: gitversioned generate

```

**Need more?** See the [Guides](../guides/index.md) section for in-depth task-specific documentation or browse the [Examples](../examples/index.md) for runnable code.
