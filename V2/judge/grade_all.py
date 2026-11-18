"""
grade_all.py (V2 entry point): judge every SHIPPED and DUE rubric category of one repository with
the AI, then write one CSV of verdicts. Students run it on their own repo (advisory); the instructor
runs the same code on fresh clones for grading.

    python3 -I grade_all.py <repo> [--student NETID] [--category ID ...]
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
COST = {"spark_analytics": (0.15, 0.35), "dataset_engineering": (0.30, 0.55), "hadoop_mapreduce": (0.45, 0.75)}
# COST was measured with claude-opus-5-5; claude-sonnet-5-5 measured about 0.3x of that (Nov 18, 1 run).
SONNET_FACTOR = 0.3
CSV_COLUMNS = ["student", "repo", "commit", "v2_version", "model", "prompt_version", "rubric_sha", "run_date",
               "current_phase", "category", "id", "kind", "verdict", "severity", "needs_human",
               "human_reasons", "category_integrity_notes", "category_cost_usd"]
# Why an item needs a human, as FIXED codes (flag text can contain student file names: never copied).
REASON_CODES = [("unsupported: no verified citation", "citation_mismatch"), ("absence not checked", "absence_unchecked"),
                ("absence_check doesn't match", "absence_unverified"), ("not called by the job", "not_called"),
                ("V1 contradiction", "v1_contradiction"), ("always confirmed by a human", "always_human")]


def human_reasons(item):
    codes = []
    for flag in item.get("flags", []):
        code = next((c for prefix, c in REASON_CODES if str(flag).startswith(prefix)), "other")
        if code not in codes:
            codes.append(code)
    if "low" in item.get("confidence", []):
        codes.append("low_confidence")
    if item.get("verdict") == "cannot_tell" and not codes:
        codes.append("cannot_tell")
    return ";".join(codes)


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


def check_antigravity(policy):
    try:
        out = subprocess.run(["agy", "--version"], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired):
        sys.exit("V2 with --adapter antigravity needs the Antigravity CLI (`agy`). Install it and log in first.")
    tested_str = (policy.get("antigravity") or {}).get("agy_tested", "1.5.11")
    have, tested = version_tuple(out), version_tuple(tested_str)
    if have is None:
        sys.exit(f"could not read the Antigravity CLI version from: {out.strip()!r}")
    if have < tested:
        sys.exit(f"Antigravity CLI {out.strip()} is older than {tested_str}, the version whose safety "
                 f"flags (--sandbox, --disable-slash-commands, --settings) were tested. Update `agy` first.")
    if have > tested:
        print(f"note: Antigravity CLI {'.'.join(map(str, have))} is newer than the tested {tested_str}.")
    return f"agy {out.strip()}"


def choose_tool(policy, ask):
    """Ask which AI tool to use; Claude (with the policy's default model) unless the user picks Antigravity.
    Without a terminal (scripts, --yes, --dry-run) the default is used without asking."""
    claude_model = policy["model"]
    agy_model = (policy.get("antigravity") or {}).get("model", "?")
    if not ask:
        return "claude"
    print("Which AI tool should judge your repository?")
    print(f"  1) Claude Code   (model {claude_model})   [default]")
    print(f"  2) Antigravity   (model {agy_model})")
    choice = input("choose 1 or 2 [1]: ").strip()
    return "antigravity" if choice in ("2", "antigravity", "a") else "claude"


def safe_cell(v):
    """CSV formula-injection guard (a repo name is chosen by the student)."""
    s = str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


def main():
    ap = argparse.ArgumentParser(description="ScholarChain V2: AI judge per rubric category (advisory).")
    ap.add_argument("repo", help="your ScholarChain repository (its root folder)")
    ap.add_argument("--student", default="", help="your NetID (goes into the CSV)")
    ap.add_argument("--category", action="append", help="judge only this category (repeatable)")
    a_runs = 1                                         # always ONE run per category (user decision Nov 18)
    ap.add_argument("--adapter", choices=("claude", "antigravity"),
                    help="AI tool: claude or antigravity. If omitted you are asked (default: claude).")
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
    plan.sort(key=lambda x: (x[1], x[0]))                # project phase order: datasets (3) before spark (6)
    print(f"ScholarChain V2 {V2_VERSION}   repo: {repo_root}")
    print(f"current phase: {phase if phase is not None else 'unknown (no docs/agent-runs/phase-NN): every category is due'}")
    for c, due in skipped:
        print(f"  skip {c}: due at phase {due} (use --include-not-due to judge it anyway)")
    if not plan:
        print("nothing to judge yet.")
        return 0

    if a.adapter is None:
        a.adapter = choose_tool(policy, ask=sys.stdin.isatty() and not a.yes and not a.dry_run)
    check_fn = check_antigravity if a.adapter == "antigravity" else check_claude
    tool = "dry run" if a.dry_run else check_fn(policy)
    model = (policy.get(a.adapter) or {}).get("model", policy["model"]) if isinstance(policy.get(a.adapter), dict) else policy["model"]
    lo = sum(COST.get(c, (0.3, 0.6))[0] for c, _ in plan) * a_runs
    hi = sum(COST.get(c, (0.3, 0.6))[1] for c, _ in plan) * a_runs
    print(f"will judge: {', '.join(c for c, _ in plan)}  (model {model}, {tool})")
    if not a.dry_run:
        if a.adapter == "antigravity":
            print("cost: uses your Antigravity (Google) quota; about 1-2 minutes per run")
        else:
            f = SONNET_FACTOR if "sonnet" in model else 1.0
            print(f"estimated cost: ${lo * f:.2f}-${hi * f:.2f} API-equivalent (on a subscription this uses your plan's "
                  f"usage), about 1-2 minutes per run")
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
               "--out", str(out / c), "--adapter", a.adapter] + (["--dry-run"] if a.dry_run else [])
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
                pv["rubric_sha"], pv["date"], "" if phase is None else phase, c]
        cost = round(sum((u or {}).get("total_cost_usd") or 0 for u in res.get("usage", [])), 4)
        tail = [len(res.get("integrity_notes", [])), cost]           # counts only: note text quotes student code
        for i, v in res["items"].items():
            rows.append(base + [i, "item", v["verdict"], "", "yes" if i in human else "no",
                                human_reasons(v) if i in human else ""] + tail)
        for d, v in res["deductions"].items():
            dh = v["applies"] == "cannot_tell"
            rows.append(base + [d, "deduction", v["applies"], v["severity"],
                                "yes" if dh else "no", "cannot_tell" if dh else ""]
                        + tail)
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
