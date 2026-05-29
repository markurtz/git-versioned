<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/markurtz/git-versioned/main/docs/assets/branding/logo-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/markurtz/git-versioned/main/docs/assets/branding/logo-light.svg">
    <img alt="GitVersioned Logo" src="https://raw.githubusercontent.com/markurtz/git-versioned/main/docs/assets/branding/logo-light.svg" width="400">
  </picture>
</p>

<p align="center">
  <em>Simple, predictable, and opinionated versioning for Python projects.</em>
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

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/markurtz/git-versioned/main/docs/assets/branding/user-flow-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/markurtz/git-versioned/main/docs/assets/branding/user-flow-light.svg">
    <img alt="User Flow Diagram" src="https://raw.githubusercontent.com/markurtz/git-versioned/main/docs/assets/branding/user-flow-light.svg" width="800">
  </picture>
</p>

GitVersioned is a PEP 440-compliant Python versioning tool for Git repositories. It leverages Git history and CI environments as the ultimate source of truth to provide predictable, automated release versioning with zero runtime dependencies.

### Why GitVersioned?

GitVersioned is designed with a core mission: **to trust the user and CI/CD flows above all else, while strictly enforcing packaging standards.** Rather than relying on rigid, heuristic-based version guessing, it prioritizes user and pipeline authority. At the same time, it strictly validates and normalizes all resolved versions against standard specifications (PEP 440 and SemVer 2) to guarantee complete compatibility across the Python packaging ecosystem and broader ecosystems.

- **Predictability & Authority First:** Enforces CI-driven and user-defined authority, giving you total control over the versioning flow, while strictly validating against PEP 440 and SemVer 2 to ensure absolute compatibility with pip, PyPI, and external packaging tools.
- **Unified Multi-File Synchronization:** Update multiple version targets—such as Python modules (`version.py`), Cargo manifests (`Cargo.toml`), and deployment manifests (`Dockerfile`)—simultaneously with a single build or write command, simplifying build processes and unifying version resolution.
- **Flexible Invocation & Rich Integration:** Run seamlessly as a build plugin for Hatchling, Setuptools, or Maturin, execute standalone from the terminal via an active CLI, or programmatically import versioning logic through a clean Python API.
- **Deep Auditing & Customization:** Provides 25+ configuration settings, custom function hooks, and ExStr template formats to generate structured metadata tracking Git commits, branches, dirty states, and environment parameters.

### Ecosystem Comparison

| Tool               | Versioning Authority & Control                                                        | Build Backends                                                                           | Configuration, Sources & Outputs                                                                    | Invocation Pathways                                                                             |
| :----------------- | :------------------------------------------------------------------------------------ | :--------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------- |
| **`GitVersioned`** | **User/CI-First.** Predictable release rules with strict PEP 440/SemVer 2 validation. | **Universal.** Native Hatchling, Setuptools, Maturin (Rust), and OCI/Dockerfile support. | **Extensive.** Resolves from Git, archives, env, files, or custom hooks. Outputs to multiple files. | **Plugin, Wrapper, CLI, or API.** High versatility across all scripting and build environments. |
| `setuptools-scm`   | Guess-based. Heuristic version incrementing with no strict custom control.            | Setuptools-only. Tightly coupled to standard Python packaging setup.                     | VCS tags primary. Environment overrides are manual; single Python module output.                    | Build hook only. Tightly bound to python packaging build runs.                                  |
| `versioneer`       | Rigidbody. Rigid tag-plus-distance logic with minimal user-defined authority.         | Legacy Setuptools. Rigidity limits adoption to standard setup scripts.                   | VCS-only. Hardcoded metadata; outputs to a single vendored Python script.                           | Vendored file. Requires copying ~2k lines of python code into the repo.                         |
| `versioningit`     | VCS-bound. Configurable but places compliance validation on the user.                 | Multi-backend. Python-only; requires custom wrapper config per backend.                  | Modular. Customizable sources but limited to single Python file output.                             | Python API & plugin hooks. Lacks a standalone CLI/API shell executable.                         |
| `hatch-vcs`        | Guess-based. Inherits setuptools-scm's tag-based guessing logic.                      | Hatchling-only. Inapplicable to Setuptools, Maturin, or non-Python.                      | SCM-bound. Resolves from SCM; outputs strictly to Python targets.                                   | Build hook only. Operates strictly inside Hatchling environment execution.                      |

## Quick Start

GitVersioned supports multiple integration paths: as a build plugin for **Hatchling**, **Setuptools**, or **Maturin**, via a standalone **CLI**, or programmatically as a **Python API**.

### 1. Hatchling Build Plugin

Declare `gitversioned` in `pyproject.toml` as a build-system requirement and version source:

```toml
[build-system]
requires = ["hatchling", "gitversioned"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "gitversioned"
```

### 2. Setuptools Build Plugin

Enable versioning in a Setuptools project by declaring `gitversioned` in `pyproject.toml` and setting your version dynamic:

```toml
[build-system]
requires = ["setuptools>=61.0", "gitversioned"]
build-backend = "setuptools.build_meta"

[project]
dynamic = ["version"]
```

### 3. Maturin Build Plugin

Declare `gitversioned` in `pyproject.toml` as a build-system requirement, specify it as the build backend wrapper, and set up a placeholder version in `Cargo.toml`:

**`pyproject.toml`**

```toml
[build-system]
requires = ["maturin>=1.0,<2.0", "gitversioned"]
build-backend = "gitversioned.plugins.maturin_plugin"

[project]
dynamic = ["version"]
```

**`Cargo.toml`**

```toml
[package]
name = "my_rust_package"
version = "0.0.0"  # Will be dynamically synchronized during builds
```

### 4. Command Line Interface (CLI)

Install the package to use the CLI standalone to resolve or write versions:

```bash
pip install gitversioned

# Resolve and print only the version string
gitversioned calculate

# Resolve and write a generated version file
gitversioned write --output src/package/version.py
```

### 5. Multi-File / Overrides Versioning

Synchronize multiple files simultaneously during a single build or CLI run by declaring overrides in your configuration:

**`pyproject.toml`**

```toml
[tool.gitversioned]
output = "src/package/version.py"

[tool.gitversioned.overrides.cargo]
output = "Cargo.toml"
output_strategies = { type = "regex", pattern = '(?ms)^\[package\].*?^(\s*version\s*=\s*)([\'\"])(?P<version>[^\'\"]+)\2' }

[tool.gitversioned.overrides.docker]
output = "Dockerfile"
output_strategies = { type = "regex", pattern = 'ARG VERSION="(?P<version>.*?)"' }
```

Running `gitversioned write` or building your package will automatically calculate the version and update `src/package/version.py`, `Cargo.toml`, and `Dockerfile` in-place!

### 6. Python API

Integrate version resolution directly inside Python scripts:

```python
from gitversioned import Settings
from gitversioned.utils import GitRepository, BuildEnvironment
from gitversioned.versioning import resolve_version

settings = Settings()
repo = GitRepository(settings.project_root)
env = BuildEnvironment(project_root=settings.project_root)

version, _, _ = resolve_version(settings, repo, env)
print(f"Resolved version: {version}")
```

### Configure Archive Support (Recommended)

To resolve the version when users download a repository ZIP file (e.g., from GitHub) where the `.git` directory is missing:

1. Create a `.git_archival.txt` file in your repository root:
   ```text
   commit_sha: $Format:%H$
   short_sha: $Format:%h$
   timestamp: $Format:%aI$
   author_name: $Format:%an$
   author_email: $Format:%ae$
   ref_names: $Format:%D$
   commit_message:
   $Format:%B$
   ```
1. Enable variable substitution by adding the following to your `.gitattributes` file:
   ```text
   .git_archival.txt export-subst
   ```

For full options and onboarding, see the **[Getting Started guide](https://github.com/markurtz/git-versioned/blob/main/docs/getting-started/index.md)**.

## Core Concepts

GitVersioned is built using modern Python tooling, enforcing strict code quality standards with Ruff and Mypy, and providing a robust Pydantic-driven settings architecture for configuration resolution.

### Component Architecture

The repository is structured to separate documentation, application logic, and testing cleanly:

- `src/gitversioned/`: The primary application source code. Contains core logic for Git interaction, version resolution, and template generation.
  - `plugins/`: Native integrations for build backends like Hatchling (`hatchling_plugin.py`) and Setuptools (`setuptools_plugin.py`).
- `tests/`: Comprehensive test suite ensuring reliability, organized into `unit/`, `integration/`, and `e2e/`.
- `docs/`: Source code for the MkDocs Material documentation site, including step-by-step guides, references, and getting started tutorials.
- `examples/`: Runnable reference projects demonstrating real-world configurations across various build systems and workflows.
- `.github/workflows/`: Advanced CI/CD pipelines governing the project lifecycle, built around reusable workflow templates.

## Advanced Usage

Please check the [`examples/`](https://github.com/markurtz/git-versioned/tree/main/examples/) directory for advanced examples and configurations.

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
