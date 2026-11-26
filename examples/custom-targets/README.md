# Files discovery cannot find

Discovery finds the standard manifests by name. Everything else is listed once
in `[[targets]]`: a dotted `key` for TOML, JSON and YAML files, or a regular
expression `pattern` for any other text file. This covers release-please's
`extra-files`, cargo-release's `pre-release-replacements` and bump-my-version's
search and replace.

| Level        | Shows                                                       | Needs |
| ------------ | ----------------------------------------------------------- | ----- |
| Intermediate | `[[targets]]` `path`, `key`, `pattern`, `commit`; `release --write` | git   |

## Run

Copy this folder anywhere and run the commands below in it. The transcript is
checked on every test run, so it is exactly what you will see, apart from
hashes and dates.

```console
$ git init -q && git add -A && git commit -qm "feat: first version" && git tag v1.1.0
$ gitversioned check | sed -n '3p'
ok    targets       api/openapi.yaml, web/manifest.json, deploy.toml, go/version/version.go, INSTALL.md, install.sh, lib/_version.py
$ gitversioned version --write
1.1.0
  api/openapi.yaml       1.1.0
  web/manifest.json      1.1.0
  deploy.toml            1.1.0
  go/version/version.go  1.1.0
  INSTALL.md             1.1.0
  install.sh             1.1.0
  lib/_version.py        1.1.0
$ git diff -U0 | grep '^[-+][^-+]'
-pip install relay==1.0.0
+pip install relay==1.1.0
-  version: 0.0.0
+  version: 1.1.0
-version = "0.0.0"
+version = "1.1.0"
-const Version = "0.0.0"
+const Version = "1.1.0"
-VERSION="0.0.0" # x-version
+VERSION="1.1.0" # x-version
-__version__ = "0.0.0"
+__version__ = "1.1.0"
-  "version": "0.0.0"
+  "version": "1.1.0"
```

Each value is the only thing that changed, and each file is spelled for its
ecosystem: SemVer everywhere except the `.py` file, which gets PEP 440. A
release candidate shows the difference:

```console
$ git checkout -q . && git commit -q --allow-empty -m "feat: next" && git tag v1.2.0-rc.1
$ gitversioned version --write >/dev/null
$ grep -h -E 'Version =|__version__|version:' go/version/version.go lib/_version.py api/openapi.yaml
const Version = "1.2.0-rc.1"
__version__ = "1.2.0rc1"
  version: 1.2.0-rc.1
```

### Released files and built files

A release commits every target except those with `commit = false`, so the
repository keeps the placeholder in `lib/_version.py` while builds stamp it:

```console
$ git checkout -q . && git commit -q --allow-empty -m "fix: final touches"
$ gitversioned release 1.2.0 --write
release   1.2.0  (set by VERSION, from 1.2.0rc1)
tag       v1.2.0
files     CHANGELOG.md, api/openapi.yaml, web/manifest.json, deploy.toml, go/version/version.go, INSTALL.md, install.sh

## [1.2.0] - 2026-11-25

### Added

- next

### Fixed

- final touches

Wrote CHANGELOG.md, api/openapi.yaml, web/manifest.json, deploy.toml, go/version/version.go, INSTALL.md, install.sh.
$ git status --short
 M INSTALL.md
 M api/openapi.yaml
 M deploy.toml
 M go/version/version.go
 M install.sh
 M web/manifest.json
?? CHANGELOG.md
```

### Mistakes are reported

A pattern without a `version` group, or a key on a file type that has no keys,
is a configuration error:

```console
$ printf '[[targets]]\npath = "install.sh"\npattern = "VERSION=.*"\n' > gitversioned.toml && gitversioned version --write
fail  target install.sh: pattern needs a (?P<version>...) group
[exit 2]
$ printf '[[targets]]\npath = "install.sh"\nkey = "version"\n' > gitversioned.toml && gitversioned version --write
fail  target install.sh: `key` works for .toml, .json, .yaml and .yml files. Use `pattern` for other files.
[exit 2]
```

## How it works

- [`gitversioned.toml`](gitversioned.toml) lists seven targets. The file name
  decides the spelling: PEP 440 for `.py` files and `pyproject.toml`, SemVer
  for the rest.
- `key` is a dotted path from the top of the document. `pattern` is a Python
  regular expression in multi-line mode; every match is replaced.
- Listed targets add to discovery. Listing a discovered file replaces its
  default handling, for example to point a `key` at another field.

## Next

- [polyglot](../polyglot/README.md) for discovered and listed targets together.
- [release-local](../release-local/README.md) for the release that commits them.
