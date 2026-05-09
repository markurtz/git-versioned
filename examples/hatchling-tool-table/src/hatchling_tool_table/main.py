try:
    from hatchling_tool_table import __version__  # type: ignore[attr-defined]
except ImportError:
    __version__ = "not available yet"


def main():
    print(f"Hello from hatchling_tool_table! (version {__version__})")


if __name__ == "__main__":
    main()
