# CS441 ScholarChain self-check

An **advisory** checker you run on **your own project repository** (your implementation of the
ScholarChain assignment, not the assignment repository). It is not your grade.

| Folder | Version | Status |
|---|---|---|
| [`V1/`](V1/) | 1.0.5 | current (what's new: [`V1/README.md`](V1/README.md#whats-new-in-105): every check applies at every phase; 1.0.4: fewer false FAILs, from your feedback) |
| [`V2/`](V2/) | 2.3.2 | (2.3.2: every category is judged at every phase; includes V1 1.0.5; judge unchanged). AI judge per rubric category (advisory; uses **your** Claude Code usage). Start with [`V2/HOW_TO_RUN.md`](V2/HOW_TO_RUN.md), then [`V2/README.md`](V2/README.md); what is judged: [`V2/RUBRIC.md`](V2/RUBRIC.md). Categories so far: dataset engineering, Hadoop MapReduce, Spark analytics. |
| [`V3/`](V3/) | 3.0.2 | experimental (3.0.2: includes V1 1.0.5; judge unchanged): AI judge for the agentic factory (3.0 pts; advisory; uses your Claude or Antigravity usage). See [`V3/README.md`](V3/README.md) and [`V3/RUBRIC.md`](V3/RUBRIC.md). |

## What each version does

| Version | What it checks | How | Cost | Run |
|---|---|---|---|---|
| **V1** | Structure and process of the whole project: control-plane files, agent frontmatter and tool fences, hooks, ownership map, phase reports vs git, secrets, copied tutorial files, tests, required paths | Deterministic static checks (no AI); reads files and git history, never runs your code | Free | `V1/selfcheck.sh` |
| **V2** | Content of three rubric categories: dataset engineering (1.0 pt, from phase 3), Hadoop MapReduce (2.0, phase 4), Spark analytics (3.0, phase 6) | AI judge (Claude Code with Sonnet by default, or Antigravity); every verdict cites your files and is checked by code | Your AI usage, about $0.30-0.50 per full run with Sonnet | `V2/judge.sh` |
| **V3** (experimental) | Content of the agentic factory category (3.0 pts): control model, agent files, separation of duties, ownership map, hooks, MCP and commands, phase records, repairs and ratification, agent catalog, reproduction instructions | Same AI judge as V2, plus V1's factory facts | Your AI usage, about $0.30-0.40 per run with Sonnet | `V3/judge.sh` |

Recommended order: V1 first (free, catches structural problems), then V2 and V3. Every check and every
category is applied whatever phase you have reached, exactly as in final grading (use V2's `--category`
to judge only some categories). All three are advisory: your grade comes from the instructor's own runs on your submitted repository.

**Start here:** [`V1/HOW_TO_RUN.md`](V1/HOW_TO_RUN.md) (step by step), then [`V1/README.md`](V1/README.md)
(what every check means) and [`V1/DESIGN.md`](V1/DESIGN.md) (how each check decides).

```bash
git clone https://github.com/rvarde2/CS441_Autograder_For_Students.git
cd CS441_Autograder_For_Students/V1
./selfcheck.sh --student <your NetID> ~/path/to/your-scholarchain-repo
```

Results are saved in `V1/selfcheck-results/`. **Share only the `.csv` file** when your instructor
asks; keep the `.json` on your computer.

V1 and V2 complement each other: V1 checks structure and process (free, no AI); V2 judges content with
Claude. Run V1 first.

New versions are added as new folders (`V2/`, ...); `git pull` gets them. Older versions stay
unchanged, so earlier results can always be traced to the code that produced them.
