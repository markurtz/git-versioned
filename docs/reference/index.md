# Reference

The Reference section contains the complete technical documentation for `{{ project_name }}` — API classes, CLI commands, and configuration options. This is the section to bookmark when you need to look something up.

## In This Section

<div class="grid cards" markdown>

- :material-code-json: **API Reference**

  ______________________________________________________________________

  Auto-generated documentation for all public classes, methods, and modules.

  <!-- Add link once API reference pages are generated -->

  *Coming soon — see [Contributing](../community/contributing.md) to help.*

- :material-console: **CLI Reference**

  ______________________________________________________________________

  Full documentation for all `{{ project_name }}` command-line interface commands,
  options, and flags.

  <!-- Add link once CLI reference pages are generated -->

  *Coming soon.*

- :material-tune-variant: **Configuration Schema**

  ______________________________________________________________________

  All supported configuration file options, types, defaults, and examples.

  <!-- Add link once configuration reference pages are generated -->

  *Coming soon.*

- :material-test-tube: **Test Coverage**

  ______________________________________________________________________

  Coverage reports are generated during CI/CD or locally.

  Run `hatch run test:cov-all` to generate HTML reports in `docs/coverage/`.

</div>

## Generating API Reference Docs

This template is pre-configured to work with [`mkdocstrings`](https://mkdocstrings.github.io/) for auto-generating API documentation from docstrings.

### Setup

> [!NOTE]
> `mkdocstrings` supports multiple languages via handlers (e.g., Python, C++, Crystal). See the [mkdocstrings documentation](https://mkdocstrings.github.io/) to configure it for your language.

1. The plugin and its Python handler are already managed by Hatch in the `docs` environment (`mkdocstrings[python]`).
1. Configure `mkdocs.yml` according to your language handler and create your reference pages.

## Generating CLI Reference Docs

For CLI documentation, consider using one of the following approaches depending on your CLI framework:

| Framework    | Plugin                                                          | Notes                                          |
| :----------- | :-------------------------------------------------------------- | :--------------------------------------------- |
| **Typer**    | [`typer-cli`](https://typer.tiangolo.com/typer-cli/)            | Generates markdown from Typer apps             |
| **Click**    | [`mkdocs-click`](https://github.com/brunoliveira8/mkdocs-click) | Auto-generates docs from Click decorators      |
| **Argparse** | Manual                                                          | Document commands in a dedicated `cli.md` page |

!!! tip "Template Reminder"
Replace this page with actual generated reference documentation as your project matures. The placeholders above are intentional starting points.
