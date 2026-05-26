try:
    import setuptools_setup_py

    __version__ = getattr(setuptools_setup_py, "__version__", "not available yet")
except ImportError:
    __version__ = "not available yet"


def main():
    print(f"Hello from setuptools_setup_py! (version {__version__})")


if __name__ == "__main__":
    main()
