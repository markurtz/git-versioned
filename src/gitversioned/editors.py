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
Locators that find a single value inside a text file without parsing and
re-serialising the file.

Each function returns the character span of a value, so a caller can replace
that span and leave every other byte of the file untouched: comments, key order,
quoting and line endings all survive.

Example:
::
    from gitversioned.editors import toml_span

    text = '[package]\\nname = "demo"\\nversion = "1.0.0"  # keep\\n'
    start, end = toml_span(text, ["package", "version"])
    assert text[start:end] == "1.0.0"
"""

from __future__ import annotations

import re

__all__ = ["json_span", "toml_span", "toml_table_spans", "yaml_span"]

_TOML_HEADER = re.compile(r"^\s*\[\[?\s*(?P<name>[^\]]+?)\s*\]\]?\s*(?:#.*)?$")


def _toml_key_pattern(key: str) -> re.Pattern[str]:
    """Build the pattern matching ``key = "value"`` with bare or quoted key parts."""
    parts = [rf"""["']?{re.escape(part)}["']?""" for part in key.split(".")]
    return re.compile(
        r"^(?P<lead>\s*"
        + r"\s*\.\s*".join(parts)
        + r"""\s*=\s*)(?P<q>["'])(?P<value>.*?)(?P=q)"""
    )


def _normal_table(name: str) -> str:
    """Normalise a TOML table name by dropping quotes and spaces around dots."""
    return ".".join(part.strip().strip("\"'") for part in name.split("."))


def toml_table_spans(text: str) -> list[tuple[str, int, int]]:
    """
    List the tables of a TOML document with the span of each body.

    :param text: TOML source.
    :return: Table name, body start and body end; the root table is named ``""``.
    """
    tables: list[tuple[str, int, int]] = []
    name = ""
    start = 0
    offset = 0
    for line in text.splitlines(keepends=True):
        match = _TOML_HEADER.match(line.rstrip("\r\n"))
        if match and "=" not in line.split("#")[0].split("]")[-1]:
            tables.append((name, start, offset))
            name = _normal_table(match["name"])
            start = offset + len(line)
        offset += len(line)
    tables.append((name, start, len(text)))
    return tables


def toml_span(text: str, path: list[str]) -> tuple[int, int] | None:
    """
    Find a string value in a TOML document by dotted path.

    The path is split into a table and a key at every possible point, so
    ``["tool", "poetry", "version"]`` finds ``version`` under ``[tool.poetry]``
    and also ``poetry.version`` under ``[tool]``.

    :param text: TOML source.
    :param path: Keys from the root to the value.
    :return: Start and end of the value between its quotes, or ``None``.
    """
    tables = toml_table_spans(text)
    for split in range(len(path) - 1, -1, -1):
        table = ".".join(path[:split])
        pattern = _toml_key_pattern(".".join(path[split:]))
        for name, start, end in tables:
            if name != table:
                continue
            offset = start
            for line in text[start:end].splitlines(keepends=True):
                match = pattern.match(line)
                if match:
                    return offset + match.start("value"), offset + match.end("value")
                offset += len(line)
    return None


class _JsonScanner:
    """A minimal JSON walker that records where string values sit."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0
        self.spans: dict[tuple[str, ...], tuple[int, int]] = {}

    def _space(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos] in " \t\r\n":
            self.pos += 1

    def _string(self) -> tuple[int, int]:
        self.pos += 1
        start = self.pos
        while self.text[self.pos] != '"':
            self.pos += 2 if self.text[self.pos] == "\\" else 1
        end = self.pos
        self.pos += 1
        return start, end

    def value(self, path: tuple[str, ...]) -> None:
        """Walk one value, recording string spans under their path."""
        self._space()
        char = self.text[self.pos]
        if char == '"':
            self.spans[path] = self._string()
        elif char == "{":
            self.pos += 1
            self._space()
            while self.text[self.pos] != "}":
                self._space()
                start, end = self._string()
                key = self.text[start:end]
                self._space()
                self.pos += 1
                self.value((*path, key))
                self._space()
                if self.text[self.pos] == ",":
                    self.pos += 1
                    self._space()
            self.pos += 1
        elif char == "[":
            self.pos += 1
            index = 0
            self._space()
            while self.text[self.pos] != "]":
                self.value((*path, str(index)))
                index += 1
                self._space()
                if self.text[self.pos] == ",":
                    self.pos += 1
                    self._space()
            self.pos += 1
        else:
            while self.pos < len(self.text) and self.text[self.pos] not in ",}] \t\r\n":
                self.pos += 1


def json_span(text: str, path: list[str]) -> tuple[int, int] | None:
    """
    Find a string value in a JSON document by key path.

    :param text: JSON source.
    :param path: Keys, and list indexes as digits, from the root to the value.
    :return: Start and end of the value between its quotes, or ``None`` when the
        path is absent, not a string, or the document is malformed.
    """
    scanner = _JsonScanner(text)
    try:
        scanner.value(())
    except IndexError:
        return None
    return scanner.spans.get(tuple(path))


_YAML_LINE = re.compile(
    r"^(?P<indent>\s*)(?P<key>[^\s#:][^:#]*?)\s*:(?:\s+(?P<rest>.*))?$"
)


def _yaml_scalar(rest: str, base: int) -> tuple[int, int] | None:
    """Return the span of a scalar within the text after ``key:``."""
    if not rest:
        return None
    if rest[0] in "\"'":
        close = rest.find(rest[0], 1)
        if close < 0:
            return None
        return base + 1, base + close
    if rest[0] in "|>&*{[":
        return None
    value = re.split(r"\s+#", rest, maxsplit=1)[0].rstrip()
    return (base, base + len(value)) if value else None


def yaml_span(text: str, path: list[str]) -> tuple[int, int] | None:
    """
    Find a scalar value in a block-style YAML document by key path.

    :param text: YAML source.
    :param path: Mapping keys from the root to the value.
    :return: Start and end of the scalar, inside its quotes when quoted, or
        ``None``.
    """
    depth = 0
    parent_indent = -1
    child_indent: int | None = None
    offset = 0
    for line in text.splitlines(keepends=True):
        bare = line.rstrip("\r\n")
        line_offset = offset
        offset += len(line)
        if not bare.strip() or bare.lstrip().startswith("#"):
            continue
        match = _YAML_LINE.match(bare)
        indent = len(bare) - len(bare.lstrip())
        if indent <= parent_indent:
            if depth == 0:
                continue
            return None
        if match is None:
            continue
        if child_indent is None:
            child_indent = indent
        if indent != child_indent:
            continue
        key = match["key"].strip().strip("\"'")
        if key != path[depth]:
            continue
        if depth == len(path) - 1:
            rest = match["rest"] or ""
            return (
                _yaml_scalar(rest, line_offset + match.start("rest")) if rest else None
            )
        depth += 1
        parent_indent = indent
        child_indent = None
    return None
