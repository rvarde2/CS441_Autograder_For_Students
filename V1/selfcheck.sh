#!/usr/bin/env bash
# ScholarChain self-check: advisory checks a student runs on their own repository.
#
#   ./selfcheck.sh [options] <path-to-your-scholarchain-repo>
#
#   --student ID      your NetID; recorded in the results, and the CSV is named selfcheck-<ID>.csv
#   --out DIR         where results go (default: ./selfcheck-results). Never inside your repo.
#   --ai-ownership    ALSO let Claude Code read your ownership map (more accurate than the
#                     built-in parser). Uses YOUR Claude usage and sends repository content to
#                     Anthropic under your account. Off by default.
#   --model ID        model for --ai-ownership (default: claude-opus-5-5)
#   --yes             don't ask before the AI step (for scripts)
#
# Exit codes: 0 = no FAIL among checks that are due; 1 = at least one FAIL; 2 = usage/setup error.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
die() { echo "selfcheck: $*" >&2; exit 2; }

AI=0; YES=0; MODEL="claude-opus-5-5"; OUT="$PWD/selfcheck-results"; STUDENT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --ai-ownership) AI=1; shift ;;
    --yes) YES=1; shift ;;
    --model) [ $# -ge 2 ] || die "--model needs a value"; MODEL="$2"; shift 2 ;;
    --out) [ $# -ge 2 ] || die "--out needs a value"; OUT="$2"; shift 2 ;;
    --student) [ $# -ge 2 ] || die "--student needs a value"; STUDENT="$2"; shift 2 ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    -*) die "unknown option: $1" ;;
    *) break ;;
  esac
done
[ $# -eq 1 ] || die "usage: $0 [--student NETID] [--ai-ownership] [--out DIR] <path-to-your-repo>"
[ -z "$STUDENT" ] || [[ "$STUDENT" =~ ^[A-Za-z0-9._-]{1,64}$ ]] || die "--student: letters, digits, . _ - only (e.g. your NetID)"
CSV_NAME="selfcheck-${STUDENT:-results}.csv"
[ -d "$1" ] || die "not a folder: $1"
REPO="$(cd "$1" && pwd)"

command -v python3 >/dev/null || die "python3 is required"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 8))' || die "python3 3.8 or newer is required"
command -v git >/dev/null || die "git is required"

mkdir -p "$OUT"; OUT="$(cd "$OUT" && pwd)"
case "$OUT/" in "$REPO/"*) die "--out must be outside your repository (results must not end up in your submission)" ;; esac

OWN_ARGS=()
if [ "$AI" = 1 ]; then
  command -v claude >/dev/null || die "--ai-ownership needs Claude Code (the 'claude' command)"
  cat >&2 <<EOF
--ai-ownership: Claude Code ($MODEL) will READ your repository to extract the ownership map.
  - It uses your own Claude usage.
  - Repository content is sent to Anthropic under your account.
  - It runs read-only: --restricted (your CLAUDE.md, hooks and settings are NOT loaded),
    --strict-mcp-config (your MCP servers are NOT started), tools Read and Glob only.
EOF
  if [ "$YES" != 1 ]; then
    [ -t 0 ] || die "--ai-ownership needs --yes when not run interactively"
    read -rp "Continue? [y/N] " ok; [[ "$ok" =~ ^[Yy] ]] || die "cancelled"
  fi
  bash "$HERE/extract_ownership.sh" "$REPO" "$OUT/ownership.json" "$MODEL"   # bash: works even if a zip lost the +x bit || die "AI ownership extraction failed (see $OUT/ownership.jsonl)"
  OWN_ARGS=(--ownership "$OUT/ownership.json")
fi

set +e
python3 -I "$HERE/checks.py" "$REPO" --json "$OUT/selfcheck-results.json" --csv "$OUT/$CSV_NAME" \
  --student "$STUDENT" ${OWN_ARGS[@]+"${OWN_ARGS[@]}"}   # this form: bash 3.2 (macOS) safe with set -u
rc=$?
set -e
[ $rc -ne 2 ] || exit 2        # wrong folder (message already printed): nothing was saved
echo
echo "Saved: $OUT/$CSV_NAME   <- the only file to share"
echo "       $OUT/selfcheck-results.json   (keep on your computer; grader version $(cat "$HERE/VERSION" 2>/dev/null || echo '?'))"
[ -n "$STUDENT" ] || echo "Tip: add --student <your NetID> so the CSV is named and labelled for you."
echo "ADVISORY ONLY: this is not your grade. See README.md for what it does and does not check."
exit $rc
