# Maintenance branches and backports

Releases from `1.x` while `main` is on 2.x: the semantic-release maintenance
branch flow. `branches` names the branches a release may also be cut from.

| Level    | Shows                                                       | Needs                       |
| -------- | ----------------------------------------------------------- | --------------------------- |
| Advanced | `branches`, `release --pr` on `1.x`, line rules, `check --tag` | git, Python, `gh` signed in |

## Run

Copy this folder anywhere and run the commands below in it. A bare repository
stands in for GitHub and a stand-in `gh` keeps pull requests in a JSON file.

```console
$ git init -q && git add -A && git commit -qm "feat: first release" && git tag v1.4.0
$ git init -q --bare ../origin.git && git remote add origin ../origin.git && git push -q -u origin main v1.4.0
$ git branch 1.x && git commit -q --allow-empty -m "feat!: the new API" && git tag v2.0.0 && git push -q origin main 1.x v2.0.0
```

[`gitversioned.toml`](gitversioned.toml) sets `branches = ["*.x"]`.

### A backport release

On `1.x` only the tags reachable from the branch count, so the next release is
1.4.1, not 2.0.1. The release pull request comes from `release/next-1.x` and
merges into `1.x`.

```console
$ git switch -q 1.x && git commit -q --allow-empty -m "fix(core): backport the parser fix (#50)" && git push -q -u origin 1.x
$ gitversioned version --next
1.4.1
$ gitversioned release --pr
release   1.4.1
branch    release/next-1.x  (rebuilt from 1.x)
commit    release: v1.4.1
pr        #57 opened  https://github.com/acme/acme/pull/57
$ gh pr view 57 --jq .base
1.x
$ git fetch -q && git merge -q --ff-only origin/release/next-1.x && git push -q && gitversioned release --tag
tag       v1.4.1 at fdd0a91, pushed
$ git tag --sort=v:refname
v1.4.0
v1.4.1
v2.0.0
```

### Line rules

A branch named `N.x` keeps releases on major N, and `N.M.x` on N.M. A tag older
than a release already on its `X.Y` line fails `check --tag`, and branches that
are not in `branches` still cannot open a release pull request.

```console
$ git commit -q --allow-empty -m "feat!: a 2.x change on 1.x" && gitversioned release
fail  2.0.0 is outside the 1.x line that '1.x' maintains. Release a smaller change, or release from the main branch.
[exit 1]
$ git reset -q --hard HEAD~1 && gitversioned check --tag v1.4.0
fail  tag  1.4.0 is older than v1.4.1 on the same 1.4 line.
[exit 1]
$ git switch -q -c topic && gitversioned release --pr
fail  release --pr runs on 'main', '*.x', not 'topic': the release would carry this branch's unmerged commits.
[exit 1]
```

## How it works

- `branches` takes glob patterns, such as `"*.x"` or `"maint/*"`. The release
  branch is `release/next-<branch>`, and `release --tag` checks the tag against
  the releases reachable from the branch.
- On `main` nothing changes: the next release is newer than every tag.

## Next

- [release-pr](../release-pr/README.md) for the release pull request on `main`.
- [github-actions](../github-actions/README.md) to run it from workflows.
