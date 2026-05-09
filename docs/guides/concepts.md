# Concepts & Resolution

`gitversioned` provides an intelligent engine that calculates PEP 440 compliant version strings dynamically based on the state of your Git repository and project configuration. This document explains the underlying concepts of how `gitversioned` evaluates sources, determines the build environment, and applies auto-increments.

______________________________________________________________________

## The Resolution Algorithm

When a build starts, `gitversioned` follows a strict evaluation order to determine the final version string.

1. **Source Evaluation:** Inspect configured sources (tags, branches, commits, files) in priority order until a match is found.
1. **Environment Detection:** Determine if the repository state implies a release, development, or pre-release build.
1. **Auto-Increment Calculation:** If the current working tree is ahead of the matched source, bump the requested version segment (`major`, `minor`, or `patch`).
1. **Template Application:** Apply the resolved version, Git metadata, and environment variables into the final formatting template to produce the output string and file.

______________________________________________________________________

## 1. Source Evaluation Priority

The `source_type` configuration setting defines an ordered list of places to look for a version string. By default, `source_type = ["auto"]` expands to:
`["file", "function", "tag", "branch", "commit"]`.

`gitversioned` iterates through this list. As soon as it extracts a valid version from one of these sources (using the corresponding `regex_*` configuration), the search stops.

### Example Flow

If `source_type = ["tag", "file"]`:

1. `gitversioned` first checks the repository for Git tags matching the `regex_tag` pattern.
1. If it finds matches (e.g., `v1.2.0`), it selects the tag that is "closest" (has the fewest commits) to the current `HEAD`.
1. If no matching tags exist (e.g., a fresh repository or a shallow clone without tags), it falls back to inspecting the file defined by `version_source_file`.

______________________________________________________________________

## 2. Environment Detection (`version_type`)

Once the base version and the corresponding Git reference are established, `gitversioned` calculates the `version_type` to dictate the suffix of the final version string.

If `version_type` is set to `"auto"` (the default), `gitversioned` inspects the repository state:

- **Clean HEAD:** If the current `HEAD` exactly matches the resolved Git reference (e.g., you checked out the `v1.2.0` tag directly) and there are **no uncommitted changes**, the `version_type` is resolved as `release`. This generates a clean PEP 440 version (e.g., `1.2.0`).
- **Dirty or Ahead:** If there are uncommitted changes, or if `HEAD` has commits beyond the matched reference, the `version_type` defaults to `dev`.

You can forcefully override this mechanism by setting `version_type` in your configuration to `release`, `dev`, `pre`, `alpha`, `nightly`, or `post`.

______________________________________________________________________

## 3. Auto-Increment Logic

When building development or nightly versions, the repository is often ahead of the base version. Re-using the same base version for continuous builds can lead to naming collisions in package registries.

The `[tool.gitversioned.auto_increment]` setting allows you to bump the base version before applying the suffix.

### Mechanics

If the repository is ahead of the matched Git reference (`distance_from_head > 0`), the engine checks the auto-increment target for the active `version_type`.

**Configuration Example:**

```toml
[tool.gitversioned.auto_increment]
dev = "minor"
pre = "patch"
```

**Scenario:**

- Base Version Resolved: `1.2.3`
- Current state: `HEAD` is 5 commits ahead of the tag. Uncommitted changes exist.
- Active `version_type`: `dev` (Resolved automatically)

**Evaluation:**

1. Since the distance is `> 0` and `version_type` is `dev`, the target is `minor`.
1. The engine splits `1.2.3` into its components.
1. It increments the minor segment and zeroes out all subsequent segments.
   - `major`: `1`
   - `minor`: `2 + 1 = 3`
   - `patch`: `0`
1. The new base version becomes `1.3.0`.

Finally, the dev template is applied to `1.3.0`, generating a string like `1.3.0.dev20260507+abc1234`.

______________________________________________________________________

## 4. Templating and Output

After all version components are calculated, `gitversioned` passes a rich context dictionary into the formatting templates.

The context contains:

- `version`: The resolved `packaging.version.Version` object.
- `repo`: Metadata about the Git repository (e.g., `dirty_files`, `current_branch`).
- `ref`: Metadata about the matched reference (e.g., `commit_sha`, `author_name`).
- `config`: The full `Settings` object.
- `env`: The build environment (OS variables, build dates).

For details on how to write these templates and customize the output strings, see the [Templates & Formatting Guide](templates.md).
