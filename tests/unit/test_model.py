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

"""Unit tests for the version value."""

from __future__ import annotations

import pytest

from gitversioned.errors import ConfigError
from gitversioned.model import Version


class TestVersion:
    """Parsing, printing, bumping and ordering."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("text", "pep440", "semver"),
        [
            ("1.2.3", "1.2.3", "1.2.3"),
            ("v1.2.3", "1.2.3", "1.2.3"),
            ("v1.3.0-rc.1", "1.3.0rc1", "1.3.0-rc.1"),
            ("v1.3.0rc2", "1.3.0rc2", "1.3.0-rc.2"),
            ("1.3.0-beta.4", "1.3.0b4", "1.3.0-beta.4"),
            ("1.3.0a1", "1.3.0a1", "1.3.0-alpha.1"),
            (
                "1.2.1.dev20261125+abc1234",
                "1.2.1.dev20261125+abc1234",
                "1.2.1-dev.20261125+abc1234",
            ),
            ("1.3.0-nightly.20261125", "1.3.0.dev20261125", "1.3.0-nightly.20261125"),
            ("1.3.0rc1.dev5", "1.3.0rc1.dev5", "1.3.0-rc.1.dev.5"),
        ],
    )
    def test_parse_and_print(self, text: str, pep440: str, semver: str) -> None:
        """Both spellings parse to one value that prints in either standard."""
        version = Version.parse(text)
        assert version.pep440() == pep440
        assert version.semver() == semver

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        "text", ["", "1.2", "abc", "v1", "1.2.3.4", "release-1.2.3"]
    )
    def test_parse_invalid(self, text: str) -> None:
        """Text that is not a version is rejected with a usage error."""
        assert Version.try_parse(text) is None
        with pytest.raises(ConfigError):
            Version.parse(text)

    @pytest.mark.sanity
    def test_bump(self) -> None:
        """Bumping resets the lower parts and drops pre-release parts."""
        version = Version.parse("1.2.3rc1")
        assert version.bump("patch").pep440() == "1.2.4"
        assert version.bump("minor").pep440() == "1.3.0"
        assert version.bump("major").pep440() == "2.0.0"

    @pytest.mark.regression
    def test_ordering(self) -> None:
        """A final sorts after its pre-releases, which sort after dev builds."""
        ordered = [
            "1.3.0.dev1",
            "1.3.0a1",
            "1.3.0b1",
            "1.3.0rc1",
            "1.3.0rc2",
            "1.3.0",
            "1.3.1",
        ]
        versions = [Version.parse(text) for text in reversed(ordered)]
        assert [
            item.pep440() for item in sorted(versions, key=Version.sort_key)
        ] == ordered

    @pytest.mark.regression
    def test_semver_is_valid(self) -> None:
        """Nightly and dev versions follow the SemVer grammar."""
        import re  # noqa: PLC0415

        grammar = re.compile(
            r"^\d+\.\d+\.\d+(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$"
        )
        for text in (
            "1.2.1.dev20261125+abc1234.dirty",
            "1.3.0-nightly.20261125",
            "1.3.0rc2",
        ):
            assert grammar.match(Version.parse(text).semver())
