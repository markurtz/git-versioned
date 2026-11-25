# Quick Start

Five minutes from an empty repository to a planned release.

## 1. Print the version

```console
$ cd my-project
$ uvx gitversioned version
0.1.0.dev20261125+abc1234
```

With no tags yet the version starts from the fallback `0.1.0`. Tag a release
and it follows the tag:

```console
$ git tag v1.0.0
$ gitversioned version
1.0.0
```

## 2. Check the setup

```console
$ gitversioned check
ok    config        defaults
ok    git           full history, 1 release tags, latest v1.0.0
ok    targets       Cargo.toml, package.json, src/my_project/version.py
warn  archive file  .git_archival.txt is not set up, so source tarballs lose the version. Run `gitversioned init`.
```

The `targets` line lists every file gitversioned found a version in. Run
`gitversioned init` once to clear the archive warning.

## 3. Wire up the build

For a Python project, let the build read the version from git:

```toml
# pyproject.toml
[build-system]
requires = ["hatchling", "gitversioned>=0.4"]
build-backend = "hatchling.build"

[project]
name = "my-project"
dynamic = ["version"]

[tool.hatch.version]
source = "gitversioned"

[tool.hatch.build.hooks.gitversioned]
```

For Rust, npm, Helm and container builds, stamp the manifests before building:

```console
$ gitversioned version --write
1.0.1.dev20261125+abc1234
  Cargo.toml    1.0.1-dev.20261125+abc1234
  package.json  1.0.1-dev.20261125+abc1234
```

## 4. Commit with Conventional Commits

```console
$ git commit -m "feat(core): add streaming parser"
$ git commit -m "fix(cli): exit code on empty input"
$ gitversioned check --commits v1.0.0..HEAD
ok    commits  2 commits
```

## 5. Plan the release

```console
$ gitversioned release
release   1.1.0  (minor, from commits, from 1.0.0)
tag       v1.1.0
files     CHANGELOG.md, Cargo.toml, package.json

## 1.1.0 - 2026-11-25

### Added

- **core**: add streaming parser

### Fixed

- **cli**: exit code on empty input

Nothing changed. Run with --write, --pr or --tag.
```

`gitversioned release --pr` opens the release pull request with exactly that
content. After it merges, `gitversioned release --tag` tags the merge.

## Next

- [Workflows](workflows.md): the common end-to-end stories.
- [Command Line Guide](../guides/cli.md): every option, with output.
- [Configuration Guide](../guides/configuration.md): the twelve settings.
