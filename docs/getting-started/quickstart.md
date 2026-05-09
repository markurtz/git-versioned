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

## Step 3 — A Complete Scenario

Let's look at a realistic, full-featured scenario for a standard Git repository utilizing Hatch. In this scenario, your `src` directory is under `project/src/package` (standard for Hatch). We will configure `gitversioned` to use tag-based versioning, document the default formats, and set up auto-incrementing rules for your development and pre-release builds.

Add the following to your `pyproject.toml`:

```toml
[tool.gitversioned]
# Only use git tags to resolve the base version
source_type = ["tag"]

# These are the default formats, explicitly documented here for reference:
format_main = "{version.major}.{version.minor}.{version.micro}"
format_dev = "dev{ref.timestamp:%Y%m%d}+{ref.short_sha}"
format_pre = "a{ref.timestamp:%Y%m%d}"
format_post = "post{ref.distance_from_head}"

[tool.gitversioned.auto_increment]
# Auto-increment the minor version for pre-releases (and nightlies)
# Example: If the last tag is 1.0.0, the next pre-release will be 1.1.0a...
pre = "minor"
nightly = "minor"

# Auto-increment the patch/micro version for dev builds to differentiate from the last release
# Example: If the last tag is 1.0.0, your local dev build will be 1.0.1.dev...
dev = "patch"
```

### CI/CD Version Resolution

By default, the `version_type` is set to `auto`. GitVersioned will intelligently determine what to build:

- If your source code perfectly matches the last version tag (e.g., you are building locally immediately after a release, or CI is building a tag), it builds a **release**.
- If there are new commits since the last tag, it builds a **dev** build.

In your CI/CD workflows, you can override this behavior using the `GITVERSIONED__VERSION_TYPE` environment variable to force specific release types based on the trigger:

- **On Tag:** Leave as `auto` (or force `release`), and it will build a release.
- **On Nightly:** Set `GITVERSIONED__VERSION_TYPE=nightly` to build a pre-release for the next minor version.
- **On User Invocation:** Set `GITVERSIONED__VERSION_TYPE=post` to build a post-release.

> [!TIP]
> You can configure GitVersioned directly within your `pyproject.toml`. See the [Reference](../reference/index.md) for all available configuration options.

## Step 4 — Explore Further

Now that your first command works, explore what `gitversioned` can do:

- **[Workflows](workflows.md)** — Common end-to-end usage patterns
- **[Guides](../guides/index.md)** — Task-specific deep dives
- **[Reference](../reference/index.md)** — Full API and configuration documentation
- **[Examples](../examples/index.md)** — Runnable code examples

**Next:** [Workflows →](workflows.md)
