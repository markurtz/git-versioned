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

# AGENTS.md — AI Agent & Coding Assistant Guide

This file provides repository-specific context, setup instructions, executable commands, and security boundaries for AI coding assistants.

## System Overview

`gitversioned` is an opinionated PEP 440-compliant Python versioning tool for Git repositories and submodules. It enforces CI and user authority over versioning, and generates structured `version.py` files with deep metadata for full auditability.

- **Primary Language:** Python 3.10+
- **Configuration & Build Backend:** Hatch (using `hatchling.build`)
- **Key Dependencies:** Pydantic / Pydantic-Settings v2, Loguru, Typer, Packaging, Setuptools

## Core Directories & Architecture

- `src/gitversioned/`: Core Python library.
  - `__main__.py`: CLI entrypoint (subcommands: `calculate`, `format`, `write`).
  - `settings.py`: Pydantic settings schema for project options.
  - `plugins/`: Integration modules for Hatchling and Setuptools.
  - `utils/`: Git, environment, and Pydantic validation helpers.
  - `versioning/`: Version calculation, template rendering, and output file writers.
- `tests/`: Organized into `python/unit/` (isolated logic), `python/integration/` (subsystem interactions), and `e2e/` (installed package & CLI integration).
- `docs/`: MkDocs Material documentation source.
- `.github/workflows/`: CI/CD workflows (prefixed with `pipeline-` and `util-`).

## Environment & Developer Workflows

This project is configured to run using Hatch environments. Use the local `.venv` for all executions as instructed by the user.

### 1. Setup & Bootstrapping

Activate the environment and initialize Hatch:

```bash
# Set up/update dependencies via Hatch inside virtualenv wrapper
.venv/bin/hatch env create
```

### 2. Testing Pipeline

Tests are tiered. Run targeted tests or full suite:

```bash
# Run all functional tests (unit + integration)
.venv/bin/hatch run python:tests-func

# Run unit tests only
.venv/bin/hatch run python:tests-unit
# Alternatively, via pytest directly:
.venv/bin/pytest tests/python/unit

# Run integration tests only
.venv/bin/hatch run python:tests-int

# Run E2E tests (builds dist wheel and installs it first)
.venv/bin/hatch run python:tests-e2e

# Run all tests with coverage reports
.venv/bin/hatch run tests-cov
```

### 3. Code Quality, Formatting & Types

Run formatting and quality gates before committing:

```bash
# Auto-format Python and project files
.venv/bin/hatch run python:format
.venv/bin/hatch run project:format

# Run all lint checks (Ruff, mdformat, yamlfix, taplo)
.venv/bin/hatch run python:lint
.venv/bin/hatch run project:lint

# Run static type checks (Mypy via Ty)
.venv/bin/hatch run python:types

# Run pre-commit hooks manually on all files
.venv/bin/pre-commit run --all-files
```

### 4. Documentation & Packaging

```bash
# Build and serve docs locally (http://127.0.0.1:8000)
.venv/bin/hatch run project:docs-serve

# Build package distributions (sdist and wheel)
.venv/bin/hatch build
```

## Security & Behavior Boundaries

To maintain project integrity and security, agents must strictly adhere to the following rules:

### 1. Secrets & Credentials

- **Never commit secrets:** Never add API keys, tokens, or credentials anywhere.
- Run security audits using: `.venv/bin/hatch run project:security`.

### 2. Critical Files & CI Guardrails

- **Do not modify `LICENSE` or `NOTICE`.**
- **Do not modify GitHub Actions workflow triggers** (in `.github/workflows/`) without explicit human review.
- **Apache 2.0 copyright header:** Every new Python source file must begin with the standard Apache 2.0 copyright and license notice.

### 3. Execution Constraints

- Always use tools installed in the `.venv` (e.g. `.venv/bin/hatch`, `.venv/bin/pytest`).
- Avoid global packages or running unverified external binaries.
- Do not add new external dependencies to `pyproject.toml` without verifying compatibility with Python 3.10+.
