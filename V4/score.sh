#!/usr/bin/env bash
# ScholarChain V4: your score from your own V1/V2/V3 results. Usage:
#   ./score.sh --student <NetID>
# Reads the LATEST results already saved in ../V1/selfcheck-results, ../V2/results and ../V3/results
# (run those first). No AI, no cost, nothing is read from your project repository itself.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
command -v python3 >/dev/null || { echo "V4 needs python3 (3.8 or newer)." >&2; exit 2; }
python3 -E -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' ||
  { echo "V4 needs Python 3.8 or newer (you have $(python3 --version 2>&1))." >&2; exit 2; }
exec python3 -I "$HERE/score.py" --autograder "$HERE/.." "$@"
