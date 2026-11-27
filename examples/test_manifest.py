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
Check that the examples, their manifest, the use case inventory and the
generated indexes agree.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from conftest import EXAMPLES, load_manifest, parse_transcript  # noqa: E402

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

_LEVELS = {"beginner", "intermediate", "advanced"}
_MARKERS = {"smoke", "sanity", "regression"}
_SOURCES = {"v03", "prd", "template", "competitor"}
_LINK_RE = re.compile(r"\]\((?P<target>\.\./[^)#]+|[\w.-][^):#]*)\)")


def _topics() -> set[str]:
    return {
        path.parent.name
        for path in EXAMPLES.glob("*/README.md")
        if not path.parent.name.startswith((".", "_"))
    }


def _use_cases() -> list[dict]:
    with (EXAMPLES / "use-cases.toml").open("rb") as handle:
        return tomllib.load(handle)["use-case"]


@pytest.mark.smoke
class TestManifest:
    """The manifest lists every example folder, and only those."""

    def test_every_folder_is_listed(self) -> None:
        """Each folder with a README has an [example.<folder>] table."""
        assert set(load_manifest()["example"]) == _topics()

    @pytest.mark.parametrize("topic", sorted(_topics()))
    def test_entry_is_complete(self, topic: str) -> None:
        """Each table has a title, a summary, a level and a known marker."""
        entry = load_manifest()["example"][topic]
        assert entry["title"]
        assert entry["summary"].endswith(".")
        assert entry["level"] in _LEVELS
        assert entry.get("marker", "sanity") in _MARKERS

    @pytest.mark.parametrize("topic", sorted(_topics()))
    def test_readme_follows_the_layout(self, topic: str) -> None:
        """Each README has a transcript, the three sections and working links."""
        readme = EXAMPLES / topic / "README.md"
        text = readme.read_text(encoding="utf-8")
        assert parse_transcript(text), f"{topic} has no console transcript"
        for heading in ("## Run", "## How it works", "## Next"):
            assert f"\n{heading}\n" in text, f"{topic} lacks {heading}"
        for found in _LINK_RE.finditer(text):
            target = (readme.parent / found["target"]).resolve()
            assert target.exists(), f"{topic} links to missing {found['target']}"


@pytest.mark.smoke
class TestUseCases:
    """Every use case is shown by an example or left out with a reason."""

    def test_ids_are_unique(self) -> None:
        """No two entries share an id."""
        ids = [case["id"] for case in _use_cases()]
        assert len(ids) == len(set(ids))

    def test_each_case_is_shown_or_out_of_scope(self) -> None:
        """An entry names examples, or is out of scope with a reason, not both."""
        for case in _use_cases():
            assert case["source"] in _SOURCES, case["id"]
            if case.get("status") == "out-of-scope":
                assert case.get("reason"), case["id"]
                assert not case.get("examples"), case["id"]
            else:
                assert case.get("examples"), case["id"]

    def test_named_examples_exist(self) -> None:
        """Every example a use case names is a folder."""
        topics = _topics()
        for case in _use_cases():
            missing = set(case.get("examples", [])) - topics
            assert not missing, f"{case['id']} names {missing}"

    def test_every_example_shows_a_use_case(self) -> None:
        """No example is left without a use case."""
        named = {name for case in _use_cases() for name in case.get("examples", [])}
        assert _topics() <= named, _topics() - named


@pytest.mark.smoke
class TestGenerated:
    """The indexes built from the manifests are up to date."""

    def test_indexes_are_current(self) -> None:
        """scripts/generate_examples.py --check passes."""
        script = EXAMPLES.parent / "scripts" / "generate_examples.py"
        result = subprocess.run(  # noqa: S603
            [sys.executable, str(script), "--check"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout


@pytest.mark.sanity
class TestWorkflows:
    """The github-actions example runs every workflow it ships."""

    def test_every_workflow_is_run(self) -> None:
        """Each workflow file is passed to ci.py in the README."""
        folder = EXAMPLES / "github-actions"
        commands = "\n".join(
            command.text
            for command in parse_transcript(
                (folder / "README.md").read_text(encoding="utf-8")
            )
        )
        for workflow in sorted((folder / ".github" / "workflows").glob("*.yml")):
            assert f".github/workflows/{workflow.name}" in commands, workflow.name
