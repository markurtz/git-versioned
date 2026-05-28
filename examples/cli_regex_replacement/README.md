# CLI Regex-Based Version Replacement

## Overview

This example demonstrates how to use the GitVersioned command-line interface (CLI) to update version files in place using regular expression patterns. It shows how developers and CI/CD pipelines can locate version strings inside files (such as python package files or configuration files) and replace them dynamically with resolved semantic versions.

## Prerequisites & Setup

Before running the example, ensure that you have initialized the virtual environment and installed GitVersioned.

```bash
# Initialize and install dependencies in the repository's virtual environment
.venv/bin/hatch env create
```

Ensure that `git` is installed and accessible in your system path, as GitVersioned relies on Git history and tags to resolve project versions.

## Execution Blueprint

To run the self-contained example script, execute the following command from the root of the repository:

```bash
.venv/bin/python examples/cli_regex_replacement/main.py
```

## Expected Results

When run successfully, the command will output the following console logs:

```text
=== GitVersioned CLI Regex-Based Replacement Example ===
1. Creating sandbox repository at: /Users/markkurtz/code/github/markurtz/git-versioned/examples/cli_regex_replacement/sandbox

=== Initial File States ===
pyproject.toml version line:
[project]
name = "my-awesome-app"
version = "0.0.0"
src/my_app/__init__.py version line:
"""My Awesome Application module."""
__version__ = "0.0.0"

2. Executing GitVersioned CLI to update pyproject.toml...
Version successfully written to /Users/markkurtz/code/github/markurtz/git-versioned/examples/cli_regex_replacement/sandbox/pyproject.toml

3. Executing GitVersioned CLI to update src/my_app/__init__.py...
Version successfully written to /Users/markkurtz/code/github/markurtz/git-versioned/examples/cli_regex_replacement/sandbox/src/my_app/__init__.py

=== Updated File States ===
pyproject.toml updated:
[project]
name = "my-awesome-app"
version = "2.5.4"
src/my_app/__init__.py updated:
"""My Awesome Application module."""
__version__ = "2.5.4"

4. Cleaned up sandbox directory: /Users/markkurtz/code/github/markurtz/git-versioned/examples/cli_regex_replacement/sandbox

=== Example Completed Successfully! ===
```

## Troubleshooting

- **Error executing CLI / GitVersioned CLI failed:** Ensure that the local virtual environment is active and that `gitversioned` is installed properly. You can verify installation by running `.venv/bin/gitversioned --version`.
- **Git command failure:** If initialization or commit commands fail inside the sandbox, check your local git installation (`git --version`) and verify that your system is configured to allow local commits without global configuration blocks blocking execution.
