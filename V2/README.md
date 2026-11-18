# ScholarChain V2: AI judge (advisory)

V2 asks Claude to judge parts of **your own ScholarChain repository** against the rubric, item by
item, with a citation (file, lines, exact quote) for every verdict. It is **advisory**: it is not
your grade. The instructor grades by re-running the checks on a fresh clone of your submission.

V1 checks structure and process deterministically; V2 judges the content. Use both.

**What exactly is judged:** [`RUBRIC.md`](RUBRIC.md): every item, deduction, threshold, and what is left to a human.

## Categories in this version

| Category | Rubric points | Judged from phase | Status |
|---|---:|---:|---|
| `dataset_engineering` (Dataset engineering) | 1.0 | 3 | available |
| `spark_analytics` (Spark coauthorship analytics) | 3.0 | 6 | available |
| other categories | | | coming in later versions (`git pull`) |

A category is judged only once your repository has reached its phase (your highest
`docs/agent-runs/phase-NN` folder). Earlier, every item would just come back "missing" and use your
usage for nothing. Use `--include-not-due` to judge it anyway.

## 1. What you need

| You need | Check with | Notes |
|---|---|---|
| bash, git | `bash --version`, `git --version` | Windows: use WSL. |
| Python 3.8+ | `python3 --version` | |
| jsonschema | `python3 -c "import jsonschema"` | If missing: `python3 -m pip install --user jsonschema` |
| Claude Code, logged in | `claude --version` | Version 2.1.326 or newer (`claude update`). |

**It uses your own Claude usage.** One run of one category costs roughly the same as a short
Claude Code session (measured, API-equivalent: about $0.15-0.35 for `spark_analytics`, $0.30-0.55 for `dataset_engineering`; on a
subscription it counts against your plan's usage). The script shows the estimate and asks before
starting. Each run takes 1-2 minutes.

## 2. Run it

Keep this folder OUTSIDE your project (like V1):

```bash
cd ~/CS441_Autograder_For_Students/V2
./judge.sh --student <your NetID> ~/projects/my-scholarchain --dry-run   # free: shows what would be judged
./judge.sh --student <your NetID> ~/projects/my-scholarchain             # the real run (asks first)
```

Options: `--category dataset_engineering` (only that one; repeatable), `--runs 2` (two independent runs; items
where they disagree are marked for a human), `--yes` (don't ask), `--include-not-due`.

## 3. Read the results

Results go to `V2/results/<repo>-<time>/`:

| File | What it is | Share? |
|---|---|---|
| `v2-<NetID>-<time>.csv` | one row per rubric item / deduction: verdict, severity, needs_human + reason codes, counts of integrity notes, cost (no text from your code) | **yes, only this file**, when your instructor asks |
| `<category>/result.md` | the verdict table | no (keep it) |
| `<category>/result.json`, `run-*.json*` | reasons, citations from your code, the full trace | **no** (contains your code) |

Verdicts: `met`, `partial`, `missing`, `cannot_tell` (the judge could not decide: a human looks).
Reasons are in `result.json` (`items.<ID>.reason`). Every item is explained in [`RUBRIC.md`](RUBRIC.md).

`needs_human = yes` means a verdict the code could not confirm (a citation that didn't match your
files, two runs that disagreed, low confidence, or a contradiction with V1's facts). Treat those as
"look at this yourself", not as wrong.

## 4. How it stays safe

- **Your code is never run.** Claude gets only Read, Glob and Grep (no shell, no edits, no web).
- `--restricted`: your repo's `CLAUDE.md`, hooks and settings are not loaded, and reads are confined to
  your repository. `--strict-mcp-config`: no MCP servers start.
- The model is fixed (`judge/grader_policy.json`), so results don't change with your default model.
- Every citation is checked against your actual files by code; a citation that doesn't match is
  discarded and the item goes to a human.
- Text in your repository addressed to the grader is reported as an integrity note, never obeyed.

## 5. Limits

- The judge reads code; it can't tell whether something ran on AWS or produced correct numbers.
- Two runs can disagree on borderline items; that's why such items are marked `needs_human`.
- It judges only what this version's rubric files cover.
