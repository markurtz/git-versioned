# Copyright 2026 markurtz
# SPDX-License-Identifier: Apache-2.0

"""Resolve, stamp and plan a release through the Python API, checking each answer."""

from __future__ import annotations

import sys
from pathlib import Path

from gitversioned import (
    NothingToReleaseError,
    Version,
    get_version,
    load_config,
    plan_release,
    resolve,
    stamp,
)


def main() -> int:
    """
    Run each API call against this folder and assert what it returns.

    :return: The exit code: 0 when every check holds.
    """
    root = Path(__file__).parent
    # --8<-- [start:resolve]
    config = load_config(root)
    resolved = resolve(config)
    kind = f"{resolved.type}, from {resolved.source}"
    print(f"version  {resolved.version.pep440()} ({kind})")
    print(f"semver   {resolved.version.semver()}")
    since = f"{resolved.distance} commit(s) since"
    print(f"tag      {resolved.tag}, {since}, sha {resolved.short_sha}")
    # --8<-- [end:resolve]
    assert resolved.tag == "v0.8.0"
    assert resolved.base == Version.parse("0.8.0")
    assert get_version(root) == resolved.version.pep440()

    # --8<-- [start:stamp]
    changes = stamp(config, resolved, dry_run=True)
    for change in changes:
        print(f"stamp    {change.path} -> {change.new} (commit={change.commit})")
    # --8<-- [end:stamp]
    assert [change.path for change in changes] == ["src/apidemo/version.py"]
    assert not (root / "src/apidemo/version.py").exists(), "dry run wrote a file"

    # --8<-- [start:plan]
    try:
        plan = plan_release(config, use_github=False)
    except NothingToReleaseError as error:
        print(f"release  none: {error}")
        return 1
    print(f"release  {plan.version.semver()} as {plan.tag} ({plan.level})")
    print(plan.section, end="")
    # --8<-- [end:plan]
    assert plan.tag == "v0.8.1"
    assert "parse empty input" in plan.section
    return 0


if __name__ == "__main__":
    sys.exit(main())
