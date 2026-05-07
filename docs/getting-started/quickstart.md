# Quick Start

This guide gets you from a fresh installation to running your first command in under 5 minutes.

> [!NOTE]
> Make sure you have completed [Installation](installation.md) before continuing.

## Step 1 — Initialize Your Environment

If you haven't already, set up your project and install `gitversioned`:

Choose your preferred package manager to set up your environment:

=== "uv (Recommended)"

````
```bash
uv init .
uv add gitversioned
```
````

=== "pip"

````
```bash
python -m venv .venv
source .venv/bin/activate
pip install gitversioned
```
````

## Step 2 — Configure the Build System

GitVersioned is primarily used automatically by your build system. Add it to your `pyproject.toml` (using Hatchling as an example):

```toml
[build-system]
requires = ["hatchling", "gitversioned"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "gitversioned"
```

Now, any time you build your package, the version will be dynamically resolved based on your Git repository state!

> [!TIP]
> You can configure GitVersioned directly within your `pyproject.toml`. See the [Reference](../reference/index.md) for all available configuration options.

## Step 3 — Explore Further

Now that your first command works, explore what `gitversioned` can do:

- **[Workflows](workflows.md)** — Common end-to-end usage patterns
- **[Guides](../guides/index.md)** — Task-specific deep dives
- **[Reference](../reference/index.md)** — Full API and configuration documentation
- **[Examples](../examples/index.md)** — Runnable code examples

**Next:** [Workflows →](workflows.md)
