# Change files and the commit prompt

Changelog entries written by hand, one file each, next to the code they
describe: the changesets workflow. `gitversioned new` writes them, or commits
staged work with a checked title, and asks for what it was not given.

| Level        | Shows                                                         | Needs |
| ------------ | ------------------------------------------------------------- | ----- |
| Intermediate | `new`, `.changes/`, `bump` overrides, `new --commit`, `check` | git   |

## Run

Copy this folder anywhere and run the commands below in it. The transcript is
checked on every test run, so it is exactly what you will see, apart from
hashes and dates.

### Write change files

Each file in `.changes/` holds a type, an optional scope and the entry text.
`check` validates them against the same types and scopes as commit titles.

```console
$ git init -q && git add -A && git commit -qm "feat: first release" && git tag v1.0.0
$ gitversioned new --type feat --scope cli "Add --explain, which shows why a version was chosen."
wrote     .changes/20261125-add-explain-which-shows-why-a-version.md  feat(cli): Add --explain, which shows why a version was chosen.
$ gitversioned new -t fix -s core "Peel annotated tags."
wrote     .changes/20261125-peel-annotated-tags.md  fix(core): Peel annotated tags.
$ gitversioned new -t docs --bump patch "Document the release flow."
wrote     .changes/20261125-document-the-release-flow.md  docs: Document the release flow.
$ cat .changes/20261125-add-explain-which-shows-why-a-version.md
---
type: feat
scope: cli
---
Add --explain, which shows why a version was chosen.
$ gitversioned new -t feat -s gui "A window."
fail  unknown scope 'gui'. Scopes: core, cli, docs.
[exit 2]
$ gitversioned check | grep changes
ok    changes       3 change files
```

`bump` replaces the level the type gives, so a docs change can still ship as a
patch, and `bump: none` keeps a change out of the version decision.
`breaking: true` (`--breaking`) makes it a major release.

### Release them

The plan reads the change files like commits. Writing the release moves their
entries into the changelog and deletes the files, so the release pull request
carries both.

```console
$ git add -A && git commit -qm "chore: changes for the release"
$ gitversioned release
release   1.1.0  (minor, from commits, from 1.0.0)
tag       v1.1.0
files     CHANGELOG.md, .changes/20261125-add-explain-which-shows-why-a-version.md, .changes/20261125-document-the-release-flow.md, .changes/20261125-peel-annotated-tags.md

## [1.1.0] - 2026-11-25

### Added

- **cli**: Add --explain, which shows why a version was chosen.

### Changed

- Document the release flow.

### Fixed

- **core**: Peel annotated tags.

Nothing changed. Run with --write, --pr or --tag.
$ gitversioned release --write | tail -1 && ls -A .changes | wc -l
Wrote CHANGELOG.md, .changes/20261125-add-explain-which-shows-why-a-version.md, .changes/20261125-document-the-release-flow.md, .changes/20261125-peel-annotated-tags.md.
0
```

### Commit with a checked title

`new --commit` commits the staged changes with a title it built and checked,
the way `cz commit` does. Without `--type` and a message, in a terminal, it asks
for each part: type, scope, message and whether the change is breaking.

```console
$ echo a > notes.txt && git add notes.txt && gitversioned new --commit -t fix -s core "Handle empty input."
commit    c7887ac  fix(core): Handle empty input.
$ git log -1 --format=%s
fix(core): Handle empty input.
$ gitversioned new --commit -t wip "half done"
fail  unknown type 'wip'. Types: feat, fix, perf, refactor, docs, test, build, ci, chore, revert, deprecate, release.
[exit 2]
$ gitversioned new < /dev/null
fail  give --type and a MESSAGE, or run in a terminal to be asked.
[exit 2]
```

## How it works

- A change file is Markdown with front matter: `type`, `scope`, `bump`,
  `breaking` and `package`. The text after the front matter is the entry.
- A change for a package with its own tag (`package: web`) is released with
  that package: `release -p web`. `changes` moves the folder.
- Change files mix freely with commits: both count for the bump, and both land
  in the section.

## Next

- [release-local](../release-local/README.md) for the rest of a local release.
- [changelog-style](../changelog-style/README.md) to change how the section looks.
