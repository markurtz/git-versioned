try:
    import hatchling_hatch_vars

    __version__ = getattr(hatchling_hatch_vars, "__version__", "not available yet")
except ImportError:
    __version__ = "not available yet"


def main():
    print(f"Hello from hatchling_hatch_vars! (version {__version__})")


if __name__ == "__main__":
    main()
