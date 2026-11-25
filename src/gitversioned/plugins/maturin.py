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
Maturin integration: a PEP 517 backend that stamps ``Cargo.toml`` and delegates.

Maturin reads the version from ``Cargo.toml``, so this backend writes the
resolved version there for the length of the build and puts the files back
afterwards.

Example:
::
    [build-system]
    requires = ["maturin>=1.0,<2.0", "gitversioned>=0.4"]
    build-backend = "gitversioned.plugins.maturin"
"""

from __future__ import annotations

import contextlib
from collections.abc import Generator
from pathlib import Path
from typing import Any

from gitversioned.config import load_config
from gitversioned.resolve import resolve
from gitversioned.targets import discover, stamp

__all__ = [
    "build_editable",
    "build_sdist",
    "build_wheel",
    "get_requires_for_build_editable",
    "get_requires_for_build_sdist",
    "get_requires_for_build_wheel",
    "prepare_metadata_for_build_wheel",
    "stamped",
]


@contextlib.contextmanager
def stamped(root: Path | None = None) -> Generator[str]:
    """
    Stamp every target for the length of a build, then restore tracked files.

    :param root: Project folder; defaults to the current one.
    :return: The resolved version in PEP 440 form.
    """
    config = load_config(root or Path.cwd())
    resolved = resolve(config)
    saved: dict[Path, str] = {}
    for target in discover(config):
        if not target.generated and target.path.is_file():
            saved[target.path] = target.path.read_text(encoding="utf-8")
    stamp(config, resolved)
    try:
        yield resolved.version.pep440()
    finally:
        for path, text in saved.items():
            with path.open("w", encoding="utf-8", newline="") as handle:
                handle.write(text)


def _maturin() -> Any:
    """Import maturin lazily so the module loads without it."""
    import maturin  # noqa: PLC0415

    return maturin


def get_requires_for_build_wheel(
    config_settings: dict[str, Any] | None = None,
) -> list[str]:
    """PEP 517 hook, delegated to maturin."""
    return _maturin().get_requires_for_build_wheel(config_settings)


def get_requires_for_build_sdist(
    config_settings: dict[str, Any] | None = None,
) -> list[str]:
    """PEP 517 hook, delegated to maturin."""
    return _maturin().get_requires_for_build_sdist(config_settings)


def get_requires_for_build_editable(
    config_settings: dict[str, Any] | None = None,
) -> list[str]:
    """PEP 660 hook, delegated to maturin."""
    return _maturin().get_requires_for_build_editable(config_settings)


def prepare_metadata_for_build_wheel(
    metadata_directory: str, config_settings: dict[str, Any] | None = None
) -> str:
    """PEP 517 hook, run with the version stamped."""
    with stamped():
        return _maturin().prepare_metadata_for_build_wheel(
            metadata_directory, config_settings
        )


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    """PEP 517 hook, run with the version stamped."""
    with stamped():
        return _maturin().build_wheel(
            wheel_directory, config_settings, metadata_directory
        )


def build_sdist(
    sdist_directory: str, config_settings: dict[str, Any] | None = None
) -> str:
    """PEP 517 hook, run with the version stamped."""
    with stamped():
        return _maturin().build_sdist(sdist_directory, config_settings)


def build_editable(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    """PEP 660 hook, run with the version stamped."""
    with stamped():
        return _maturin().build_editable(
            wheel_directory, config_settings, metadata_directory
        )
