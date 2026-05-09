from pathlib import Path
from gitversioned.settings import Settings
s = Settings(project_root=Path("examples/setuptools-setup-cfg"), package_name="foo")
print(f"source_type: {s.source_type}")
