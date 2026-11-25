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

"""Unit tests for commit parsing and the bump rules."""

from __future__ import annotations

import pytest

from gitversioned.commits import level_of, next_version, parse_subject, plan_bump
from gitversioned.errors import ConfigError, NothingToReleaseError
from gitversioned.git import Commit
from gitversioned.model import Version


def _plan(*subjects: str):  # noqa: ANN202
    return plan_bump(
        [Commit(str(index), subject) for index, subject in enumerate(subjects)]
    )


class TestParseSubject:
    """Conventional Commit subjects split into their parts."""

    @pytest.mark.smoke
    def test_full(self) -> None:
        """Type, scope, breaking marker, subject and pull request are read."""
        parsed = parse_subject("feat(cli)!: drop the old commands (#12)")
        assert parsed is not None
        assert (
            parsed.type,
            parsed.scope,
            parsed.breaking,
            parsed.subject,
            parsed.pr,
        ) == (
            "feat",
            "cli",
            True,
            "drop the old commands",
            12,
        )

    @pytest.mark.sanity
    def test_footer_breaking(self) -> None:
        """A BREAKING CHANGE footer marks the commit as breaking."""
        parsed = parse_subject(
            "fix: tighten parsing", "body\n\nBREAKING CHANGE: stricter"
        )
        assert parsed is not None
        assert parsed.breaking

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        "subject", ["added a thing", "feat add", "feat:missing space", ": empty"]
    )
    def test_unconventional(self, subject: str) -> None:
        """Subjects without the type and colon form do not parse."""
        assert parse_subject(subject) is None


class TestLevels:
    """Fixed bump rules."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("subject", "level"),
        [
            ("feat: a", "minor"),
            ("fix: a", "patch"),
            ("docs: a", "patch"),
            ("refactor!: a", "major"),
            ("chore: a", None),
            ("ci: a", None),
            ("test: a", None),
            ("release: v1.0.0", None),
            ("chore!: drop python 3.9", "major"),
            ("Merge branch 'x' into main", None),
            ("plain message", "patch"),
        ],
    )
    def test_level_of(self, subject: str, level: str | None) -> None:
        """Each kind of commit maps to its level."""
        assert level_of(parse_subject(subject), subject) == level

    @pytest.mark.sanity
    def test_highest_wins(self) -> None:
        """The plan carries the highest level among the commits."""
        assert _plan("fix: a", "feat: b", "chore: c").level == "minor"
        assert _plan("chore: a", "ci: b").level is None


class TestNextVersion:
    """Choosing the next release."""

    fallback = Version.parse("0.1.0")

    @pytest.mark.smoke
    def test_from_commits(self) -> None:
        """Commits pick the level at or above 1.0."""
        current = Version.parse("1.2.0")
        assert (
            next_version(current, [], _plan("feat: a"), fallback=self.fallback).pep440()
            == "1.3.0"
        )
        assert (
            next_version(current, [], _plan("fix: a"), fallback=self.fallback).pep440()
            == "1.2.1"
        )
        assert (
            next_version(
                current, [], _plan("feat!: a"), fallback=self.fallback
            ).pep440()
            == "2.0.0"
        )

    @pytest.mark.sanity
    def test_shift_below_one(self) -> None:
        """Below 1.0 every commit-derived level shifts down by one."""
        current = Version.parse("0.4.0")
        assert (
            next_version(
                current, [], _plan("feat!: a"), fallback=self.fallback
            ).pep440()
            == "0.5.0"
        )
        assert (
            next_version(current, [], _plan("feat: a"), fallback=self.fallback).pep440()
            == "0.4.1"
        )
        assert (
            next_version(
                current, [], _plan("x"), fallback=self.fallback, bump="major"
            ).pep440()
            == "1.0.0"
        )

    @pytest.mark.sanity
    def test_nothing_to_release(self) -> None:
        """Maintenance commits alone raise the nothing-to-release error."""
        with pytest.raises(NothingToReleaseError):
            next_version(
                Version.parse("1.0.0"), [], _plan("chore: a"), fallback=self.fallback
            )

    @pytest.mark.sanity
    def test_first_release_and_explicit(self) -> None:
        """Without tags the fallback is released; an explicit version wins."""
        assert (
            next_version(None, [], _plan("feat: a"), fallback=self.fallback).pep440()
            == "0.1.0"
        )
        assert (
            next_version(
                Version.parse("1.0.0"),
                [],
                _plan(),
                fallback=self.fallback,
                explicit="3.1.4",
            ).pep440()
            == "3.1.4"
        )
        with pytest.raises(ConfigError):
            next_version(
                Version.parse("1.0.0"), [], _plan(), fallback=self.fallback, bump="huge"
            )

    @pytest.mark.regression
    def test_pre_release_numbering(self) -> None:
        """Pre-releases number themselves after existing tags of the same kind."""
        current = Version.parse("1.2.0")
        known = [
            Version.parse(text) for text in ("1.2.0", "1.3.0rc1", "1.3.0rc2", "1.3.0b1")
        ]
        plan = _plan("feat: a")
        assert (
            next_version(
                current, known, plan, fallback=self.fallback, pre="rc"
            ).pep440()
            == "1.3.0rc3"
        )
        assert (
            next_version(
                current, known, plan, fallback=self.fallback, pre="beta"
            ).pep440()
            == "1.3.0b2"
        )
        assert (
            next_version(
                current, known, plan, fallback=self.fallback, pre="alpha"
            ).pep440()
            == "1.3.0a1"
        )

    @pytest.mark.regression
    def test_final_after_rc(self) -> None:
        """After a release candidate the next final is the release it belongs to."""
        current = Version.parse("1.3.0rc2")
        assert (
            next_version(
                current, [current], _plan("fix: a"), fallback=self.fallback
            ).pep440()
            == "1.3.0"
        )
        assert (
            next_version(
                current, [current], _plan("fix: a"), fallback=self.fallback, pre="rc"
            ).pep440()
            == "1.3.0rc3"
        )
