<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/branding/logo-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/branding/logo-light.svg">
    <img alt="project_name Logo" src="docs/assets/branding/logo-light.svg" width="400">
  </picture>
</p>

<p align="center">
  <em>An opinionated, production-ready Apache 2.0 template repository for bootstrapping modern software projects.</em>
</p>

<p align="center">
  <!-- Package & Release Status -->
  <a href="https://github.com/{{organization}}/project_name/releases">
    <img src="https://img.shields.io/github/v/release/{{organization}}/project_name?label=Release" alt="GitHub Release">
  </a>
  <a href="https://pypi.org/project/project_name/">
    <img src="https://img.shields.io/pypi/v/project_name?label=PyPI" alt="PyPI Release">
  </a>
  <a href="https://pypi.org/project/project_name/">
    <img src="https://img.shields.io/pypi/pyversions/project_name?label=Python" alt="Supported Python Versions">
  </a>
  <br/>
  <!-- CI/CD & Build Status -->
  <a href="https://github.com/{{organization}}/project_name/actions/workflows/main.yml">
    <img src="https://github.com/{{organization}}/project_name/actions/workflows/main.yml/badge.svg" alt="CI Status">
  </a>
  <!-- Uncomment to display code coverage:
  <a href="https://codecov.io/gh/{{organization}}/project_name">
    <img src="https://codecov.io/gh/{{organization}}/project_name/branch/main/graph/badge.svg" alt="Coverage">
  </a>
  -->
  <br/>
  <!-- Issues & Support -->
  <a href="https://github.com/{{organization}}/project_name/issues?q=is%3Aissue+is%3Aclosed">
    <img src="https://img.shields.io/github/issues-closed/{{organization}}/project_name?label=Issues%20Closed" alt="Closed Issues">
  </a>
  <!-- Uncomment to display open issues:
  <a href="https://github.com/{{organization}}/project_name/issues?q=is%3Aissue+is%3Aopen">
    <img src="https://img.shields.io/github/issues/{{organization}}/project_name?label=Issues%20Open" alt="Open Issues">
  </a>
  -->
  <a href="https://opensource.org/licenses/Apache-2.0">
    <img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License">
  </a>
</p>

<p align="center">
  <a href="https://{{organization}}.github.io/project_name">Documentation</a> |
  <a href="https://blog.{{organization}}.org">Blog</a> |
  <a href="https://github.com/{{organization}}/project_name/milestones">Roadmap</a> |
  <a href="https://slack.{{organization}}.org">Slack</a> |
  <a href="https://calendar.{{organization}}.org">Weekly Syncs</a>
</p>

______________________________________________________________________

## Overview

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/branding/user-flow-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/branding/user-flow-light.svg">
    <img alt="User Flow Diagram" src="docs/assets/branding/user-flow-light.svg" width="800">
  </picture>
</p>

Welcome to the project_name template repository! This template provides a robust foundation for building high-quality, scalable software projects. It includes standard directories, issue templates, CI/CD workflows, and comprehensive placeholder documentation.

To use this template, simply find and replace all instances of `project_name` and `{{organization}}` with your actual project details, update the placeholder SVG images in `docs/assets/branding/`, and you are ready to start coding.

### Why Use project_name?

- **Consistency:** Enforces a standardized layout and structure across your organization's repositories.
- **Speed:** Bootstraps your project with pre-configured Actions, badges, and templates so you don't start from scratch.
- **Best Practices:** Baked-in guides for contributing, security, and developer setup.

### Comparisons

When evaluating project_name against other templates, consider the following differences:

| Feature            | project_name Template            | Standard GitHub Init | Cookiecutter / Copier      |
| :----------------- | :------------------------------- | :------------------- | :------------------------- |
| **Setup Speed**    | Very Fast                        | Fast                 | Slower (requires CLI tool) |
| **Visual Assets**  | Pre-configured Light/Dark assets | None                 | Varies                     |
| **CI/CD Built-in** | Yes (GitHub Actions)             | No                   | Optional                   |
| **Complexity**     | Low (Find and Replace)           | None                 | Medium (Jinja templates)   |

## What's New

**Welcome to the project_name Launch!**

This project has just been instantiated from the template repository. Keep an eye on this section for future release highlights, new features, and community announcements!

<!-- Once your project is active, replace the launch message above with links to your latest release notes or top 3 new features here. -->

## Quick Start

```bash
pip install project_name
```

For full installation options (from source, Docker, platform-specific notes) and step-by-step onboarding, see the **[Getting Started guide](https://%7B%7Borganization%7D%7D.github.io/%7B%7Bproject_name%7D%7D/getting-started/)**.

## Core Concepts

This project is built using modern Python tooling, ensuring a stable and typed foundation. It utilizes Pydantic for data validation and Ruff/Mypy for code quality.

### Component Architecture

The template is organized into several key areas:

- `docs/`: Stores your documentation and branding assets.
- `src/` (or your primary package directory): The core application logic.
- `tests/`: Automated tests to ensure code quality.

## Advanced Usage

Please check the [`docs/examples/`](docs/examples/) directory for advanced examples and configurations.

## General

### Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for more details. For development setup, check out [DEVELOPING.md](DEVELOPING.md).
Please ensure you follow our [Code of Conduct](CODE_OF_CONDUCT.md) in all interactions.

### Support and Security

- For help and general questions, see [SUPPORT.md](SUPPORT.md).
- To report a security vulnerability, please refer to our [Security Policy](SECURITY.md).

### AI & LLM Tooling

This repository includes first-class support for agentic and LLM-assisted development workflows:

- **[AGENTS.md](AGENTS.md):** Repository-specific instructions for AI coding agents (Codex, Copilot Workspace, Gemini, Claude, Cursor, and similar tools). Contains the authoritative guide for project structure, executable commands, code style, and critical constraints.
- **[llms.txt](llms.txt):** A machine-readable index of the project's documentation, following the [llms.txt specification](https://llmstxt.org/). Served at `/llms.txt` on the documentation site to help LLMs quickly locate and consume relevant content.

### License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

### Citations

If you use this template or the resulting software in your research, please cite it using the following BibTeX entry:

```bibtex
@software{project_name,
  author = {{{organization}}},
  title = {project_name},
  version = {{{version}}},
  month = {{{month}}},
  year = {2026},
  url = {https://github.com/{{organization}}/project_name}
}
```
