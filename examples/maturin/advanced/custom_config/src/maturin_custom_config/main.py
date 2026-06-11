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
Main entrypoint orchestration for the Maturin custom config example.
"""

from __future__ import annotations

import sys

from maturin_custom_config import __version__

try:
    import maturin_custom_config as rust_lib
except ImportError:
    rust_lib = None

__all__ = ["run_example"]


def run_example() -> None:
    """
    Orchestrates the example execution and prints output logs.
    """
    sys.stdout.write(f"Maturin Custom Config Example Version: {__version__}\n")

    if rust_lib is not None and hasattr(rust_lib, "rust_greeting"):
        greeting = rust_lib.rust_greeting()
        sys.stdout.write(f"Rust extension output: {greeting}\n")
    else:
        sys.stdout.write(
            "Rust extension was not compiled, running in stub/dummy mode.\n"
        )


if __name__ == "__main__":
    run_example()
