#!/usr/bin/env bash
# ScholarChain V3 (experimental advisory AI judge: agentic factory). Usage:
#   ./judge.sh --student <NetID> ~/path/to/your-scholarchain-repo [--category spark_analytics] [--dry-run]
# Reads your repository only; never runs its code. Uses YOUR Claude Code login and usage.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
command -v python3 >/dev/null || { echo "V3 needs python3 (3.8 or newer)." >&2; exit 2; }
python3 -E -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' ||
  { echo "V3 needs Python 3.8 or newer (you have $(python3 --version 2>&1))." >&2; exit 2; }
python3 -E -c 'import jsonschema' 2>/dev/null ||
  { echo "V3 needs the Python package jsonschema. Install it once with:" >&2
    echo "    python3 -m pip install --user jsonschema" >&2; exit 2; }
# -E: ignore PYTHON* environment variables. The script folder (ours) is the only code path added;
# nothing is ever imported from your repository.
exec python3 -E "$HERE/judge/grade_all.py" "$@"
