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

**One version for the whole repository, from git tags. `gitversioned` resolves it, stamps it into every Python, Rust, npm, Helm and container manifest, checks Conventional Commit titles and drives a reviewed release with a changelog. Three commands: `version`, `check` and `release`.**

[Get Started](getting-started/index.md){ .md-button .md-button--primary }
[View on GitHub](https://github.com/markurtz/git-versioned){ .md-button }

</div>
</div>

## Overview

Every step of a version's life is one command, and the same engine runs inside
the build backends.

| When                                     | Command                                         |
| ---------------------------------------- | ----------------------------------------------- |
| Every Python build                       | none: the Hatchling, setuptools or Maturin hook |
| Print the version in a script            | `gitversioned version`                          |
| Stamp every manifest before a build      | `gitversioned version --write`                  |
| Nightly build                            | `GITVERSIONED__TYPE=nightly python -m build`    |
| What the next release would be, and why  | `gitversioned version --next --explain`         |
| Is this repository set up correctly      | `gitversioned check`                            |
| Pull request title check                 | `gitversioned check "$PR_TITLE"`                |
| Preview a release                        | `gitversioned release`                          |
| Open or refresh the release pull request | `gitversioned release --pr`                     |
| Tag the merged release                   | `gitversioned release --tag`                    |

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

Pick the build backend, or use the command line on its own.

### Hatchling

```toml
[build-system]
requires = ["hatchling", "gitversioned>=0.4"]
build-backend = "hatchling.build"

[project]
name = "my-project"
dynamic = ["version"]

[tool.hatch.version]
source = "gitversioned"

[tool.hatch.build.hooks.gitversioned]
```

### Setuptools

```toml
[build-system]
requires = ["setuptools>=64", "gitversioned>=0.4"]
build-backend = "setuptools.build_meta"

[project]
name = "my-project"
dynamic = ["version"]
```

### Maturin

```toml
[build-system]
requires = ["maturin>=1.0,<2.0", "gitversioned>=0.4"]
build-backend = "gitversioned.plugins.maturin"

[project]
name = "my-project"
dynamic = ["version"]
```

### Command line

```bash
uvx gitversioned version            # print the version of this checkout
uvx gitversioned version --write    # stamp Cargo.toml, package.json, Chart.yaml, ...
uvx gitversioned check              # is this repository set up correctly?
```

### Extra files

```toml
# .config/gitversioned.toml: only for files discovery cannot find
[[targets]]
path = "deploy/values.yaml"
key = "image.tag"

[[targets]]
path = "docs/install.md"
pattern = 'my-tool@(?P<version>[0-9][^\s`]*)'
```

For advanced options, archive support, and step-by-step onboarding, see the [Installation Guide](getting-started/installation.md) and the [Quick Start Guide](getting-started/quickstart.md).

## Links

- :material-github: [GitHub Repository](https://github.com/markurtz/git-versioned)
- :material-map-marker-path: [Roadmap](https://github.com/markurtz/git-versioned/milestones)
