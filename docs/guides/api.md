# Python API Guide

Everything the command line does is available from Python. The top-level
package exports the stable surface.

| Name                               | What it is                                            |
| ---------------------------------- | ----------------------------------------------------- |
| `get_version(root, standard=)`     | The version of a project as text.                     |
| `load_config(start)`               | The validated settings for a project.                 |
| `resolve(config, ...)`             | The resolved version with its source, tag and commit. |
| `stamp(config, resolved, ...)`     | Write the version into every target.                  |
| `plan_release(config, ...)`        | The next release: version, tag, changelog section.    |
| `Version`                          | A version that prints as PEP 440 or SemVer.           |
| `GitVersionedError` and subclasses | Errors, each with the exit code the CLI would use.    |

## Get the version

<!--phmdoctest-skip-->

```python
from gitversioned import get_version

print(get_version())  # 1.4.1.dev20261125+60439dc
print(get_version(standard="semver"))  # 1.4.1-dev.20261125+60439dc
print(get_version("path/to/project"))
```

## Resolve with detail

<!--phmdoctest-skip-->

```python
from gitversioned import load_config, resolve

config = load_config()
resolved = resolve(config)

print(resolved.version.pep440())  # 1.4.1.dev20261125+60439dc
print(resolved.type)  # dev, nightly or release
print(resolved.source)  # tag, archive, metadata, pin or fallback
print(resolved.tag, resolved.distance, resolved.sha)
print(resolved.warnings)

nightly = resolve(config, build_type="nightly")
pinned = resolve(config, pin="2.0.0")
```

## Stamp files

<!--phmdoctest-skip-->

```python
from gitversioned import load_config, resolve, stamp

config = load_config()
for change in stamp(config, resolve(config), dry_run=True):
    print(change.path, change.old, "->", change.new)
```

Each `Change` has `path`, `old`, `new`, `diff`, `commit` and `written`.

## Plan a release

<!--phmdoctest-skip-->

```python
from gitversioned import NothingToReleaseError, load_config, plan_release

try:
    plan = plan_release(load_config(), use_github=False)
except NothingToReleaseError:
    print("nothing to release")
else:
    print(plan.version.pep440(), plan.tag, plan.level)
    print(plan.section)  # the changelog section, as Markdown
```

## Work with versions

`Version` needs no repository, so it is useful on its own for parsing,
comparing and converting.

```python
from gitversioned import Version

version = Version.parse("1.2.0-rc.1")
print(version.pep440())
print(version.semver())
print(version.is_final)
print(version.bump("minor").pep440())
print(Version.try_parse("not a version"))

names = ["1.2.0", "1.2.0rc1", "1.2.0.dev1", "1.1.9"]
print(sorted(names, key=lambda name: Version.parse(name).sort_key()))
```

```
1.2.0rc1
1.2.0-rc.1
False
1.3.0
None
['1.1.9', '1.2.0.dev1', '1.2.0rc1', '1.2.0']
```

## Errors

| Error                     | Exit code | Raised when                                     |
| ------------------------- | --------- | ----------------------------------------------- |
| `CheckFailedError`        | 1         | A check failed.                                 |
| `NothingToReleaseError`   | 1         | No commit since the last release calls for one. |
| `ConfigError`             | 2         | Settings are invalid or live in two homes.      |
| `EnvironmentProblemError` | 3         | Git or `gh` cannot give a trustworthy answer.   |

All of them derive from `GitVersionedError`.

## Logging

gitversioned logs through Loguru and is silent as a library: importing it
disables its logger, as Loguru advises for libraries. Turn it on with
`logger.enable("gitversioned")` to send its messages to your own handlers, or
get the same output as the command line:

<!--phmdoctest-skip-->

```python
from gitversioned.logging import configure_logging

configure_logging(1)  # -1 errors only, 0 warnings, 1 info, 2 debug
```
