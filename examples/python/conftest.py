import os
import sys
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
# Tests always run against mock models, whatever the developer's shell says.
os.environ["COURSE_LLM_PROVIDER"] = "mock"
# Let tests import sibling example modules (e.g. `import hello_agent`).
for module_dir in sorted(Path(__file__).parent.glob("m*")):
    sys.path.insert(0, str(module_dir))
