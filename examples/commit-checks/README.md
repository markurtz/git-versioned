# Pull request titles and commit messages

`gitversioned check` validates Conventional Commit subjects the same way in a
pull request workflow, in a commit-msg hook and in a terminal, against one list
of types and one list of scopes.

| Level    | Shows                                                                       | Needs |
| -------- | --------------------------------------------------------------------------- | ----- |
| Beginner | `check TITLE`, `--commits`, `--file`, `--warn`, `--tag`, `--json`, `scopes` | git   |

## Run

Copy this folder anywhere and run the commands below in it. The transcript is
checked on every test run, so it is exactly what you will see, apart from
hashes and dates.

### Titles

```console
$ git init -q && git add -A && git commit -qm "chore: start" && git tag v1.0.0
$ gitversioned check "feat(cli): add --explain"
ok
$ gitversioned check "fix!: drop Python 3.9"
ok
$ gitversioned check "added explain"
fail  title  'added explain' is not a Conventional Commit title. Expected type(scope): subject. Types: feat, fix, perf, refactor, docs, test, build, ci, chore, revert, deprecate, release.
[exit 1]
$ gitversioned check "feat(gui): add a window"
fail  title  unknown scope 'gui'. Scopes: core, cli, docs, deps, ci, release.
[exit 1]
$ gitversioned check "wip: half done"
fail  title  unknown type 'wip'. Types: feat, fix, perf, refactor, docs, test, build, ci, chore, revert, deprecate, release.
[exit 1]
```

The default types are the template's twelve: `feat`, `fix`, `perf`,
`refactor`, `docs`, `test`, `build`, `ci`, `chore`, `revert`, `deprecate` and
`release`. Scopes are open unless `scopes` lists them, as
[`gitversioned.toml`](gitversioned.toml) does here.

`--json` gives the same answer to a script:

```console
$ gitversioned check "feat(gui): add a window" --json
{
  "ok": false,
  "findings": [
    {
      "status": "fail",
      "area": "title",
      "message": "unknown scope 'gui'. Scopes: core, cli, docs, deps, ci, release."
    }
  ]
}
[exit 1]
```

### Every commit on a branch

`--commits` takes any git range, so a pull request can check each commit, not
only its title:

```console
$ git switch -q -c topic
$ echo a >> notes.txt && git commit -qam "feat(core): parse the input"
$ echo b >> notes.txt && git commit -qam "updated stuff"
$ gitversioned check --commits main..HEAD
fail  5580f3f  'updated stuff' is not a Conventional Commit title. Expected type(scope): subject. Types: feat, fix, perf, refactor, docs, test, build, ci, chore, revert, deprecate, release.
[exit 1]
$ git reset -q --hard HEAD~1 && gitversioned check --commits main..HEAD
ok    commits  1 commit
```

### A commit-msg hook that only warns

`--file` reads the message git is about to commit, and `--warn` reports a
problem without blocking the commit:

```console
$ printf '#!/bin/sh\nexec gitversioned check --file "$1" --warn\n' > .git/hooks/commit-msg && chmod +x .git/hooks/commit-msg
$ echo c >> notes.txt && git commit -qam "tweak things"
warn  title  'tweak things' is not a Conventional Commit title. Expected type(scope): subject. Types: feat, fix, perf, refactor, docs, test, build, ci, chore, revert, deprecate, release.
$ git log -1 --format=%s
tweak things
$ echo d >> notes.txt && git commit -qam "docs: explain the hook"
ok
```

Git's own subjects (merges, `fixup!` and `squash!`) are not checked.

```console
$ echo e >> notes.txt && git commit -qam "fixup! docs: explain the hook"
ok
```

### Tags

`--tag` checks a tag name before a release: it must match the tag template and
be newer than the last release.

```console
$ gitversioned check --tag v1.1.0
ok    tag  1.1.0, newer than v1.0.0
$ gitversioned check --tag v1.1.0-rc.1
ok    tag  1.1.0rc1, newer than v1.0.0
$ gitversioned check --tag v0.9.0
fail  tag  0.9.0 is not newer than v1.0.0.
[exit 1]
$ gitversioned check --tag release-1.1
fail  tag  'release-1.1' is not a release tag. Expected vX.Y.Z with an optional pre-release such as -rc.1.
[exit 1]
```

## How it works

- [`gitversioned.toml`](gitversioned.toml) sets `scopes`. `types` replaces the
  default type list the same way. `scopes` can also name a TOML file whose
  tables are the scopes, as the [template-polyglot](../template-polyglot/README.md)
  example does with `.config/blocks.toml`.
- Exit codes: 0 when everything passes, 1 when a check fails, 2 for bad usage.

## Next

- [github-actions](../github-actions/README.md) for the pull request title job.
- [next-version](../next-version/README.md) for what each type does to the version.
