# Quick Start

This guide gets you from a fresh installation to running your first command in under 5 minutes.

> [!NOTE]
> Make sure you have completed [Installation](installation.md) before continuing.

## Step 1 — Initialize Your Environment

If you haven't already, set up your project and install `{{ project_name }}`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install project_name
```

## Step 2 — Verify the Install

```bash
{{ project_name }} --version
```

Expected output:

```console
{{ project_name }} 0.1.0
```

## Step 3 — Run Your First Command

```python
from project_name import Client

# Initialize the client
client = Client(api_key="YOUR_KEY")

# Run a core action
result = client.run_action("hello_world")
print(result)
```

Expected output:

```console
[INFO] Initializing {{ project_name }} client...
[SUCCESS] Action completed! Result: Hello, World from {{ project_name }}!
```

> [!TIP]
> Replace `"YOUR_KEY"` with your actual API key or credentials. See the [Reference](../reference/index.md) for all available client configuration options.

## Step 4 — Explore Further

Now that your first command works, explore what `{{ project_name }}` can do:

- **[Workflows](workflows.md)** — Common end-to-end usage patterns
- **[Guides](../guides/index.md)** — Task-specific deep dives
- **[Reference](../reference/index.md)** — Full API and CLI documentation
- **[Examples](../examples/index.md)** — Runnable code examples

**Next:** [Workflows →](workflows.md)
