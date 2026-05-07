try:
    from setuptools_version_file import __version__  # type: ignore[attr-defined]
except ImportError:
    __version__ = "not available yet"


def main():
    print(f"Hello from setuptools_version_file! (version {__version__})")


if __name__ == "__main__":
    main()
