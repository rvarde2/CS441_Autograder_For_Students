# CS441 ScholarChain autograder

This repository holds the autograder used to grade the ScholarChain project. The instructor runs it on each
submitted repository, at its submitted tag. The versions below are the ones used for grading, and you can run
the same code on your own repository to see exactly what the grader sees.

**How points are given and taken: [`RUBRIC.md`](RUBRIC.md).** A step-by-step guide is in
[`ScholarChain_Autograder_Student_Guide.pdf`](ScholarChain_Autograder_Student_Guide.pdf).

## How your project is graded

1. Your private repository is cloned at the **submitted tag**, and the commit is recorded.
2. **V1** runs deterministic checks of structure and process: the agent control plane, phase evidence compared
   with git history, secrets, copied tutorial files, tests, required files. It never runs your code.
3. **V2** (datasets, Hadoop, Spark) and **V3** (agentic factory) use an AI judge (Claude Code) that only reads your
   repository. Every verdict must cite your files with exact lines, and code checks every citation.
4. **Scoring** ([`RUBRIC.md`](RUBRIC.md)) turns the results into **points gained**, **points deducted** and a
   **score**, per phase and overall, with a reason on every row.
5. The instructor reviews every row the autograder marks for a human (undecided verdicts, flagged verdicts,
   possible secrets) before any points are final, and grades the parts the autograder does not cover.

The autograder scores **9.0 of the 20 points** (agentic factory 3.0, dataset engineering 1.0, Hadoop MapReduce
2.0, Spark analytics 3.0) and the deductions listed in `RUBRIC.md`. The other **11.0 points** and the other
deductions of the assignment README are graded by the instructor.

## What each folder does

| Folder | Version | Checks | How |
|---|---|---|---|
| [`V1/`](V1/) | 1.0.8 | Structure and process of the whole project (about 60 checks) | Deterministic: reads files and git history, never runs anything. [`V1/README.md`](V1/README.md) lists every check; [`V1/DESIGN.md`](V1/DESIGN.md) explains how each one decides. |
| [`V2/`](V2/) | 2.3.5 | Dataset engineering, Hadoop MapReduce, Spark analytics | AI judge, item by item ([`V2/RUBRIC.md`](V2/RUBRIC.md): what each item requires). |
| [`V3/`](V3/) | 3.0.5 | Agentic factory and agent reproducibility | Same AI judge, plus V1's facts about your factory ([`V3/RUBRIC.md`](V3/RUBRIC.md)). |
| [`V4/`](V4/) | 4.0.0 | Your score | Combines your latest V1/V2/V3 results with the grading weights: points gained, deducted and score per phase, with reasons ([`V4/README.md`](V4/README.md)). No AI, no cost. |
| [`RUBRIC.md`](RUBRIC.md) | scoring 4.0.0 | Weights and deductions | How verdicts and checks become points (what V4 uses). |

Every check and every category applies whatever phase your repository has reached, the same as in grading.

## Safety

Nothing in your repository is executed. Your `CLAUDE.md`, hooks, settings and MCP servers are not loaded
(`--restricted --strict-mcp-config`), and the AI can only read files inside your repository (Read, Glob, Grep).
Text in your repository that addresses the grader is reported, never obeyed.

## Running it yourself (optional)

You don't need to run anything or send anything. If you want to see what the grader sees:

```bash
git clone https://github.com/rvarde2/CS441_Autograder_For_Students.git
cd CS441_Autograder_For_Students/V1
./selfcheck.sh --student <your NetID> ~/path/to/your-scholarchain-repo       # free, no AI

cd ../V2 && ./judge.sh --student <your NetID> ~/path/to/your-repo --dry-run  # free preview
cd ../V2 && ./judge.sh --student <your NetID> ~/path/to/your-repo            # uses YOUR Claude Code usage
cd ../V3 && ./judge.sh --student <your NetID> ~/path/to/your-repo            # uses YOUR Claude Code usage
cd ../V4 && ./score.sh --student <your NetID>                                  # your score: free, no AI
```

Only committed files are checked, so commit before running. V4 scores your latest V1, V2 and V3 runs, so run
all three on the same commit first. Results stay on your computer. Step-by-step
instructions: [`V1/HOW_TO_RUN.md`](V1/HOW_TO_RUN.md) and [`V2/HOW_TO_RUN.md`](V2/HOW_TO_RUN.md). A run of your
own can differ slightly from the grading run: the AI judge can vary between runs, and the grading run is made on
your submitted tag.

The READMEs inside `V1/`, `V2/` and `V3/` were written when these folders were self-check tools, so they call
results "advisory" and mention sharing CSV files. For grading, this page and [`RUBRIC.md`](RUBRIC.md) apply, and
nothing needs to be shared.
