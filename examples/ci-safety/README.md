# No silent wrong versions in CI

A wrong version that nobody notices is worse than a failed build. When
gitversioned cannot trust what it sees (a shallow clone, a folder with no git
history) it warns on a developer machine and fails in CI, where the `CI`
variable is set. `gitversioned init` adds the archive file that lets a source
tarball keep its version.

| Level        | Shows                                                     | Needs |
| ------------ | --------------------------------------------------------- | ----- |
| Intermediate | `check`, `init`, `CI`, `.git_archival.txt`, `GITVERSIONED__VERSION` | git   |

## Run

Copy this folder anywhere and run the commands below in it. The transcript is
checked on every test run, so it is exactly what you will see, apart from
hashes and dates.

### Set up the project

`init` adds `.git_archival.txt` and its `export-subst` line in
`.gitattributes`, and points Hatchling at gitversioned. It says what is left to
do by hand, if anything:

```console
$ git init -q && gitversioned init
wrote  .git_archival.txt
edit   .gitattributes          + .git_archival.txt  export-subst
edit   pyproject.toml          + [tool.hatch.version] source = "gitversioned"
edit   pyproject.toml          + [tool.hatch.build.hooks.gitversioned]
No gitversioned settings needed: defaults and discovery cover this repo.
$ cat .gitattributes
.git_archival.txt  export-subst
$ cat .git_archival.txt
node: $Format:%H$
node-date: $Format:%cI$
describe-name: $Format:%(describe:tags=true,match=*[0-9]*)$
ref-names: $Format:%D$
$ grep -A1 "tool.hatch.version" pyproject.toml
[tool.hatch.version]
source = "gitversioned"
```

`init` is optional: a repository rendered from markurtz/template already has
these files.

```console
$ git add -A && git commit -qm "feat: first version" && git tag v1.3.0
$ git commit -q --allow-empty -m "fix: second" && git commit -q --allow-empty -m "fix: third"
$ gitversioned check
ok    config        defaults
ok    git           full history, 1 release tag, latest v1.3.0
ok    targets       src/safety/version.py
ok    archive file  .git_archival.txt and .gitattributes export-subst
warn  github        gh is missing or not signed in: release --pr, GitHub releases and pull request titles in the changelog are unavailable.
```

### A shallow clone

`actions/checkout` fetches one commit by default, so no tag is in reach. On a
laptop that is a warning; in CI it is an error with exit code 3 that says how
to fix it:

```console
$ git clone -q --depth 1 "file://$PWD" ../shallow
$ gitversioned version -C ../shallow
WARNING shallow clone with no release tags reachable, so the version cannot be trusted. Fetch full history (fetch-depth: 0 on actions/checkout).
0.1.0.dev20261125+4fb137b
$ CI=true gitversioned version -C ../shallow
fail  shallow clone with no release tags reachable, so the version cannot be trusted. Fetch full history (fetch-depth: 0 on actions/checkout).
[exit 3]
$ CI=true gitversioned check -C ../shallow | grep git
fail  git           shallow clone, no tags reachable. Set fetch-depth: 0 on actions/checkout.
ok    archive file  .git_archival.txt and .gitattributes export-subst
warn  github        gh is missing or not signed in: release --pr, GitHub releases and pull request titles in the changelog are unavailable.
[exit 3]
```

With the full history (`fetch-depth: 0`) the version is right again:

```console
$ cd ../shallow && git fetch -q --unshallow --tags && CI=true gitversioned version
1.3.1.dev20261125+4fb137b
```

### A source tarball

`git archive` fills in `.git_archival.txt`, so a tarball downloaded from a tag
or a commit keeps its version with no `.git` folder at all:

```console
$ mkdir ../at-tag && git archive v1.3.0 | tar -x -C ../at-tag
$ CI=true gitversioned version -C ../at-tag
1.3.0
$ mkdir ../at-main && git archive HEAD | tar -x -C ../at-main
$ CI=true gitversioned version -C ../at-main --explain
version   1.3.1.dev20261125+4fb137b
type      dev
current   1.3.0  (tag v1.3.0, 4fb137b, 2 commits since)
note      base 1.3.0 from .git_archival.txt (v1.3.0)
config    defaults  (0 keys set, 28 defaults)
```

A copy without the archive file has nothing to go on, so CI stops:

```console
$ mkdir ../copy && cp -r src pyproject.toml ../copy
$ CI=true gitversioned version -C ../copy
fail  no git repository, archive file or package metadata found, so the version cannot be resolved; using fallback 0.1.0. Set GITVERSIONED__VERSION to pin one.
[exit 3]
```

A build job that already knows the version pins it, as
`SETUPTOOLS_SCM_PRETEND_VERSION` does for setuptools-scm:

```console
$ CI=true GITVERSIONED__VERSION=1.3.0 gitversioned version -C ../copy
1.3.0
```

### A brand-new repository

A full clone with no release tag yet is not a problem to report: the history
proves there is no tag, so CI builds the fallback version.

```console
$ git init -q ../fresh && cd ../fresh && git commit -q --allow-empty -m "feat: start"
$ cd ../fresh && CI=true gitversioned version
0.1.0-dev.20261125+8fd1f5c
```

## How it works

- Sources are read in a fixed order: a pin, git tags, the archive file, an
  sdist's `PKG-INFO`, then the fallback.
- `CI` is the switch between warning and failing. GitHub Actions, GitLab CI and
  most other systems set it.

## Next

- [github-actions](../github-actions/README.md) for `fetch-depth: 0` in a workflow.
- [hatchling](../hatchling/README.md) for the sdist path.
