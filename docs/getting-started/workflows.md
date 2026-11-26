# Workflows

The common stories, end to end.

## A build that always has the right version

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
- run: pipx run build
```

With gitversioned in `build-system.requires`, a tag build is `1.2.0` and every
other build is a development version such as `1.2.1.dev20261125+abc1234`.

## Every manifest in step

```bash
gitversioned version --write
cargo build --release --locked
npm pack
docker build --build-arg VERSION="$(gitversioned version --standard semver)" .
```

One command stamps `Cargo.toml`, `Cargo.lock`, `package.json`, `Chart.yaml`,
`CITATION.cff` and the Dockerfile label, each in its own spelling.

## A reviewed release

1. Pull requests merge to `main` with Conventional Commit titles, checked by
   `gitversioned check "$TITLE"`.
1. On every push to `main`, `gitversioned release --pr` opens or updates the
   release pull request: the changelog section and the stamped manifests.
1. A maintainer reviews, edits the changelog if needed and merges.
1. `gitversioned release --tag` tags the merge, and the tag starts the publish
   jobs.

The full workflow files are in the
[GitHub Workflows Guide](../guides/github-workflows.md).

## A release candidate

Add the label `release:rc` to the release pull request. It becomes
`release: v1.5.0-rc.1`; each further merge and tag gives `rc.2`, `rc.3`. Remove
the label to release `1.5.0`, whose changelog section replaces the candidates'.

## Nightly builds

```bash
GITVERSIONED__TYPE=nightly python -m build       # Python: the build hook
gitversioned version --write --type nightly      # Cargo, npm and other manifests
```

A nightly is the next release with the date, such as `1.5.0.dev20261125`, and
has no commit hash, so package indexes accept it. The build plugins take no
flags, so a Python build reads the type from `GITVERSIONED__TYPE`.

## One package of a monorepo

```toml
[packages.web]
path = "packages/web"
tag = "web-v{version}"
```

```bash
gitversioned version -p web
gitversioned release -p web --pr
```

The package is versioned from its own tags and only the commits that touch its
folder count.
