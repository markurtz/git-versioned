from setuptools import find_packages, setup

setup(
    name="setuptools_setup_py",
    version_config=True,
    setup_requires=[
        "setuptools>=61.0",
        "gitversioned @ file:///Users/markkurtz/code/github/markurtz/git-versioned",
    ],
    packages=find_packages(where="src"),
    package_dir={"": "src"},
)
