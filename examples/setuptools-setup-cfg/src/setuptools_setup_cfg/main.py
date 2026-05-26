try:
    import setuptools_setup_cfg

    __version__ = getattr(setuptools_setup_cfg, "__version__", "not available yet")
except ImportError:
    __version__ = "not available yet"


def main():
    print(f"Hello from setuptools_setup_cfg! (version {__version__})")


if __name__ == "__main__":
    main()
