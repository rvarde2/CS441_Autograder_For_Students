"""
grade_all.py (V2 entry point): judge every SHIPPED and DUE rubric category of one repository with
the AI, then write one CSV of verdicts. Students run it on their own repo (advisory); the instructor
runs the same code on fresh clones for grading.

    python3 -I grade_all.py <repo> [--student NETID] [--category ID ...] [--runs N]
                            [--include-not-due] [--yes] [--dry-run] [--out DIR]

Shipped categories = the rubric files present in rubric/ (the package decides, not this code).
Due = the rubric's phase <= the repo's current phase (highest docs/agent-runs/phase-NN). A repo with no
phase folders: every category is due (same rule as V1: nothing relaxed).
Nothing in the repository is executed. Each category is judged by grade_category.py (unchanged).
The CSV holds verdicts only: no reasons, no quotes from the code (share only the CSV).
"""
import argparse
import csv
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))                     # V1's autograder package (our code)
from autograder.repo import Repo                         # noqa: E402

V2_VERSION = (HERE / "VERSION").read_text().strip() if (HERE / "VERSION").exists() else "dev"
# Measured cost per run (API-equivalent USD; on a Pro plan it counts against your usage instead).
COST = {"spark_analytics": (0.15, 0.35), "dataset_engineering": (0.30, 0.55), "hadoop_mapreduce": (0.20, 0.50)}
CSV_COLUMNS = ["student", "repo", "commit", "v2_version", "model", "prompt_version", "rubric_sha", "run_date",
               "category", "id", "kind", "verdict", "severity", "per_run", "needs_human"]


def version_tuple(s):
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", s or "")
    return tuple(int(x) for x in m.groups()) if m else None


def check_claude(policy):
    try:
        out = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired):
        sys.exit("V2 needs Claude Code (the `claude` command). Install it and log in first: "
                 "https://docs.claude.com/en/docs/claude-code")
    have, tested = version_tuple(out), version_tuple(policy["claude_code_tested"])
    if have is None:
        sys.exit(f"could not read the Claude Code version from: {out.strip()!r}")
    if have < tested:
        sys.exit(f"Claude Code {out.strip()} is older than {policy['claude_code_tested']}, the version whose safety "
                 f"flags (--restricted, --strict-mcp-config) were tested. Update it: `claude update`.")
    if have > tested:
        print(f"note: Claude Code {'.'.join(map(str, have))} is newer than the tested {policy['claude_code_tested']}.")
    return out.strip()


def safe_cell(v):
    """CSV formula-injection guard (a repo name is chosen by the student)."""
    s = str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


def main():
    ap = argparse.ArgumentParser(description="ScholarChain V2: AI judge per rubric category (advisory).")
    ap.add_argument("repo", help="your ScholarChain repository (its root folder)")
    ap.add_argument("--student", default="", help="your NetID (goes into the CSV)")
    ap.add_argument("--category", action="append", help="judge only this category (repeatable)")
    ap.add_argument("--runs", type=int, default=1, help="runs per category (default 1)")
    ap.add_argument("--include-not-due", action="store_true", help="also judge categories whose phase is not reached")
    ap.add_argument("--yes", action="store_true", help="do not ask before starting the AI runs")
    ap.add_argument("--dry-run", action="store_true", help="build everything the AI would get; no AI call, no cost")
    ap.add_argument("--out", help="results folder (default: results/<repo>-<time> in the V2 folder)")
    a = ap.parse_args()

    repo_root = Path(a.repo).resolve()
    repo = Repo(repo_root)
    if not repo.is_git or (repo.toplevel() and repo.toplevel() != repo.root):
        sys.exit(f"{repo_root} is not the root folder of a git repository (where .git is). Point V2 at your repo root.")
    policy = json.loads((HERE / "grader_policy.json").read_text())
    shipped = sorted(p.stem for p in (HERE / "rubric").glob("*.json"))
    wanted = a.category or shipped
    unknown = [c for c in wanted if c not in shipped]
    if unknown:
        sys.exit(f"unknown or not yet available categories: {unknown}; available: {shipped}")

    phase = repo.current_phase
    plan, skipped = [], []
    for c in wanted:
        due = min(json.loads((HERE / "rubric" / f"{c}.json").read_text())["evidence"].get("phases") or [0])
        (plan if phase is None or due <= phase or a.include_not_due else skipped).append((c, due))
    print(f"ScholarChain V2 {V2_VERSION}   repo: {repo_root}")
    print(f"current phase: {phase if phase is not None else 'unknown (no docs/agent-runs/phase-NN): every category is due'}")
    for c, due in skipped:
        print(f"  skip {c}: due at phase {due} (use --include-not-due to judge it anyway)")
    if not plan:
        print("nothing to judge yet.")
        return 0

    tool = "dry run" if a.dry_run else check_claude(policy)
    lo = sum(COST.get(c, (0.3, 0.6))[0] for c, _ in plan) * a.runs
    hi = sum(COST.get(c, (0.3, 0.6))[1] for c, _ in plan) * a.runs
    print(f"will judge: {', '.join(c for c, _ in plan)}  ({a.runs} run(s) each, model {policy['model']}, {tool})")
    if not a.dry_run:
        print(f"estimated cost: ${lo:.2f}-${hi:.2f} API-equivalent (on a subscription this uses your plan's usage), "
              f"about 1-2 minutes per run")
        if not a.yes:
            if not sys.stdin.isatty() or input("continue? [y/N] ").strip().lower() not in ("y", "yes"):
                print("stopped; nothing was sent.")
                return 1

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(a.out).resolve() if a.out else HERE.parent / "results" / f"{repo_root.name}-{stamp}"
    if out == repo_root or repo_root in out.parents:
        sys.exit("refused: the results folder must be outside your repository")
    rows, summary = [], []
    for c, _ in plan:
        print(f"\n== {c}")
        # same isolation as this process: -I (instructor) or -E (student wrapper: keeps pip --user packages)
        cmd = [sys.executable, "-I" if sys.flags.isolated else "-E", str(HERE / "grade_category.py"), "--category", c, "--repo", str(repo_root),
               "--out", str(out / c), "--runs", str(a.runs)] + (["--dry-run"] if a.dry_run else [])
        sys.stdout.flush()                               # keep our lines before the child's output
        r = subprocess.run(cmd)
        res_file = out / c / "result.json"
        if r.returncode != 0 or not res_file.exists():
            summary.append(f"{c}: FAILED (exit {r.returncode}); see {out / c}")
            continue
        res = json.loads(res_file.read_text())
        if a.dry_run:
            summary.append(f"{c}: dry run (pack {len(res.get('pack', []))} files)")
            continue
        pv, human = res["provenance"], set(res.get("human_queue", []))
        base = [a.student, repo_root.name, pv["commit"], V2_VERSION, pv["model"], pv["prompt_version"],
                pv["rubric_sha"], pv["date"], c]
        for i, v in res["items"].items():
            rows.append(base + [i, "item", v["verdict"], "", "/".join(v["per_run"]), "yes" if i in human else "no"])
        for d, v in res["deductions"].items():
            rows.append(base + [d, "deduction", v["applies"], v["severity"], "/".join(f"{x[0]}:{x[1]}" for x in v["per_run"]),
                                "yes" if v["applies"] == "cannot_tell" else "no"])
        if res["runs_valid"] == 0:
            summary.append(f"{c}: no valid run (see {out / c}/result.md)")
        else:
            counts = {}
            for v in res["items"].values():
                counts[v["verdict"]] = counts.get(v["verdict"], 0) + 1
            summary.append(f"{c}: " + ", ".join(f"{n} {k}" for k, n in sorted(counts.items()))
                           + f"; details: {out / c / 'result.md'}")

    if rows:
        name = f"v2-{safe_cell(a.student) or 'student'}-{stamp}.csv".replace("/", "_")
        with open(out / name, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(CSV_COLUMNS)
            w.writerows([[safe_cell(x) for x in row] for row in rows])
        summary.append(f"CSV (share only this file): {out / name}")
    print("\n" + "\n".join(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
