# Reference

The Reference section contains the complete technical documentation for `gitversioned` — API classes, configuration options, CLI reference, and test coverage reports.

## In This Section

<div class="grid cards" markdown>

-   **[:material-console: CLI](cli.md)**

    Command-line usage and subcommands.

-   **[:material-api: Python API](python_api/index.md)**

    Complete public Python API documentation.

-   **[:material-shield-check: Python Tests](python_coverage.md)**

    Python coverage reports for unit, integration, functional, and E2E tests.

</div>

## Python API Usage

`gitversioned` can be used from your own Python code:

<!--phmdoctest-skip-->

```python
from gitversioned import get_version, load_config, resolve

print(get_version())

resolved = resolve(load_config())
print(resolved.version.semver(), resolved.type, resolved.source)
```

See the [API Guide](../guides/api.md) for more.
