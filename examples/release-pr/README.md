# The release pull request

The reviewed release, as release-please and release-plz run it: on every push to
`main`, `gitversioned release --pr` rebuilds the `release/next` branch from
`main` and opens or updates one pull request holding the changelog section and
the stamped files. Merging it is the release decision, and
`gitversioned release --tag` tags the merge.

| Level    | Shows                                                                                             | Needs               |
| -------- | ------------------------------------------------------------------------------------------------- | ------------------- |
| Advanced | `release --pr`, `release --tag`, `release:rc` and `release:<level>` labels, `## Changelog` blocks | git, `gh` signed in |

## Run

Copy this folder anywhere and run the commands below in it. Here a bare
repository stands in for GitHub and a stand-in `gh` keeps pull requests in a
JSON file; with a real remote and a signed-in `gh` the commands are the same.
Squash merges are done with git, as GitHub would do them.

```console
$ git init -q && git add -A && git commit -qm "feat: first release" && git tag v1.2.0
$ git init -q --bare ../origin.git && git remote add origin ../origin.git && git push -q -u origin main v1.2.0
```

### Feature pull requests

Two feature pull requests are merged. The second rewrites its changelog entry
with a `## Changelog` block in its body, which replaces the title in the
release notes:

```console
$ echo "a = 1" > src/beacon/a.py && git add -A && git commit -qm "feat(cli): add --explain (#41)" && git push -q
$ git switch -q -c fix-tags && echo "b = 1" > src/beacon/b.py && git add -A && git commit -qm "fix(core): peel tags" && git push -q -u origin fix-tags
$ gh pr create --base main --head fix-tags --title "fix(core): peel annotated tags" --body $'Peels tags.\n\n## Changelog\n\n### Fixed\n\n- Annotated tags now resolve to their commit, so `version` agrees with `git describe`.'
https://github.com/acme/acme/pull/57
$ git switch -q main && git merge -q --squash fix-tags >/dev/null && git commit -qm "fix(core): peel annotated tags (#57)" && git push -q && gh pr merge 57 --squash
```

### Open the release pull request

```console
$ gitversioned release --pr
release   1.3.0
branch    release/next  (rebuilt from main)
commit    release: v1.3.0
pr        #58 opened  https://github.com/acme/acme/pull/58
$ gh pr view 58 --jq .title
release: v1.3.0
$ gh pr view 58 --jq .body
## [1.3.0] - 2026-11-25

### Added

- **cli**: add --explain (#41)

### Fixed

- **core**: Annotated tags now resolve to their commit, so `version` agrees with `git describe`. (#57)

---
Merging this pull request releases `v1.3.0`. Add the `release:rc` label to make it a release candidate.

$ git log -1 --format=%s origin/release/next && git diff --stat main origin/release/next
release: v1.3.0
 CHANGELOG.md | 10 ++++++++++
 1 file changed, 10 insertions(+)
```

Nothing changed on `main` itself:

```console
$ git status --short && git log -1 --format=%s
fix(core): peel annotated tags (#57)
```

### Keep it up to date

Every push to `main` rebuilds the branch from scratch, so the pull request never
drifts from `main` and never reverts a file:

```console
$ echo "c = 1" > src/beacon/c.py && git add -A && git commit -qm "perf(core): cache tag lookups (#45)" && git push -q
$ gitversioned release --pr
release   1.3.0
branch    release/next  (rebuilt from main)
commit    release: v1.3.0
pr        #58 updated  https://github.com/acme/acme/pull/58
$ gh pr view 58 --jq .body | grep -c "^- "
3
```

### Release candidates

The `release:rc` label on the release pull request makes the next refresh a
release candidate:

```console
$ gh pr edit 58 --add-label release:rc >/dev/null
$ gitversioned release --pr
release   1.3.0rc1
branch    release/next  (rebuilt from main)
commit    release: v1.3.0-rc.1
pr        #58 updated  https://github.com/acme/acme/pull/58
$ gh pr view 58 --jq .title
release: v1.3.0-rc.1
```

Merging it releases the candidate. Until the tag exists, `release --pr` waits
instead of opening the next release:

```console
$ git merge -q --squash origin/release/next >/dev/null && git commit -qm "release: v1.3.0-rc.1 (#58)" && git push -q && gh pr merge 58 --squash
$ gitversioned release --pr
fail  HEAD is the merged release commit for v1.3.0-rc.1, which is not tagged yet. Run release --tag first.
[exit 1]
$ gitversioned release --tag
tag       v1.3.0-rc.1 at 94eaaf3, pushed
$ gitversioned version
1.3.0rc1
```

### The final release

The next run opens a new pull request for the final release. Its section takes
over the candidate's entries and replaces the candidate's section:

```console
$ gitversioned release --pr
release   1.3.0
branch    release/next  (rebuilt from main)
commit    release: v1.3.0
pr        #59 opened  https://github.com/acme/acme/pull/59
$ gh pr view 59 --jq .title
release: v1.3.0
$ git show origin/release/next:CHANGELOG.md | sed -n '6,24p'
## [Unreleased]

## [1.3.0] - 2026-11-25

### Added

- **cli**: add --explain (#41)

### Changed

- **core**: cache tag lookups (#45)

### Fixed

- **core**: Annotated tags now resolve to their commit, so `version` agrees with `git describe`. (#57)

## [1.2.0] - 2026-10-01

### Added
```

A `release:major`, `release:minor` or `release:patch` label on a feature pull
request merged since the last release overrides the level:

```console
$ gh pr edit 57 --add-label release:major >/dev/null
$ gitversioned release --pr | grep "^release"
release   2.0.0
$ gh pr edit 57 --remove-label release:major >/dev/null && gitversioned release --pr | grep "^release"
release   1.3.0
```

Merge it and tag it:

```console
$ git merge -q --squash origin/release/next >/dev/null && git commit -qm "release: v1.3.0 (#59)" && git push -q && gh pr merge 59 --squash
$ gitversioned release --tag
tag       v1.3.0 at a0f0635, pushed
$ git ls-remote --tags origin | sed 's/^[0-9a-f]*\t//'
refs/tags/v1.2.0
refs/tags/v1.3.0
refs/tags/v1.3.0-rc.1
```

## How it works

- The branch, title and labels are fixed: `release/next`, `release: vX.Y.Z`, and
  the `release` label; `release:rc` asks for a candidate.
- `release --pr` refuses to run on any branch but `branch` (`main` by default)
  and on a dirty tree, so a release never carries unmerged work.
- Entries come from pull request titles when `gh` can read them, and from
  squash commit subjects otherwise. `chore`, `ci` and `test` are left out.
- The [github-actions](../github-actions/README.md) example runs these steps in
  workflows.

## Next

- [release-local](../release-local/README.md) for the same release without GitHub.
- [github-actions](../github-actions/README.md) for the workflows that run it.
