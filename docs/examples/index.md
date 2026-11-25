# Examples

Runnable projects live in the
[`examples/`](https://github.com/markurtz/git-versioned/tree/main/examples)
folder of the repository. Each one is covered by a test that copies it into a
fresh git repository, tags it and runs the real command line against it.

## Example Index

| Example                                                                                 | Shows                                                                                                        |
| --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| [`hatchling`](https://github.com/markurtz/git-versioned/tree/main/examples/hatchling)   | A pure Python project with no settings at all.                                                               |
| [`setuptools`](https://github.com/markurtz/git-versioned/tree/main/examples/setuptools) | The setuptools opt-in, with settings and scopes in `pyproject.toml`.                                         |
| [`maturin`](https://github.com/markurtz/git-versioned/tree/main/examples/maturin)       | A Rust extension built through the wrapper backend.                                                          |
| [`polyglot`](https://github.com/markurtz/git-versioned/tree/main/examples/polyglot)     | Python, a Cargo workspace, npm, Helm, citation, Dockerfile, a listed target and a package with its own tags. |

## Try one

```bash
cp -r examples/polyglot /tmp/polyglot && cd /tmp/polyglot
git init -q && git add -A && git commit -qm "feat: first version"
git tag v1.4.0
gitversioned version --write --dry-run
```

## Run the example tests

```bash
hatch run project:tests-e2e
```
