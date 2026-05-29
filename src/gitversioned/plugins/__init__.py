r"""
Build system plugins for integrating gitversioned with Python build backends.

This package provides the integration plugins required to connect the core
git-versioned version resolution logic with standard Python build backends,
such as Hatchling, Setuptools, and Maturin. These plugins serve as build system hooks
and entry points that intercept the build lifecycle to query and inject
dynamically generated PEP 440 version strings into the distribution metadata.

Build systems discover and load these plugins using standardized packaging
entry points. The submodules handle the backend-specific API calls and map
the build configuration options defined in files like ``pyproject.toml`` to
the underlying versioning parameters.

Examples
--------
Configure Hatchling to use the gitversioned plugin within ``pyproject.toml``:

.. code-block:: toml

   [build-system]
   requires = ["hatchling", "git-versioned"]
   build-backend = "hatchling.build"

   [tool.hatch.version]
   source = "gitversioned"

Configure Maturin with overridden configurations within ``pyproject.toml``:

.. code-block:: toml

   [build-system]
   requires = ["maturin>=1.0,<2.0", "git-versioned"]
   build-backend = "gitversioned.plugins.maturin_plugin"

   [tool.gitversioned]
   output = "src/my_package/version.py"

   [tool.gitversioned.overrides.cargo]
   output = "Cargo.toml"
   output_strategies.type = "regex"
   output_strategies.pattern = '''
   (?ms)^\[package\].*?^(\s*version\s*=\s*)(["\'])(?P<version>[^"\']+)\2
   '''
"""
