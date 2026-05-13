---
hide:
  - navigation
  - toc
---

<div class="hero" markdown>
<div class="hero-content" markdown>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/branding/logo-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/branding/logo-light.svg">
  <img alt="GitVersioned Logo" src="assets/branding/logo-light.svg" width="400">
</picture>

# GitVersioned

**Opinionated PEP 440 Python versioning for Git repos and submodules. Enforces CI/User authority and generates rich version.py files with deep metadata for auditability. Native Hatch & Setuptools support. Simple, predictable, and foolproof automation.**

[Get Started](getting-started/index.md){ .md-button .md-button--primary }
[View on GitHub](https://github.com/markurtz/git-versioned){ .md-button }

</div>
</div>

## Overview

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/branding/user-flow-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/branding/user-flow-light.svg">
    <img alt="User Flow Diagram" src="assets/branding/user-flow-light.svg" width="800">
  </picture>
</p>

## What's Included

<div class="grid" markdown>

<div class="card" markdown>
:material-rocket-launch-outline: **Getting Started**

______________________________________________________________________

Installation guide, quick start tutorial, and common workflow walkthroughs.

[:octicons-arrow-right-24: Get Started](getting-started/index.md)

</div>

<div class="card" markdown>
:material-book-open-outline: **Guides**

______________________________________________________________________

Step-by-step guides for common tasks, integrations, and configuration patterns.

[:octicons-arrow-right-24: Browse Guides](guides/index.md)

</div>

<div class="card" markdown>
:material-code-braces: **Examples**

______________________________________________________________________

Runnable code examples that demonstrate real-world usage of GitVersioned.

[:octicons-arrow-right-24: See Examples](examples/index.md)

</div>

<div class="card" markdown>
:material-file-document-outline: **Reference**

______________________________________________________________________

Full API reference and configuration schema.

[:octicons-arrow-right-24: View Reference](reference/index.md)

</div>

<div class="card" markdown>
:material-account-group-outline: **Community**

______________________________________________________________________

Contributing guide, developer setup, Code of Conduct, and support resources.

[:octicons-arrow-right-24: Get Involved](community/index.md)

</div>

<div class="card" markdown>
:material-shield-lock-outline: **Security**

______________________________________________________________________

Our security policy, responsible disclosure process, and supported versions.

[:octicons-arrow-right-24: Security Policy](community/security.md)

</div>

</div>

## Quick Install

### Build Configuration

GitVersioned is primarily used as a build plugin. The preferred pathway is to configure it in your `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling", "gitversioned"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "gitversioned"
```

For advanced installation options, Setuptools alternatives, and step-by-step onboarding, see the [Installation Guide](getting-started/installation.md).

## Links

- :material-github: [GitHub Repository](https://github.com/markurtz/git-versioned)
- :material-map-marker-path: [Roadmap](https://github.com/markurtz/git-versioned/milestones)
- :material-post-outline: [Blog](https://blog.markurtz.org)
- :material-slack: [Slack Community](https://slack.markurtz.org)
