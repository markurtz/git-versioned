---
hide:
  - navigation
  - toc
---

<!--
Copyright 2026 markurtz

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Unless otherwise noted, all files in this directory and its subdirectories
are licensed under the Apache License, Version 2.0.
-->

<div class="hero" markdown>
<div class="hero-content" markdown>

<img alt="GitVersioned Logo" src="assets/branding/logo-light.svg#only-light" width="400">
<img alt="GitVersioned Logo" src="assets/branding/logo-dark.svg#only-dark" width="400">

# GitVersioned

**Opinionated compliance-first versioning automation for Git repositories. Enforces CI/User authority and generates rich metadata. Supports Python, Rust (Maturin), Docker/OCI, and multi-file version synchronization via declarative overrides. Powered by a flexible CLI, programmatic API, and native build backend integrations.**

[Get Started](getting-started/index.md){ .md-button .md-button--primary }
[View on GitHub](https://github.com/markurtz/git-versioned){ .md-button }

</div>
</div>

## Overview

<p align="center">
  <img alt="User Flow Diagram" src="assets/branding/user-flow-light.svg#only-light" width="800">
  <img alt="User Flow Diagram" src="assets/branding/user-flow-dark.svg#only-dark" width="800">
</p>

## What's Included

<div class="grid cards" markdown>

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

GitVersioned supports multiple integration paths. Select your preferred method to get started:

=== "Hatchling"

````
```toml
[build-system]
requires = ["hatchling", "gitversioned"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "gitversioned"
```
````

=== "Setuptools"

````
```toml
[build-system]
requires = ["setuptools>=61.0", "gitversioned"]
build-backend = "setuptools.build_meta"

[project]
dynamic = ["version"]
```
````

=== "Maturin"

````
```toml
[build-system]
requires = ["maturin>=1.0,<2.0", "gitversioned"]
build-backend = "gitversioned.plugins.maturin_plugin"

[project]
dynamic = ["version"]
```
````

=== "CLI & API"

````
```bash
pip install gitversioned
# Preview version string
gitversioned calculate
# Write version and all overrides in-place
gitversioned write
```
````

=== "Multi-File Overrides"

````
```toml
# pyproject.toml
[tool.gitversioned]
output = "src/package/version.py"

[tool.gitversioned.overrides.cargo]
output = "Cargo.toml"
output_strategies = { type = "regex", pattern = 'version = "(?P<version>.*?)"' }

[tool.gitversioned.overrides.docker]
output = "Dockerfile"
output_strategies = { type = "regex", pattern = 'ARG VERSION="(?P<version>.*?)"' }
```
````

For advanced options, archive support, and step-by-step onboarding, see the [Installation Guide](getting-started/installation.md) and the [Quick Start Guide](getting-started/quickstart.md).

## Links

- :material-github: [GitHub Repository](https://github.com/markurtz/git-versioned)
- :material-map-marker-path: [Roadmap](https://github.com/markurtz/git-versioned/milestones)
