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

"""Integration tests for config homes, precedence and errors."""

from __future__ import annotations

from pathlib import Path

import pytest

from gitversioned.config import Config, load_config
from gitversioned.errors import ConfigError


class TestConfigHomes:
    """Each native home is read; two homes or unknown keys are errors."""

    @pytest.mark.smoke
    def test_defaults(self, tmp_path: Path) -> None:
        """A folder with no home gets every default."""
        config = load_config(tmp_path)
        assert config.home == "defaults"
        assert (config.tag, config.branch, config.dev, config.nightly) == (
            "v{version}",
            "main",
            "patch",
            "next",
        )
        assert config.changelog == "CHANGELOG.md"
        assert len(Config.key_names()) == 14

    @pytest.mark.sanity
    @pytest.mark.parametrize(
        ("name", "text"),
        [
            (".config/gitversioned.toml", 'branch = "trunk"\n'),
            ("gitversioned.toml", 'branch = "trunk"\n'),
            ("pyproject.toml", '[tool.gitversioned]\nbranch = "trunk"\n'),
            ("Cargo.toml", '[workspace.metadata.gitversioned]\nbranch = "trunk"\n'),
            ("Cargo.toml", '[package.metadata.gitversioned]\nbranch = "trunk"\n'),
            ("package.json", '{"name": "x", "gitversioned": {"branch": "trunk"}}'),
            ("setup.cfg", "[tool:gitversioned]\nbranch = trunk\nannotated = true\n"),
        ],
    )
    def test_each_home(self, tmp_path: Path, name: str, text: str) -> None:
        """Settings are read from every supported home."""
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        config = load_config(tmp_path)
        assert config.branch == "trunk"
        assert name.rsplit("/", maxsplit=1)[-1] in config.home

    @pytest.mark.sanity
    def test_two_homes_is_an_error(self, tmp_path: Path) -> None:
        """Settings in two homes name both files."""
        (tmp_path / "gitversioned.toml").write_text('branch = "a"\n', encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text(
            '[tool.gitversioned]\nbranch = "b"\n', encoding="utf-8"
        )
        with pytest.raises(
            ConfigError, match=r"two homes.*gitversioned\.toml.*pyproject\.toml"
        ):
            load_config(tmp_path)

    @pytest.mark.sanity
    def test_unknown_key_suggests_the_nearest(self, tmp_path: Path) -> None:
        """An unknown key is an error with a hint."""
        (tmp_path / "gitversioned.toml").write_text('brnch = "a"\n', encoding="utf-8")
        with pytest.raises(ConfigError, match="Did you mean `branch`"):
            load_config(tmp_path)

    @pytest.mark.regression
    def test_old_keys_are_rejected(self, tmp_path: Path) -> None:
        """A 0.3 key fails instead of being silently ignored."""
        (tmp_path / "pyproject.toml").write_text(
            '[tool.gitversioned]\noutput = "x.py"\n', encoding="utf-8"
        )
        with pytest.raises(ConfigError, match="unknown key `output`"):
            load_config(tmp_path)

    @pytest.mark.sanity
    def test_invalid_values(self, tmp_path: Path) -> None:
        """Bad values name the key."""
        (tmp_path / "gitversioned.toml").write_text(
            'dev = "weekly"\n', encoding="utf-8"
        )
        with pytest.raises(ConfigError, match="dev"):
            load_config(tmp_path)
        (tmp_path / "gitversioned.toml").write_text(
            'tag = "release"\n', encoding="utf-8"
        )
        with pytest.raises(ConfigError, match="version"):
            load_config(tmp_path)
        (tmp_path / "gitversioned.toml").write_text(
            '[[targets]]\npath = "a.toml"\nkey = "a"\npattern = "b"\n', encoding="utf-8"
        )
        with pytest.raises(ConfigError, match="not both"):
            load_config(tmp_path)


class TestEnvironment:
    """Environment overrides for root keys."""

    @pytest.mark.smoke
    def test_overrides(self, tmp_path: Path) -> None:
        """Environment values win over the home and are typed."""
        (tmp_path / "gitversioned.toml").write_text(
            'branch = "a"\nlocal = true\n', encoding="utf-8"
        )
        config = load_config(
            tmp_path,
            env={
                "GITVERSIONED__BRANCH": "b",
                "GITVERSIONED__LOCAL": "false",
                "GITVERSIONED__SCOPES": '["x", "y"]',
                "GITVERSIONED__VERSION": "1.2.3",
                "GITVERSIONED__BUMP": "minor",
            },
        )
        assert (config.branch, config.local, config.scopes, config.version) == (
            "b",
            False,
            ["x", "y"],
            "1.2.3",
        )

    @pytest.mark.sanity
    def test_unknown_override(self, tmp_path: Path) -> None:
        """An unknown override is an error."""
        with pytest.raises(ConfigError, match="GITVERSIONED__BRNCH"):
            load_config(tmp_path, env={"GITVERSIONED__BRNCH": "x"})


class TestRootDiscovery:
    """The project root is the nearest folder with a home."""

    @pytest.mark.sanity
    def test_nearest_home_wins(self, tmp_path: Path) -> None:
        """A command started in a subfolder finds the home above it."""
        (tmp_path / "gitversioned.toml").write_text(
            'branch = "trunk"\n', encoding="utf-8"
        )
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        config = load_config(nested)
        assert config.root == tmp_path.resolve()
        assert config.branch == "trunk"
