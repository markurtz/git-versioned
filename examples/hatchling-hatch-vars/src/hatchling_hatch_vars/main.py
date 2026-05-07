try:
    from hatchling_hatch_vars import __version__  # type: ignore[attr-defined]
except ImportError:
    __version__ = "not available yet"


def main():
    print(f"Hello from hatchling_hatch_vars! (version {__version__})")


if __name__ == "__main__":
    main()
