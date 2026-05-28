# CLI File Version Injection Example

This example demonstrates how to resolve the repository version and inject it directly in-place into `Cargo.toml` or `pyproject.toml` files.

By pointing `--output` to `Cargo.toml` or `pyproject.toml`, GitVersioned detects the file format, locates the `version` field via regex, and replaces it with the resolved version.

## Usage

To update a `Cargo.toml` version:

```bash
gitversioned --output Cargo.toml
```

To update a `pyproject.toml` version:

```bash
gitversioned --output pyproject.toml
```

## Running the Demonstration Script

We have provided a script `run_cli_file.sh` that copies template files, runs the injection, displays the results, and cleans up:

```bash
cd examples/cli-file-injection
chmod +x run_cli_file.sh
./run_cli_file.sh
```
