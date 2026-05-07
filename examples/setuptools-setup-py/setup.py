from setuptools import find_packages, setup

setup(
    name="setuptools_setup_py",
    gitversioned={"version_source": "tags"},
    setup_requires=[
        "setuptools>=61.0",
        "gitversioned",
    ],
    packages=find_packages(where="src"),
    package_dir={"": "src"},
)
