# Configuration Guide

`gitversioned` is designed to be fully configurable to adapt to any project's release strategy. While the default settings work seamlessly for most standard semantic versioning (PEP 440) workflows, you can finely tune how versions are extracted, incremented, and outputted.

This guide explores all configuration options available and demonstrates how to leverage them in different scenarios.

______________________________________________________________________

## Configuration Sources

`gitversioned` uses a hierarchy of configuration sources. The tool aggregates and prioritizes configuration in the following order (from lowest to highest priority):

1. **`setup.cfg`**: Under the `[tool:gitversioned]` section.
1. **`pyproject.toml`**: Under the `[tool.gitversioned]` table.
1. **`.env` files**: Variables prefixed with `GITVERSIONED__` (e.g., `GITVERSIONED__FORMAT_DEV="dev{ref.short_sha}"`).
1. **Environment Variables**: Variables prefixed with `GITVERSIONED__` (e.g., `export GITVERSIONED__AUTO_INCREMENT='{"dev": "patch"}'`).

Most users will define their configuration in `pyproject.toml`.

______________________________________________________________________

## Source & Resolution Options

These settings determine **where** `gitversioned` looks to find the base version string.

### `source_type`

Controls the priority order of sources used to extract the version.

- **Type:** List of strings
- **Default:** `["auto"]` (Expands to: `file`, `function`, `tag`, `branch`, `commit`)
- **Options:** `tag`, `branch`, `commit`, `file`, `function`, `auto`

> [!NOTE]
> If `gitversioned` fails to extract a version from all configured sources (or if the `.git` directory is entirely absent, such as in a GitHub ZIP download), it will automatically attempt an **Archive Fallback**.

```toml
# Only resolve versions from Git tags or a hardcoded file.
[tool.gitversioned]
source_type = ["tag", "file"]
```

### `version`

Explicit version override. If set to anything other than `"auto"`, the dynamic resolution process is completely bypassed and this version is used directly.

- **Type:** String
- **Default:** `"auto"`

### `version_source_file`

The file to inspect when the `file` source type is evaluated.

- **Type:** String (Path)
- **Default:** `"version.txt"`

### `version_source_function`

A Python module and function to execute when the `function` source type is evaluated. The function must accept `**kwargs` (including `settings`, `repo`, and `env`) and return a tuple containing a `Version` object and an optional `GitReference` object.

- **Type:** String (Format: `module.path:function_name`)
- **Default:** `None`

### `version_source_archive`

The file to inspect when the archive fallback mechanism is triggered (e.g., when the repository is downloaded as a ZIP file without a `.git` directory).

- **Type:** String (Path)
- **Default:** `".git_archival.txt"`

### Regex Patterns

When evaluating Git sources or files, `gitversioned` uses regex to capture the major, minor, and patch numbers. You can provide a list of patterns to match against. Your regex MUST use named capture groups: `(?P<major>\d+)`, `(?P<minor>\d+)`, and `(?P<patch>\d+)` (or `micro`).

- **`regex_tag`**: Matches against Git tag names.
- **`regex_branch`**: Matches against the current branch name.
- **`regex_commit`**: Matches against commit messages.
- **`regex_file`**: Matches against the contents of `version_source_file`.
- **`regex_archive`**: Matches against the contents of `version_source_archive` during the archive fallback.

```toml
[tool.gitversioned]
# Match tags like "v1.2.3" or "release/1.2.3"
regex_tag = [
    '^(?:release/)?v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$'
]
```

______________________________________________________________________

## Output & Generation Options

Once the base version is resolved, these settings control how it is transformed and written to disk.

### `version_type`

Forces a specific build type. By default, `gitversioned` intelligently decides this based on repository state (e.g., clean HEAD = `release`, dirty/detached = `dev`).

- **Type:** String
- **Default:** `"auto"`
- **Options:** `auto`, `release`, `dev`, `pre`, `alpha`, `nightly`, `post`

### `dirty_ignore`

A list of file paths to ignore when `gitversioned` checks if the repository is in a "dirty" state (which normally forces a `dev` version type). The `output` and `version_source_file` are always automatically ignored. This is particularly useful for configuration files that might be modified during build processes.

- **Type:** List of strings
- **Default:** `[]`

```toml
[tool.gitversioned]
# Ignore changes to these files when checking dirty state
dirty_ignore = ["poetry.lock", "tests/sandbox/"]
```

### `auto_increment`

Determines which segment of the version string is incremented for pre-releases and development builds when the repository is ahead of the last version source.

- **Type:** Dictionary (Mapping string release types to string increment targets)
- **Default:** `None`
- **Keys:** `auto`, `release`, `dev`, `pre`, `alpha`, `nightly`, `post`
- **Values:** `major`, `minor`, `micro` (or `patch`, `bug`)

```toml
[tool.gitversioned.auto_increment]
# Automatically bump the patch version for dev builds instead of minor.
dev = "patch"
```

### `output`

The file path where the generated version metadata module will be written. If you want to disable file generation entirely, set this to an empty string.

- **Type:** String
- **Default:** `"version.py"`

```toml
[tool.gitversioned]
# Place the output file inside your package directory
output = "src/my_package/version.py"
```

### `version_standard`

The standard formatting layout used to normalize and compile the version string.

- **Type:** String
- **Default:** `"pep440"`
- **Options:** `pep440`, `semver2`

```toml
[tool.gitversioned]
version_standard = "semver2"
```

### `output_strategies`

Configures the output formatting, templating, and text-replacement actions executed when generating the version file. This can be configured as a single strategy or a dictionary mapping specific `version_type` outputs (such as `release` or `dev`) to separate strategy objects.

- **Type:** Dictionary or Single Strategy Object
- **Default:** Pre-configured to output full metadata files using template files for `release` and `dev` states.
- **Strategy Types:**
  - `template_str`: Formats an inline string pattern containing placeholder variables (e.g. `{version}`, `{repo.current_commit.commit_sha}`).
  - `template_path`: Reads and formats an external template file relative to the project root.
  - `regex`: Searches an existing file for a pattern containing a `(?P<version>...)` group and updates the matched version string in-place.

```toml
# Inline Template String Strategy
[tool.gitversioned.output_strategies]
type = "template_str"
content = "__version__ = '{version}'"

# Or partitioned by release state:
[tool.gitversioned.output_strategies.release]
type = "template_path"
path = "templates/release.py.template"

[tool.gitversioned.output_strategies.dev]
type = "template_str"
content = "__version__ = '{version}'"
```

______________________________________________________________________

## Formatting Options

`gitversioned` provides formatting strings to construct the different segments of the PEP 440 compliant version.

- **`format_main`**: Base semantic version string.
- **`format_dev`**: Dev suffix.
- **`format_pre`**: Pre-release suffix.
- **`format_post`**: Post-release suffix.

For comprehensive details on customizing these formats and the available context variables, please read the [Templates & Formatting Guide](templates.md).

______________________________________________________________________

## Example Configurations

### Scenario 1: Strict Tag-Based Releases

In this scenario, a project only considers annotated Git tags as the source of truth. It outputs the file directly into the package structure and bumps the `patch` version for intermediate commits for dev releases and the `minor` version for pre-releases.

```toml
[tool.gitversioned]
source_type = ["tag"]
output = "src/my_application/__version__.py"

[tool.gitversioned.auto_increment]
dev = "patch"
pre = "minor"
```

### Scenario 2: Legacy File Fallback

A project migrating to `gitversioned` might want to prioritize Git tags, but fall back to a hardcoded `__init__.py` file if no tags exist in the current clone.

```toml
[tool.gitversioned]
source_type = ["tag", "file"]
version_source_file = "src/my_application/__init__.py"
regex_file = [
    # Look for: __version__ = "1.0.0"
    '(?i)__version__\s*=\s*[\'"](?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)[\'"]'
]
```

### Scenario 3: Monorepo Sub-Packages

For projects with multiple packages in a single repository, you can filter tags using specific regexes so that each package only triggers version bumps on its specific tags (e.g., `pkgA-v1.0.0`).

```toml
[tool.gitversioned]
source_type = ["tag"]
# Only match tags that start with "pkgA-v"
regex_tag = [
    '^pkgA-v(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$'
]
```

### Scenario 4: Auto-Incrementing Releases

By default, the `release` version type is strictly bound to a clean, exact Git match (e.g., a tagged commit). However, if your project resolves the version type to `release` while still being ahead of the base source (e.g., forced via `version_type = "release"` or through custom resolution), you can auto-increment the release segment.

```toml
[tool.gitversioned]
source_type = ["tag"]
version_type = "release"  # Force all builds to be parsed as releases

[tool.gitversioned.auto_increment]
# If we are 3 commits ahead of v1.5.0, this will generate 1.6.0
release = "minor"
```
