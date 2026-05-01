# Workflows

This page walks through the most common end-to-end usage patterns for `{{ project_name }}`. Each workflow is a self-contained user story — pick the one that matches your use case.

> [!NOTE]
> These are placeholder workflows. Replace each section with the real workflows that users of your project will follow.

## Workflow 1 — Basic Usage

**Goal:** Perform the most common, standard operation with `{{ project_name }}`.

### Steps

1. **Initialize the client**

```python
from {{ project_name }} import Client
client = Client(api_key="YOUR_KEY")
```

2. **Configure your inputs**

```python
config = {"mode": "fast", "retries": 3}
```

3. **Execute the action**

```python
result = client.run_action("hello_world", config=config)
```

4. **Handle the output**

```python
print(f"Success: {result}")
```

## Workflow 2 — Docker-Based Execution

**Goal:** Run `{{ project_name }}` in a containerized environment without any local setup.

### Steps

1. **Pull the image**

   ```bash
   docker pull ghcr.io/{{ org_name }}/{{ project_name }}:latest
   ```

1. **Run with environment variables**

   ```bash
   docker run --rm \
     -e API_KEY="YOUR_KEY" \
     -v $(pwd)/output:/app/output \
     ghcr.io/{{ org_name }}/{{ project_name }}:latest \
     {{ project_name }} run --output /app/output
   ```

1. **Inspect the output**

   ```bash
   ls ./output/
   ```

## Workflow 3 — CI/CD Integration

**Goal:** Integrate `{{ project_name }}` into a GitHub Actions pipeline.

```yaml
# .github/workflows/run.yml
name: Run {{ project_name }}

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

      - name: Install {{ project_name }}
        run: |
          pip install .

      - name: Run action
        env:
          API_KEY: ${{ "{{" }} secrets.API_KEY {{ "}}" }}
        run: {{ project_name }} run --config config.yaml
```

**Need more?** See the [Guides](../guides/index.md) section for in-depth task-specific documentation or browse the [Examples](../examples/index.md) for runnable code.
