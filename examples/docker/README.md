# Container images

Container images take the version three ways: an OCI version label written into
the Dockerfile, a build argument, and the image tags. Registries refuse `+` in a
tag, so an image of a development build uses a nightly version or turns the
local part off.

| Level        | Shows                                                                       | Needs |
| ------------ | --------------------------------------------------------------------------- | ----- |
| Intermediate | `Dockerfile` and `Containerfile` labels, `--standard semver`, `--json`, `--type nightly` | git   |

## Run

Copy this folder anywhere and run the commands below in it. The transcript is
checked on every test run, so it is exactly what you will see, apart from
hashes and dates.

```console
$ git init -q && git add -A && git commit -qm "feat: first version" && git tag v2.3.0
$ gitversioned version --write
2.3.0
  Dockerfile  2.3.0
$ git diff -U0 | grep '^[-+][^-+]'
-      org.opencontainers.image.version="0.0.0"
+      org.opencontainers.image.version="2.3.0"
```

The label in `worker/Containerfile` reads a build argument, so it is not a
target. Pass the version as that argument:

```console
$ echo docker build --build-arg VERSION="$(gitversioned version)" -t relay:"$(gitversioned version)" .
docker build --build-arg VERSION=2.3.0 -t relay:2.3.0 .
```

### Tags for a release

A release workflow tags a final release `X.Y.Z`, `X.Y`, `X` and `latest`, and a
pre-release only with its own version, so `latest` stays on the last final
release. `--json` says which one it is:

```console
$ gitversioned version --json | python -c 'import json, sys; v = json.load(sys.stdin); x, y, z = v["semver"].split(".")[:3]; print(" ".join([v["semver"]] if v["prerelease"] else [v["semver"], f"{x}.{y}", x, "latest"]))'
2.3.0 2.3 2 latest
$ git checkout -q . && git commit -q --allow-empty -m "feat: new endpoint" && git tag v2.4.0-rc.1
$ gitversioned version --json | python -c 'import json, sys; v = json.load(sys.stdin); x, y, z = v["semver"].split(".")[:3]; print(" ".join([v["semver"]] if v["prerelease"] else [v["semver"], f"{x}.{y}", x, "latest"]))'
2.4.0-rc.1
```

### Nightly images

A development version carries `+<hash>`, which is not a valid image tag. A
nightly image uses `--type nightly`, which never has a local part, or turns the
local part off with `GITVERSIONED__LOCAL=false`:

```console
$ git commit -q --allow-empty -m "fix: nightly fix"
$ gitversioned version
2.4.0-rc.2.dev.20261125+f2c7d19
$ gitversioned version --type nightly
2.4.0-rc.2.nightly.20261125
$ GITVERSIONED__LOCAL=false gitversioned version
2.4.0-rc.2.dev.20261125
```

## How it works

- The OCI label `org.opencontainers.image.version` is discovered in any
  `Dockerfile`, `Dockerfile.<name>`, `<name>.Dockerfile` or `Containerfile`,
  unless its value is a `$` reference.
- Docker is not needed to run this example; the `docker build` line is printed,
  not run.

## Next

- [github-actions](../github-actions/README.md) for the nightly workflow.
- [polyglot](../polyglot/README.md) for a Dockerfile next to other manifests.
