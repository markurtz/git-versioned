# GitHub Actions workflows

Six workflows cover the whole release flow: pull request titles, the release
pull request, tagging and publishing the merge, a manual release, nightly
builds and hand-pushed tags. They sit in [`.github/workflows/`](.github/workflows)
ready to copy, and every step that runs gitversioned is run below.

| Level    | Shows                                                       | Needs                         |
| -------- | ----------------------------------------------------------- | ----------------------------- |
| Advanced | `check`, `release --pr`, `release --tag`, nightly builds, CI safety | git, Python, `build`, `gh` signed in |

## Run

Copy this folder anywhere and run the commands below in it. A bare repository
stands in for GitHub and a stand-in `gh` keeps pull requests in a JSON file.
[`ci.py`](ci.py) runs a workflow's steps the way a runner would: each `run` step
in `bash` with its `env` and `CI=true`, `${{ … }}` filled from `--event`, and
`uses` steps skipped because this folder is already the checkout.

```console
$ git init -q && git add -A && git commit -qm "feat: first release" && git tag v1.0.0
$ git init -q --bare ../origin.git && git remote add origin ../origin.git && git push -q -u origin main v1.0.0
```

### Pull request titles

[`pr-title.yml`](.github/workflows/pr-title.yml) checks the title, which a
squash merge turns into the commit subject:

```console
$ python ci.py .github/workflows/pr-title.yml --event github.event.pull_request.title="feat(cli): add --explain"
job title
  uses actions/checkout@v4: skipped
  step Check the title
ok
$ python ci.py .github/workflows/pr-title.yml --event github.event.pull_request.title="Add explain flag"
job title
  uses actions/checkout@v4: skipped
  step Check the title
fail  title  'Add explain flag' is not a Conventional Commit title. Expected type(scope): subject. Types: feat, fix, perf, refactor, docs, test, build, ci, chore, revert, deprecate, release.
  failed with exit code 1
[exit 1]
```

### The release pull request

The pull request merges, and the push to `main` starts both
[`release-pr.yml`](.github/workflows/release-pr.yml) and
[`release.yml`](.github/workflows/release.yml). Only the first runs, since the
commit is not a release:

```console
$ echo "a = 1" > src/beam/a.py && git add -A && git commit -qm "feat(cli): add --explain (#12)" && git push -q
$ python ci.py .github/workflows/release-pr.yml --event github.event.head_commit.message="feat(cli): add --explain (#12)"
job release-pr
  uses actions/checkout@v4: skipped
  step Open or update the release pull request
release   1.1.0
branch    release/next  (rebuilt from main)
commit    release: v1.1.0
pr        #57 opened  https://github.com/acme/acme/pull/57
$ python ci.py .github/workflows/release.yml --event github.event.head_commit.message="feat(cli): add --explain (#12)"
job tag: skipped
```

Merging the release pull request is the release. On that push only
`release.yml` runs: it tags the merge, pushes the tag, and builds from it:

```console
$ git merge -q --squash origin/release/next >/dev/null && git commit -qm "release: v1.1.0 (#57)" && git push -q && gh pr merge 57 --squash
$ python ci.py .github/workflows/release-pr.yml --event github.event.head_commit.message="release: v1.1.0 (#57)"
job release-pr: skipped
$ python ci.py .github/workflows/release.yml --event github.event.head_commit.message="release: v1.1.0 (#57)"
job tag
  uses actions/checkout@v4: skipped
  step Tag the release commit
tag       v1.1.0 at da21321, pushed
  step Build
beam-1.1.0-py3-none-any.whl
beam-1.1.0.tar.gz
  uses pypa/gh-action-pypi-publish@release/v1: skipped
$ git ls-remote --tags origin | sed 's/^[0-9a-f]*\t//'
refs/tags/v1.0.0
refs/tags/v1.1.0
```

### Hand-pushed tags

[`tag-check.yml`](.github/workflows/tag-check.yml) runs on every pushed tag. A
tag pushed by hand that is not newer than the last release fails:

```console
$ GITHUB_REF_NAME=v1.1.0 python ci.py .github/workflows/tag-check.yml
job check
  uses actions/checkout@v4: skipped
  step Check the tag
ok    tag        1.1.0 at HEAD, newer than v1.0.0
ok    changelog  CHANGELOG.md has the section
$ git tag v1.0.1 && GITHUB_REF_NAME=v1.0.1 python ci.py .github/workflows/tag-check.yml
job check
  uses actions/checkout@v4: skipped
  step Check the tag
fail  tag  1.0.1 is not newer than v1.1.0.
  failed with exit code 1
[exit 1]
$ git tag -d v1.0.1 >/dev/null
```

### Nightly builds

[`nightly.yml`](.github/workflows/nightly.yml) builds the next release as a
dated nightly, with no commit hash, so a package index accepts it. The build
plugin reads the type from `GITVERSIONED__TYPE`, and nothing is committed:

```console
$ echo "b = 1" > src/beam/b.py && git add -A && git commit -qm "fix(core): handle empty input (#14)" && git push -q
$ rm -rf dist && python ci.py .github/workflows/nightly.yml
job nightly
  uses actions/checkout@v4: skipped
  step Version
ok    config        defaults
ok    git           full history, 2 release tags, latest v1.1.0
ok    targets       src/beam/version.py
warn  archive file  .git_archival.txt is not set up, so source tarballs lose the version. Run `gitversioned init`.
ok    github        gh is signed in
  env VERSION=1.1.1.dev20261125
  step Build
beam-1.1.1.dev20261125-py3-none-any.whl
beam-1.1.1.dev20261125.tar.gz
$ git status --short
```

### Full history is required

Every job that reads a version checks out with `fetch-depth: 0`. In a shallow
clone gitversioned stops with exit code 3 in CI instead of building a wrong
version:

```console
$ git clone -q --depth 1 file://$PWD/../origin.git ../shallow && cd ../shallow && CI=true gitversioned version
fail  shallow clone with no release tags reachable, so the version cannot be trusted. Fetch full history (fetch-depth: 0 on actions/checkout).
[exit 3]
```

### A manual release

[`release-manual.yml`](.github/workflows/release-manual.yml) releases without
the pull request, at the version given or the next one:

```console
$ rm -rf dist && python ci.py .github/workflows/release-manual.yml --event inputs.version=2.0.0
job release
  uses actions/checkout@v4: skipped
  step Write the release
release   2.0.0  (set by VERSION, from 1.1.0)
tag       v2.0.0
files     CHANGELOG.md

## [2.0.0] - 2026-11-25

### Fixed

- **core**: handle empty input (#14)

Wrote CHANGELOG.md.
  step Tag it
tag       v2.0.0 at 4c211b3, pushed
$ git log --oneline -1 origin/main && git ls-remote --tags origin v2.0.0 | sed 's/^[0-9a-f]*\t//'
4c211b3 release: v2.0.0
refs/tags/v2.0.0
```

## How it works

- Every workflow pins its permissions: `contents: write` to push tags and the
  release branch, `pull-requests: write` for the release pull request, and
  `id-token: write` for trusted publishing to PyPI.
- `release-pr.yml` accepts exit code 1, which means nothing is releasable yet.
  It skips release commits, which `release.yml` handles.
- Pull requests opened with the default `GITHUB_TOKEN` start no other
  workflows. Use a GitHub App token if checks must run on the release pull
  request.
- `release --tag` refuses a tag that is not newer than the last release, so a
  rerun of `release.yml` cannot tag twice.
- The [GitHub Workflows guide](https://markurtz.github.io/git-versioned/guides/github-workflows/)
  explains each workflow.

## Next

- [release-pr](../release-pr/README.md) for the release pull request in detail,
  with candidates and labels.
- [ci-safety](../ci-safety/README.md) for every check that stops a CI build.
