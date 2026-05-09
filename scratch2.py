from pathlib import Path
from gitversioned.settings import Settings

with open("examples/setuptools-setup-cfg/setup.cfg", "w") as f:
    f.write("""[tool:gitversioned]
source_type = tag
""")

s = Settings(project_root=Path("examples/setuptools-setup-cfg"), package_name="foo")
print(f"source_type (tag): {s.source_type}")

with open("examples/setuptools-setup-cfg/setup.cfg", "w") as f:
    f.write("""[tool:gitversioned]
source_type = ["tag"]
""")
