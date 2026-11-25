"""
Build a standalone ``gitversioned`` executable with PyInstaller.

The result is one file that needs no Python on the machine that runs it, for
repositories that have no Python toolchain (Rust or npm only) and for container
images. The binary is written to ``dist/bin/`` and named for the platform, such
as ``gitversioned-linux-x86_64``.

Example:
::
    python scripts/build_binary.py
    dist/bin/gitversioned-linux-x86_64 --version
"""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from pathlib import Path
from typing import Annotated

__all__ = ["OUT_DIR", "binary_name", "build", "main"]

ROOT: Annotated[Path, "Repository root"] = Path(__file__).resolve().parent.parent
OUT_DIR: Annotated[Path, "Folder the binary is written to"] = ROOT / "dist" / "bin"
_ARCH_NAMES = {"amd64": "x86_64", "arm64": "aarch64"}
_OS_NAMES = {"darwin": "macos"}


def binary_name() -> str:
    """
    Name the binary for the platform it is built on.

    :return: A name such as ``gitversioned-linux-x86_64`` or
        ``gitversioned-windows-x86_64.exe``.
    """
    system = platform.system().lower()
    machine = platform.machine().lower()
    name = (
        f"gitversioned-{_OS_NAMES.get(system, system)}-"
        f"{_ARCH_NAMES.get(machine, machine)}"
    )
    return f"{name}.exe" if system == "windows" else name


def build(out_dir: Path = OUT_DIR, *, check: bool = True) -> Path:
    """
    Build the executable and, optionally, run it once to prove it starts.

    :param out_dir: Folder to write the binary to.
    :param check: Run ``--version`` on the result.
    :return: Path of the built binary.
    :raises SystemExit: If PyInstaller is not installed.
    :raises subprocess.CalledProcessError: If the build or the check fails.
    """
    try:
        import PyInstaller  # noqa: F401, PLC0415
    except ImportError as error:
        raise SystemExit(
            "[ERROR] PyInstaller is not installed. Run: pip install pyinstaller"
        ) from error
    name = binary_name()
    work = ROOT / "build" / "pyinstaller"
    stem = name.removesuffix(".exe")
    subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onefile",
            "--clean",
            "--noconfirm",
            "--name",
            stem,
            "--distpath",
            str(out_dir),
            "--workpath",
            str(work),
            "--specpath",
            str(work),
            "--collect-submodules",
            "gitversioned",
            "--exclude-module",
            "hatchling",
            "--exclude-module",
            "setuptools",
            "--exclude-module",
            "maturin",
            str(ROOT / "src" / "gitversioned" / "__main__.py"),
        ],
        cwd=ROOT,
        check=True,
    )
    binary = out_dir / name
    if check:
        subprocess.run([str(binary), "--version"], check=True)  # noqa: S603
    print(f"[INFO] Built {binary}")
    return binary


def main() -> None:
    """Parse the command line and build the binary."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--out-dir", type=Path, default=OUT_DIR, help="Folder to write the binary to."
    )
    parser.add_argument(
        "--no-check", action="store_true", help="Do not run the binary after building."
    )
    arguments = parser.parse_args()
    build(arguments.out_dir, check=not arguments.no_check)


if __name__ == "__main__":
    main()
