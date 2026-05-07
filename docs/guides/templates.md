# Templates and Formatting

`gitversioned` provides extensive flexibility over both the semantic version strings it computes and the Python files it generates. It achieves this using a dynamic templating system evaluated during the build process.

This guide explains how to customize your version strings and output files, and details the rich build context available to your templates.

______________________________________________________________________

## Formatting Strings

Before generating the final output file, `gitversioned` uses formatting strings to construct the different segments of a PEP 440 compliant version.

You can override these formats in your `pyproject.toml` or `setup.cfg`.

### Available Configuration

| Setting       | Default Value                                     | Description                                       |
| ------------- | ------------------------------------------------- | ------------------------------------------------- |
| `format_main` | `{version.major}.{version.minor}.{version.micro}` | The primary semantic version string.              |
| `format_dev`  | `{ref.timestamp:%Y%m%d}+{ref.short_sha}`          | The suffix appended during development builds.    |
| `format_pre`  | `{ref.timestamp:%Y%m%d}`                          | The suffix used for pre-release and alpha builds. |
| `format_post` | `{ref.distance_from_head}`                        | The suffix used for post-release builds.          |

**Example configuration in `pyproject.toml`:**

```toml
[tool.gitversioned]
format_dev = "dev{ref.distance_from_head}+{ref.short_sha}"
```

______________________________________________________________________

## Output Templates

The final action `gitversioned` performs is generating an output file (by default, `version.py`). The contents of this file are entirely controlled by templates.

There are two primary templates used, chosen based on the build state:

- `template_release`: Used for stable, clean releases.
- `template_dev`: Used when the repository is dirty, detached, or explicitly configured for development.

By default, these templates generate a comprehensive module with rich metadata (such as `__VERSION_METADATA__`, `__GIT_METADATA__`, and `__BUILD_METADATA__`).

### Customizing Output

You can override the entire template string in your configuration if you need a different file structure, specific exports, or compatibility with legacy code.

!!! tip "Multi-line Strings in TOML"
Use TOML's multi-line string syntax (`"""`) to clearly define your custom templates within your `pyproject.toml`.

**Example:** Generating a minimal `version.py` file.

```toml
[tool.gitversioned]
template_release = """
__version__ = "{version}"
"""

template_dev = """
__version__ = "{version}"
__commit__ = "{repo.current_commit.commit_sha if repo.is_available and repo.current_commit else ''}"
"""
```

______________________________________________________________________

## The Build Context Reference

Both the formatting strings and output templates are evaluated using `tstr.generate_template`, giving you access to Python-style evaluation (`use_eval=True`).

The following variables are injected into the template context:

### `version`

The base PEP 440 `Version` object resolved before formatting is applied.

- **Type:** `packaging.version.Version`
- **Example Usage:** `{version.major}`, `{version.minor}`, `{version.micro}`

### `ref`

The specific Git reference object (Commit, Tag, or Branch) from which the base version was resolved.

- **Type:** `Commit | Tag | Branch`
- **Example Usage:** `{ref.timestamp:%Y-%m-%d}`, `{ref.distance_from_head}`

### `repo`

The full repository interface, allowing deep introspection of the current Git state.

- **Type:** `GitRepository`
- **Key Properties:**
  - `repo.is_available`: Boolean indicating if the Git work tree is valid.
  - `repo.is_dirty`: Boolean indicating uncommitted changes.
  - `repo.current_commit`: The latest `Commit` object.
  - `repo.head_name`: The branch name or short SHA of HEAD.
  - `repo.commit_count`: Total number of commits in the repository.

### `env`

Structured metadata about the system and environment where the build is executing.

- **Type:** `BuildEnvironment`
- **Key Properties:**
  - `env.timestamp`: UTC timestamp of the build.
  - `env.hostname` & `env.user`: The executing machine and user.
  - `env.python_version`: The Python runtime version.
  - `env.is_ci`: Boolean indicating if the build is running in a recognized CI environment.
  - `env.ci_provider`: The name of the CI provider (e.g., "GitHub Actions").

### `config`

The unified configuration object containing the active settings for this run.

- **Type:** `Settings`
- **Example Usage:** `{config.package_name}`
