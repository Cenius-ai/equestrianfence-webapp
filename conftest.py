import sys
from pathlib import Path

# Make the single-file module importable from the tests without an install step.
sys.path.insert(0, str(Path(__file__).resolve().parent))
