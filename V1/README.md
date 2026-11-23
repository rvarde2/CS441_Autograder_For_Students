# ScholarChain self-check

An **advisory** checker for **your own project repository** (your implementation of the
ScholarChain assignment, not the assignment repository). Run it as often as you like while you
work. **It is not your grade.** It checks facts that a script can verify (files, git history,
phase evidence, secrets, copying), so you find problems early, not at submission time.

## Quick start

First time? Follow **`HOW_TO_RUN.md`**: requirements (incl. Windows), example output, what to do
about a FAIL, and fixes for common errors.

From the folder that contains this README (e.g. `CS441_Autograder_For_Students/V1/`):

```bash
./selfcheck.sh --student <your NetID> ~/path/to/your-scholarchain-repo
```

Keep this folder **outside** your ScholarChain repository. Your repository can have any name
and live anywhere; point the command at its **root** folder (where `.git` and `.claude/` are).
If you point it at a subfolder or at a folder above your repository, it tells you which folder
to use instead (exit code 2, nothing saved).

Needs Python 3.8+ and git. Nothing to install. Runs offline (except the optional AI step below).
Results are printed and saved in `./selfcheck-results/` (always outside your repository):
- `selfcheck-<NetID>.csv`: one row per check (opens in Excel / Google Sheets). **This is the file
  to share** when your instructor asks for results.
- `selfcheck-results.json`: the same results plus an index of where your files are, for tools.
  **Keep it on your computer; don't send it.** Only the CSV is ever shared.

## What's new in 1.0.7

- **E03/E04, a phase's commits:** work committed as "wip" or "fix tests" between two gates now belongs to
  the phase: everything after the previous phase's accepted commit (its `commit.txt`) up to this phase's.
- **E03 is a FAIL only when no commit supports a claim.** A file changed by another phase's commits, or a
  gitignored local file that was never committed, is a **warn** (a human checks the phase record). A claimed
  evidence file under `docs/agent-runs/` is compared like any other (it always failed before).
- **E01:** a legend table (`| Status | Meaning |`) or a note like `Status: copied from the agent` before the
  real `STATUS:` line no longer hides it.

## What's new in 1.0.6

From more of your notes (thank you):

- **P01:** an agent report is found under any name containing its parts (`phase-10-agent-report.md`), in a
  subfolder (`reports/`, `repair-01/`), or by its content (STATUS, OWNER and most of the 14 fields).
- **P01/G03, combined or skipped phases:** a phase with no evidence of its own is still a FAIL (the assignment
  asks for a folder per phase), but the message no longer assumes the work wasn't done: if you combined
  phases, a human checks the other phase's record. Leave a short note in the empty folder; it is pointed out.
- **G02:** numbers next to the hash in `commit.txt` (run IDs, dates) are no longer read as missing commits.
- **G03:** `feat(phase-03): ...`, `[phase-03] ...`, `chore: phase-03 ...` and sub-phases (`phase-10b`) are recognised.
- **O01:** `orchestrator` (the main session) and the human need no agent file.
- **C03:** a hook that searches for or blocks "TaskForge" leftovers no longer counts as a leftover.
- **E05:** `.gitkeep` placeholders and test-agent files inside another agent's phase are no longer reported.
- **V2/V3 pre-scan:** a result like "checks passed 10/10" is no longer flagged as an attempt to set marks.

## What's new in 1.0.5

- **Every check applies, whatever phase you have reached.** There is no `later` any more: a check for
  work you haven't done yet shows FAIL or warn, like any other. This is the same result the final grading
  run will give for the same commit, so nothing changes between what you see and what is graded. The
  `due_phase` column says which phase's work order a check belongs to, so you can tell "phase-17 work not
  done yet" from a problem in work you have done.
- **P01:** missing evidence files (prompt, report, gate, commit record) are a FAIL in every phase, including
  your highest one (it was a warn, "in progress?").

## What's new in 1.0.4

After the first round of student feedback (thank you, especially for the notes on why a result was wrong).
Fewer false FAILs; nothing that was really wrong is accepted now.

- **F05 (hooks):** hooks written with the whole path in quotes, `"$CLAUDE_PROJECT_DIR/.claude/hooks/x.sh"`,
  are found (they were reported as missing, with a stray `"` at the end of the path).
- **F07 (.mcp.json):** `"Authorization": "Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}"` counts as an environment-variable
  reference (GitHub's server needs the `Bearer ` prefix). A literal value still FAILs.
- **K01/K02 (secrets):** placeholder values are no longer findings: AWS's documentation example key
  (`AKIAIOSFODNN7EXAMPLE`), values containing EXAMPLE/FAKE/TEST/DUMMY, sequences like `ABCDEFGHIJ`, and a
  `BEGIN PRIVATE KEY` header with no key after it (they are counted in one line). A realistic-looking value in a
  test or fixture file or in `docs/agent-runs/` is a **warn** ("confirm it's not a real key"); anywhere else it
  is still a FAIL.
- **E01 (report fields):** labels with a note in brackets (`FILES CREATED (all under modules/):`) and an
  ALL-CAPS label alone on its line (`FILES MODIFIED`) are recognised.
- **E03 (claimed files):** files listed as an indented tree (`modules/` then `  storage/README.md`) are matched
  to the real path, instead of "this path never existed".
- **E06 (human gate):** `human-gate.md` is read first; other `gate*` files (e.g. `gate-summary.md`) only when there
  is no human gate. A gate that mentions other commits but not the one in `commit.txt` is now a **warn** (it was a
  FAIL): please still write the accepted hash in the gate, as the assignment asks.
- **R03 (guard):** deny patterns written as regular expressions (`\baws\b\s+emr\s+terminate`) are read correctly.
- **R07 (MCP servers):** AWS's managed MCP server (`aws-mcp`) counts as the AWS API server.
- **O02/O03 (ownership):** other tables in `docs/agents.md` (escalation, "run by", review gates) and **bold**
  situation names are no longer read as owners.
- **V01 (hard-coded values):** public dataset buckets (`s3://openalex`, `s3://arxiv`), ARNs built from parts, and
  placeholder account IDs (`000000000000`) are no longer flagged.
- **Tip:** only committed files are checked. Commit your work before running, or the results describe your last
  commit, not your working folder.

If you ran 1.0.3: `git pull` and run again.

## What's new in 1.0.3

- **T01 (25 meaningful tests) now counts JUnit tests.** Java (or Scala) tests written with `@Test`,
  `@ParameterizedTest`, `@RepeatedTest` or `@TestFactory` were not counted before, so projects with
  Java tests could get a wrong FAIL. A test that only asserts non-null (`assertNotNull`) or
  `assertTrue(true)` still counts as trivial. Nothing changes for Scala munit/ScalaTest or Python tests.

## What's new in 1.0.2

- **A01 (Spark `collect`) gives fewer false warnings.** It no longer flags `collect_set` /
  `collect_list` (Spark's distributed aggregate functions) or `.collect { case ... }` /
  `.collect(partialFunction)` (Scala's filter-and-map, or RDD's distributed transformation).
  Real `.collect()`, `.collectAsMap()`, `.collectAsList()`, `.toLocalIterator` and `.toPandas()`
  are still reported.

## What's new in 1.0.1

After the first student feedback (thank you):

- **Evidence written in other styles is accepted**: several reports per phase (`agent-report-01.md`,
  `agent-report-02.md`), folder names like `phase_03`, report fields as `**Bold:**` labels,
  `## Headings` or a table, and common synonyms. A style the checker doesn't recognise is now a
  `warn`, not a FAIL.
- **Fewer false alarms**: hooks written as `"$CLAUDE_PROJECT_DIR"/...` are found; strict mode set in a
  sourced `scripts/lib/...` library counts; guard patterns split across lines are read; S3 paths built
  from variables (`s"s3://$bucket"`) are not "hard-coded"; prose in reports (`.collect()`, `Spark/Hadoop`)
  is no longer taken for file names.
- **Now warnings instead of FAILs**: a committed `.tfvars` (make sure it holds no secrets), an
  ownership table the checker can't read, a human gate that doesn't repeat the hash when `commit.txt`
  has it, and missing gate/commit files in the phase you're still working on.
- **New**: a warning when commits are labelled for a phase that has no `docs/agent-runs` folder.
- **Share only the CSV.** The JSON now also lists where your files are, for tools: keep it local.

If you ran 1.0.0: `git pull` and run again.

## Reading the result

| Label | Meaning |
|---|---|
| `ok` | the check ran and passed |
| `FAIL` | something required is missing or wrong; the lines below say what and where |
| `warn` | something a human should look at (it may be fine, e.g. an overlap you documented) |
| `info` | recorded, not judged |

**Every check applies to every repository**, whatever phase you have reached. Your phase (your highest
`docs/agent-runs/phase-NN/` folder) is shown for information, and each check's `due_phase` (in the CSV and
the table below) says which phase's work order introduces it.

The exit code is 1 if any check FAILs, otherwise 0.

## Phase evidence: what the checker expects

- One folder per phase: `docs/agent-runs/phase-00/`, `phase-01/`, ... with `prompt.md`,
  `agent-report.md`, `human-gate.md`, `commit.txt` (and `repair-NN.md`, review/test reports when used).
- Commit messages start with the phase: `phase-06 spark-engineer: add graph analytics`.
- **Several commits per phase are fine**, as are repairs and small late fixes committed after a
  later phase: a phase's work is every commit whose message starts with its `phase-NN`, plus the
  commit in its `commit.txt`.
- `agent-report.md` uses the field labels from the assignment (`STATUS:`, `OWNER:`,
  `FILES CREATED:`, `FILES MODIFIED:`, `COMMANDS RUN:`, ...). Files you list there are compared
  with what that phase's commits actually changed.
- `human-gate.md` states the decision (accepted/rejected) and the accepted commit hash, the same
  one as in `commit.txt`.
- Name and style variants are fine: `agent-report-01.md` (several reports per phase), `phase_03/`,
  `## Files Created` headings, **bold** labels, a table of fields, a GitHub commit URL in the gate.
  If the checker doesn't recognise your style you get a `warn`, not a FAIL (DESIGN.md section 8.7).

## Following the tutorial vs copying it

You are told to follow AgenticScalaAppTutorial, and keeping a generic file (e.g. a formatter hook)
is fine: that's a `warn`. A control plane that is **mostly** the tutorial's, renamed or not, or that
still mentions TaskForge, FAILs: the assignment gives a renamed tutorial fork zero.

## What this does NOT check

- Anything that runs: `sbt check`, your tests, Hadoop/Spark jobs, Terraform, AWS, the API.
- Whether your hooks actually *block* commands (it reads them; it doesn't run them).
- The quality of your agents, code, analytics, evaluation or report.
- Most of the 20 points: a clean result here does not mean a good grade.

## Safety and privacy

- It only reads your repository. It never runs your code, hooks or scripts.
- Git is called with your repository's own command settings switched off (`core.fsmonitor`,
  diff/textconv drivers), so a repo's git config can't make it run commands.
- Secrets are reported by type, file and line, never by value.
- The saved JSON/CSV contain check results and your repo's folder name, not your code.
- `X` rows are **observations**: they never pass or fail you. They record names, counts and yes/no
  (e.g. which manifest field names you used, which named scripts exist) so the next version can be
  built from what students actually do. Never file contents, manifest values or report text.
- Only files tracked by git are read: what you'll submit anyway.

## Optional: `--ai-ownership`

```bash
./selfcheck.sh --ai-ownership ~/path/to/your-repo
```

The built-in parser reads the ownership table in `docs/agents.md` but misses writers named in
prose or extra columns. With this option, Claude Code reads your ownership statements instead, and
the checker verifies every line it cites. **It uses your own Claude usage and sends repository
content to Anthropic under your account**, so it is off by default and asks before running. It
runs read-only: your `CLAUDE.md`, hooks, settings and MCP servers are not loaded.

## Feedback

If a result looks wrong, send your `selfcheck-<NetID>.csv` the way your instructor asks, with a
short note on why. Please don't send your code or prompts. The CSV holds check IDs, statuses,
and the file names/lines each problem was found at, not your files' contents.

## Every check

Every check applies to every repository; the last column is the phase whose work order introduces it.

| ID | What it checks | Work order phase |
|---|---|---|
| A01 | Spark code doesn't collect data to one machine (.collect, .toLocalIterator, ...) | 6 |
| H01 | Hadoop MapReduce is used (classes extending Mapper and Reducer) | 4 |
| U01 | Scripts under scripts/ use bash strict mode (set -euo pipefail) | 13 |
| V01 | No hard-coded buckets, ARNs, endpoints, account IDs or model IDs in source code | 4 |
| S01 | No symlinks pointing outside the repo | 0 |
| P01 | Phase evidence folders docs/agent-runs/phase-NN/ | 0 |
| G01 | Submission is a git repository with history | 0 |
| G02 | Each phase's commit.txt names a commit that exists | 0 |
| G03 | Commit messages identify the phase (e.g. 'phase-06 spark-engineer: ...') | 0 |
| K01 | No secrets in the current files (tracked by git) | 0 |
| K02 | No secrets anywhere in git history (deleted secrets are still leaked) | 0 |
| K03 | No .env, Terraform state or key files committed (tfvars: review) | 0 |
| K04 | A .gitignore is present (Git logistics: 'Include a complete .gitignore') | 2 |
| E01 | Agent reports have every required field and a valid STATUS | 0 |
| E02 | Each report's OWNER is an existing agent | 0 |
| E03 | Files a report claims were really changed by that phase's commits | 0 |
| E04 | Files the phase changed but its report doesn't list (undisclosed manual edits?) | 0 |
| E05 | Files changed in a phase belong to its OWNER (one writer, in practice) | 0 |
| E06 | human-gate.md states a decision and the accepted commit, matching commit.txt | 0 |
| E07 | Commits per phase (several commits, repairs and late fixes are allowed) | 0 |
| C01 | Files copied from the tutorial (>= 80% of their lines; one generic file is fine) | 0 |
| C02 | Agent control plane is written for ScholarChain, not mostly copied from the tutorial | 0 |
| C03 | No TaskForge leftovers in the control plane or code (README attribution is fine) | 0 |
| F01 | Control-plane files present (CLAUDE.md, docs/agents.md, settings, .mcp.json, agents, hooks) | 1 |
| F02 | Every agent has name, description and an EXPLICIT tools field (least privilege) | 0 |
| F03 | Reviewer agents have no write tools | 1 |
| F04 | Settings and MCP config are valid JSON | 1 |
| F05 | Hook scripts exist, are executable, and pass `bash -n` | 1 |
| F06 | Floor invariants present (deny rules + guard/test/format hooks) | 1 |
| F07 | .mcp.json: secret-looking settings use ${VAR} references, not literal values | 1 |
| O01 | Ownership map found and readable; every writer has an agent file | 1 |
| O02 | One writer per artifact (each overlap must have documented control; judge below) | 1 |
| O03 | Writers have write tools (ownership matches the tool fence) | 1 |
| O04 | Agents that write nothing (fine for reviewers/operators) | 1 |
| O05 | Ambiguities the AI flagged for a human | 1 |
| O06 | Writer names as written match an agent file (AI mappings are shown, not trusted) | 1 |
| R01 | Required hooks: guard-dangerous, format-scala, verify-tests-ran, validate-agent-files | 1 |
| R02 | Required commands: deploy, rollback, incident, run-pipeline, experiment | 1 |
| R03 | guard-dangerous.sh covers every destructive category ScholarChain names | 1 |
| R04 | settings.json has explicit allow AND deny rules, and PreToolUse, PostToolUse, Stop hooks | 1 |
| R05 | Commands route to agents that exist (deploy, incident, experiment are named by the README) | 1 |
| R06 | CLAUDE.md identifies ScholarChain and imports docs/agents.md | 1 |
| R07 | .mcp.json has GitHub, AWS API, Terraform and documentation servers (least privilege: judged later) | 1 |
| R08 | docs/agents.md covers ownership, routing, authority, escalation, human gates (keyword hint) | 1 |
| B01 | Build skeleton files: build.sbt, project/build.properties, project/plugins.sbt | 2 |
| M01 | datasets/dataset-manifest.yaml exists and has a readable datasets section | 3 |
| M02 | The manifest lists DBLP plus at least three additional datasets | 3 |
| M03 | datasets/scripts, datasets/samples, datasets/schemas exist and are not empty | 3 |
| M04 | The 20 Scala domain records named in Phase 3 are defined | 3 |
| W01 | Phase 17 documents exist at the paths the work order names | 17 |
| W02 | README.md has the subsection 'Reproducing the agentic workflow' | 17 |
| T01 | At least 25 meaningful automated tests | 11 |
| X01 | Observation: field names used in the dataset manifest | observation |
| X02 | Observation: scripts present (README: 'required scripts or equivalent commands') | observation |
| X03 | Observation: report items from each phase's work order found in its agent-report.md | observation |
| X04 | Observation: tutorial similarity of each control-plane file (to tune C01/C02 cut-offs) | observation |
| X05 | Observation: test counts (to tune T01) | observation |
| X06 | Observation: folder layout (folders to depth 2, tracked file counts) | observation |
| X07 | Observation: report label styles recognised (colon, bold, heading, table, bare label) | observation |
