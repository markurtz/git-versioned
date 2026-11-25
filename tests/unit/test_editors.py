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

"""Unit tests for the scoped value locators."""

from __future__ import annotations

import pytest

from gitversioned.editors import json_span, toml_span, yaml_span

TOML = """# comment
name = "root"

[package]
name = "demo"   # the name
version = "1.0.0"  # keep me

[workspace.package]
version = '2.0.0'

[tool]
poetry.version = "3.0.0"

[dependencies]
serde = { version = "1" }
"""

JSON = """{
  "name": "demo",
  "nested": {"version": "9.0.0", "list": [1, {"version": "7.0.0"}]},
  "escaped": "a \\" quote",
  "version": "1.2.3"
}
"""

YAML = """apiVersion: v2
name: chart
# a comment
version: 0.1.0 # trailing
appVersion: "1.0.0"
catalog:
  react: ^18.0.0
  acme-core: 1.0.0
other:
  acme-core: 5.0.0
"""


def _text(source: str, span: tuple[int, int] | None) -> str | None:
    return source[span[0] : span[1]] if span else None


class TestTomlSpan:
    """TOML values are found by table and key."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            (["package", "version"], "1.0.0"),
            (["workspace", "package", "version"], "2.0.0"),
            (["tool", "poetry", "version"], "3.0.0"),
            (["name"], "root"),
            (["package", "missing"], None),
            (["missing", "version"], None),
        ],
    )
    def test_span(self, path: list[str], expected: str | None) -> None:
        """Each path resolves to the value between its quotes."""
        assert _text(TOML, toml_span(TOML, path)) == expected

    @pytest.mark.regression
    def test_replace_keeps_everything_else(self) -> None:
        """Replacing a span changes only the value."""
        span = toml_span(TOML, ["package", "version"])
        assert span is not None
        start, end = span
        changed = TOML[:start] + "9.9.9" + TOML[end:]
        assert changed == TOML.replace('version = "1.0.0"', 'version = "9.9.9"')
        assert "# keep me" in changed


class TestJsonSpan:
    """JSON values are found by key path."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            (["version"], "1.2.3"),
            (["nested", "version"], "9.0.0"),
            (["nested", "list", "1", "version"], "7.0.0"),
            (["missing"], None),
        ],
    )
    def test_span(self, path: list[str], expected: str | None) -> None:
        """Nested keys and list indexes resolve; escaped quotes do not confuse it."""
        assert _text(JSON, json_span(JSON, path)) == expected

    @pytest.mark.sanity
    def test_malformed(self) -> None:
        """A broken document gives no span instead of an exception."""
        assert json_span('{"version": "1.0', ["version"]) is None


class TestYamlSpan:
    """YAML scalars are found by mapping path."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            (["version"], "0.1.0"),
            (["appVersion"], "1.0.0"),
            (["catalog", "acme-core"], "1.0.0"),
            (["other", "acme-core"], "5.0.0"),
            (["missing"], None),
            (["catalog", "missing"], None),
        ],
    )
    def test_span(self, path: list[str], expected: str | None) -> None:
        """Top-level and nested keys resolve; comments and quotes are left out."""
        assert _text(YAML, yaml_span(YAML, path)) == expected
