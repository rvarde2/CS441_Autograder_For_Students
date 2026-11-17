"""
Entry point:   python3 -I checks.py <repo> [--json out.json] [--ownership rows.json]

`-I` (isolated mode) stops Python from importing anything from the current folder, so a file in
the student's repo named like a module (json.py, re.py) can't be loaded by accident. Isolated mode
also leaves THIS folder off the import path, so it's added explicitly: it holds only our code.
All the logic lives in the autograder/ package (see DESIGN.md).
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from autograder.main import main  # noqa: E402

try:
    rc = main()
    sys.stdout.flush()          # surface a closed pipe HERE, not as a traceback at shutdown
except BrokenPipeError:
    # output piped into `head`/`less` that quit early: not an error. Results files are already
    # saved (main writes them before printing). Point stdout at /dev/null so exit is quiet.
    os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
    rc = 0
sys.exit(rc)
