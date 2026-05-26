try:
    import setuptools_tool_table

    __version__ = getattr(setuptools_tool_table, "__version__", "not available yet")
except ImportError:
    __version__ = "not available yet"


def main():
    print(f"Hello from setuptools_tool_table! (version {__version__})")


if __name__ == "__main__":
    main()
