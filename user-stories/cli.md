### **US-1: Standard Python Project (pyproject.toml) Versioning**

**As a** Product Owner of an external, standard Python project,

**I want to** execute the `gitversioned` CLI to update the version string inside my `pyproject.toml` in place,

**So that** I can easily automate project version shifts across different development workflows.

#### **Acceptance Criteria:**

* **AC 1.1 (Parameterized Version Sources):** Given a standard Python project utilizing a `pyproject.toml` config, when the `gitversioned` CLI is invoked with a specific `--source` strategy, then the `version` field in `pyproject.toml` must be modified in place accurately matching the source data.
* **AC 1.2 (Source Strategy Matrix):** The system must cleanly resolve and apply the version when parameterized across the following five input sources:
| Parameter Option | Input Scenario Strategy | Expected Output Verification |
| --- | --- | --- |
| `git-tags` | Active semantic git tags on current HEAD (e.g., `v1.2.3`) | Replaces version with `1.2.3` |
| `git-branch` | Current branch parsing (e.g., `release/2.0.0`) | Replaces version with `2.0.0` |
| `git-commits` | Total commit counting/hashes (e.g., `rev-412`) | Replaces version with calculated hash/count |
| `version-file` | Reading an independent file entry (e.g., `VERSION.txt`) | Replaces version with file's exact string |
| `custom-function` | Executing a dynamically loaded Python path/hook | Replaces version with function return value |


* **AC 1.3 (Error Isolation):** When an invalid parameter combination or an unresolvable source hook is supplied, the CLI must return a non-zero exit code, print a verbose error to stderr, and leave the original `pyproject.toml` completely untouched.

### **US-2: Multi-Artifact (pyproject.toml + Docker) Standardization**

**As an** experienced Maintainer of a standard Python project packaged with a Dockerfile,

**I want to** use the `gitversioned` CLI to synchronize the version strings in both my `pyproject.toml` and Docker image configuration simultaneously,

**So that** my application and its containerized deployment remain perfectly aligned across release scopes.

#### **Acceptance Criteria:**

* **AC 2.1 (Simultaneous Targeting):** Given a project repository containing both a `pyproject.toml` and a target build `Dockerfile`, when `gitversioned` is executed, then both files must be updated concurrently to avoid split-version errors.
* **AC 2.2 (Source Execution Matrix):** The simultaneous update must execute flawlessly when evaluated across the standard matrix:
* **Tags:** Syncs both artifacts to the active git tag.
* **Branch:** Syncs both artifacts to the current branch name format.
* **Commits:** Syncs both artifacts to the commit metadata value.
* **Source File:** Reads from a designated version file and synchronizes both outputs.
* **Custom Hook:** Dispatches an external Python function to compute the shared version string.


* **AC 2.3 (Atomic Failures):** If one artifact file update fails (e.g., write permissions or malformed configuration), the entire operation must rollback atomically so that neither file is left out of sync.

### **US-3: Legacy Python Project (setup.cfg) Management**

**As a** Maintainer of a legacy Python project using a static `setup.cfg` metadata setup,

**I want to** target `setup.cfg` via the `gitversioned` CLI to override configuration versions in place,

**So that** I can loop older codebases into our modern, unified CI/CD delivery pipeline.

#### **Acceptance Criteria:**

* **AC 3.1 (INI Config Compliance):** Given an established legacy Python project containing a `setup.cfg` file, when the CLI parses the configuration, then it must inject the new version value under the `[metadata]` section block without destroying file comments or formatting.
* **AC 3.2 (Parameterized Injections):** The injection mechanism must dynamically derive versions from all five source matrices (`git-tags`, `git-branch`, `git-commits`, external reference file, or a programmatic `custom-function` hook).
* **AC 3.3 (Validation Check):** Running the CLI against a `setup.cfg` file that completely lacks a `[metadata]` block must gracefully initialize the missing section or exit cleanly with an informative error message.

### **US-4: Deprecated Manifest (setup.py) Interception**

**As a** Maintainer of a Python project utilizing a deprecated dynamic `setup.py` layout,

**I want to** utilize the `gitversioned` CLI to control the `version="..."` parameter argument within the executable script,

**So that** I can enforce modern automated versioning standards without being forced to rewrite the legacy packaging paradigm.

#### **Acceptance Criteria:**

* **AC 4.1 (AST/Regex In-Place Replacement):** Given a project defined by a dynamic `setup.py` file, when `gitversioned` targets it, then it must find and safely swap out the `version` variable assignment or keyword argument block.
* **AC 4.2 (Robust Parsing Boundaries):** The script parser must evaluate correctly across varying codebase inputs, pulling data from git tags, branch patterns, commit strings, standalone version tracking files, or specific user-defined execution functions.
* **AC 4.3 (Functional Rigor):** The resulting `setup.py` file must remain perfectly valid Python code post-update, throwing no syntax errors when executed by standard build pipelines.


### **US-5: Polyglot/Hybrid Projects (Cargo.toml + Docker) Control**

**As a** Maintainer of a complex, polyglot Python project featuring a high-performance Rust backend, Rust bindings, and a Docker container framework,

**I want to** orchestrate multi-language version synchronization across my `Cargo.toml` and `Dockerfile` via the `gitversioned` CLI,

**So that** compiled binary extensions and shipping containers match the host framework's release metadata.

#### **Acceptance Criteria:**

* **AC 5.1 (TOML Language Interoperability):** Given a hybrid repository layout featuring a Rust workspace/sub-crate with a `Cargo.toml` file along with a `Dockerfile`, when `gitversioned` executes, then it must correctly find and replace the `package.version` property block inside the Rust configuration.
* **AC 5.2 (Deep Matrix Validation):** The multi-language synchronization engine must derive the version string accurately across the full parameter surface area:
| Source Flag | Triggering Event | Expected Structural Injections |
| --- | --- | --- |
| `git-tags` | Release hook event | Replaces `Cargo.toml` and `Dockerfile` version vectors with tag string |
| `git-branch` | Development feature tracking | Injects branch notation seamlessly into both build files |
| `git-commits` | Continuous Integration builds | Applies commit counter markers to both configurations |
| `version-file` | Decentralized build systems | Extracts state from raw file, pushes to Cargo & Docker |
| `custom-function` | Advanced build orchestration | Evaluates Python plugin hook, binds resulting string to both environments |


* **AC 5.3 (Stress Handling):** The CLI must elegantly handle large Cargo workspaces (multiple nested `Cargo.toml` targets) and deep multi-stage Docker builds without causing structural parsing failures or broken build states.