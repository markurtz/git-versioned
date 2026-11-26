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
-->

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/markurtz/git-versioned/main/docs/assets/branding/logo-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/markurtz/git-versioned/main/docs/assets/branding/logo-light.svg">
    <img alt="GitVersioned Logo" src="https://raw.githubusercontent.com/markurtz/git-versioned/main/docs/assets/branding/logo-light.svg" width="400">
  </picture>
</p>

<p align="center">
  <em>One version for the whole repository, from git tags: resolved, stamped, checked and released.</em>
</p>

<p align="center">
  <!-- Package & Release Status -->
  <a href="https://github.com/markurtz/git-versioned/releases">
    <img src="https://badgen.net/github/release/markurtz/git-versioned?label=Release" alt="GitHub Release">
  </a>
  <a href="https://pypi.org/project/gitversioned/">
    <img src="https://img.shields.io/pypi/v/gitversioned?label=PyPI" alt="PyPI Release">
  </a>
  <a href="https://pypi.org/project/gitversioned/">
    <img src="https://img.shields.io/pypi/pyversions/gitversioned?label=Python" alt="Supported Python Versions">
  </a>
  <br/>
  <!-- CI/CD & Build Status -->
  <a href="https://github.com/markurtz/git-versioned/actions/workflows/pipeline-main.yml">
    <img src="https://github.com/markurtz/git-versioned/actions/workflows/pipeline-main.yml/badge.svg?branch=main" alt="CI Status">
  </a>
  <a href="https://github.com/markurtz/git-versioned/issues?q=is%3Aissue+is%3Aopen">
    <img src="https://img.shields.io/github/issues/markurtz/git-versioned?label=Issues%20Open" alt="Open Issues">
  </a>
  <a href="https://opensource.org/licenses/Apache-2.0">
    <img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License">
  </a>
</p>

<p align="center">
  <a href="https://markurtz.github.io/git-versioned/">Documentation</a> |
  <a href="https://github.com/markurtz/git-versioned/milestones">Roadmap</a> |
  <a href="https://github.com/markurtz/git-versioned/issues">Issues</a> |
  <a href="https://github.com/markurtz/git-versioned/discussions">Discussions</a>
</p>

______________________________________________________________________

## Overview

GitVersioned gives a repository one version, taken from its git tags, and keeps
every manifest in step with it. It covers the whole path from a commit to a
published release with three commands, plus `new` for hand-written changelog
entries.

| Command                | Job                                                                     |
| ---------------------- | ----------------------------------------------------------------------- |
| `gitversioned version` | Print the version, print the next one, or stamp it into every manifest. |
| `gitversioned check`   | Validate the setup, a pull request title, a commit range or a tag.      |
| `gitversioned release` | Plan a release, open the release pull request, tag and publish it.      |

### Why GitVersioned?

- **One tool for a polyglot repository.** Python, Rust, npm, Helm, citation
  files and container labels are stamped by one command, each in the spelling
  its ecosystem expects (PEP 440 or SemVer).
- **Tags are the only source of truth.** No version is committed between
  releases and there is no version file to keep in sync. Source tarballs and
  sdists still resolve correctly.
- **Reviewed releases.** The next version and the changelog come from
  Conventional Commits and arrive as a pull request you can read, edit and
  merge. Tagging the merge is the release.
- **Small surface.** Three commands and no configuration at all for the common
  case. Settings for the rest (bump rules, changelog layout and templates,
  change files, maintenance branches, publishing) stay off until set.
- **Any forge.** GitHub through `gh`, GitLab and Gitea through their APIs, and
  a GitHub Action at the repository root.
- **Safe in CI.** A shallow clone or missing history warns on a laptop and
  fails in CI, so a wrong version is never published.
- **Edits that leave files alone.** Only the version value changes: comments,
  key order, quoting and line endings survive, and stamped files never make
  the tree count as dirty.

### Ecosystem Comparison

| Tool               | Version from tags | Python builds                          | Rust and npm manifests | Commit checks | Release PR and changelog | Monorepo packages |
| :----------------- | :---------------- | :------------------------------------- | :--------------------- | :------------ | :----------------------- | :---------------- |
| **`GitVersioned`** | Yes               | Hatchling, setuptools, Maturin         | Yes, with `Cargo.lock` | Yes           | Yes: GitHub, GitLab, Gitea | Yes               |
| `setuptools-scm`   | Yes               | setuptools (Hatchling via `hatch-vcs`) | No                     | No            | No                       | Limited           |
| `release-please`   | No, committed     | No                                     | Yes                    | No            | Yes                      | Yes               |
| `release-plz`      | No, committed     | No                                     | Rust only              | No            | Yes                      | Cargo workspaces  |
| `commitizen`       | No, committed     | No                                     | By pattern             | Yes           | Changelog only           | Limited           |
| `semantic-release` | Yes               | By plugin                              | By plugin              | By plugin     | No pull request          | By plugin         |

## Quick Start

```bash
uvx gitversioned version     # or: pipx run gitversioned version
```

### 1. Print the version

```console
$ gitversioned version
1.4.1.dev20261125+60439dc
$ gitversioned version --standard semver
1.4.1-dev.20261125+60439dc
$ gitversioned version --next
1.5.0
```

On a tag the output is the tag's version. After it, the output is a development
version: the next patch, the commit date and the commit hash.

### 2. Build Python packages from the tag

```toml
# pyproject.toml
[build-system]
requires = ["hatchling", "gitversioned>=0.4"]
build-backend = "hatchling.build"

[project]
name = "my-package"
dynamic = ["version"]

[tool.hatch.version]
source = "gitversioned"

[tool.hatch.build.hooks.gitversioned]
```

Setuptools opts in by listing `gitversioned` in `build-system.requires`. Maturin
uses `build-backend = "gitversioned.plugins.maturin"`.

### 3. Stamp every other manifest

```console
$ gitversioned version --write
1.4.1.dev20261125+60439dc
  CITATION.cff            1.4.1-dev.20261125+60439dc
  Dockerfile              1.4.1-dev.20261125+60439dc
  charts/demo/Chart.yaml  1.4.1-dev.20261125+60439dc
  crates/cli/Cargo.toml   1.4.1-dev.20261125+60439dc
  crates/core/Cargo.toml  1.4.1-dev.20261125+60439dc
  src/demo/version.py     1.4.1.dev20261125+60439dc
  Cargo.lock              1.4.1-dev.20261125+60439dc
```

### 4. Check titles and commits

```console
$ gitversioned check "feat(core): add streaming parser"
ok
$ gitversioned check "added a thing"
fail  title  'added a thing' is not a Conventional Commit title. Expected type(scope): subject.
$ gitversioned check
ok    config   .config/gitversioned.toml
ok    git      full history, 1 release tags, latest v1.4.0
ok    targets  CITATION.cff, Dockerfile, charts/demo/Chart.yaml, ...
```

### 5. Release

```console
$ gitversioned release
release   1.5.0  (minor, from commits, from 1.4.0)
tag       v1.5.0

## [1.5.0] - 2026-11-25

### Added

- **core**: add streaming parser

### Fixed

- **cli**: exit code on empty input

$ gitversioned release --pr      # open or update the release pull request
$ gitversioned release --tag     # after it merges: tag and push
```

### 6. Python API

<!--phmdoctest-skip-->

```python
from gitversioned import get_version, load_config, resolve

print(get_version())
resolved = resolve(load_config())
print(resolved.version.semver(), resolved.type, resolved.source)
```

For the full walkthrough, see the **[Getting Started guide](https://github.com/markurtz/git-versioned/blob/main/docs/getting-started/index.md)**.

## Configuration

Everything is optional. Settings live in one of `.config/gitversioned.toml`,
`gitversioned.toml`, `pyproject.toml`, `Cargo.toml`, `package.json` or
`setup.cfg`.

```toml
# .config/gitversioned.toml (the values shown are the defaults)
version = "auto"            # or a pinned version
fallback = "0.1.0"          # before the first tag
tag = "v{version}"
annotated = false
branch = "main"
dev = "patch"               # base of development builds
nightly = "next"            # base of nightly builds
date = "commit"             # or "build"
local = true                # +hash on development builds
changelog = "CHANGELOG.md"  # or false
scopes = []                 # any scope; or a list, or a TOML file

[[targets]]                 # a file discovery cannot recognise
path = "docs/install.md"
pattern = 'my-tool@(?P<version>[0-9][^\s`]*)'

[packages.web]              # a package with its own tags and releases
path = "packages/web"
tag = "web-v{version}"
```

Any setting can be overridden from the environment as `GITVERSIONED__KEY`. See
the **[Configuration Guide](https://github.com/markurtz/git-versioned/blob/main/docs/guides/configuration.md)**.

## Core Concepts

- **Sources, in order:** a pin, git tags, the archive file for source
  tarballs, sdist metadata, then the fallback.
- **Bump rules:** a breaking change is major, `feat` is minor, other releasable
  types are patch; below 1.0.0 each level shifts down one.
- **Release flow:** commits on `main`, a release pull request on
  `release/next`, a tag on the merge.

### Repository Layout

- `src/gitversioned/`: the package. `cli.py` holds the commands; `resolve.py`,
  `targets.py`, `commits.py`, `changelog.py`, `checks.py` and `release.py` hold
  the logic; `plugins/` holds the Hatchling, setuptools and Maturin backends.
- `tests/`: `unit/`, `integration/` and `e2e/`, with one end-to-end class per
  user story.
- `examples/`: 22 runnable projects, from a zero-config Hatchling package to
  GitHub Actions workflows and template renders; each README is its test.
- `docs/`: the documentation site.
- `.github/workflows/`: the CI/CD pipelines.

## Advanced Usage

See the [`examples/`](https://github.com/markurtz/git-versioned/tree/main/examples/)
directory and the [guides](https://github.com/markurtz/git-versioned/tree/main/docs/guides).
Coming from 0.3? Read the
[Migration Guide](https://github.com/markurtz/git-versioned/blob/main/docs/guides/migration.md).

## General

### Contributing

We welcome contributions! Please see our [Contributing Guide](https://github.com/markurtz/git-versioned/blob/main/CONTRIBUTING.md) for more details. For development setup, check out [DEVELOPING.md](https://github.com/markurtz/git-versioned/blob/main/DEVELOPING.md).
Please ensure you follow our [Code of Conduct](https://github.com/markurtz/git-versioned/blob/main/CODE_OF_CONDUCT.md) in all interactions.

### Support and Security

- For help and general questions, see [SUPPORT.md](https://github.com/markurtz/git-versioned/blob/main/SUPPORT.md).
- To report a security vulnerability, please refer to our [Security Policy](https://github.com/markurtz/git-versioned/blob/main/SECURITY.md).

### AI & LLM Tooling

This repository includes first-class support for agentic and LLM-assisted development workflows:

- **[AGENTS.md](https://github.com/markurtz/git-versioned/blob/main/AGENTS.md):** Repository-specific instructions for AI coding agents (Codex, Copilot Workspace, Gemini, Claude, Cursor, and similar tools). Contains the authoritative guide for project structure, executable commands, code style, and critical constraints.
- **[llms.txt](https://github.com/markurtz/git-versioned/blob/main/llms.txt):** A machine-readable index of the project's documentation, following the [llms.txt specification](https://llmstxt.org/). Served at `/llms.txt` on the documentation site to help LLMs quickly locate and consume relevant content.

### License

This project is licensed under the Apache License 2.0. See the [LICENSE](https://github.com/markurtz/git-versioned/blob/main/LICENSE) file for details.

### Citations

If you use this software in your research, please cite it using the following BibTeX entry:

```bibtex
@software{gitversioned,
  author = {Mark Kurtz},
  title = {gitversioned},
  year = {2026},
  url = {https://github.com/markurtz/git-versioned}
}
```
