# Concepts

## One version, two spellings

gitversioned keeps one version per checkout and prints it the way each
ecosystem expects.

| Build       | PEP 440 (Python)                  | SemVer (Rust, npm, Helm, OCI)      |
| ----------- | --------------------------------- | ---------------------------------- |
| Release     | `1.2.0`                           | `1.2.0`                            |
| Pre-release | `1.2.0rc1`                        | `1.2.0-rc.1`                       |
| Development | `1.2.1.dev20261125+abc1234`       | `1.2.1-dev.20261125+abc1234`       |
| Nightly     | `1.3.0.dev20261125`               | `1.3.0-nightly.20261125`           |
| Dirty tree  | `1.2.1.dev20261125+abc1234.dirty` | `1.2.1-dev.20261125+abc1234.dirty` |

A development version is the next patch after the last release, dated with the
commit date so the same commit always gives the same version. A nightly has no
hash, so it can be uploaded to a package index. The hash is the first seven
characters of the commit, lengthened only in the rare case where those would be
all digits with a leading zero, which Python packaging tools would renumber.

## Where the version comes from

The first source that answers wins:

1. **A pin.** A `VERSION` argument, `GITVERSIONED__VERSION`, or
   `version = "1.2.3"` in the settings.
1. **Git tags.** The highest release tag reachable from `HEAD` that matches the
   tag template, plus the number of commits since.
1. **The archive file.** `.git_archival.txt`, filled in by `git archive`, for
   source tarballs downloaded from GitHub. Files written for setuptools-scm are
   read too.
1. **Package metadata.** `PKG-INFO` in an unpacked sdist.
1. **The fallback.** `0.1.0` unless configured, with a warning.

A tag that looks like a version but does not match the tag template, such as
`1.2.0` when the template is `v{version}`, is ignored with a warning that names
it. The date in a development or nightly version is the commit's date, so a
rebuild gives the same version; `date = "build"` uses the build time, which
honours `SOURCE_DATE_EPOCH` for reproducible builds.

There are no version files to keep in sync and no version committed between
releases. A tag is the only thing that makes a release.

## Warn on a laptop, fail in CI

When the answer cannot be trusted (a shallow clone with no tag in reach, no git
history at all) gitversioned warns and uses the fallback on a developer
machine. In CI, detected by the `CI` environment variable, the same situation
exits with code 3 so a wrong version is never published.

## How the next version is chosen

`version --next` and `release` read the Conventional Commit subjects since the
last release.

| Commit                                                            | Level |
| ----------------------------------------------------------------- | ----- |
| `feat!: ...` or a `BREAKING CHANGE:` footer                       | major |
| `feat: ...`                                                       | minor |
| `fix`, `perf`, `refactor`, `docs`, `build`, `revert`, `deprecate` | patch |
| `chore`, `ci`, `test`, `release`, merge commits                   | none  |

Below 1.0.0 every level shifts down one, and the plan says so (`minor, a patch
below 1.0.0`): a breaking change is a minor bump and
a feature is a patch bump. An explicit `--bump` is taken as written.

## Stamping

`version --write` puts the version into every target with scoped text edits.
Only the characters of the version change; comments, ordering, quoting and line
endings are kept. Because a stamped manifest differs from git only in its
version, gitversioned does not count it as a dirty tree, so builds that stamp
first and resolve later agree.

## The release flow

```text
commits on main ──► gitversioned release --pr ──► release pull request
                                                    │  review, edit, merge
                                                    ▼
                    gitversioned release --tag ──► tag v1.5.0 ──► publish jobs
```

The release pull request holds one commit: the changelog section and the
stamped manifests. It is rebuilt on every push to the release branch, so it
always shows what the next release would be. Merging it is the decision to
release; tagging the merge is what makes the version.

## The changelog

Each release gets a `## [1.5.0] - 2026-11-25` section with Keep a Changelog
kinds (Added, Changed, Deprecated, Removed, Fixed, Security), and the scope in
bold before each entry. `chore`, `ci`, `test` and `release` commits are left
out unless they are breaking. Lines written by hand under `## [Unreleased]`
join the new section and `[Unreleased]` is left empty, so a project can keep
notes there between releases. When `gh` is available, the pull
request title replaces a squash commit's subject, and a `## Changelog` block in
a pull request body replaces the generated entry. A final release takes over
the entries of its release candidates and replaces their sections.
