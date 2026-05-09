# Reference

The Reference section contains the complete technical documentation for GitVersioned — API classes and configuration options. This is the section to bookmark when you need to look something up.

## In This Section

<div class="grid cards" markdown>

- :material-code-json: **API Reference**

  ______________________________________________________________________

  Auto-generated documentation for all public classes, methods, and modules.

  [:octicons-arrow-right-24: Python API Reference](api.md)

- :material-tune-variant: **Configuration Schema**

  ______________________________________________________________________

  All supported configuration file options, types, defaults, and examples.

  [:octicons-arrow-right-24: Configuration Guide](../guides/configuration.md)

- :material-test-tube: **Test Coverage**

  ______________________________________________________________________

  Coverage reports are generated during CI/CD or locally.

  Run `hatch run test:all-cov` to generate HTML reports in `docs/coverage/`.

</div>

## Python API Usage

While `gitversioned` is primarily used as a build plugin, it can also be used programmatically in your own Python scripts:

```python
from gitversioned import Settings, resolve_version
from gitversioned.utils import BuildEnvironment, GitRepository

# Resolve the version using default settings
version, ref = resolve_version(
    Settings(), GitRepository(), BuildEnvironment()
)
print(f"Resolved version: {version}")

# Or pass custom settings
custom_settings = Settings(package_name="my_pkg", source_type=["commit"])
version, ref = resolve_version(
    custom_settings, GitRepository(), BuildEnvironment()
)
```

## Generating Reference Docs

This project is pre-configured to work with [`mkdocstrings`](https://mkdocstrings.github.io/) for auto-generating API documentation from docstrings.

### Setup

> [!NOTE]
> `mkdocstrings` supports multiple languages via handlers (e.g., Python, C++, Crystal). See the [mkdocstrings documentation](https://mkdocstrings.github.io/) to configure it for your language.

1. The plugin and its Python handler are already managed by Hatch in the `docs` environment (`mkdocstrings[python]`).
1. Configure `mkdocs.yml` according to your language handler and create your reference pages.
