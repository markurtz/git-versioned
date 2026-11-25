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

## Development and nightly builds

```yaml
- run: |
    pipx run gitversioned version --write --type nightly
    echo "VERSION=$(pipx run gitversioned version --type nightly)" >> "$GITHUB_ENV"
```

`--type dev` is the default away from a tag. `--type nightly` has no commit hash
and can be uploaded to a package index.

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
