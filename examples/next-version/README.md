# The next version and why

How gitversioned picks the next release from Conventional Commits, and every
way to override it. The project is a plain folder with no manifest, so versions
print in SemVer.

| Level        | Shows                                                                 | Needs |
| ------------ | --------------------------------------------------------------------- | ----- |
| Intermediate | `version --next`, `--explain`, `--bump`, `--pre`, `GITVERSIONED__BUMP` | git   |

## Run

Copy this folder anywhere and run the commands below in it. The transcript is
checked on every test run, so it is exactly what you will see, apart from
hashes and dates.

### Levels from commits

A fix asks for a patch release, a feature for a minor one, and a breaking change
(`!` after the type, or a `BREAKING CHANGE:` footer) for a major one. `chore`,
`ci` and `test` ask for nothing.

```console
$ git init -q && git add -A && git commit -qm "feat: first version" && git tag v1.2.0
$ echo fix >> notes.txt && git commit -qam "fix(core): handle empty input (#40)"
$ gitversioned version --next
1.2.1
$ echo feat >> notes.txt && git commit -qam "feat(cli): add --explain (#41)"
$ echo chore >> notes.txt && git commit -qam "chore(deps): bump ruff (#42)"
$ gitversioned version --next --explain
next      1.3.0
current   1.2.0  (tag v1.2.0, c3bebe5, 3 commits since)
why       minor, the highest level of 3 commits since v1.2.0
  none    chore(deps): bump ruff (#42)
  minor   feat(cli): add --explain (#41)
  patch   fix(core): handle empty input (#40)
note      base 1.2.0 from tag v1.2.0
config    defaults  (0 keys set, 14 defaults)
```

A breaking change in the footer counts the same as `!`:

```console
$ echo api >> notes.txt && git commit -qam "refactor(core): rename the entry point" -m "BREAKING CHANGE: run() is now main()."
$ gitversioned version --next
2.0.0
```

### Overrides

`--bump` forces a level, and `GITVERSIONED__BUMP` does the same from the
environment, or names the version outright, like release-please's `Release-As`:

```console
$ gitversioned version --next --bump minor
1.3.0
$ GITVERSIONED__BUMP=patch gitversioned version --next
1.2.1
$ GITVERSIONED__BUMP=4.0.0 gitversioned version --next
4.0.0
```

### Pre-releases

`--pre` makes the next version a pre-release and numbers it from the tags that
already exist. `rc`, `beta` and `alpha` work the same way:

```console
$ gitversioned version --next --pre beta
2.0.0-beta.1
$ gitversioned version --next --pre rc
2.0.0-rc.1
$ git tag v2.0.0-rc.1
$ echo more >> notes.txt && git commit -qam "fix(core): late fix"
$ gitversioned version --next --pre rc
2.0.0-rc.2
$ gitversioned version --next
2.0.0
```

### Nothing to release

When the commits since the last release ask for nothing, there is no next
version and the exit code is 1, so a workflow can skip the release:

```console
$ git tag v2.0.0 && echo ci >> notes.txt && git commit -qam "ci: cache the venv"
$ gitversioned version --next
fail  Nothing to release since 2.0.0: no commit since is a feat, a fix or another releasable type.
[exit 1]
$ gitversioned version --next --bump patch
2.0.1
```

### Below 1.0

Before 1.0.0 every level shifts down one: a breaking change is a minor release
and a feature a patch release.

```console
$ git init -q ../early && cd ../early && git commit -q --allow-empty -m "feat: start" && git tag v0.3.0
$ cd ../early && git commit -q --allow-empty -m "feat: add a thing" && gitversioned version --next
0.3.1
$ cd ../early && git commit -q --allow-empty -m "feat!: drop the old thing" && gitversioned version --next
0.4.0
$ cd ../early && gitversioned version --next --bump major
1.0.0
```

## How it works

- The rules are fixed: there is no bump setting. The
  [concepts guide](https://markurtz.github.io/git-versioned/guides/concepts/)
  lists every type and its level.
- Overrides win in this order: a `VERSION` argument or `--bump`, then
  `GITVERSIONED__BUMP`, then the `release:major`, `release:minor` and
  `release:patch` labels on pull requests (see
  [release-pr](../release-pr/README.md)).

## Next

- [release-local](../release-local/README.md) to turn the next version into a release.
- [commit-checks](../commit-checks/README.md) to keep commit subjects parseable.
