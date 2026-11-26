# Command Line Guide

`gitversioned` has three commands, one per job: `version`, `check` and
`release`. `new` records a change for the changelog, and `init` is an optional
setup step.

| Command   | Job                                                                |
| --------- | ------------------------------------------------------------------ |
| `version` | Print the version, print the next one, or stamp it into the files. |
| `check`   | Validate the repository setup, a title, a commit range or a tag.   |
| `release` | Plan a release, open the release pull request, tag and publish it. |
| `new`     | Record a change: a change file, or a commit with a checked title.  |
| `init`    | Optional: add the archive file and wire up the build backend.      |

Every command takes the same shared options.

| Option              | Meaning                                             |
| ------------------- | --------------------------------------------------- |
| `-C`, `--root DIR`  | Run as if started in `DIR`.                         |
| `-p`, `--package N` | Act on one package from `[packages]`.               |
| `--json`            | Machine-readable output on stdout, errors included. |
| `-v`, `-vv`         | More detail on stderr.                              |
| `-q`, `--quiet`     | Errors only.                                        |

Results go to stdout and everything else goes to stderr, so
`VERSION=$(gitversioned version)` is always safe.

## Exit codes

| Code | Meaning                                                                                       |
| ---- | --------------------------------------------------------------------------------------------- |
| 0    | Success.                                                                                      |
| 1    | A check failed, or there is nothing to release.                                               |
| 2    | Wrong usage or invalid configuration.                                                         |
| 3    | The environment cannot give a trustworthy answer (shallow clone in CI, no git, `gh` missing). |

______________________________________________________________________

## `version`

```text
gitversioned version [VERSION] [--next] [--bump LEVEL] [--pre KIND]
                     [--type TYPE] [--standard STD]
                     [--write] [--dry-run] [--explain]
```

### Print the version of this checkout

```console
$ gitversioned version
1.4.1.dev20261125+60439dc
$ gitversioned version --standard semver
1.4.1-dev.20261125+60439dc
$ gitversioned version --type nightly
1.5.0.dev20261125
```

On a release tag the output is the tag's version. After the tag it is a
development version: the next patch, the commit date and the short commit hash.
A changed tracked file adds `.dirty`. The default spelling is PEP 440 when the
project has a `pyproject.toml` with a `[project]` table, and SemVer otherwise.

### Print the next release

```console
$ gitversioned version --next
1.5.0
$ gitversioned version --next --pre rc
1.5.0rc1
$ gitversioned version --next --bump major
2.0.0
```

`--next` reads the Conventional Commit subjects since the last release. It exits
with code 1 when no commit since then calls for a release.

### See why

```console
$ gitversioned version --explain
version   1.4.1.dev20261125+60439dc
type      dev
current   1.4.0  (tag v1.4.0, 60439dc, 2 commits since)
why       minor: 1 patch, 1 minor
  patch   fix(cli): exit code on empty input
  minor   feat(core): add streaming parser
note      base 1.4.0 from tag v1.4.0
config    .config/gitversioned.toml  (6 keys set, 8 defaults)
```

### Stamp the files

```console
$ gitversioned version --write
1.4.1.dev20261125+60439dc
  CITATION.cff            1.4.1-dev.20261125+60439dc
  Dockerfile              1.4.1-dev.20261125+60439dc
  charts/demo/Chart.yaml  1.4.1-dev.20261125+60439dc
  crates/cli/Cargo.toml   1.4.1-dev.20261125+60439dc
  crates/core/Cargo.toml  1.4.1-dev.20261125+60439dc
  src/demo/version.py     1.4.1.dev20261125+60439dc
  Cargo.lock              1.4.1-dev.20261125+60439dc
  docs/install.md         1.4.1-dev.20261125+60439dc
```

Each file gets the spelling its ecosystem expects. `--dry-run` prints a unified
diff and changes nothing. Stamping never makes the tree count as dirty: a file
whose only change is its version is ignored when the version is resolved again.

Pass a `VERSION` to use that version instead of resolving one, for example
`gitversioned version 2.0.0 --write`.

### JSON

```console
$ gitversioned version --json
{
  "version": "1.4.1.dev20261125+60439dc",
  "pep440": "1.4.1.dev20261125+60439dc",
  "semver": "1.4.1-dev.20261125+60439dc",
  "type": "dev",
  "source": "tag",
  "tag": "v1.4.0",
  "distance": 2,
  "sha": "60439dc",
  "dirty": false,
  "warnings": [],
  "written": []
}
```

______________________________________________________________________

## `check`

```text
gitversioned check [TITLE] [--commits RANGE] [--tag NAME] [--file PATH] [--warn]
```

### The repository setup

```console
$ gitversioned check
ok    config        .config/gitversioned.toml
ok    git           full history, 1 release tags, latest v1.4.0
ok    targets       CITATION.cff, Dockerfile, charts/demo/Chart.yaml, ...
ok    scopes        core, cli, web, chart, docs, deps
warn  archive file  .git_archival.txt is not set up, so source tarballs lose the version. Run `gitversioned init`.
warn  github        gh is missing or not signed in: release --pr and pull request titles in the changelog are unavailable.
```

Problems that only warn on a laptop fail in CI (when the `CI` environment
variable is set), with exit code 3. The usual one is a shallow clone: set
`fetch-depth: 0` on `actions/checkout`.

### A pull request title or commit message

```console
$ gitversioned check "feat(core): add a thing"
ok
$ gitversioned check "added a thing"
fail  title  'added a thing' is not a Conventional Commit title. Expected type(scope): subject. Types: feat, fix, perf, ...
$ gitversioned check --file .git/COMMIT_EDITMSG
$ gitversioned check --commits origin/main..HEAD
ok    commits  2 commits
```

`--file` reads the first line of a file, which is what a `commit-msg` hook
passes. `--warn` reports problems as `warn` and still exits 0, which suits a
hook that should only advise.

### A tag name

```console
$ gitversioned check --tag v1.5.0
ok    tag  1.5.0, newer than v1.4.0
```

The tag must match the template and be newer than the last release. If it
exists already, it must point at `HEAD`. When the project has a changelog, it
must have the version's `## [1.5.0]` section. Use this in a workflow that runs
when a tag is pushed, or before tagging by hand; `release --tag` runs the same
checks.

______________________________________________________________________

## `release`

```text
gitversioned release [VERSION] [--bump LEVEL] [--pre KIND] [--post]
                     [--write | --pr | --tag] [--publish [--dry-run]]
```

A release has three stages, and an optional fourth that uploads it. Without a
flag the command only shows the plan; `-q` hides the report.

### Plan

```console
$ gitversioned release
release   1.5.0  (minor, from commits, from 1.4.0)
tag       v1.5.0
files     CHANGELOG.md, CITATION.cff, Dockerfile, charts/demo/Chart.yaml, crates/cli/Cargo.toml, crates/core/Cargo.toml, Cargo.lock, docs/install.md

## [1.5.0] - 2026-11-25

### Added

- **core**: add streaming parser

### Fixed

- **cli**: exit code on empty input

Nothing changed. Run with --write, --pr or --tag.
```

### `--write`: update the working tree

Writes the changelog section, stamps every committed target and deletes the
change files the section took in. Nothing is committed, so this is the stage to
use when you make the release commit yourself.

### `--pr`: open or update the release pull request

Rebuilds the branch `release/next` from the current commit with one commit
titled `release: v1.5.0`, pushes it, and opens a pull request labelled
`release`, or updates the one already open. The pull request body is the
changelog section. Run it on every push to the release branch and the pull
request always shows what the next release will be. It refuses to run on any
other branch, and exits with code 1 when `HEAD` is a merged release commit that
is not tagged yet, so it never reopens a release that is waiting for
`release --tag`. On GitHub it needs the GitHub CLI `gh`, signed in (`GH_TOKEN`
in CI); on GitLab `GITLAB_TOKEN` and on Gitea `GITEA_TOKEN` (see the `forge`
setting).

On a maintenance branch listed in `branches`, such as `1.x`, the branch is
`release/next-1.x` and the pull request merges into `1.x`. A branch named
`N.x` or `N.M.x` only releases versions on that line.

Add the label `release:rc` to the pull request to make it a release candidate.
Add `release:major`, `release:minor` or `release:patch` to a merged pull request
to override the level its title would give.

### `--tag`: tag the merged release

Run on the `branch` setting's branch (`main` by default) right after the release
pull request merges. It reads the
tag from the release commit's subject, checks it is newer than the last
release, creates it and pushes it. Pass a `VERSION` to tag `HEAD` by hand.
Either way it runs the checks of `check --tag` first, so a version without its
changelog section is never tagged. With `forge_release = true` it then creates
the GitHub, GitLab or Gitea release for the pushed tag, with the changelog
section as its notes.

### `--publish`: upload to the registries

Builds the release tagged at `HEAD` and uploads it to PyPI (`uv build` and
`uv publish`, or `python -m build` and `twine upload`), crates.io
(`cargo publish --workspace --locked`) and npm (`npm publish`, `--tag next` for
a pre-release). `publish` picks the registries; by default every one with a
public manifest. `--dry-run` runs each tool's dry run. With `--tag` it tags
first, and the GitHub release gets the built files attached.

```console
$ gitversioned release --publish --dry-run
publish   cargo publish --workspace --locked --dry-run
publish   npm publish --dry-run
publish   uv build --out-dir dist
publish   uv publish --dry-run dist/beam_gv-1.0.0-py3-none-any.whl dist/beam_gv-1.0.0.tar.gz
Dry run: nothing was uploaded.
```

### `--post`: a post release

Plans the next post release of the latest release, `1.4.0.post1` (tag
`v1.4.0.post1`, SemVer `1.4.0+post.1`), for a packaging fix that ships the same
code. It works with `--write` and `--pr`.

### Choosing the version

The first of these that is set decides:

1. The `VERSION` argument.
1. `--bump major|minor|patch`.
1. `GITVERSIONED__BUMP` in the environment (a level or a version).
1. A `release:major|minor|patch` label on a pull request merged since the last
   final release.
1. The commits and change files since the last release, by the `levels`
   setting, raised to major when `semver_checks` finds a breaking API change.

______________________________________________________________________

## `new`

```text
gitversioned new [MESSAGE] [--type TYPE] [--scope SCOPE] [--breaking] [--bump LEVEL] [--commit]
```

Records a change. By default it writes a change file to `.changes/`, which the
next release takes into its changelog section and deletes; `--bump` sets the
level the change asks for, including `none`. With `--commit` it commits the
staged changes with the title instead. The title is checked like `check TITLE`.
Without `--type` and a message, in a terminal, it asks for type, scope,
message and whether the change is breaking.

```console
$ gitversioned new --type feat --scope cli "Add --explain."
wrote     .changes/20261125-add-explain.md  feat(cli): Add --explain.
$ gitversioned new --commit -t fix -s core "Handle empty input."
commit    c7887ac  fix(core): Handle empty input.
```

______________________________________________________________________

## `init`

```console
$ gitversioned init
wrote  .git_archival.txt
edit   .gitattributes          + .git_archival.txt  export-subst
```

Adds the two things a repository needs for a version to survive a source
tarball from GitHub, and adds `[tool.hatch.version] source = "gitversioned"` to
a Hatchling project that does not have it yet. It only creates files or appends
to them. Nothing else in gitversioned depends on it.

______________________________________________________________________

## Recipes

### Git hook for commit messages

```bash
# .git/hooks/commit-msg
gitversioned check --file "$1"
```

### Build a container with the right version

```bash
gitversioned version --write
docker build --build-arg VERSION="$(gitversioned version --standard semver)" .
```

### One package in a monorepo

```bash
gitversioned version -p web
gitversioned release -p web --pr
```
