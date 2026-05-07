# Example: hatchling-hatch-vars

This example demonstrates how to configure GitVersioned within a modern Python project. It uses `hatchling` as the PEP 517 build backend.

## Setup & Installation

We recommend using a virtual environment to isolate the dependencies for this example. You can use standard Python tools or modern tools like `uv`.

### Using standard tools (venv + pip)

1. **Create and activate a virtual environment:**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

1. **Install the example in editable mode:**

   ```bash
   pip install -e .
   ```

### Using uv (Recommended)

1. **Create a virtual environment and install:**
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e .
   ```

## Building the Package

Because this project uses `hatchling`, the standard and most native way to build distributions (sdist and wheel) is using the `hatch` command:

```bash
hatch build
```

Alternatively, you can use the standard Python `build` tool:

```bash
python3 -m build
```

## Running the Example

Once installed, you can run the example module to observe how GitVersioned has dynamically resolved the version at build/install time:

```bash
python3 -m hatchling_hatch_vars.main
```

## Expected Output

You should see output indicating the package name and the version resolved from Git. For example, if you are on a tagged commit `v1.0.0`:

```text
Hello from hatchling_hatch_vars! (version 1.0.0)
```

If you are on a commit past the tag, the version will include the local distance and git hash. If `gitversioned` cannot resolve a version, it may fallback or output the error state.
