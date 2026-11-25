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

`gitversioned` gives a repository one version, taken from its git tags. It resolves that version, stamps it into every Python, Rust, npm, Helm and container manifest with scoped text edits, validates Conventional Commit titles and drives a reviewed release (changelog, release pull request, tag). The command line has three commands, `version`, `check` and `release`, plus an optional `init`.

- **Primary Language:** Python 3.10+
- **Configuration & Build Backend:** Hatch (using `hatchling.build`)
- **Runtime Dependencies:** Pydantic v2, Typer and Loguru (plus `tomli` on Python 3.10). Do not add runtime dependencies without a strong reason.

## Core Directories & Architecture

- `src/gitversioned/`: The library, one flat package.
  - `cli.py`: The Typer app and the four commands. `__main__.py` only calls it.
  - `model.py`: `Version`, printed as PEP 440 or SemVer.
  - `config.py`: The settings model (twelve root keys, `[[targets]]`, `[packages]`), its homes and `GITVERSIONED__KEY` overrides.
  - `git.py`: All git access, the archive file and sdist metadata.
  - `resolve.py`: Resolves the version of a checkout.
  - `commits.py`: Conventional Commit parsing and bump rules.
  - `editors.py`, `targets.py`: Locating version values in files, discovery and stamping.
  - `changelog.py`, `github.py`, `release.py`: Changelog sections, the `gh` CLI wrapper, release planning, the release pull request and tagging.
  - `checks.py`: Findings for `check`.
  - `scaffold.py`: The `init` step.
  - `errors.py`: Errors, each carrying its exit code (1 check failed, 2 usage or config, 3 environment).
  - `plugins/`: Hatchling, setuptools and Maturin build integrations.
- `tests/`: `unit/` (isolated logic), `integration/` (settings and build backends) and `e2e/` (one class per user story, run through the CLI in real git repositories built by `tests/conftest.py`).
- `examples/`: Runnable projects per backend plus a polyglot repository, tested by `examples/test_examples.py`.
- `docs/`: Zensical documentation source.
- `scripts/`: Developer and CI helpers, including `build_binary.py` and `generate_llms_full.py`.
- `.github/workflows/`: CI/CD workflows (prefixed with `pipeline-` and `util-`).

### Design Rules

- The surface is deliberately small. Do not add a command, a root setting or an option without an explicit request; behaviour that every repository should share is fixed in code, not configurable.
- Results go to stdout and everything else to stderr. Every command supports `--json`.
- File edits are scoped text edits that change only the version value. Never rewrite a manifest through a parser and serializer.
- Tests for new behaviour belong in `tests/e2e` as a user story when the behaviour is visible from the command line.
- After changing a guide, the source or `pyproject.toml`, run `python scripts/generate_llms_full.py`.

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
.venv/bin/pytest tests/unit

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

# Run static type checks (ty)
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

# Build the standalone binary into dist/bin/ (needs pyinstaller)
.venv/bin/python scripts/build_binary.py
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
