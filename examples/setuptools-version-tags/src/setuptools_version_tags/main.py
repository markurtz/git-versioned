try:
    import setuptools_version_tags

    __version__ = getattr(setuptools_version_tags, "__version__", "not available yet")
except ImportError:
    __version__ = "not available yet"


def main():
    print(f"Hello from setuptools_version_tags! (version {__version__})")


if __name__ == "__main__":
    main()
