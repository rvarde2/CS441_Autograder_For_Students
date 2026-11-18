# ScholarChain V2: AI judge (advisory)

V2 asks Claude to judge parts of **your own ScholarChain repository** against the rubric, item by
item, with a citation (file, lines, exact quote) for every verdict. It is **advisory**: it is not
your grade. The instructor grades by re-running the checks on a fresh clone of your submission.

V1 checks structure and process deterministically; V2 judges the content. Use both.

**Step by step:** [`HOW_TO_RUN.md`](HOW_TO_RUN.md). **What exactly is judged:** [`RUBRIC.md`](RUBRIC.md): every item, deduction, threshold, and what is left to a human.

## Categories in this version

| Category | Rubric points | Judged from phase | Status |
|---|---:|---:|---|
| `dataset_engineering` (Dataset engineering) | 1.0 | 3 | available |
| `hadoop_mapreduce` (Hadoop MapReduce) | 2.0 | 4 | available |
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
| *or* Antigravity CLI, logged in | `agy --version` | Optional second AI tool; version 1.5.11 or newer. |

**It uses your own Claude usage.** One run of one category costs roughly the same as a short
Claude Code session (measured, API-equivalent: about $0.30-0.55 for `dataset_engineering`, $0.45-0.75 for `hadoop_mapreduce`,
$0.15-0.35 for `spark_analytics`; on a
subscription it counts against your plan's usage). The script shows the estimate and asks before
starting. Each run takes 1-2 minutes.

## 2. Run it

When you start a real run, V2 asks which AI tool to use: **1) Claude Code** (model `claude-sonnet-5-5`, the
default) or **2) Antigravity** (model `gemini-4-argon-medium`, uses your Google quota). `--adapter claude` or
`--adapter antigravity` skips the question. The Claude judge is the one measured against our labelled test
repositories; the Antigravity judge has the same safety rules but has not been measured yet, so treat its
verdicts with extra care.

Keep this folder OUTSIDE your project (like V1):

```bash
cd ~/CS441_Autograder_For_Students/V2
./judge.sh --student <your NetID> ~/projects/my-scholarchain --dry-run   # free: shows what would be judged
./judge.sh --student <your NetID> ~/projects/my-scholarchain             # the real run (asks first)
```

Options: `--category dataset_engineering` (only that one; repeatable), `--yes` (don't ask), `--include-not-due`.
Each category is judged once per run of the script.

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
files, low confidence, or a contradiction with V1's facts). Treat those as
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
- Borderline items can be judged differently than a human would; `needs_human` marks the verdicts the code could
  not confirm, so look at those yourself.
- It judges only what this version's rubric files cover.
