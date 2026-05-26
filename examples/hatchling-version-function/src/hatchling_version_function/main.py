try:
    import hatchling_version_function

    __version__ = getattr(
        hatchling_version_function, "__version__", "not available yet"
    )
except ImportError:
    __version__ = "not available yet"


def get_version() -> str:
    """Return the package version for gitversioned."""
    return "0.1.0"


def main() -> None:
    print(f"Hello from hatchling_version_function! (version {__version__})")


if __name__ == "__main__":
    main()
