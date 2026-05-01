# Quick Start

This guide gets you from a fresh installation to running your first command in under 5 minutes.

> [!NOTE]
> Make sure you have completed [Installation](installation.md) before continuing.

## Step 1 — Initialize Your Environment

If you haven't already, set up your project and install `gitversioned`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install gitversioned
```

## Step 2 — Verify the Install

```bash
gitversioned --version
```

Expected output:

```console
gitversioned 0.1.0
```

## Step 3 — Run Your First Command

```bash
# Example: Generate version.py
gitversioned generate
```

Expected output:

```console
[INFO] Generating version...
[SUCCESS] version.py created! Version: 0.1.0
```

> [!TIP]
> You can also configure GitVersioned directly within your `pyproject.toml`. See the [Reference](../reference/index.md) for all available configuration options.

## Step 4 — Explore Further

Now that your first command works, explore what `gitversioned` can do:

- **[Workflows](workflows.md)** — Common end-to-end usage patterns
- **[Guides](../guides/index.md)** — Task-specific deep dives
- **[Reference](../reference/index.md)** — Full API and CLI documentation
- **[Examples](../examples/index.md)** — Runnable code examples

**Next:** [Workflows →](workflows.md)
