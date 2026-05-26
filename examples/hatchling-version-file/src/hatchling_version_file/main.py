try:
    import hatchling_version_file

    __version__ = getattr(hatchling_version_file, "__version__", "not available yet")
except ImportError:
    __version__ = "not available yet"


def main():
    print(f"Hello from hatchling_version_file! (version {__version__})")


if __name__ == "__main__":
    main()
