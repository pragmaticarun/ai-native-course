import os
import sys
from pathlib import Path

HERE = Path(__file__).parent
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
os.environ["COURSE_LLM_PROVIDER"] = "mock"
sys.path.insert(0, str(HERE))
# Exercises may reuse worked-example code (e.g. M1's assess.py).
for module_dir in sorted((HERE.parent / "examples" / "python").glob("m*")):
    sys.path.insert(0, str(module_dir))
