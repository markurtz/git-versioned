# A template python-size repository

The parts of a [markurtz/template](https://github.com/markurtz/template)
python-size render that gitversioned touches: hatchling with the build hook, no
settings, a Keep a Changelog file with an `[Unreleased]` section, and the
`release:verify`, `release:notes` and `release:manual` tasks behind
`release.yml` and `release-manual.yml`. The tasks are the mise file tasks from
[`.mise/tasks/release/`](.mise/tasks/release), run here directly with bash.

| Level    | Shows                                                                       | Needs                             |
| -------- | --------------------------------------------------------------------------- | --------------------------------- |
| Advanced | zero config, `[Unreleased]` folding, `check --tag`, `release VERSION --tag` | git, Python, `build`, `hatchling` |

## Run

Copy this folder anywhere and run the commands below in it. A bare repository
stands in for GitHub.

```console
$ git init -q && git add -A && git commit -qm "feat: first release" && git tag v0.1.0
$ git init -q --bare ../origin.git && git remote add origin ../origin.git && git push -q -u origin main v0.1.0
$ gitversioned check
ok    config        defaults
ok    git           full history, 1 release tag, latest v0.1.0
ok    targets       src/text_stats/version.py
warn  archive file  .git_archival.txt is not set up, so source tarballs lose the version. Run `gitversioned init`.
warn  github        gh is missing or not signed in: release --pr, GitHub releases and pull request titles in the changelog are unavailable.
```

Pull requests merge with Conventional Commit titles. A build of `main` is a
development version, and the tree stays clean because `version.py` is ignored:

```console
$ echo "a = 1" > src/text_stats/lines.py && git add -A && git commit -qm "feat(python): count blank lines (#7)" && git push -q
$ echo "b = 1" > src/text_stats/words.py && git add -A && git commit -qm "fix(python): count hyphenated words once (#8)" && git push -q
$ python -m build --no-isolation >/dev/null 2>&1 && ls dist && git status --short
text_stats-0.1.1.dev20261125+d4175e5-py3-none-any.whl
text_stats-0.1.1.dev20261125+d4175e5.tar.gz
```

### Prepare the release

Until the release pull request is turned on, a maintainer writes the release in
a pull request of its own. Below 1.0.0 every level shifts down one, so the
feature makes a patch release. The `[Unreleased]` entries written by hand join
the entries from the commits, and `[Unreleased]` is left empty:

```console
$ git switch -q -c release-0.1.1 && gitversioned release --write && git diff --stat
release   0.1.1  (minor, a patch below 1.0.0, from commits, from 0.1.0)
tag       v0.1.1
files     CHANGELOG.md

## [0.1.1] - 2026-11-25

### Added

- **python**: count blank lines (#7)

### Deprecated

- `count_words()` is deprecated; use `count()`.

### Fixed

- **python**: count hyphenated words once (#8)

Wrote CHANGELOG.md.
 CHANGELOG.md | 10 ++++++++++
 1 file changed, 10 insertions(+)
$ sed -n '8,30p' CHANGELOG.md
## [Unreleased]

## [0.1.1] - 2026-11-25

### Added

- **python**: count blank lines (#7)

### Deprecated

- `count_words()` is deprecated; use `count()`.

### Fixed

- **python**: count hyphenated words once (#8)

## [0.1.0] - 2026-10-01

### Added

- First release of text-stats.
```

Before it merges, `release:verify` passes for the new tag:

```console
$ git commit -qam "release: v0.1.1" && .mise/tasks/release/verify v0.1.1
ok    tag        0.1.1, newer than v0.1.0
ok    changelog  CHANGELOG.md has the section
$ git switch -q main && git merge -q --squash release-0.1.1 >/dev/null && git commit -qm "release: v0.1.1 (#9)" && git push -q
```

### Tag it by hand

`release-manual.yml` runs `release:manual` with the version. It runs the same
checks as `release:verify`, then tags `main` and pushes the tag, which starts
`release.yml`:

```console
$ .mise/tasks/release/manual 0.1.1
tag       v0.1.1 at b18756a, pushed
$ .mise/tasks/release/verify v0.1.1 --tagged
ok    tag        0.1.1 at HEAD, newer than v0.1.0
ok    changelog  CHANGELOG.md has the section
$ .mise/tasks/release/notes v0.1.1
### Added

- **python**: count blank lines (#7)

### Deprecated

- `count_words()` is deprecated; use `count()`.

### Fixed

- **python**: count hyphenated words once (#8)

```

`release.yml` builds from the tag:

```console
$ rm -rf dist && python -m build --no-isolation >/dev/null 2>&1 && ls dist
text_stats-0.1.1-py3-none-any.whl
text_stats-0.1.1.tar.gz
$ pip install -q --root-user-action=ignore --no-deps --no-index --target ../site dist/*.whl && PYTHONPATH=../site python -m text_stats --version
text-stats 0.1.1
```

### What release:verify refuses

A version that is not newer than the last release, a version with no changelog
section, and a tag that exists away from `HEAD` all fail:

```console
$ .mise/tasks/release/verify v0.0.9
fail  tag  0.0.9 is not newer than v0.1.1.
[exit 1]
$ .mise/tasks/release/verify v0.3.0
ok    tag        0.3.0, newer than v0.1.1
fail  changelog  CHANGELOG.md has no [0.3.0] section. Run `gitversioned release 0.3.0 --write` and commit it first.
[exit 1]
$ git commit -q --allow-empty -m "docs: typo (#10)" && .mise/tasks/release/verify v0.1.1 --tagged
fail  tag  v0.1.1 already exists at b18756a, not at HEAD.
[exit 1]
$ .mise/tasks/release/manual 0.1.2
fail  CHANGELOG.md has no [0.1.2] section. Run `gitversioned release 0.1.2 --write` and commit it first.
[exit 1]
```

## How it works

- [`pyproject.toml`](pyproject.toml) has no `[tool.gitversioned]` table. The
  defaults are the template's: `v{version}` tags, PEP 440 for Python, the
  `release: vX.Y.Z` title and `CHANGELOG.md`.
- `release:verify` is `gitversioned check --tag`: the tag must match the
  template, be newer than the last release, have its `## [X.Y.Z]` section in
  `CHANGELOG.md`, and, if it exists, be at `HEAD`.
- `release:manual` is `gitversioned release VERSION --tag`, which runs the same
  checks before it tags.
- `release:notes` cuts the `## [X.Y.Z]` section out of `CHANGELOG.md` for the
  GitHub release body.
- With the release pull request on, `release-pr.yml` runs `release --pr` and
  `release --tag` instead: see [release-pr](../release-pr/README.md).

## Next

- [template-polyglot](../template-polyglot/README.md) for a render with Rust,
  npm and CITATION.cff.
- [github-actions](../github-actions/README.md) for the workflows that run these
  steps.
