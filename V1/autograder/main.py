"""
main.py: runs every check group, labels checks that aren't due yet, prints, writes JSON.

Flow:
  0. wrong_folder(repo)          a subfolder of a repo, or a folder above repos -> say which folder, exit 2
  1. Repo(root)                  safe, read-only view of the student's repository (repo.py)
  2. registry.run_all(repo)      every @check_group (checks/*), in phase order -> list of results
  3. "not yet due" relabelling   apply_due() below
  4. write JSON/CSV, then print  exit 1 if any due check FAILs, else 0
"""
import argparse
import csv
import datetime
import json
import re
import sys
from pathlib import Path

from . import VERSION
from . import checks  # noqa: F401  (importing registers every check group)
from .registry import run_all
from .repo import Repo

ICON = {"PASS": "ok  ", "FAIL": "FAIL", "WARN": "warn", "INFO": "info", "LATER": "later"}
CSV_COLUMNS = ["student", "repo", "version", "run_date", "current_phase", "check_id", "title", "status",
               "due_phase", "details", "observed"]
STUDENT_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")
RUN_DATE = datetime.datetime.now(datetime.timezone.utc).date().isoformat()   # day only, UTC


def safe_cell(value):
    """Spreadsheet formula injection guard. Excel/Sheets treat a cell starting with = + - @ (or a
    tab/CR) as a FORMULA. Cell text here can come from the student's repo (file names, report
    text), so such cells get a leading apostrophe, which spreadsheets display as plain text."""
    v = "" if value is None else str(value)
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v


def write_csv(path, student, repo_name, current, results):
    """One row per check; the student/run columns repeat on every row so the file can be
    filtered in a spreadsheet and merged across students without extra context.
    Several detail lines go into one cell, separated by ' | '."""
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(CSV_COLUMNS)
        for r in results:
            w.writerow([safe_cell(x) for x in (student, repo_name, VERSION, RUN_DATE,
                                               "" if current is None else current,
                                               r["id"], r["title"], r["status"], r["due_phase"],
                                               " | ".join(r["details"]),
                                               json.dumps(r["data"], sort_keys=True) if "data" in r else "")])


def apply_due(results, current):
    """A check whose phase is after the student's current phase becomes LATER, ALWAYS, even if it
    would pass: an early pass is often vacuous ("all hooks executable" is true when there are no
    hooks). Its would-be status is kept in the details. INFO stays INFO.
    current=None (no phase folders): the phase is unknown, nothing is relaxed. Otherwise a repo
    with no evidence at all would look better than one with some."""
    for r in results:
        if current is not None and r["due_phase"] > current and r["status"] != "INFO":
            r["details"].insert(0, f"not due yet: needed by phase {r['due_phase']}; your highest phase is "
                                   f"{current} (right now it would be {r['status']})")
            r["status"] = "LATER"


def wrong_folder(repo):
    """The checker needs the repository ROOT (where .git and .claude/ are). Two common mistakes
    would otherwise produce a wall of FAILs:
      1. a SUBFOLDER of a git repository (e.g. my-repo/scholarchain/)
      2. a folder ABOVE the repository (e.g. ~/projects instead of ~/projects/my-repo)
    Returns a message saying which folder to use, or None if the folder looks right.
    Uses the hardened repo.git(), like every other git call."""
    top = repo.toplevel()
    if top and top != repo.root:
        return (f"selfcheck: {repo.root}\n  is a subfolder of the git repository at {top}.\n"
                f"  Point selfcheck at the repository root (where .git and .claude/ are):\n"
                f"    ./selfcheck.sh {top}")
    if not repo.is_git:
        # not a repo itself: is there a repo one or two levels below?
        below = repo.repos_below()
        if below:
            return (f"selfcheck: {repo.root} is not a git repository, but contains "
                    f"{'one' if len(below) == 1 else len(below)}:\n"
                    + "\n".join(f"    ./selfcheck.sh {b}" for b in below[:5])
                    + ("\n    ..." if len(below) > 5 else "")
                    + "\n  Point selfcheck at your repository's root folder.")
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="ScholarChain self-check (advisory, read-only).")
    ap.add_argument("repo", help="path to the student's ScholarChain repository")
    ap.add_argument("--json", help="also write the results as JSON to this path")
    ap.add_argument("--csv", help="also write the results as CSV (one row per check) to this path")
    ap.add_argument("--student", default="", help="student ID (e.g. NetID) recorded in the JSON/CSV")
    ap.add_argument("--ownership", help="ownership rows extracted by the AI (extract_ownership.sh); "
                                        "without it, the table in docs/agents.md is parsed")
    args = ap.parse_args(argv)
    root = Path(args.repo).resolve()
    if not root.is_dir():
        sys.exit(f"not a folder: {root}")
    if args.student and not STUDENT_ID.fullmatch(args.student):
        sys.exit("--student: use letters, digits, '.', '_' or '-' only (max 64), e.g. your NetID")

    repo = Repo(root, args.ownership)
    if (msg := wrong_folder(repo)):
        print(msg, file=sys.stderr)
        return 2
    run = run_all(repo)
    results = run.items
    current = repo.current_phase
    apply_due(results, current)

    # Save the results BEFORE printing: if the output is piped into `head` and the pipe closes,
    # printing stops, but the CSV/JSON are already written.
    if args.json:
        # repo: folder NAME only. The full path would contain the student's home folder / username.
        Path(args.json).write_text(json.dumps({
            "student": args.student, "version": VERSION, "run_date": RUN_DATE, "repo": root.name,
            "current_phase": current,
            # FILE INDEX for later grading steps. Valid ONLY for this commit; a grader must regenerate
            # it on its own copy of the submission rather than trust one it was sent.
            "index": {"index_version": 1, "commit": (repo.git("rev-parse", "HEAD") or "").strip() or None,
                      **run.index},
            "ownership_source": repo.ownership["source"] if repo.ownership["rows"] else None,
            "results": results}, indent=2))
    if args.csv:
        write_csv(args.csv, args.student, root.name, current, results)

    print(f"ScholarChain self-check v{VERSION}   repo: {root}")
    print("current phase: " + (f"{current} (highest docs/agent-runs/phase-NN)" if current is not None
                               else "unknown (no docs/agent-runs/phase-NN): every check applies") + "\n")
    for r in results:
        print(f"[{ICON[r['status']]}] {r['id']}  {r['title']}")
        for d in r["details"]:
            print(f"         - {d}")
    counts = {s: sum(r["status"] == s for r in results) for s in ICON}
    print(f"\n{counts['PASS']} pass, {counts['FAIL']} fail, {counts['WARN']} warn, {counts['INFO']} info, "
          f"{counts['LATER']} not yet due")

    return 1 if counts["FAIL"] else 0
