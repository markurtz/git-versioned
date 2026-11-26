# Releasing from a terminal

The whole release, by hand: preview the plan, write the changelog and the
committed manifests, commit, and tag. A workflow runs the same steps with the
same checks (see [release-pr](../release-pr/README.md)).

| Level        | Shows                                                                        | Needs |
| ------------ | ---------------------------------------------------------------------------- | ----- |
| Intermediate | `release`, `--write`, `--tag`, `VERSION`, `annotated`, `[Unreleased]`, `check --tag` | git   |

## Run

Copy this folder anywhere and run the commands below in it. The transcript is
checked on every test run, so it is exactly what you will see, apart from
hashes and dates. A bare repository next to the example stands in for GitHub.

```console
$ git init -q && git add -A && git commit -qm "feat: first public release" && git tag v1.2.0
$ git init -q --bare ../origin.git && git remote add origin ../origin.git && git push -q origin main v1.2.0
$ echo "a = 1" > src/relay/a.py && git add -A && git commit -qm "feat(cli): add --explain (#41)"
$ echo "b = 1" > src/relay/b.py && git add -A && git commit -qm "fix(core): peel annotated tags (#40)"
$ echo "c = 1" > src/relay/c.py && git add -A && git commit -qm "chore(deps): bump ruff (#39)"
$ echo "d = 1" > src/relay/d.py && git add -A && git commit -qm "docs: describe the plan (#42)"
```

### The plan

`release` changes nothing. It prints the version, the tag, the files a release
would touch and the changelog section. Maintenance commits (`chore`, `ci`,
`test`) are left out, and `docs` goes under Changed:

```console
$ gitversioned release
release   1.3.0  (minor, from commits, from 1.2.0)
tag       v1.3.0
files     CHANGELOG.md, CITATION.cff

## [1.3.0] - 2026-11-25

### Added

- **cli**: add --explain (#41)

### Changed

- describe the plan (#42)

### Fixed

- **core**: peel annotated tags (#40)

### Security

- Pin the build image by digest.

Nothing changed. Run with --write, --pr or --tag.
$ git status --short
```

`--json` gives a script the same plan:

```console
$ gitversioned release --json
{
  "stage": "plan",
  "version": "1.3.0",
  "semver": "1.3.0",
  "previous": "1.2.0",
  "tag": "v1.3.0",
  "level": "minor, from commits, from 1.2.0",
  "files": [
    "CHANGELOG.md",
    "CITATION.cff"
  ],
  "changed": [],
  "changes": [],
  "base": "main",
  "changelog": "## [1.3.0] - 2026-11-25\n\n### Added\n\n- **cli**: add --explain (#41)\n\n### Changed\n\n- describe the plan (#42)\n\n### Fixed\n\n- **core**: peel annotated tags (#40)\n\n### Security\n\n- Pin the build image by digest.\n"
}
```

### Write, commit, tag

`--write` applies the plan to the working tree. The lines under
`## [Unreleased]` move into the new section, as Keep a Changelog asks, and the
citation file gets the new version and date:

```console
$ gitversioned release --write
release   1.3.0  (minor, from commits, from 1.2.0)
tag       v1.3.0
files     CHANGELOG.md, CITATION.cff

## [1.3.0] - 2026-11-25

### Added

- **cli**: add --explain (#41)

### Changed

- describe the plan (#42)

### Fixed

- **core**: peel annotated tags (#40)

### Security

- Pin the build image by digest.

Wrote CHANGELOG.md, CITATION.cff.
$ git diff CITATION.cff | tail -4
-version: "1.2.0"
-date-released: "2026-01-15"
+version: "1.3.0"
+date-released: "2026-11-25"
$ sed -n '6,30p' CHANGELOG.md
## [Unreleased]

## [1.3.0] - 2026-11-25

### Added

- **cli**: add --explain (#41)

### Changed

- describe the plan (#42)

### Fixed

- **core**: peel annotated tags (#40)

### Security

- Pin the build image by digest.

## [1.2.0] - 2026-01-15

### Added

- First public release.
```

Commit it with the release title, then `--tag` tags that commit and pushes the
tag. Because `annotated = true` is set, the tag message is the changelog
section:

```console
$ git commit -qam "release: v1.3.0" && git push -q origin main
$ gitversioned release --tag
tag       v1.3.0 at 1252338, pushed
$ git ls-remote --tags origin | sed 's/^[0-9a-f]*\t//' | grep -v '\^{}'
refs/tags/v1.2.0
refs/tags/v1.3.0
$ git tag -l --format='%(contents)' v1.3.0
## [1.3.0] - 2026-11-25

### Added

- **cli**: add --explain (#41)

### Changed

- describe the plan (#42)

### Fixed

- **core**: peel annotated tags (#40)

### Security

- Pin the build image by digest.

$ gitversioned version
1.3.0
```

Once the tag exists there is nothing left to release:

```console
$ gitversioned release
fail  Nothing to release since 1.3.0: no commit since is a feat, a fix or another releasable type.
[exit 1]
```

### Tag by hand

With a `VERSION`, `--tag` tags the current commit by hand, like the template's
`release-manual` workflow. It runs the checks of `check --tag`: the version is
newer than every release, and the changelog holds its section.

```console
$ echo "e = 1" > src/relay/e.py && git add -A && git commit -qm "fix(core): one more fix" && git push -q origin main
$ gitversioned check --tag v1.3.0
fail  tag  v1.3.0 already exists at 1252338, not at HEAD.
[exit 1]
$ gitversioned release 1.2.9 --tag
fail  1.2.9 is not newer than v1.3.0.
[exit 1]
$ gitversioned release 1.3.1 --tag
fail  CHANGELOG.md has no [1.3.1] section. Run `gitversioned release 1.3.1 --write` and commit it first.
[exit 1]
```

Write the section first, commit it, and the same command tags:

```console
$ gitversioned release 1.3.1 --write && git commit -qam "release: v1.3.1"
release   1.3.1  (set by VERSION, from 1.3.0)
tag       v1.3.1
files     CHANGELOG.md, CITATION.cff

## [1.3.1] - 2026-11-25

### Fixed

- **core**: one more fix

Wrote CHANGELOG.md, CITATION.cff.
$ gitversioned check --tag v1.3.1
ok    tag        1.3.1, newer than v1.3.0
ok    changelog  CHANGELOG.md has the section
$ gitversioned release 1.3.1 --tag
tag       v1.3.1 at 098285d, pushed
$ gitversioned version
1.3.1
```

## How it works

- [`pyproject.toml`](pyproject.toml) sets one key, `annotated = true`, under
  `[tool.gitversioned]`; lightweight tags are the default.
- [`CHANGELOG.md`](CHANGELOG.md) starts with an `[Unreleased]` section written
  by hand. Releases insert their section below it and never edit older ones.
- [`CITATION.cff`](CITATION.cff) is found by discovery; its `version` and
  `date-released` follow each release.
- `changelog = false` turns the changelog off, and `changelog = "docs/changes.md"`
  moves it.

## Next

- [release-pr](../release-pr/README.md) for the same release through a reviewed pull request.
- [next-version](../next-version/README.md) for how the level is chosen.
