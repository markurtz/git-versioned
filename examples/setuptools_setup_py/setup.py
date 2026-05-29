"""
Setup configuration file for the setuptools_setup_py example.
"""

from __future__ import annotations

from setuptools import setup

setup(
    name="setuptools_setup_py",
    packages=["setuptools_setup_py"],
    package_dir={"": "src"},
    gitversioned={
        "output": "src/setuptools_setup_py/version.py",
        "source_type": ["tag"],
    },
)
