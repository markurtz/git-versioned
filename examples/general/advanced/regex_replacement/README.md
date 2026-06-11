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

# In-place CLI Regex Replacement

This example demonstrates how to use the GitVersioned CLI to perform in-place version string updates in arbitrary files using regular expressions.

## Overview

The `gitversioned write` CLI command supports custom regex strategies. By passing a regex pattern with a named group `(?P<version>...)`, the CLI reads the target file, matches the pattern, replaces the version value with the dynamically calculated package version, and writes it back in-place.

## Prerequisites & Setup

Ensure you are in the virtual environment and have `gitversioned` installed:

```bash
# Verify active environment has gitversioned
.venv/bin/gitversioned --help
```

## Execution Blueprint

To run the self-contained demonstration:

```bash
python examples/general/advanced/regex_replacement/main.py
```

## Expected Results

The demo script runs a full mock sequence (initializing a repository, committing files, tagging, and running `write` using regex patterns). The script will output logs like:

```text
=== GitVersioned CLI Regex-Based Replacement Example ===
1. Creating sandbox repository at: /Users/markkurtz/code/github/markurtz/git-versioned/examples/general/advanced/regex_replacement/sandbox

=== Initial File States ===
pyproject.toml version line:
version = "0.0.0"
src/my_app/__init__.py version line:
__version__ = "0.0.0"

2. Executing GitVersioned CLI to update pyproject.toml...
Version successfully written to /Users/markkurtz/code/github/markurtz/git-versioned/examples/general/advanced/regex_replacement/sandbox/pyproject.toml

3. Executing GitVersioned CLI to update src/my_app/__init__.py...
Version successfully written to /Users/markkurtz/code/github/markurtz/git-versioned/examples/general/advanced/regex_replacement/sandbox/src/my_app/__init__.py

=== Updated File States ===
pyproject.toml updated:
version = "2.5.4"
src/my_app/__init__.py updated:
__version__ = "2.5.4"

4. Cleaned up sandbox directory: /Users/markkurtz/code/github/markurtz/git-versioned/examples/general/advanced/regex_replacement/sandbox

=== Example Completed Successfully! ===
```

## Troubleshooting

- **Regex Group Names**: The regex replacement strategy requires the presence of a named capture group specifically named `version` (i.e. `(?P<version>...)`), otherwise replacement will fail.
- **Escape Characters in Shell**: If invoking the CLI directly from the terminal, ensure you escape double quotes in the JSON strategy argument properly according to your shell constraints (e.g. bash vs zsh).
