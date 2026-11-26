# Configuration Guide

gitversioned works with no configuration. Everything below is optional: twelve
core settings, a list of extra files, a table of packages, and settings for the
less common release flows (version sources, templates, bump rules, change
files, changelog style, forges, maintenance branches and publishing).

## Where settings live

Settings live in exactly one of these places, searched in this order from the
folder the command runs in up to the repository root:

| Home                        | Table                                                                    |
| --------------------------- | ------------------------------------------------------------------------ |
| `.config/gitversioned.toml` | The whole file                                                           |
| `gitversioned.toml`         | The whole file                                                           |
| `pyproject.toml`            | `[tool.gitversioned]`                                                    |
| `Cargo.toml`                | `[workspace.metadata.gitversioned]` or `[package.metadata.gitversioned]` |
| `package.json`              | `"gitversioned"`                                                         |
| `setup.cfg`                 | `[tool:gitversioned]`                                                    |

Two homes in the same folder is an error that names both, so a setting can
never be silently shadowed. An unknown key is also an error, and it names the
nearest valid key.

## The settings

| Key         | Default                | What it does                                                                     |
| ----------- | ---------------------- | -------------------------------------------------------------------------------- |
| `version`   | `"auto"`               | `auto` resolves from git; a version pins it; `branch`, `commit`, `file:PATH` or `python:MODULE:FUNCTION` read it from a source (see below). |
| `fallback`  | `"0.1.0"`              | The base version before the first tag exists.                                    |
| `tag`       | `"v{version}"`         | The tag template; also how release tags are recognised.                          |
| `annotated` | `false`                | Create annotated tags that carry the changelog section.                          |
| `branch`    | `"main"`               | The branch releases are cut from and release pull requests target.               |
| `dev`       | `"patch"`              | The base of a development build: `patch`, `minor`, `major` or `next`.            |
| `nightly`   | `"next"`               | The base of a nightly build; `next` is the next release from commits.            |
| `date`      | `"commit"`             | The date in dev and nightly versions: `commit` (reproducible) or `build`.        |
| `local`     | `true`                 | Add `+<hash>` to development builds.                                             |
| `changelog` | `"CHANGELOG.md"`       | The changelog file, or `false` to turn it off.                                   |
| `types`     | The twelve types below | The commit types `check` accepts.                                                |
| `scopes`    | `[]` (any scope)       | The allowed scopes. An entry ending in `.toml` is a file whose table names are scopes, so `[".config/blocks.toml", "deps"]` mixes both. |

The default types are `feat`, `fix`, `perf`, `refactor`, `docs`, `test`,
`build`, `ci`, `chore`, `revert`, `deprecate` and `release`.

### Release flow settings

| Key                  | Default        | What it does                                                                                          |
| -------------------- | -------------- | ----------------------------------------------------------------------------------------------------- |
| `formats`            | `{}`           | Templates for `dev` and `nightly` versions, such as `{dev = "{next}.dev{distance}"}`.                 |
| `module_template`    | none           | A `string.Template` file that replaces the generated `version.py`.                                    |
| `levels`             | `{}`           | Bump level per commit type: `major`, `minor`, `patch` or `none`. Breaking changes stay major.         |
| `zero_shift`         | `true`         | Below 1.0.0 shift every level down one; `false` releases a feature as a minor from the first tag.     |
| `changelog_layout`   | `"kind"`       | `kind` (Added, Fixed, with scopes in bold) or `scope` (a heading per scope, then kinds).              |
| `changelog_sections` | `{}`           | Heading per commit type, such as `{perf = "Performance"}`; `false` hides a type unless it is breaking. |
| `changelog_template` | none           | A `string.Template` file for a whole release section; it must start with `## [$version]`.             |
| `changes`            | `".changes"`   | The folder of change files, hand-written changelog entries a release takes in and deletes.             |
| `forge`              | `"auto"`       | `github`, `gitlab` or `gitea`; `auto` reads the `origin` host and the CI environment.                 |
| `forge_release`      | `false`        | Create the forge release, with the changelog section as notes, when `release --tag` pushes a tag.     |
| `branches`           | `[]`           | Maintenance branches (globs such as `"*.x"`) releases may also be cut from.                           |
| `exclude`            | `[]`           | Files discovery leaves alone (globs or folders). A `[[targets]]` entry still wins.                    |
| `semver_checks`      | `false`        | Run `cargo semver-checks` against the last tag; a breaking API change makes the release major.        |
| `publish`            | by manifest    | Registries `release --publish` uploads to: `pypi`, `crates`, `npm`.                                   |

#### Version sources

`version = "branch"` reads `X.Y.Z` from the branch name (also from
`GITHUB_HEAD_REF` or `GITHUB_REF_NAME` on a detached CI checkout), and
`version = "commit"` from the `HEAD` subject; both fall back to tags when there
is none. `file:VERSION` reads the first `X.Y.Z` in a file, and
`python:pkg.meta:version` imports the module from the project root and calls the
function. A source sets the version the way a pin does.

#### Templates

`formats` placeholders are `{next}` (the next release), `{base}` (the latest
release), `{distance}` (commits since it), `{date}` (`YYYYMMDD`), `{sha}` (the
short hash) and `{branch}`; the result must be a PEP 440 version.
`module_template` placeholders are `$version`, `$version_semver`,
`$version_tuple`, `$major`, `$minor`, `$patch`, `$tag`, `$distance`, `$commit`
and `$commit_date`. `changelog_template` placeholders are `$version`,
`$pep440`, `$tag`, `$date`, `$previous`, `$compare`, `$entries` and
`$migrations`. Templates are substitutions, never code.

#### Change files

A change file in `.changes/` is Markdown with front matter:

```markdown
---
type: feat
scope: cli
bump: minor      # optional: major, minor, patch or none
breaking: false  # optional
package: web     # optional: a package with its own tag
---
Add `--explain`, which shows why a version was chosen.
```

`gitversioned new` writes one. Change files count for the bump like commits,
their entries land in the release section, and `release --write` deletes them.

#### Forges

| Forge          | Reached through        | Token          | Address                                                        |
| -------------- | ---------------------- | -------------- | -------------------------------------------------------------- |
| GitHub         | `gh`                   | `GH_TOKEN`     | The `origin` remote                                            |
| GitLab         | REST API v4            | `GITLAB_TOKEN` | `origin`, `GITLAB_API_URL`, or `CI_API_V4_URL` and `CI_PROJECT_PATH` |
| Gitea, Forgejo | REST API v1            | `GITEA_TOKEN`  | `origin`, `GITEA_API_URL`, or `GITHUB_SERVER_URL` and `GITHUB_REPOSITORY` |

### Example: every setting

```toml
# .config/gitversioned.toml
version = "auto"
fallback = "0.1.0"
tag = "v{version}"
annotated = false
branch = "main"
dev = "patch"
nightly = "next"
date = "commit"
local = true
changelog = "CHANGELOG.md"
types = ["feat", "fix", "perf", "refactor", "docs", "test", "build", "ci", "chore", "revert", "deprecate", "release"]
scopes = ["core", "cli", "docs"]
module_template = ".config/version.tmpl"
zero_shift = true
changelog_layout = "scope"
changelog_template = ".config/changelog-section.tmpl"
changes = ".changes"
forge = "auto"
forge_release = true
branches = ["*.x"]
exclude = ["docs/snippets/*"]
semver_checks = false
publish = ["pypi"]

[formats]
dev = "{next}.dev{distance}"

[levels]
perf = "minor"
docs = "patch"

[changelog_sections]
perf = "Performance"
refactor = false
```

The same settings in the other homes:

```toml
# pyproject.toml
[tool.gitversioned]
tag = "v{version}"
scopes = ["core", "cli", "docs"]
```

```toml
# Cargo.toml
[workspace.metadata.gitversioned]
tag = "v{version}"
scopes = ["core", "cli", "docs"]
```

```json
{
  "name": "my-package",
  "gitversioned": {
    "tag": "v{version}",
    "scopes": ["core", "cli", "docs"]
  }
}
```

```ini
# setup.cfg
[tool:gitversioned]
tag = v{version}
scopes = ["core", "cli", "docs"]
```

## Targets: the files that get stamped

Discovery finds these files on its own, among the files git tracks:

| File                   | What is stamped                                                                                             | Spelling |
| ---------------------- | ----------------------------------------------------------------------------------------------------------- | -------- |
| `pyproject.toml`       | `project.version`, when it is static                                                                        | PEP 440  |
| `<package>/version.py` | Generated, when the build uses gitversioned and the version is dynamic                                      | PEP 440  |
| `Cargo.toml`           | `package.version` or `workspace.package.version`, and the versions of path dependencies on workspace crates | SemVer   |
| `Cargo.lock`           | The entries of the workspace crates                                                                         | SemVer   |
| `package.json`         | `version`                                                                                                   | SemVer   |
| `tauri.conf.json`      | `version`                                                                                                   | SemVer   |
| `Chart.yaml`           | `version` and `appVersion`                                                                                  | SemVer   |
| `CITATION.cff` (root)  | `version`, and `date-released` on a release; both are added when missing                                    | SemVer   |
| `Dockerfile`, `Containerfile` | The `org.opencontainers.image.version` label, unless it is a `$VARIABLE`                             | SemVer   |

In a repository with several `package.json` files, a dependency of one package
on another is stamped too, keeping its operator (`^`, `~`, `=`); `workspace:`
and `catalog:` references are left alone. A private `package.json` with no
`version`, such as a workspace root, is not a target.

Files under `node_modules`, `target`, `dist`, `build`, `site`, `examples`,
`tests`, `test`, `testdata`, `fixtures`, `vendor` and `third_party` are left
alone, and so are manifests that say they are never released: a
`pyproject.toml` with the `Private :: Do Not Upload` classifier and a
cargo-fuzz harness (`cargo-fuzz = true`). `exclude` leaves out any other
file, by glob or folder. Edits are scoped text edits: only the version value
changes, so comments, key order, quoting and line endings survive.

List any other file with `[[targets]]`:

```toml
# A value in a TOML, JSON or YAML file, by dotted key
[[targets]]
path = "deploy/values.yaml"
key = "image.tag"

# Any text file, by a regular expression with a `version` group
[[targets]]
path = "docs/install.md"
pattern = 'my-tool@(?P<version>[0-9][^\s`]*)'

# A file discovery would skip, or one that should not be committed
[[targets]]
path = "examples/demo/package.json"
commit = false
```

| Key       | Meaning                                                                                                          |
| --------- | ---------------------------------------------------------------------------------------------------------------- |
| `path`    | The file, relative to the project root. Required.                                                                |
| `key`     | Dotted path of the value in a TOML, JSON or YAML file.                                                           |
| `pattern` | Regular expression with a `version` group. Not together with `key`.                                              |
| `commit`  | Whether the release pull request commits the file. Defaults to true for manifests and false for generated files. |

## Packages: more than one version in a repository

```toml
[packages.core]
path = "crates/core"              # follows the repository version

[packages.web]
path = "packages/web"
tag = "web-v{version}"            # its own tags, version and release pull request
```

| Key    | Meaning                                                                |
| ------ | ---------------------------------------------------------------------- |
| `path` | The package folder, relative to the project root. Required.            |
| `tag`  | A tag template. Without it the package follows the repository version. |

A package with its own `tag` is versioned from its own tags, counts only the
commits that touch its folder, and is left out of the repository's own version
and stamping. Use `-p NAME` on any command to act on it. The package names are
added to the allowed scopes.

## Environment overrides

Any setting can be overridden with `GITVERSIONED__<KEY>`. Lists and booleans
are written as JSON. An unknown `GITVERSIONED__` variable is ignored with a
warning, since the environment is shared with other tools and older releases.

```bash
GITVERSIONED__VERSION=1.2.3 python -m build       # pin the version for one build
GITVERSIONED__LOCAL=false gitversioned version    # no +hash, e.g. for TestPyPI
GITVERSIONED__TAG='release-{version}' gitversioned version
GITVERSIONED__SCOPES='["core","cli"]' gitversioned check "feat(core): x"
GITVERSIONED__BUMP=minor gitversioned release     # a level or an exact version
GITVERSIONED__TYPE=nightly python -m build        # release, dev or nightly
```

`GITVERSIONED__BUMP` and `GITVERSIONED__TYPE` are not settings: they stand in
for `--bump` and `--type`. `GITVERSIONED__TYPE` is the only way to pick the
build type inside a build backend, since the build plugins take no flags.

`gitversioned version --explain` lists how many keys were set and where the
settings were read from.

## What is not configurable

These are fixed on purpose, so every repository behaves the same way.

- **Breaking changes are major.** `levels` changes every other type, but a `!`
  or a `BREAKING CHANGE:` footer always asks for a major release (a minor below
  1.0.0 unless `zero_shift = false`).
- **Release names.** The branch is `release/next` (`release/next-<branch>` on a
  maintenance branch), the pull request title is `release: <tag>`, and the
  labels are `release`, `release:rc` and `release:major|minor|patch`.
- **Keep a Changelog.** Sections are `## [X.Y.Z] - YYYY-MM-DD`, so releases can
  find, fold and replace them; layout, headings and templates sit on top.
