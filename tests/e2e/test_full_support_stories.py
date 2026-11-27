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

"""
Story tests for the use cases that were out of scope before 0.4: version sources,
templates, post releases, bump rules, change files, changelog styles, forges,
maintenance branches, API checks, publishing and the GitHub Action.
"""

# ruff: noqa: F811 (the shared fixtures are imported, then requested by name)

from __future__ import annotations

import os
import stat
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests import fake_gh
from tests.conftest import RepoBuilder
from tests.e2e.test_check_release_stories import gh, no_gh, remote  # noqa: F401
from tests.fake_forge import TOKEN, FakeForge

ROOT = Path(__file__).resolve().parents[2]


def config(repo: RepoBuilder, text: str) -> None:
    """Write gitversioned.toml and commit it."""
    repo.commit("chore: configure", {"gitversioned.toml": text})


def tool(folder: Path, name: str, script: str) -> None:
    """Write a fake executable that logs its arguments to ``calls.log``."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "{name} $*" >> "{folder}/calls.log"\n' + script + "\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Fake uv, cargo and npm on PATH; returns their folder."""
    folder = tmp_path / "tools"
    tool(
        folder,
        "uv",
        'if [ "$1" = build ]; then mkdir -p dist; '
        "touch dist/demo-1.0.0.tar.gz dist/demo-1.0.0-py3-none-any.whl; fi",
    )
    tool(
        folder,
        "cargo",
        'if [ "$1" = semver-checks ]; then\n'
        '  if [ -n "${FAKE_SEMVER_BREAK:-}" ]; then\n'
        '    echo "--- failure function_missing ---"; '
        'echo "Summary semver requires new major version"; exit 1; fi\n'
        '  echo "Summary no semver update required"; fi',
    )
    tool(folder, "npm", "")
    monkeypatch.setenv("PATH", f"{folder}{os.pathsep}{os.environ['PATH']}")
    return folder


def calls(folder: Path) -> list[str]:
    """Read the fake tools' call log."""
    log = folder / "calls.log"
    return log.read_text(encoding="utf-8").splitlines() if log.is_file() else []


@pytest.fixture
def gitlab(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeForge]:
    """A fake GitLab API, with the token and project set."""
    forge = FakeForge("gitlab").start()
    monkeypatch.setenv("GITLAB_API_URL", forge.url)
    monkeypatch.setenv("GITLAB_TOKEN", TOKEN)
    monkeypatch.setenv("CI_PROJECT_PATH", "acme/demo")
    yield forge
    forge.stop()


@pytest.fixture
def gitea(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeForge]:
    """A fake Gitea API, with the token and repository set."""
    forge = FakeForge("gitea").start()
    monkeypatch.setenv("GITEA_API_URL", forge.url)
    monkeypatch.setenv("GITEA_TOKEN", TOKEN)
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/demo")
    yield forge
    forge.stop()


@pytest.mark.usefixtures("no_gh")
class TestV20VersionSources:
    """V20: the version read from a branch, the commit, a file or a function."""

    @pytest.mark.smoke
    def test_branch(self, repo: RepoBuilder) -> None:
        """A release/1.4.0 branch gives 1.4.0; other branches fall back to tags."""
        config(repo, 'version = "branch"\n')
        repo.tag("v1.0.0")
        repo.git("checkout", "-q", "-b", "release/1.4.0")
        assert repo.run("version").first == "1.4.0"
        repo.git("checkout", "-q", "-b", "topic")
        assert repo.run("version").first == "1.0.0"

    @pytest.mark.sanity
    def test_commit_file_and_function(self, repo: RepoBuilder) -> None:
        """The commit subject, a VERSION file and a function each set the version."""
        config(repo, 'version = "commit"\n')
        repo.commit("chore: bump to 2.1.0")
        assert repo.run("version").first == "2.1.0"
        repo.commit(
            "chore: file source",
            {"gitversioned.toml": 'version = "file:VERSION"\n', "VERSION": "3.0.1\n"},
        )
        assert repo.run("version").first == "3.0.1"
        repo.commit(
            "chore: function source",
            {
                "gitversioned.toml": 'version = "python:verfn_mod:get"\n',
                "verfn_mod.py": "def get():\n    return '4.2.0'\n",
            },
        )
        assert repo.run("version").first == "4.2.0"

    @pytest.mark.regression
    def test_bad_sources_are_config_errors(self, repo: RepoBuilder) -> None:
        """A malformed source is exit 2."""
        config(repo, 'version = "python:nocolon"\n')
        assert repo.run("version").code == 2
        config(repo, 'version = "file:MISSING"\n')
        assert repo.run("version").code == 2


@pytest.mark.usefixtures("no_gh")
class TestV21V22TemplatesAndPost:
    """V21 and V22: version templates, the version module template, post releases."""

    @pytest.mark.smoke
    def test_dev_format(self, repo: RepoBuilder) -> None:
        """formats.dev shapes development versions; unknown placeholders fail."""
        repo.tag("v1.0.0")
        config(repo, '[formats]\ndev = "{next}.dev{distance}"\n')
        assert repo.run("version").first == "1.0.1.dev1"
        config(repo, '[formats]\ndev = "{next}.dev{nope}"\n')
        assert repo.run("version").code == 2

    @pytest.mark.sanity
    def test_module_template(self, repo: RepoBuilder) -> None:
        """module_template writes the version module from a template file."""
        repo.commit(
            "feat: package",
            {
                "pyproject.toml": (
                    '[project]\nname = "demo"\ndynamic = ["version"]\n'
                    '[build-system]\nrequires = ["hatchling", "gitversioned"]\n'
                    'build-backend = "hatchling.build"\n'
                ),
                "src/demo/__init__.py": "",
                "version.tmpl": "VERSION = '$version'\nPARTS = $version_tuple\n",
                "gitversioned.toml": 'module_template = "version.tmpl"\n',
            },
        )
        repo.tag("v1.2.0")
        assert repo.run("version", "--write").code == 0
        text = repo.read("src/demo/version.py")
        assert "VERSION = '1.2.0'" in text
        assert "PARTS = (1, 2, 0)" in text

    @pytest.mark.smoke
    def test_post_release(self, repo: RepoBuilder) -> None:
        """release --post plans X.Y.Z.post1, tagged vX.Y.Z.post1."""
        repo.tag("v1.2.0")
        repo.commit("docs: fix the packaging metadata")
        result = repo.run("release", "--post", "--json")
        assert result.code == 0, result.err
        assert result.json["version"] == "1.2.0.post1"
        assert result.json["tag"] == "v1.2.0.post1"
        assert repo.run("release", "--post", "--write").code == 0
        repo.git("add", "-A")
        repo.git("commit", "-qm", "release: v1.2.0.post1")
        tagged = repo.run("release", "--tag")
        assert tagged.code == 0, tagged.err
        assert repo.run("version").first == "1.2.0.post1"
        assert repo.run("version", "--standard", "semver").first == "1.2.0+post.1"
        assert repo.run("release", "--post", "--json").json["version"] == "1.2.0.post2"


@pytest.mark.usefixtures("no_gh")
class TestC35BumpRules:
    """C35 and the 0.x question: custom levels and the zero shift."""

    @pytest.mark.smoke
    def test_levels(self, repo: RepoBuilder) -> None:
        """levels maps types to levels, and none means no release."""
        config(repo, '[levels]\nperf = "minor"\ndocs = "patch"\nfix = "none"\n')
        repo.tag("v1.0.0")
        repo.commit("perf: faster")
        assert repo.run("version", "--next").first == "1.1.0"
        repo.git("reset", "-q", "--hard", "HEAD~1")
        repo.commit("fix: nothing to release")
        assert repo.run("release").code == 1
        repo.commit("docs: a patch now")
        assert repo.run("version", "--next").first == "1.0.1"

    @pytest.mark.sanity
    def test_zero_shift_off(self, repo: RepoBuilder) -> None:
        """zero_shift = false makes feat a minor and breaking a major below 1.0."""
        repo.tag("v0.3.0")
        repo.commit("feat!: drop the old API")
        assert repo.run("version", "--next").first == "0.4.0"
        config(repo, "zero_shift = false\n")
        assert repo.run("version", "--next").first == "1.0.0"


@pytest.mark.usefixtures("no_gh")
class TestC29C34ChangeFiles:
    """C29 and C34: change files and the `new` command."""

    @pytest.mark.smoke
    def test_new_plan_write(self, repo: RepoBuilder) -> None:
        """`new` writes a change file; the release takes it in and deletes it."""
        repo.tag("v1.0.0")
        made = repo.run("new", "--type", "feat", "--scope", "cli", "add --explain")
        assert made.code == 0, made.err
        path = made.out.split()[1]
        assert path.startswith(".changes/")
        assert (repo.path / path).is_file()
        assert repo.run("check").code == 0
        plan = repo.run("release", "--json").json
        assert plan["version"] == "1.1.0"
        assert plan["changes"] == [path]
        assert "**cli**: add --explain" in plan["changelog"]
        written = repo.run("release", "--write", "--json").json
        assert path in written["changed"]
        assert not (repo.path / path).exists()

    @pytest.mark.sanity
    def test_bump_override_and_bad_file(self, repo: RepoBuilder) -> None:
        """A change file's bump wins; a malformed one fails check."""
        repo.tag("v1.0.0")
        repo.run("new", "-t", "fix", "--bump", "major", "drop Python 3.9")
        assert repo.run("version", "--next").first == "2.0.0"
        repo.write(".changes/bad.md", "no front matter\n")
        assert repo.run("check").code == 2

    @pytest.mark.sanity
    def test_new_commit_and_title_check(self, repo: RepoBuilder) -> None:
        """--commit commits staged work with a checked title; bad types fail."""
        repo.write("a.txt", "a\n")
        repo.git("add", "a.txt")
        made = repo.run("new", "--commit", "-t", "fix", "-s", "core", "handle empty")
        assert made.code == 0, made.err
        assert repo.git("log", "-1", "--format=%s") == "fix(core): handle empty"
        assert repo.run("new", "-t", "oops", "message").code == 2

    @pytest.mark.regression
    def test_needs_a_terminal_to_ask(self, repo: RepoBuilder) -> None:
        """Without --type and a message, and no terminal, `new` explains itself."""
        result = repo.run("new")
        assert result.code == 2
        assert "--type" in result.err


@pytest.mark.usefixtures("no_gh")
class TestT18C36ChangelogStyles:
    """T18 and C36: scope-first layout, Migrations, headings and templates."""

    @pytest.mark.smoke
    def test_scope_layout_and_migrations(self, repo: RepoBuilder) -> None:
        """Scope headings first, kinds below, and BREAKING CHANGE footers listed."""
        config(repo, 'changelog_layout = "scope"\n')
        repo.tag("v1.0.0")
        repo.commit("fix(core): peel tags")
        repo.commit(
            "feat(cli)!: rename --out\n\nBREAKING CHANGE: use --output instead of --out."
        )
        repo.commit("fix: general fix")
        section = repo.run("release", "--json").json["changelog"]
        assert section.index("### cli") < section.index("### core")
        assert "#### Added" in section
        assert "### General" in section
        assert "### Migrations" in section
        assert "use --output instead of --out." in section

    @pytest.mark.sanity
    def test_sections_and_template(self, repo: RepoBuilder) -> None:
        """changelog_sections renames and hides types; a template shapes the section."""
        repo.commit(
            "chore: configure",
            {
                "gitversioned.toml": (
                    'changelog_template = "section.tmpl"\n'
                    "[changelog_sections]\n"
                    'perf = "Performance"\n'
                    "refactor = false\n"
                ),
                "section.tmpl": "## [$version] ($date)\n\n$entries\n",
            },
        )
        repo.tag("v1.0.0")
        repo.commit("perf: faster")
        repo.commit("refactor: tidy")
        section = repo.run("release", "--json").json["changelog"]
        assert section.startswith("## [1.0.1] (")
        assert "### Performance" in section
        assert "tidy" not in section
        repo.write("section.tmpl", "Release $version\n")
        assert repo.run("release").code == 2


class TestC28C30Forges:
    """C28 and C30: forge releases, GitLab merge requests and Gitea pull requests."""

    @pytest.mark.smoke
    def test_github_release(self, repo: RepoBuilder, remote: Path, gh: Path) -> None:
        """forge_release = true creates the GitHub release with the section."""
        config(repo, "forge_release = true\n")
        repo.tag("v1.0.0")
        repo.commit("feat: new thing")
        repo.run("release", "--write")
        repo.git("add", "-A")
        repo.git("commit", "-qm", "release: v1.1.0")
        result = repo.run("release", "--tag")
        assert result.code == 0, result.err
        assert (
            "release   https://github.com/acme/acme/releases/tag/v1.1.0" in result.out
        )
        made = fake_gh.read_state(gh)["releases"]["v1.1.0"]
        assert "new thing" in made["notes"]
        assert made["draft"] is False

    @pytest.mark.sanity
    def test_gitlab(self, repo: RepoBuilder, remote: Path, gitlab: FakeForge) -> None:
        """GitLab: release --pr opens a merge request, --tag creates a release."""
        config(repo, 'forge = "gitlab"\nforge_release = true\n')
        repo.tag("v1.0.0")
        repo.commit("feat: merge requests (!12)")
        repo.git("push", "-q", "origin", "main")
        assert repo.run("check").out.count("ok    gitlab") == 1
        opened = repo.run("release", "--pr")
        assert opened.code == 0, opened.err
        request = gitlab.pulls[57]
        assert request["source_branch"] == "release/next"
        assert request["labels"] == ["release"]
        again = repo.run("release", "--pr")
        assert "#57 updated" in again.out
        repo.git("merge", "-q", "--ff-only", "release/next")
        tagged = repo.run("release", "--tag")
        assert tagged.code == 0, tagged.err
        assert "merge requests" in gitlab.releases["v1.1.0"]["description"]

    @pytest.mark.sanity
    def test_gitea(self, repo: RepoBuilder, remote: Path, gitea: FakeForge) -> None:
        """Gitea: the pull request gets the release label, created if missing."""
        config(repo, 'forge = "gitea"\nforge_release = true\n')
        repo.tag("v1.0.0")
        repo.commit("fix: gitea")
        repo.git("push", "-q", "origin", "main")
        opened = repo.run("release", "--pr")
        assert opened.code == 0, opened.err
        assert gitea.pulls[57]["labels"] == [{"name": "release"}]
        repo.git("merge", "-q", "--ff-only", "release/next")
        assert repo.run("release", "--tag").code == 0
        assert gitea.releases["v1.0.1"]["prerelease"] is False

    @pytest.mark.regression
    def test_missing_token(
        self, repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without a token, release --pr is an environment problem (exit 3)."""
        monkeypatch.delenv("GITLAB_TOKEN", raising=False)
        config(repo, 'forge = "gitlab"\n')
        repo.tag("v1.0.0")
        repo.commit("fix: x")
        result = repo.run("release", "--pr")
        assert result.code == 3
        assert "GITLAB_TOKEN" in result.err


class TestC33MaintenanceBranches:
    """C33: backports released from maintenance branches."""

    @pytest.mark.smoke
    def test_backport_pr_and_tag(
        self, repo: RepoBuilder, remote: Path, gh: Path
    ) -> None:
        """On 1.x after 2.0.0, the release PR targets 1.x and 1.4.1 is tagged."""
        config(repo, 'branches = ["*.x"]\n')
        repo.tag("v1.4.0")
        repo.git("branch", "1.x")
        repo.commit("feat!: the new API")
        repo.tag("v2.0.0")
        repo.git("checkout", "-q", "1.x")
        repo.commit("fix: backport a fix")
        repo.git("push", "-q", "origin", "1.x")
        result = repo.run("release", "--pr")
        assert result.code == 0, result.err
        pull = fake_gh.read_state(gh)["pulls"]["57"]
        assert (pull["head"], pull["base"]) == ("release/next-1.x", "1.x")
        assert pull["title"] == "release: v1.4.1"
        repo.git("merge", "-q", "--ff-only", "release/next-1.x")
        assert repo.run("check", "--tag", "v1.4.1").code == 0
        tagged = repo.run("release", "--tag")
        assert tagged.code == 0, tagged.err

    @pytest.mark.sanity
    def test_line_rules(self, repo: RepoBuilder, no_gh: None) -> None:
        """A feat on 1.4.x leaves its line; an old tag on a line fails."""
        config(repo, 'branches = ["*.x"]\n')
        repo.tag("v1.4.0")
        repo.git("checkout", "-q", "-b", "1.4.x")
        repo.commit("feat: too big for a patch line")
        assert repo.run("release").code == 1
        repo.git("checkout", "-q", "main")
        repo.commit("fix: main")
        repo.tag("v1.4.2")
        repo.git("checkout", "-q", "1.4.x")
        assert repo.run("check", "--tag", "v1.4.1").code == 1

    @pytest.mark.regression
    def test_other_branches_still_refused(
        self, repo: RepoBuilder, remote: Path, gh: Path
    ) -> None:
        """A branch outside `branches` still cannot open the release PR."""
        config(repo, 'branches = ["*.x"]\n')
        repo.tag("v1.0.0")
        repo.git("checkout", "-q", "-b", "topic")
        repo.commit("fix: x")
        assert repo.run("release", "--pr").code == 1


@pytest.mark.usefixtures("no_gh")
class TestC32SemverChecks:
    """C32: cargo semver-checks raises the level of a Rust release."""

    @pytest.mark.smoke
    def test_breaking_api_is_major(
        self, repo: RepoBuilder, tools: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A breaking API change turns a fix release into a major."""
        repo.commit(
            "feat: crate",
            {
                "Cargo.toml": '[package]\nname = "demo"\nversion = "1.0.0"\n',
                "gitversioned.toml": "semver_checks = true\n",
            },
        )
        repo.tag("v1.0.0")
        repo.commit("fix: remove a function")
        assert repo.run("release", "--json").json["version"] == "1.0.1"
        monkeypatch.setenv("FAKE_SEMVER_BREAK", "1")
        plan = repo.run("release", "--json").json
        assert plan["version"] == "2.0.0"
        assert "cargo semver-checks" in plan["level"]
        assert "cargo semver-checks --workspace --baseline-rev v1.0.0" in calls(tools)


@pytest.mark.usefixtures("no_gh")
class TestC27Publish:
    """C27: publishing to PyPI, crates.io and npm from the tagged commit."""

    @pytest.mark.smoke
    def test_publish_all(self, repo: RepoBuilder, tools: Path) -> None:
        """--publish builds and uploads to every registry with a manifest."""
        repo.commit(
            "feat: manifests",
            {
                "Cargo.toml": '[package]\nname = "demo"\nversion = "1.0.0"\n',
                "package.json": '{"name": "demo", "version": "1.0.0"}\n',
            },
        )
        assert repo.run("release", "--publish").code == 1
        repo.tag("v1.0.0-rc.1")
        result = repo.run("release", "--publish", "--json")
        assert result.code == 0, result.err
        assert result.json["published"]["commands"] == [
            "cargo publish --workspace --locked",
            "npm publish --tag next",
            "uv build --out-dir dist",
            "uv publish dist/demo-1.0.0-py3-none-any.whl dist/demo-1.0.0.tar.gz",
        ]

    @pytest.mark.sanity
    def test_dry_run_and_choice(self, repo: RepoBuilder, tools: Path) -> None:
        """publish picks registries; --dry-run passes each tool's dry run."""
        config(repo, 'publish = ["crates"]\n')
        repo.write("Cargo.toml", '[package]\nname = "demo"\nversion = "1.0.0"\n')
        repo.commit("feat: crate")
        repo.tag("v1.0.0")
        result = repo.run("release", "--publish", "--dry-run")
        assert result.code == 0, result.err
        assert calls(tools) == ["cargo publish --workspace --locked --dry-run"]

    @pytest.mark.regression
    def test_private_package_skipped(self, repo: RepoBuilder, tools: Path) -> None:
        """A private package.json and a Do Not Upload pyproject are not published."""
        repo.commit(
            "chore: private",
            {
                "pyproject.toml": '[project]\nname = "demo"\nversion = "1.0.0"\n'
                'classifiers = ["Private :: Do Not Upload"]\n',
                "package.json": '{"name": "demo", "private": true}\n',
            },
        )
        repo.tag("v1.0.0")
        assert repo.run("release", "--publish").code == 1


@pytest.mark.usefixtures("no_gh")
class TestDiscoveryAndQuiet:
    """The exclude setting and -q on release."""

    @pytest.mark.sanity
    def test_exclude(self, repo: RepoBuilder) -> None:
        """exclude keeps a discovered manifest out of the targets."""
        repo.commit(
            "feat: two manifests",
            {
                "web/package.json": '{"name": "web", "version": "0.0.0"}\n',
                "fixtures/package.json": '{"name": "fixture", "version": "0.0.0"}\n',
                "gitversioned.toml": 'exclude = ["fixtures/*"]\n',
            },
        )
        report = repo.run("check").out
        assert "web/package.json" in report
        assert "fixtures/package.json" not in report

    @pytest.mark.regression
    def test_quiet_release(self, repo: RepoBuilder) -> None:
        """-q prints nothing for a plan; errors still reach stderr."""
        repo.tag("v1.0.0")
        repo.commit("fix: x")
        assert repo.run("release", "-q").out == ""
        assert repo.run("release", "--write", "-q").out == ""


class TestC31Action:
    """C31: the composite GitHub Action at the repository root."""

    @pytest.mark.smoke
    def test_action_runs_a_command(self, repo: RepoBuilder, tmp_path: Path) -> None:
        """run.sh runs the command, passes the title as one argument, sets outputs."""
        bin_dir = tmp_path / "abin"
        bin_dir.mkdir()
        venv = ROOT / ".venv" / "bin" / "gitversioned"
        (bin_dir / "uvx").write_text(
            f'#!/usr/bin/env bash\nshift 4\nexec "{venv}" "$@"\n', encoding="utf-8"
        )
        (bin_dir / "uvx").chmod(0o755)
        repo.tag("v1.0.0")
        output = tmp_path / "github-output"
        env = {
            **os.environ,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "GITHUB_OUTPUT": str(output),
            "INPUT_COMMAND": "check",
            "INPUT_TITLE": "feat(cli): $(touch pwned) add a flag",
            "INPUT_VERSION": "",
        }
        result = subprocess.run(
            ["bash", str(ROOT / "action" / "run.sh")],
            cwd=repo.path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert not (repo.path / "pwned").exists()
        written = output.read_text(encoding="utf-8")
        assert "version=1.0.0" in written
        assert "output<<gitversioned_" in written
        bad = subprocess.run(
            ["bash", str(ROOT / "action" / "run.sh")],
            cwd=repo.path,
            env={**env, "INPUT_TITLE": "no type"},
            capture_output=True,
            text=True,
            check=False,
        )
        assert bad.returncode == 1
