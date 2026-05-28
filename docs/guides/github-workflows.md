# Using CI/CD and GitHub workflows

This guide explains the continuous integration and continuous deployment (CI/CD) pipelines used in `GitVersioned`. It outlines the standard pathways, development cycles, and what standards must be met to contribute to the repository.

## Understand the architecture

The repository utilizes a modular, standardized GitHub Actions architecture. Workflows are categorized into core lifecycle events (prefixed with `pipeline-`) and utility triggers (prefixed with `util-`).

Our CI/CD pipelines ensure that all code merged into the `main` branch meets strict code quality, type-safety, testing, and security standards.

## Navigate standard development pathways

When contributing to this repository, your code will travel through the following pipeline stages.

### 1. The pull request cycle (`pipeline-development.yml`)

When you open a Pull Request against `main`, the `pipeline-development.yml` workflow is triggered. This is the primary gateway for all code changes.

**What it enables:**

- **Quality Gates:** Runs code quality and formatting checks (`hatch run python:lint`, `hatch run project:lint`, `hatch run oci:lint`) and static type verification (`hatch run python:types`) to enforce consistent standards.
- **Security Audits:** Scans for vulnerabilities in dependencies and code patterns.
- **Testing:** Runs the unit and integration test suites. The PR will be blocked from merging if any tests fail.
- **Documentation Previews:** Verifies that the documentation can be built cleanly.

**Validation Standards:**
Your PR must pass all checks before it can be merged. We require strict adherence to PEP 8, full type annotations, and all tests must pass with adequate coverage.

### 2. Main branch validation (`pipeline-main.yml`)

Once your PR is reviewed and merged into `main`, the `pipeline-main.yml` workflow acts as a secondary validation layer.

**What it enables:**

- **Full Test Suite:** Runs unit, integration, and full end-to-end (e2e) tests to ensure the merged changes didn't introduce regressions.
- **Documentation Deployment:** Builds and deploys the `latest` version of the documentation site to the `gh-pages` branch.
- **Sanity Checks:** Re-runs quality and security checks on the finalized codebase.

### 3. Nightly and weekly pipelines

To catch configuration drift and conduct deeper analysis, we run scheduled workflows:

- **Nightly (`pipeline-nightly.yml`):** Runs daily at 00:00 UTC. It performs extended regression testing, builds alpha container images, and does deep security analysis.
- **Weekly (`pipeline-weekly.yml`):** Runs every Sunday at 00:00 UTC. Focused on dependency hygiene, checking for outdated constraints and ensuring the test suite is robust against external changes.

## Manage releases (`pipeline-release.yml`)

Releasing a new version is automated using Git tags.

**What it enables:**
When a maintainer pushes a `v*.*.*` tag (e.g., `v1.2.0`), the `pipeline-release.yml` workflow takes over.

- It performs a final, full verification of the entire test suite.
- It builds immutable Python packages (sdist and wheel).
- It attests the build provenance using OIDC.
- It publishes the artifacts to **PyPI** and the container image to the **GitHub Container Registry (GHCR)**.

## Utilize custom actions

To maintain consistency and reduce duplication, our lifecycle pipelines rely on composite actions located in the `.github/actions/` directory:

- `python/tests`: Orchestrates test suite execution (unit, integration, e2e) for Python.
- `python/quality`: Defines the exact linting and type-checking commands for Python.
- `project/quality`: Enforces repository-wide guidelines (mdformat, yamlfix, taplo).
- `project/docs`: Handles building MkDocs/Zensical sites.
- `python/build` and `oci/build`: Standardizes artifact and container generation.

By relying on these shared actions, we ensure that the exact same linting and test rules are applied whether you are testing a PR, running a nightly build, or deploying a release.

______________________________________________________________________

**Next Steps:**

- See the [Contributing Guide](../community/contributing.md) for details on how to set up your local environment.
