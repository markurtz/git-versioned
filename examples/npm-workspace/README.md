# An npm workspace

Two npm packages on one version: a published library and a private app that
depends on it, under a private workspace root with no version. Changesets and
release-please keep internal dependency ranges in step on a release; here
`gitversioned version --write` does it from the tag on every build.

| Level        | Shows                                                         | Needs     |
| ------------ | ------------------------------------------------------------- | --------- |
| Intermediate | `version --write`, internal dependencies, `[[targets]]` `key`, `npm pack` | git, npm  |

## Run

Copy this folder anywhere and run the commands below in it. The transcript is
checked on every test run, so it is exactly what you will see, apart from
hashes and dates.

```console
$ git init -q && git add -A && git commit -qm "feat: first version" && git tag v2.0.0
$ gitversioned version --write
2.0.0
  packages/app/package.json   2.0.0
  packages/core/package.json  2.0.0
  pnpm-workspace.yaml         2.0.0
$ git diff -U0 | grep '^[-+][^-+]'
-  "version": "0.0.0",
+  "version": "2.0.0",
-    "@demo/core": "^0.0.0"
+    "@demo/core": "^2.0.0"
-  "version": "0.0.0",
+  "version": "2.0.0",
-  "@demo/core": 0.0.0
+  "@demo/core": 2.0.0
```

The root `package.json` has no version and is left alone. The app's
`^0.0.0` range on the library became `^2.0.0`, keeping its operator, so npm
links the workspace copy and the packed library carries the release:

```console
$ npm install --offline --no-audit --no-fund --silent && node packages/app/index.js
hello app
$ npm pack --dry-run --json -w @demo/core | grep '"version"'
    "version": "2.0.0",
```

`npm version` would commit and tag by itself; here the tag is the only source,
and the stamped files never count as a dirty tree:

```console
$ gitversioned version
2.0.0
$ git checkout -q . && rm -rf node_modules package-lock.json
```

Pre-releases are spelled the npm way, and `--json` says it is one, so a release
job can publish it to the
`next` dist-tag instead of `latest`:

```console
$ git commit -q --allow-empty -m "feat: try a new API" && git tag v2.1.0-rc.1
$ gitversioned version --write >/dev/null && grep '"version"' packages/core/package.json
  "version": "2.1.0-rc.1",
$ gitversioned version --json | grep -E '"(type|prerelease)"'
  "type": "release",
  "prerelease": true,
```

## How it works

- Every `package.json` with a `version` is found by discovery. When a repository
  has several, dependencies between them that name a single version (`1.2.0`,
  `^1.2.0`, `~1.2.0`) follow the release; `workspace:` and `*` ranges are left
  for the package manager.
- [`gitversioned.toml`](gitversioned.toml) lists the pnpm catalog entry, a
  dotted `key` in a YAML file.
- [`package.json`](package.json) at the root is private and has no version.

## Next

- [monorepo-packages](../monorepo-packages/README.md) to give a package its own tags.
- [docker](../docker/README.md) for image tags from the same version.
