# Changelog layouts, headings and templates

How a release section looks: kinds first or scopes first, which commit types
get a heading and what it is called, a Migrations list from `BREAKING CHANGE:`
footers, and a template for the whole section.

| Level        | Shows                                                                      | Needs |
| ------------ | -------------------------------------------------------------------------- | ----- |
| Intermediate | `changelog_layout`, `changelog_sections`, `changelog_template`, Migrations | git   |

## Run

Copy this folder anywhere and run the commands below in it. The transcript is
checked on every test run, so it is exactly what you will see, apart from
hashes and dates.

### Kinds first, the default

```console
$ git init -q && git add -A && git commit -qm "feat: first release" && git tag v1.0.0
$ git commit -q --allow-empty -m "feat(cli): add --explain (#41)"
$ git commit -q --allow-empty -m "fix(core): peel annotated tags (#40)"
$ git commit -q --allow-empty -m "perf(core): cache the parse (#42)"
$ git commit -q --allow-empty -m "refactor: tidy the resolver (#43)"
$ git commit -q --allow-empty -m "feat(cli)!: rename --out to --output (#44)" -m "BREAKING CHANGE: pass --output instead of --out."
$ gitversioned release | sed -n '/^## /,$p'
## [2.0.0] - 2026-11-25

### Added

- **cli**: **Breaking:** rename --out to --output (#44)
- **cli**: add --explain (#41)

### Changed

- **core**: cache the parse (#42)
- tidy the resolver (#43)

### Fixed

- **core**: peel annotated tags (#40)

### Migrations

- **cli**: pass --output instead of --out. (#44)

Nothing changed. Run with --write, --pr or --tag.
```

A `BREAKING CHANGE:` footer, in the commit or the pull request body, becomes a
Migrations entry: what a user has to change.

### Scopes first

`changelog_layout = "scope"` puts a heading per scope first, then kinds below
it, the layout the agentic template's CHANGELOG uses. Entries without a scope go
under General.

```console
$ GITVERSIONED__CHANGELOG_LAYOUT=scope gitversioned release | sed -n '/^## /,$p'
## [2.0.0] - 2026-11-25

### cli

#### Added

- **Breaking:** rename --out to --output (#44)
- add --explain (#41)

### core

#### Changed

- cache the parse (#42)

#### Fixed

- peel annotated tags (#40)

### General

#### Changed

- tidy the resolver (#43)

### Migrations

- **cli**: pass --output instead of --out. (#44)

Nothing changed. Run with --write, --pr or --tag.
```

### Headings per type

`changelog_sections` names the heading a type goes under, and `false` hides a
type; a hidden type still shows when it is breaking.

```console
$ GITVERSIONED__CHANGELOG_SECTIONS='{"perf": "Performance", "refactor": false}' gitversioned release | sed -n '/^## /,$p'
## [2.0.0] - 2026-11-25

### Added

- **cli**: **Breaking:** rename --out to --output (#44)
- **cli**: add --explain (#41)

### Fixed

- **core**: peel annotated tags (#40)

### Performance

- **core**: cache the parse (#42)

### Migrations

- **cli**: pass --output instead of --out. (#44)

Nothing changed. Run with --write, --pr or --tag.
```

### A template for the whole section

`changelog_template` names a
[`string.Template`](https://docs.python.org/3/library/string.html#template-strings)
file, here [`section.tmpl`](section.tmpl), with `$version`, `$pep440`, `$tag`,
`$date`, `$previous`, `$compare`, `$entries` and `$migrations`. It must start
with `## [$version]`, so later releases can find their section.

```console
$ GITVERSIONED__CHANGELOG_TEMPLATE=section.tmpl gitversioned release | sed -n '/^## /,$p'
## [2.0.0] - 2026-11-25

Released as `v2.0.0`, the release after `v1.0.0`.

### Added

- **cli**: **Breaking:** rename --out to --output (#44)
- **cli**: add --explain (#41)

### Changed

- **core**: cache the parse (#42)
- tidy the resolver (#43)

### Fixed

- **core**: peel annotated tags (#40)

### Migrations

- **cli**: pass --output instead of --out. (#44)

Nothing changed. Run with --write, --pr or --tag.
$ echo 'Release $version' > bad.tmpl && GITVERSIONED__CHANGELOG_TEMPLATE=bad.tmpl gitversioned release
fail  changelog_template must start with `## [$version]`, so releases can find and replace their sections.
[exit 2]
```

## How it works

- The settings change only new sections; earlier ones stay as written.
  `[Unreleased]` entries and earlier release candidate sections are read back
  in either layout.
- Links to pull requests and the `$compare` link follow the forge: `/pull/` on
  GitHub, `/-/merge_requests/` on GitLab and `/pulls/` on Gitea.

## Next

- [change-files](../change-files/README.md) for entries written by hand.
- [release-local](../release-local/README.md) for the release that writes the section.
