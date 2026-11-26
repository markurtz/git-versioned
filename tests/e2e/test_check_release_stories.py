# Copyright 2026 markurtz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Story tests S7 to S13: checks, changelog, release pull request, tag, packages."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tests import fake_gh
from tests.conftest import RepoBuilder
from tests.e2e.test_version_stories import CARGO, PACKAGE_JSON


@pytest.fixture
def remote(repo: RepoBuilder, tmp_path: Path) -> Path:
    """Give the repository a bare ``origin`` on disk and push ``main`` to it."""
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    repo.git("remote", "add", "origin", str(bare))
    repo.git("push", "-q", "origin", "main")
    return bare


@pytest.fixture
def gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Install the fake GitHub CLI and return its state file."""
    state = tmp_path / "gh-state.json"
    folder = fake_gh.install(tmp_path / "bin", state)
    monkeypatch.setenv("PATH", f"{folder}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_GH_STATE", str(state))
    return state


@pytest.fixture
def no_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the GitHub CLI look signed out."""
    state = tmp_path / "gh-state.json"
    folder = fake_gh.install(tmp_path / "bin", state)
    monkeypatch.setenv("PATH", f"{folder}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_GH_STATE", str(state))
    monkeypatch.setenv("FAKE_GH_SIGNED_OUT", "1")


def seed(repo: RepoBuilder) -> None:
    """Tag 1.2.0 and add the commits the PRD examples use."""
    repo.commit(
        "feat: manifests",
        {"Cargo.toml": CARGO, "packages/web/package.json": PACKAGE_JSON},
    )
    repo.tag("v1.2.0")
    repo.commit("chore(deps): bump ruff (#39)")
    repo.commit("fix(core): peel annotated tags (#40)")
    repo.commit("feat(cli): add explain (#41)")


@pytest.mark.usefixtures("no_gh")
class TestS7Check:
    """S7: titles and commits validated the same way everywhere."""

    @pytest.mark.smoke
    def test_title(self, repo: RepoBuilder) -> None:
        """A valid title passes; an unconventional one fails with the expected form."""
        ok = repo.run("check", "feat(cli): add explain")
        assert (ok.code, ok.out.strip()) == (0, "ok")
        bad = repo.run("check", "added explain")
        assert bad.code == 1
        assert "type(scope): subject" in bad.err

    @pytest.mark.sanity
    def test_types_and_scopes(self, repo: RepoBuilder) -> None:
        """Unknown types and scopes fail and list the allowed ones."""
        repo.write("gitversioned.toml", 'scopes = ["core", "cli"]\n')
        assert repo.run("check", "feat(cli): x").code == 0
        assert repo.run("check", "feat: no scope is fine").code == 0
        scope = repo.run("check", "feat(gui): add window")
        assert scope.code == 1
        assert 'unknown scope "gui"' in scope.err.replace("'", '"')
        kind = repo.run("check", "feature(cli): x")
        assert kind.code == 1
        assert "unknown type" in kind.err

    @pytest.mark.sanity
    def test_scopes_file(self, repo: RepoBuilder) -> None:
        """Scopes can come from the table names of a TOML file."""
        repo.write(".config/gitversioned.toml", 'scopes = ".config/blocks.toml"\n')
        repo.write(
            ".config/blocks.toml",
            "[python]\nenabled = true\n\n[rust]\nenabled = false\n",
        )
        assert repo.run("check", "fix(rust): x").code == 0
        assert repo.run("check", "fix(web): x").code == 1

    @pytest.mark.sanity
    def test_commits_range(self, repo: RepoBuilder) -> None:
        """Every commit in a range is validated and bad ones are named."""
        base = repo.git("rev-parse", "HEAD")
        repo.commit("feat: good")
        assert repo.run("check", "--commits", f"{base}..HEAD").code == 0
        bad = repo.commit("oops")
        result = repo.run("check", "--commits", f"{base}..HEAD")
        assert result.code == 1
        assert bad[:7] in result.err

    @pytest.mark.sanity
    def test_hook_file_and_warn(self, repo: RepoBuilder) -> None:
        """--file reads a commit message file; --warn reports without failing."""
        message = repo.write("MSG", "# comment\nnot conventional\n\nbody\n")
        assert repo.run("check", "--file", str(message)).code == 1
        warned = repo.run("check", "--file", str(message), "--warn")
        assert warned.code == 0
        assert "not a Conventional Commit" in warned.err

    @pytest.mark.sanity
    def test_tag(self, repo: RepoBuilder) -> None:
        """A tag must follow the template and be newer than the last release."""
        repo.tag("v1.2.0")
        assert repo.run("check", "--tag", "v1.3.0-rc.1").code == 0
        assert repo.run("check", "--tag", "v1.2.0").code == 0
        assert repo.run("check", "--tag", "v1.1.0").code == 1
        assert repo.run("check", "--tag", "release-1.3.0").code == 1

    @pytest.mark.smoke
    def test_repo_report(self, repo: RepoBuilder) -> None:
        """With no argument the repository itself is checked."""
        repo.tag("v1.2.0")
        result = repo.run("check")
        assert result.code == 0
        assert "full history, 1 release tag, latest v1.2.0" in result.out
        assert "gitversioned init" in result.out
        data = repo.run("check", "--json").json
        assert data["ok"] is True
        assert {item["area"] for item in data["findings"]} >= {
            "config",
            "git",
            "archive file",
            "github",
        }


@pytest.mark.usefixtures("no_gh")
class TestS9S12PlanAndChangelog:
    """S9 and S12: the plan changes nothing; the changelog groups by kind then scope."""

    @pytest.mark.smoke
    def test_plan(self, repo: RepoBuilder) -> None:
        """release prints the version, tag, files and section and touches nothing."""
        seed(repo)
        before = repo.git("status", "--porcelain")
        result = repo.run("release")
        assert result.code == 0
        assert "release   1.3.0  (minor, from commits, from 1.2.0)" in result.out
        assert "tag       v1.3.0" in result.out
        assert (
            "files     CHANGELOG.md, Cargo.toml, packages/web/package.json"
            in result.out
        )
        assert "### Added\n\n- **cli**: add explain (#41)" in result.out
        assert "### Fixed\n\n- **core**: peel annotated tags (#40)" in result.out
        assert "bump ruff" not in result.out
        assert "Nothing changed." in result.out
        assert repo.git("status", "--porcelain") == before

    @pytest.mark.sanity
    def test_nothing_to_release(self, repo: RepoBuilder) -> None:
        """Only maintenance commits since the tag exits 1."""
        repo.tag("v1.2.0")
        repo.commit("ci: tweak")
        result = repo.run("release")
        assert result.code == 1
        assert "Nothing to release" in result.err

    @pytest.mark.smoke
    def test_write(self, repo: RepoBuilder) -> None:
        """--write updates the changelog and the committed targets only."""
        seed(repo)
        result = repo.run("release", "--write")
        assert result.code == 0
        changelog = repo.read("CHANGELOG.md")
        assert changelog.startswith("# Changelog\n")
        assert "## [1.3.0] - " in changelog
        assert 'version = "1.3.0"' in repo.read("Cargo.toml")
        assert '"version": "1.3.0"' in repo.read("packages/web/package.json")

    @pytest.mark.regression
    def test_section_is_inserted_above_older_ones(self, repo: RepoBuilder) -> None:
        """A new section goes above earlier releases, and a rerun replaces it."""
        seed(repo)
        repo.write(
            "CHANGELOG.md",
            "# Changelog\n\nIntro text.\n\n## 1.2.0 - 2026-01-01\n\n### Added\n\n- old\n",
        )
        repo.git("add", "-A")
        repo.commit("docs: changelog")
        repo.run("release", "--write")
        repo.run("release", "--write")
        changelog = repo.read("CHANGELOG.md")
        assert changelog.count("## [1.3.0] - ") == 1
        assert (
            changelog.index("Intro text.")
            < changelog.index("## [1.3.0]")
            < changelog.index("## 1.2.0")
        )
        assert changelog.endswith("### Added\n\n- old\n")

    @pytest.mark.regression
    def test_final_replaces_rc_sections(self, repo: RepoBuilder) -> None:
        """The final release section covers and replaces its release candidates."""
        seed(repo)
        repo.run("release", "--write", "--pre", "rc")
        assert "## [1.3.0-rc.1] - " in repo.read("CHANGELOG.md")
        repo.git("add", "-A")
        repo.commit("release: v1.3.0-rc.1")
        repo.tag("v1.3.0-rc.1")
        repo.commit("fix(cli): late fix (#42)")
        repo.run("release", "--write")
        changelog = repo.read("CHANGELOG.md")
        assert "rc.1" not in changelog
        assert "add explain (#41)" in changelog
        assert "late fix (#42)" in changelog

    @pytest.mark.sanity
    def test_breaking_and_explicit(self, repo: RepoBuilder) -> None:
        """Breaking changes are marked, and VERSION or --bump override the level."""
        seed(repo)
        repo.commit("refactor(api)!: rename the entry point (#43)")
        result = repo.run("release")
        assert "release   2.0.0" in result.out
        assert "- **api**: **Breaking:** rename the entry point (#43)" in result.out
        assert "release   1.2.5" in repo.run("release", "1.2.5").out
        assert (
            "release   1.2.1  (patch, from --bump"
            in repo.run("release", "--bump", "patch").out
        )
        assert repo.run("release", "1.0.0").code == 1

    @pytest.mark.sanity
    def test_json_plan(self, repo: RepoBuilder) -> None:
        """release --json is a complete, machine-readable plan."""
        seed(repo)
        data = repo.run("release", "--json").json
        assert (data["stage"], data["version"], data["previous"], data["tag"]) == (
            "plan",
            "1.3.0",
            "1.2.0",
            "v1.3.0",
        )
        assert "CHANGELOG.md" in data["files"]
        assert data["changelog"].startswith("## [1.3.0] - ")


class TestS8S10S11ReleasePrAndTag:
    """S8, S10 and S11: the release pull request, the tag and release candidates."""

    @pytest.mark.smoke
    def test_open_then_update_pr(
        self, repo: RepoBuilder, remote: Path, gh: Path
    ) -> None:
        """--pr pushes one release commit and opens, then updates, the pull request."""
        seed(repo)
        repo.git("push", "-q", "origin", "main")
        result = repo.run("release", "--pr")
        assert result.code == 0, result.err
        assert "pr        #57 opened" in result.out
        assert repo.git("branch", "--show-current") == "main"
        assert repo.git("status", "--porcelain") == ""
        pulls = fake_gh.read_state(gh)["pulls"]
        assert pulls["57"]["title"] == "release: v1.3.0"
        assert (pulls["57"]["head"], pulls["57"]["base"]) == ("release/next", "main")
        assert "add explain" in pulls["57"]["body"]
        log = subprocess.run(
            ["git", "log", "--format=%s", "main..release/next"],
            cwd=remote,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split("\n")
        assert log[0] == "release: v1.3.0"
        shown = subprocess.run(
            ["git", "show", "release/next:Cargo.toml"],
            cwd=remote,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert 'version = "1.3.0"' in shown

        repo.commit("fix(web): another (#44)")
        again = repo.run("release", "--pr")
        assert "pr        #57 updated" in again.out
        assert "another" in fake_gh.read_state(gh)["pulls"]["57"]["body"]
        count = subprocess.run(
            ["git", "rev-list", "--count", "main..release/next"],
            cwd=repo.path,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert count == "1"

    @pytest.mark.sanity
    def test_rc_label_makes_a_release_candidate(
        self, repo: RepoBuilder, remote: Path, gh: Path
    ) -> None:
        """The release:rc label on the open pull request turns it into an rc."""
        seed(repo)
        repo.run("release", "--pr")
        state = fake_gh.read_state(gh)
        state["pulls"]["57"]["labels"].append({"name": "release:rc"})
        gh.write_text(__import__("json").dumps(state), encoding="utf-8")
        result = repo.run("release", "--pr")
        assert "release   1.3.0rc1" in result.out
        assert fake_gh.read_state(gh)["pulls"]["57"]["title"] == "release: v1.3.0-rc.1"

    @pytest.mark.sanity
    def test_pr_titles_bodies_and_labels(
        self, repo: RepoBuilder, remote: Path, gh: Path
    ) -> None:
        """Pull request titles, Changelog blocks and bump labels shape the release."""
        seed(repo)
        state = fake_gh.read_state(gh)
        state["pulls"]["41"] = {
            "number": 41,
            "title": "feat(cli): add the explain flag",
            "state": "merged",
            "body": "Details.\n\n## Changelog\n\n### Added\n- `--explain` on version\n### Removed\n- the old report\n",
            "labels": [{"name": "release:major"}],
            "url": "",
        }
        gh.write_text(__import__("json").dumps(state), encoding="utf-8")
        result = repo.run("release")
        assert "release   2.0.0  (major, from label" in result.out
        assert "- **cli**: `--explain` on version (#41)" in result.out
        assert "### Removed\n\n- **cli**: the old report (#41)" in result.out
        assert "add explain (#41)" not in result.out

    @pytest.mark.smoke
    def test_tag_after_merge(self, repo: RepoBuilder, remote: Path, gh: Path) -> None:
        """--tag tags the merged release commit and pushes the tag."""
        seed(repo)
        repo.run("release", "--write")
        repo.git("add", "-A")
        repo.commit("release: v1.3.0 (#57)")
        result = repo.run("release", "--tag")
        assert result.code == 0, result.err
        assert "tag       v1.3.0 at" in result.out
        assert "pushed" in result.out
        tags = subprocess.run(
            ["git", "tag"], cwd=remote, capture_output=True, text=True, check=True
        ).stdout
        assert "v1.3.0" in tags.split()
        assert repo.run("version").first == "1.3.0"
        assert repo.run("release", "--tag").code == 1

    @pytest.mark.sanity
    def test_tag_by_hand_and_refusals(
        self, repo: RepoBuilder, remote: Path, gh: Path
    ) -> None:
        """A manual tag needs a VERSION, must be new and must be newer."""
        seed(repo)
        nothing = repo.run("release", "--tag")
        assert nothing.code == 1
        assert "nothing to tag" in nothing.err
        assert repo.run("release", "1.1.0", "--tag").code == 1
        assert repo.run("release", "1.2.1", "--tag").code == 0
        assert repo.run("release", "1.2.1", "--tag").code == 1

    @pytest.mark.sanity
    def test_annotated_tag_carries_changelog(
        self, repo: RepoBuilder, remote: Path, gh: Path
    ) -> None:
        """With annotated = true the tag message is the changelog section."""
        seed(repo)
        repo.write("gitversioned.toml", "annotated = true\n")
        repo.run("release", "--write")
        repo.git("add", "-A")
        repo.commit("release: v1.3.0")
        assert repo.run("release", "--tag").code == 0
        assert repo.git("cat-file", "-t", "v1.3.0") == "tag"
        assert "add explain" in repo.git("tag", "-l", "--format=%(contents)", "v1.3.0")
        assert repo.run("version").first == "1.3.0"

    @pytest.mark.sanity
    def test_pr_needs_gh_and_clean_tree(
        self, repo: RepoBuilder, remote: Path, gh: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--pr refuses a dirty tree, and exits 3 when gh is signed out."""
        seed(repo)
        repo.write("README.md", "changed\n")
        assert repo.run("release", "--pr").code == 1
        repo.git("checkout", "--", "README.md")
        monkeypatch.setenv("FAKE_GH_SIGNED_OUT", "1")
        assert repo.run("release", "--pr").code == 3


@pytest.mark.usefixtures("no_gh")
class TestS13Packages:
    """S13: optional per-package tags."""

    CONFIG = '[packages.core]\npath = "packages/core"\ntag = "core-v{version}"\n\n[packages.web]\npath = "packages/web"\n'

    def _setup(self, repo: RepoBuilder) -> None:
        repo.commit(
            "feat: workspace",
            {
                "gitversioned.toml": self.CONFIG,
                "package.json": '{\n  "name": "root",\n  "version": "0.0.0"\n}\n',
                "packages/core/Cargo.toml": '[package]\nname = "core"\nversion = "0.0.0"\n',
                "packages/web/package.json": PACKAGE_JSON,
            },
        )
        repo.tag("v1.0.0")
        repo.tag("core-v0.5.0")

    @pytest.mark.smoke
    def test_versions_are_independent(self, repo: RepoBuilder) -> None:
        """A tagged package resolves from its own tags and its own commits."""
        self._setup(repo)
        repo.commit("fix(web): only web", {"packages/web/index.js": "1\n"})
        assert repo.run("version", "-p", "core").first == "0.5.0"
        assert repo.run("version").first.startswith("1.0.1.dev")
        repo.commit("feat(core): core change", {"packages/core/src/lib.rs": "// x\n"})
        assert repo.run("version", "-p", "core", "--next").first == "0.5.1"
        assert repo.run("version", "-p", "web", "--next").first == "1.0.1"

    @pytest.mark.sanity
    def test_stamping_is_scoped(self, repo: RepoBuilder) -> None:
        """Repository stamping skips tagged packages; -p stamps only that package."""
        self._setup(repo)
        repo.run("version", "2.0.0", "--write")
        assert '"version": "2.0.0"' in repo.read("package.json")
        assert '"version": "2.0.0"' in repo.read("packages/web/package.json")
        assert 'version = "0.0.0"' in repo.read("packages/core/Cargo.toml")
        repo.run("version", "0.6.0", "--write", "-p", "core")
        assert 'version = "0.6.0"' in repo.read("packages/core/Cargo.toml")

    @pytest.mark.sanity
    def test_package_release(self, repo: RepoBuilder) -> None:
        """A package release has its own tag, changelog and commit scope."""
        self._setup(repo)
        repo.commit("feat(web): not core", {"packages/web/index.js": "1\n"})
        repo.commit(
            "feat(core): core change (#7)", {"packages/core/src/lib.rs": "// x\n"}
        )
        result = repo.run("release", "-p", "core")
        assert "tag       core-v0.5.1" in result.out
        assert (
            "files     packages/core/CHANGELOG.md, packages/core/Cargo.toml"
            in result.out
        )
        assert "core change" in result.out
        assert "not core" not in result.out
        repo.run("release", "-p", "core", "--write")
        repo.git("add", "-A")
        repo.commit("release(core): core-v0.5.1")
        assert repo.run("release", "--tag").code == 1
        assert repo.run("release", "--tag", "-p", "core").code == 0
        assert "core-v0.5.1" in repo.git("tag").split()
        assert repo.run("check", "--tag", "core-v0.5.1", "-p", "core").code == 0
        unwritten = repo.run("check", "--tag", "core-v0.6.0", "-p", "core")
        assert "0.6.0, newer than core-v0.5.1" in unwritten.out
        assert "packages/core/CHANGELOG.md has no [0.6.0] section" in unwritten.err
        assert unwritten.code == 1

    @pytest.mark.sanity
    def test_unknown_package(self, repo: RepoBuilder) -> None:
        """An unknown package name is a usage error."""
        self._setup(repo)
        assert repo.run("version", "-p", "nope").code == 2
