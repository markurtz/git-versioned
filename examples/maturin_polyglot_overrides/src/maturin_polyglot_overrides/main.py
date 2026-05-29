"""
Main entrypoint orchestration for the Maturin Polyglot Overrides example.
"""

from __future__ import annotations

import sys

from maturin_polyglot_overrides import __version__

try:
    import maturin_polyglot_overrides as rust_lib
except ImportError:
    rust_lib = None

__all__ = ["run_example"]


def run_example() -> None:
    """
    Orchestrates the example execution and prints output logs.
    """
    sys.stdout.write(f"Maturin Polyglot Overrides Example Version: {__version__}\n")

    if rust_lib is not None and hasattr(rust_lib, "rust_greeting"):
        greeting = rust_lib.rust_greeting()
        sys.stdout.write(f"Rust extension output: {greeting}\n")
    else:
        sys.stdout.write(
            "Rust extension was not compiled, running in stub/dummy mode.\n"
        )


if __name__ == "__main__":
    run_example()
