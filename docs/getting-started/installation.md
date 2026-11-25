# Installation

## Requirements

- Python 3.10 or newer
- `git` on the `PATH`
- Optional: the GitHub CLI `gh`, for `release --pr` and pull request titles in
  the changelog

## As a command line tool

```bash
# Run without installing
uvx gitversioned version
pipx run gitversioned version

# Or install it
uv tool install gitversioned
pipx install gitversioned
pip install gitversioned
```

### Verify the installation

```console
$ gitversioned --version
gitversioned v0.4.0
$ gitversioned check
```

`gitversioned check` reports whether the repository can give a trustworthy
version and lists the files that would be stamped.

## As a build dependency

A Python project does not install gitversioned by hand. It lists it in
`build-system.requires` and the build front end installs it into the isolated
build:

```toml
[build-system]
requires = ["hatchling", "gitversioned>=0.4"]
build-backend = "hatchling.build"
```

See the [Hatchling](../guides/hatchling.md), [Setuptools](../guides/setuptools.md)
and [Maturin](../guides/maturin.md) guides.

## Container image

```bash
docker run --rm -v "$PWD:/repo" -w /repo ghcr.io/markurtz/git-versioned:latest \
  gitversioned version
```

## From source

```bash
git clone https://github.com/markurtz/git-versioned.git
cd git-versioned
uv sync
uv run gitversioned --version
```

## Upgrading and uninstalling

```bash
uv tool upgrade gitversioned     # or: pipx upgrade gitversioned
uv tool uninstall gitversioned   # or: pipx uninstall gitversioned
```

Upgrading from 0.3? See the [Migration Guide](../guides/migration.md).

## Troubleshooting

| Symptom                                         | Fix                                                               |
| ----------------------------------------------- | ----------------------------------------------------------------- |
| The version is `0.1.0...` in CI, or exit code 3 | The clone is shallow. Set `fetch-depth: 0` on `actions/checkout`. |
| A GitHub source tarball builds as `0.1.0`       | Run `gitversioned init` once and commit the two files.            |
| `settings found in two homes`                   | Keep the settings in one file.                                    |
| `release --pr` says `gh` is missing             | Install the GitHub CLI and set `GH_TOKEN` in CI.                  |
