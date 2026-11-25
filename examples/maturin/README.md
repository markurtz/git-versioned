# Maturin example

Maturin reads the version from `Cargo.toml`, which stays at the placeholder
`0.0.0` in git. The `gitversioned.plugins.maturin` backend stamps the resolved
version into `Cargo.toml` for the length of the build, hands over to Maturin,
then puts the file back.

```bash
git tag v0.3.0
python -m build --wheel    # demo_maturin-0.3.0-...whl
git status --short         # clean: Cargo.toml was restored
```

To stamp the manifest for a plain `cargo build`, run
`gitversioned version --write`. The edit does not count as a dirty tree.
