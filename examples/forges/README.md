# GitHub releases, GitLab and Gitea

The release pull request and the release itself on each forge: GitHub through
`gh`, GitLab and Gitea (and Forgejo) through their REST APIs with a token. With
`forge_release = true`, `release --tag` also creates the forge's release, with
the changelog section as its notes.

| Level    | Shows                                                               | Needs                     |
| -------- | ------------------------------------------------------------------- | ------------------------- |
| Advanced | `forge_release`, `forge`, `release --pr` and `--tag` on each forge   | git, Python, `gh` signed in |

## Run

Copy this folder anywhere and run the commands below in it. A bare repository
stands in for the forge's git server. During the test a stand-in `gh` and
stand-in GitLab and Gitea APIs on localhost record what is created, and
[`show.py`](show.py) prints it; against a real forge, set the token and look at
its web pages instead.

```console
$ git init -q && git add -A && git commit -qm "feat: first release" && git tag v1.0.0
$ git init -q --bare ../origin.git && git remote add origin ../origin.git && git push -q -u origin main v1.0.0
```

### A GitHub release with the tag

```console
$ git commit -q --allow-empty -m "feat(cli): add --explain (#41)"
$ gitversioned release --write | tail -1 && git commit -qam "release: v1.1.0" && git push -q
Wrote CHANGELOG.md.
$ GITVERSIONED__FORGE_RELEASE=true gitversioned release --tag
tag       v1.1.0 at 43b61ac, pushed
release   https://github.com/acme/acme/releases/tag/v1.1.0
$ python show.py github
release v1.1.0  - **cli**: add --explain (#41)
```

The release is created as a draft, files from `release --publish` are attached
(see [publish](../publish/README.md)), then it is published, which works with
immutable releases too.

### GitLab merge requests and releases

`forge = "gitlab"` (or a gitlab host on `origin`, or `GITLAB_CI`) talks to the
GitLab API with `GITLAB_TOKEN`, a token with the `api` scope. In GitLab CI,
`CI_API_V4_URL` and `CI_PROJECT_PATH` say where.

```console
$ git clone -q ../origin.git ../on-gitlab && cd ../on-gitlab && printf 'forge = "gitlab"\nforge_release = true\n' > gitversioned.toml && git add -A && git commit -qm "chore: release on GitLab" && git push -q
$ cd ../on-gitlab && gitversioned check | grep gitlab
ok    gitlab        token is set
$ cd ../on-gitlab && git commit -q --allow-empty -m "fix(core): peel annotated tags (!12)" && git push -q && gitversioned release --pr
release   1.1.1
branch    release/next  (rebuilt from main)
commit    release: v1.1.1
pr        #57 opened  https://gitlab.example/acme/demo/-/merge_requests/57
$ cd ../on-gitlab && git fetch -q && git merge -q --ff-only origin/release/next && git push -q && gitversioned release --tag
tag       v1.1.1 at 764f1ca, pushed
release   https://gitlab.example/acme/demo/-/releases/v1.1.1
$ python show.py gitlab
pull 57  release/next -> main  release: v1.1.1  ['release']
release v1.1.1  - **core**: peel annotated tags (!12)
$ cd ../on-gitlab && GITLAB_TOKEN= gitversioned release --pr
fail  release --pr needs GITLAB_TOKEN, a token with the api scope.
[exit 3]
```

### Gitea and Forgejo pull requests and releases

`forge = "gitea"` (or a gitea, forgejo or codeberg host, or Gitea Actions)
talks to the Gitea API with `GITEA_TOKEN`. The `release` label is created when
the repository does not have it.

```console
$ git clone -q ../origin.git ../on-gitea && cd ../on-gitea && printf 'forge = "gitea"\nforge_release = true\n' > gitversioned.toml && git add -A && git commit -qm "chore: release on Gitea" && git push -q
$ cd ../on-gitea && git commit -q --allow-empty -m "fix: gitea labels (#7)" && git push -q && gitversioned release --pr
release   1.1.2
branch    release/next  (rebuilt from main)
commit    release: v1.1.2
pr        #57 opened  https://gitea.example/acme/demo/pulls/57
$ cd ../on-gitea && git fetch -q && git merge -q --ff-only origin/release/next && git push -q && gitversioned release --tag
tag       v1.1.2 at fdb9496, pushed
release   https://gitea.example/acme/demo/releases/tag/v1.1.2
$ python show.py gitea
pull 57  release/next -> main  release: v1.1.2  ['release']
release v1.1.2  - gitea labels (#7)
```

## How it works

- `forge = "auto"` reads the `origin` host and the CI environment; anything
  else is GitHub. `GITLAB_API_URL` and `GITEA_API_URL` point at a server whose
  API is not at the usual address.
- Pull request numbers come from `(#N)` and, for GitLab, `(!N)` suffixes, and
  their titles, labels and `## Changelog` blocks are read the same way on each
  forge. Release files are attached on GitHub only.
- Without the token, `release --pr` stops with exit 3; `release --tag` still
  tags and warns that no release was created.

## Next

- [release-pr](../release-pr/README.md) for the release pull request on GitHub in detail.
- [publish](../publish/README.md) to upload the tagged release to registries.
