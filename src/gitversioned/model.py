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
The version value: parsing of tag and version spellings and printing per standard.

A :class:`Version` holds the parts shared by PEP 440 and SemVer and prints itself in
either spelling, so one resolved version can be stamped into Python and non-Python
files alike.

Example:
::
    from gitversioned.model import Version

    version = Version.parse("v1.3.0-rc.1")
    assert version.pep440() == "1.3.0rc1"
    assert version.semver() == "1.3.0-rc.1"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Literal

from gitversioned.errors import ConfigError

__all__ = ["Level", "PreKind", "Standard", "Version"]

Level = Literal["major", "minor", "patch"]
PreKind = Literal["alpha", "beta", "rc"]
Standard = Literal["pep440", "semver"]

_PRE_ALIASES: dict[str, PreKind] = {
    "a": "alpha",
    "alpha": "alpha",
    "b": "beta",
    "beta": "beta",
    "rc": "rc",
    "c": "rc",
    "pre": "rc",
    "preview": "rc",
}
_PRE_PEP440: dict[str, str] = {"alpha": "a", "beta": "b", "rc": "rc"}
_PRE_ORDER: dict[str, int] = {"alpha": 0, "beta": 1, "rc": 2}

_VERSION_RE = re.compile(
    r"""
    ^v?
    (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)
    (?:[-._]?(?P<pre>alpha|beta|preview|pre|rc|a|b|c)[-._]?(?P<pre_num>\d+)?)?
    (?:[-._]?(?P<dev_kind>dev|nightly)[-._]?(?P<dev>\d+)?)?
    (?:\+(?P<local>[0-9A-Za-z.-]+))?
    $
    """,
    re.VERBOSE | re.IGNORECASE,
)


@dataclass(frozen=True)
class Version:
    """
    A version with the parts PEP 440 and SemVer have in common.

    :param major: Major release number.
    :param minor: Minor release number.
    :param patch: Patch release number.
    :param pre: Pre-release kind and number, such as ``("rc", 1)``.
    :param dev: Development number, normally a ``YYYYMMDD`` date.
    :param local: Local build label, normally the short commit hash.
    :param nightly: Whether the development number marks a nightly build, which
        changes only the SemVer spelling.
    """

    major: int
    minor: int
    patch: int
    pre: tuple[PreKind, int] | None = None
    dev: int | None = None
    local: str | None = None
    nightly: bool = False

    @classmethod
    def parse(cls, text: str) -> Version:
        """
        Parse a version or tag spelling in PEP 440 or SemVer form.

        :param text: Text such as ``1.2.3``, ``v1.3.0-rc.1``, ``1.3.0rc1`` or
            ``1.2.1.dev20261125+abc1234``.
        :return: The parsed version.
        :raises ConfigError: If the text is not a recognised version.
        """
        found = cls.try_parse(text)
        if found is None:
            raise ConfigError(
                f"not a version: {text!r}. Expected X.Y.Z with an optional "
                "pre-release such as -rc.1 or rc1."
            )
        return found

    @classmethod
    def try_parse(cls, text: str) -> Version | None:
        """
        Parse a version spelling, returning ``None`` when it does not match.

        :param text: Candidate version text.
        :return: The parsed version, or ``None``.
        """
        match = _VERSION_RE.match(text.strip())
        if match is None:
            return None
        pre: tuple[PreKind, int] | None = None
        if match["pre"]:
            pre = (_PRE_ALIASES[match["pre"].lower()], int(match["pre_num"] or 0))
        dev = None
        if match["dev_kind"]:
            dev = int(match["dev"] or 0)
        return cls(
            major=int(match["major"]),
            minor=int(match["minor"]),
            patch=int(match["patch"]),
            pre=pre,
            dev=dev,
            local=match["local"],
            nightly=(match["dev_kind"] or "").lower() == "nightly",
        )

    @property
    def release(self) -> Version:
        """
        :return: The plain ``X.Y.Z`` release this version belongs to.
        """
        return Version(self.major, self.minor, self.patch)

    @property
    def is_final(self) -> bool:
        """
        :return: True for a plain ``X.Y.Z`` release.
        """
        return self.pre is None and self.dev is None

    def bump(self, level: Level) -> Version:
        """
        Return the next plain release at the given level.

        :param level: Which part to raise.
        :return: A plain ``X.Y.Z`` version.
        """
        if level == "major":
            return Version(self.major + 1, 0, 0)
        if level == "minor":
            return Version(self.major, self.minor + 1, 0)
        return Version(self.major, self.minor, self.patch + 1)

    def with_parts(
        self,
        *,
        pre: tuple[PreKind, int] | None = None,
        dev: int | None = None,
        local: str | None = None,
        nightly: bool = False,
    ) -> Version:
        """
        Return a copy with the variable parts replaced.

        :param pre: Pre-release kind and number.
        :param dev: Development number.
        :param local: Local build label.
        :param nightly: Whether the development number marks a nightly.
        :return: The new version.
        """
        return replace(self, pre=pre, dev=dev, local=local, nightly=nightly)

    def pep440(self) -> str:
        """
        :return: The PEP 440 spelling, such as ``1.3.0rc1.dev20261125+abc1234``.
        """
        text = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre is not None:
            text += f"{_PRE_PEP440[self.pre[0]]}{self.pre[1]}"
        if self.dev is not None:
            text += f".dev{self.dev}"
        if self.local:
            text += "+" + re.sub(r"[^0-9A-Za-z.]", ".", self.local)
        return text

    def semver(self) -> str:
        """
        :return: The SemVer spelling, such as ``1.3.0-rc.1`` or
            ``1.2.1-dev.20261125+abc1234``.
        """
        text = f"{self.major}.{self.minor}.{self.patch}"
        parts: list[str] = []
        if self.pre is not None:
            parts += [self.pre[0], str(self.pre[1])]
        if self.dev is not None:
            parts += ["nightly" if self.nightly else "dev", str(self.dev)]
        if parts:
            text += "-" + ".".join(parts)
        if self.local:
            text += "+" + re.sub(r"[^0-9A-Za-z.-]", ".", self.local)
        return text

    def render(self, standard: Standard) -> str:
        """
        Print the version in the given standard.

        :param standard: ``pep440`` or ``semver``.
        :return: The version text.
        """
        return self.pep440() if standard == "pep440" else self.semver()

    def sort_key(self) -> tuple[int, int, int, int, int, int, int]:
        """
        Return a key ordering versions the way both standards agree on.

        A development build sorts before its release, a pre-release sorts before
        the final, and a final sorts last for the same ``X.Y.Z``.

        :return: A tuple usable with ``sorted`` and ``max``.
        """
        if self.pre is not None:
            pre_rank, pre_num = _PRE_ORDER[self.pre[0]], self.pre[1]
        elif self.dev is not None:
            pre_rank, pre_num = -1, 0
        else:
            pre_rank, pre_num = 3, 0
        dev_rank, dev_num = (1, 0) if self.dev is None else (0, self.dev)
        return (
            self.major,
            self.minor,
            self.patch,
            pre_rank,
            pre_num,
            dev_rank,
            dev_num,
        )

    def __str__(self) -> str:
        return self.pep440()
