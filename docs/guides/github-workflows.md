# GitHub Workflows Guide

Three small jobs cover the whole release flow. Every job that reads a version
needs full history:

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
```

Without it, gitversioned exits with code 3 in CI instead of publishing a wrong
version.

## Check pull request titles

```yaml
name: pr-title
on:
  pull_request:
    types: [opened, edited, synchronize, reopened]
jobs:
  title:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pipx run gitversioned check "$TITLE"
        env:
          TITLE: ${{ github.event.pull_request.title }}
```

With squash merges the pull request title becomes the commit subject, so this
one check keeps the history releasable.

### With the gitversioned action

The repository root is also a composite action. It runs gitversioned without a
Python setup, passes the title as an input rather than through the shell, and
sets `version` and `output` step outputs:

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
- id: gv
  uses: markurtz/git-versioned@v0.4.0
  with:
    command: check
    title: ${{ github.event.pull_request.title }}
- run: echo "version ${{ steps.gv.outputs.version }}"
```

`command` takes any command and its options, such as `release --pr` with
`GH_TOKEN` in `env`; `version` pins the gitversioned release it runs.

## Keep the release pull request up to date

```yaml
name: release-pr
on:
  push:
    branches: [main]
permissions:
  contents: write
  pull-requests: write
jobs:
  release-pr:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - run: pipx run gitversioned release --pr || [ $? -eq 1 ]
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Exit code 1 means there is nothing to release yet, which is not a failure here.
Add `if: ${{ !startsWith(github.event.head_commit.message, 'release') }}` to the
job so the push of a merged release is left to the tagging workflow.
Pull requests opened with the default `GITHUB_TOKEN` do not start other
workflows; use a GitHub App token or a personal access token if your checks must
run on the release pull request.

## Tag the merged release and publish

```yaml
name: release
on:
  push:
    branches: [main]
permissions:
  contents: write
jobs:
  tag:
    if: startsWith(github.event.head_commit.message, 'release')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - run: pipx run gitversioned release --tag
      - run: pipx run build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

`release --tag` reads the tag from the merged release commit, refuses a tag that
is not newer than the last release, and pushes it.

gitversioned can do the publishing and the GitHub release itself. With
`forge_release = true`, give the job `GH_TOKEN` and, for PyPI trusted
publishing, `id-token: write`:

```yaml
permissions:
  contents: write
  id-token: write
steps:
  - uses: actions/checkout@v4
    with:
      fetch-depth: 0
  - uses: astral-sh/setup-uv@v6
  - run: uvx gitversioned release --tag --publish
    env:
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      CARGO_REGISTRY_TOKEN: ${{ secrets.CARGO_REGISTRY_TOKEN }}
      NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

It tags, builds and uploads to each registry, then creates the GitHub release
with the changelog section as notes and the built files attached.

## Maintenance branches

Add the branches to the workflows' `on.push.branches` and to the `branches`
setting, such as `branches = ["*.x"]`. A push to `1.x` then keeps a release
pull request from `release/next-1.x` into `1.x`, and its merge is tagged the
same way.

## GitLab and Gitea

The commands are the same. In GitLab CI set `GITLAB_TOKEN` (a project access
token with the `api` scope); `CI_API_V4_URL` and `CI_PROJECT_PATH` are read on
their own. In Gitea or Forgejo Actions set `GITEA_TOKEN`. `forge = "auto"`
picks the forge from the CI environment and the `origin` host.

## Development and nightly builds

```yaml
- run: echo "VERSION=$(pipx run gitversioned version --type nightly)" >> "$GITHUB_ENV"
- run: pipx run build
  env:
    GITVERSIONED__TYPE: nightly
```

`--type dev` is the default away from a tag. `--type nightly` has no commit hash
and can be uploaded to a package index. The build plugins take no flags, so the
build reads the type from `GITVERSIONED__TYPE`. For a backend without a plugin,
such as uv_build or Cargo, write it into the files first with
`gitversioned version --write --type nightly`.

## Release without a pull request

```yaml
on:
  workflow_dispatch:
    inputs:
      version:
        required: false
        default: ""
jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - run: |
          pipx run gitversioned release $VERSION --write
          git add -A
          git commit -qm "release: v$(pipx run gitversioned release $VERSION --json | jq -r .version)"
          git push -q
          pipx run gitversioned release --tag
        env:
          VERSION: ${{ inputs.version }}
```

An empty input releases the version the commits call for.

## Reject bad tags

```yaml
on:
  push:
    tags: ["v*"]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - run: pipx run gitversioned check --tag "$GITHUB_REF_NAME"
```

## Run them

The [github-actions example](https://github.com/markurtz/git-versioned/tree/main/examples/github-actions)
holds all seven workflows, one of them with the action, and runs every
gitversioned step in them on each test run.
