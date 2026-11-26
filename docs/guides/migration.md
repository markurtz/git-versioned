# Migrating from 0.3

Version 0.4 is a rewrite with no compatibility layer. The tool now covers
Python, Rust and npm manifests, checks Conventional Commits and drives
releases, and its surface is much smaller.

## Commands

| 0.3                                             | 0.4                                                     |
| ----------------------------------------------- | ------------------------------------------------------- |
| `gitversioned calculate`                        | `gitversioned version`                                  |
| `gitversioned calculate --version-type nightly` | `gitversioned version --type nightly`                   |
| `gitversioned write`                            | `gitversioned version --write`                          |
| `gitversioned format`                           | `gitversioned version --write --dry-run`                |
| `gitversioned overrides`                        | `gitversioned version --write` (targets are discovered) |
| `gitversioned init-archive`                     | `gitversioned init`                                     |
| No equivalent                                   | `gitversioned check`, `release`, `new`                  |

## Settings

Old keys are rejected with an error that names the nearest new key.

| 0.3                                                      | 0.4                                                               |
| -------------------------------------------------------- | ----------------------------------------------------------------- |
| `output`, `output_strategies`                            | `module_template`, a template for the generated `version.py`.    |
| `overrides`                                              | `[[targets]]` with `key` or `pattern`; most files are discovered. |
| `version_type`                                           | `--type` on the command line, or `GITVERSIONED__TYPE` in a build. |
| `version_standard`                                       | `--standard`; each file gets its own spelling.                    |
| `regex_tag` and the other `regex_*` keys                 | `tag = "v{version}"`.                                             |
| `format_main`, `format_dev`, `format_pre`, `format_post` | `formats` for dev and nightly; `release --post` for post releases. |
| `auto_increment`                                         | `dev` and `nightly`.                                              |
| `source_type`, `version_source_*`                        | `version = "branch"`, `"commit"`, `"file:PATH"` or `"python:MOD:FUNC"`. |
| `dirty_ignore`                                           | Removed. Stamped files never count as dirty.                      |

Environment overrides are spelled `GITVERSIONED__KEY`, with two underscores.

## Build backends

| Backend    | Change                                                                                        |
| ---------- | --------------------------------------------------------------------------------------------- |
| Hatchling  | Keep `source = "gitversioned"`. Add `[tool.hatch.build.hooks.gitversioned]` for `version.py`. |
| Setuptools | Now opt-in: list `gitversioned` in `build-system.requires`.                                   |
| Maturin    | Set `build-backend = "gitversioned.plugins.maturin"`.                                         |

## Version shapes

Development versions changed from a commit count to the commit date:
`1.2.1.dev4+gabc1234` is now `1.2.1.dev20261125+abc1234`. Nightly versions have
no local part. Tags are read the same way, so existing tags keep working.

## Python API

`Settings`, the strategy classes and the template helpers are gone. Use
`load_config`, `resolve`, `stamp` and `plan_release`; see the
[API Guide](api.md).
