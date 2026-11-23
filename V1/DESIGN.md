# CS441 ScholarChain Autograder: V1 design

Version 1.0.7. How the self-check works and exactly how each check decides, for students and
course staff. How to run it is in `HOW_TO_RUN.md`; what changed in each version is in `README.md`.
It checks a student's OWN project repository (their implementation of the ScholarChain
assignment), not the ScholarChain assignment repository.

## 1. Purpose and scope

V1 is an **advisory self-check**. Students run it on their own ScholarChain repository while they
work, to catch structural and process mistakes early. It is not the grade.

| In scope (V1) | Out of scope (V1) |
|---|---|
| Facts a script can verify by **reading** the repository: files, configuration, git history, phase evidence, secrets, copying | Running anything: `sbt`, tests, Hadoop/Spark, Terraform, AWS, the API |
| The agentic workflow evidence the README requires (`docs/agent-runs/phase-NN/`) | Judging quality: agent instructions, code, analytics, report |
| Phase 0-1 (the agent control plane) in depth; the exact files the README names for Phases 2, 3 and 17; tests (Phase 11) | the content of Phase 4-16 work (Hadoop, Spark, Neptune, RAG, Terraform, experiments) |
| Observations (X) that record what students do where the README is ambiguous | |
| Optional AI step that only **reads** (ownership map), with code verifying its output | AI grading of any rubric category |

What V1 covers of the 20-point rubric: much of the structural part of "Agentic factory and agent
reproducibility" (3 pts), plus several deductions (secrets, test count, phase commits, agent
reports claiming work that wasn't done, ownership overlaps, tutorial forks).

## 2. Design principles

1. **Read-only.** The checker never executes or modifies anything in the student's repository.
2. **Code checks facts; the AI only reads.** Everything in V1 is deterministic Python. The one
   optional AI step extracts data (who owns what) and code verifies every line it cites.
3. **Every check has a fixed ID and a quoted rule.** IDs (F01, E03, ...) never change meaning, so
   results compare across students, runs and versions. Each check's code comment names the
   ScholarChain README rule it enforces.
4. **PASS must mean something a copy can't fake.** File existence alone is passed by copying the
   tutorial, so V1 adds copy detection (C) and ScholarChain-only content checks (R), and compares
   phase reports with git history (E).
5. **Every check applies to every repository** (1.0.5). The phase whose work order introduces a check
   is recorded with it (`due_phase`), as information only. Until 1.0.4 checks from a later phase than the
   repo's showed as `later`; the same tool is used for final grading, where that would hide missing work.
6. **Proven against planted defects.** Every check has been shown to FAIL on a test repository
   built to break it, not only to PASS on a good one.

## 3. How a run works

```
selfcheck.sh <repo>                      checks Python/git, refuses --out inside the repo,
   |                                     optional AI step (asks first), then:
   v
checks.py  (python3 -I)                  launcher; isolated mode = no imports from the student's folder
   |
   v
autograder/main.py
   0. wrong_folder(repo)                 subfolder of a repo / folder above repos -> say which folder, exit 2
   1. Repo(root)                         safe read-only view of the repo; ALL file/git access goes through it (repo.py)
   2. run_all(repo)                      every @check_group, in phase order         (registry.py)
         checks/always.py         phase 0  S01 F02 P01 G01-03 K01-03 E01-07 C01-03
         checks/phase01_factory.py phase 1 F01 F03-07 O01-06 R01-08
         checks/phase02_build.py   phase 2 K04
         checks/phase04_hadoop.py  phase 4  H01
         checks/code_hygiene.py    phase 4  V01
         checks/phase06_spark.py   phase 6  A01
         checks/phase11_tests.py   phase 11 T01 (+ X05)
         checks/phase13_automation.py phase 13 U01
         checks/requirements.py    per row  B01 M01-M04 W01 W02   (the requirements TABLE, data/phase_requirements.json)
         checks/observations.py    info     X01-X03 X06           (+ X04 in always.py): record, never judge
   3. write JSON and CSV, print, exit 0/1
```

## 4. Code layout

```
V1/
├── selfcheck.sh            student entry point (options, safety of --out, optional AI step)
├── checks.py               Python launcher (adds its own folder to the path; -I keeps the student's out)
├── extract_ownership.sh    optional AI step: Claude Code reads the ownership map (read-only flags)
├── ownership.schema.json   the JSON shape the AI must return
├── autograder/
│   ├── __init__.py         VERSION
│   ├── main.py             runner, output, exit code
│   ├── registry.py         @check_group(phase=N), Results, run_all
│   ├── repo.py             ALL access to the student's repo: safe reads, hardened git, parsed config
│   ├── ownership.py        ownership rows (AI or table parser), citation verification, path patterns
│   ├── fingerprints.py     line normalization for copy detection
│   ├── checks/
│   │   ├── __init__.py     imports every check module (this registers them)
│   │   ├── always.py       phase 0
│   │   ├── phase01_factory.py
│   │   ├── phase02_build.py
│   │   ├── phase04_hadoop.py    H01
│   │   ├── code_hygiene.py      V01
│   │   ├── phase06_spark.py     A01
│   │   ├── phase11_tests.py
│   │   ├── phase13_automation.py U01
│   │   ├── requirements.py      the table module: generic code for each KIND of requirement
│   │   └── observations.py      X-checks: record what students do where the README is ambiguous
│   ├── manifest.py         safe reader for datasets/dataset-manifest.yaml (structure only)
│   ├── sources.py          non-comment lines of tracked source files (for H01, A01, V01)
│   ├── evidence.py         TOLERANT reading of phase evidence: file-name variants, label styles, claimed paths
│   └── data/
│       ├── tutorial_fingerprints.json   line hashes of the tutorial, pinned commit
│       ├── phase_requirements.json      the requirements table: one row per check, each quoting the README
│       └── evidence_formats.json        accepted evidence file names, report label synonyms, STATUS values
├── README.md, DESIGN.md, VERSION
```

Rules that keep it maintainable:
- **Only `repo.py` touches the repository.** Checks call `repo.read()`, `repo.is_file()`,
  `repo.glob()`, `repo.git()`, `repo.bash_syntax_error()`, `repo.agents`, ... and never open,
  list, stat or run anything themselves, so the safety rules live in one place.
- **Simple requirements are data, not code**: a row in `data/phase_requirements.json`.
- **A check group declares its phase where it's defined** (`@check_group(phase=1)`), not in a
  separate table that can drift.
- **Shared parsed data is computed once** (`cached_property`): agents, settings, phases, ownership.

## 5. Phases: information, not relaxation

**Current phase** = the highest `docs/agent-runs/phase-NN/` folder. It is printed and recorded, and
nothing depends on it: every check applies to every repository, at every phase (1.0.5). The table
says which phase's work order introduces each check (`due_phase` in the JSON/CSV), so a student at
phase 9 can see that a FAIL of W02 is phase-17 work not done yet.

| Work order phase | Checks | Why this phase (ScholarChain phase list) |
|---|---|---|
| 0 | S01, F02, P01, G01-G03, K01-K03, E01-E07, C01-C03 | evidence, git, secrets and copying apply from the first commit; Phase 0 creates the seed agent (F02) |
| 1 | F01, F03-F07, O01-O06, R01-R08 | Phase 1: "the factory builds the ScholarChain factory" |
| 2 | K04, B01 | Phase 2: build and repository skeleton (Phase 0 says "create exactly one file") |
| 3 | M01-M04 | Phase 3: contracts, configuration, dataset manifests |
| 4 | H01, V01 | Phase 4: Hadoop MapReduce (and module code starts) |
| 6 | A01 | Phase 6: Spark analytics |
| 11 | T01 | Phase 11: adversarial testing and full repository review |
| 13 | U01 | Phase 13: reproducible automation |
| 17 | W01, W02 | Phase 17: documentation, final review, release |
| — | X01-X06 | observations: always `info`, never pass or fail |

Until 1.0.4 a check from a later phase than the repo's was shown as `LATER` (neither pass nor fail),
and P01 accepted missing files in the highest phase as "in progress". Both are gone: the advisory
runs and the final grading run give the same result for the same commit.

## 6. Results

| Status | Meaning | Affects exit code |
|---|---|---|
| PASS (`ok`) | the fact holds | no |
| FAIL | it doesn't; details say what and where | **yes** |
| WARN | needs human judgement (e.g. an overlap that may be documented) | no |
| INFO | recorded, not judged | no |

Exit code: 1 if any FAIL, else 0. 2 = usage/setup error, including the wrong folder: the student's
repository can have any name and location (the ScholarChain repo is only the assignment; each
student builds their own private repo, README D01 and line 852 "a clean repository"), but the
checker needs its ROOT. A subfolder of a git repository, or a folder with repositories one or two
levels below it, gets a message naming the folder to use instead of a wall of FAILs.

JSON (`--json`, saved by `selfcheck.sh` to `selfcheck-results/selfcheck-results.json`):
```json
{ "student": "ab123", "version": "1.0.1", "run_date": "2026-11-17", "repo": "<folder name only>",
  "current_phase": 2, "ownership_source": "...",
  "index": { "index_version": 1, "commit": "<full hash>", "phases": {...}, "spark": {...}, ... },
  "results": [
    { "id": "E03", "title": "...", "status": "FAIL", "details": ["..."], "due_phase": 0 },
    { "id": "X01", "title": "...", "status": "INFO", "details": ["..."], "due_phase": 0, "data": {...} } ] }
```
The repo is recorded by folder name only: a full path would contain the student's username.

**File index** (`"index"` in the JSON only, never in the CSV): what each check found, as repo-relative
paths grouped by topic: `phases` (each phase's evidence files, commits, files changed, files claimed,
owners), `control_plane`, `ownership`, `datasets`, `domain_records` (name -> file:line), `build`,
`hadoop`, `spark`, `tests`, `scripts`, `hardcoded_values`, `docs`, `copied_from_tutorial`, and
`areas` (terraform, docs, reports, experiments, evaluation, incidents, modules). It records the
`commit` it describes and is valid only for that commit. It lets a later grading step find the
files for one rubric category without searching. Students share only the CSV; the JSON (and
therefore the index) stays on their machine.

CSV (`--csv`, saved by `selfcheck.sh` as `selfcheck-<student>.csv`): one row per check, columns
`student, repo, version, current_phase, check_id, title, status, due_phase, details` (detail lines
joined by ` | `). Student/run columns repeat on every row so the file filters and merges easily.
`--student` accepts letters, digits, `.`, `_`, `-` only.

**Formula injection.** Cell text can come from the student's repository (file names, agent names,
report text), and spreadsheets execute a cell starting with `=`, `+`, `-`, `@` (or tab/CR) as a
formula. Every cell that starts with one of those is written with a leading `'` (`safe_cell`). Tested with `=cmd|...`, `+1+1`, `-2+3`, `@SUM`, tab.

**Sharing results.** The CSV is for feedback: it shows the course staff where students struggle
and where the checker may be wrong. It is not a submission. Grades come from the staff running the
checker (and more) on your submitted repository, so editing a CSV changes nothing.

## 7. Check catalogue

Levels: F = FAIL when broken, W = WARN, I = INFO. "Source" quotes or names the ScholarChain README rule.

### Phase 0 (always)

| ID | Lvl | Checks | Source | How |
|---|---|---|---|---|
| S01 | F | no symlink points outside the repo | safety | resolve every symlink |
| F02 | F | every agent file has `name`, `description`, explicit `tools` | Phase 0: "Require least privilege and explicit tools fields" | parse frontmatter |
| P01 | F/W | phase folders (`phase-03`, `phase_03`, `Phase-3`), none skipped, each with a prompt, agent report(s), human gate and commit record under any accepted name (a folder with none of them, or no folder, is reported neutrally: missing, skipped or combined with another phase is for a human to decide; other files left in the folder are listed); commits labelled phase-NN without a folder = W | "Agent-generated deliverable evidence" | section 8.7 |
| G01 | F | git repository with history | Git logistics | `git log` |
| G02 | F | each commit.txt names a commit that exists (a digits-only token, e.g. a run ID, counts only if it is a commit) | evidence | `git cat-file -e` |
| G03 | F | each phase has a commit whose message starts with `phase-NN`, also after a type or bracket (`feat(phase-06):`, `[phase-06]`, `chore: phase-06`); sub-phases (`phase-10b`) count for their phase | "commit messages that identify the phase" | message prefix (prose mentions don't count) |
| K01 | F/W | no keys/tokens in current tracked files (AWS, GitHub, Anthropic, OpenAI, Slack, private keys); placeholders ignored; a realistic value in a test/fixture file or `docs/agent-runs/` is W; `password='...'` is W | "Secrets committed: up to 4 points lost" | section 8.4; values never printed |
| K02 | F/W | none in any commit on any branch (same placeholder and test-file rules as K01) | same | every added line in `git log -p --all` |
| K03 | F/W | no `.env`, `.tfstate` or key files tracked (F); a `.tfvars` file is W (check it holds no secrets) | Git logistics: "Terraform state containing sensitive values" | tracked file names |
| E01 | F/W | the phase's report(s) have all 14 required fields; STATUS ∈ COMPLETE/BLOCKED-ON/FAILED (any STATUS line; a table's header row is never a field). F when most labels are recognised but some are missing, or the report is essentially empty; W when few labels are recognised (probably an unknown style) | "Required agent report fields" | section 8.7 |
| E02 | F | OWNER is an existing agent | ownership | agent files |
| E03 | F/W | every file in FILES CREATED/MODIFIED was changed by one of the phase's commits (a partial path from a file tree is matched to the one real path ending with it). F: no commit supports the claim; W: changed only by another phase's commits, or gitignored and never committed | "Agent reports claim commands or tests that were not actually run" | section 8.1 |
| E04 | W | files the phase changed but the report doesn't list | manual edits "must be disclosed" | section 8.1 |
| E05 | W | files changed in the phase are owned by OWNER (`.gitkeep` placeholders and files owned by a test agent are not counted: the README's phase sequence invokes test agents inside a phase) | one writer per artifact | ownership patterns |
| E06 | F/W | the gate (`human-gate*` first; other `gate*` files only if there is none) names the same commit as commit.txt (other commits but not that one = W; no hash but commit.txt valid = W; neither names a commit = F) and states a decision (accept/approve/ratify/reject/decline; none = W) | human-gate contents | hash cross-check |
| E07 | I | commits per phase, repair records, late fixes | — | — |
| C01 | W | files ≥ 80% copied from the tutorial | — | section 8.2 |
| C02 | F | > 50% of control-plane files copied | "tutorial fork with TaskForge renamed: zero" | section 8.2 |
| C03 | F/W | "TaskForge" left in control plane or code (F) / other docs (W); a script line that searches for or blocks the name (`grep`, `=~`, deny, reject, leftover) is listed, not counted | same | text search |

### Phase 1 (the agent control plane)

| ID | Lvl | Checks | Source |
|---|---|---|---|
| F01 | F | CLAUDE.md, docs/agents.md, settings.json, .mcp.json, agents, hooks exist | "Required factory artifacts" |
| F03 | F/W | reviewer agents (name contains "review") have no Write/Edit; Bash = W | "Forbid reviewer agents from receiving write tools" |
| F04 | F | settings, settings.local, .mcp.json are valid JSON | "Require JSON parsing" |
| F05 | F/W | hooks referenced in settings exist, are executable (unless run via an interpreter), shell hooks pass `bash -n` (parse only); `"$CLAUDE_PROJECT_DIR"/…`, `"$CLAUDE_PROJECT_DIR/…"`, `${CLAUDE_PROJECT_DIR}/…`, `bash x.sh`, `python3 x.py` understood | "shell syntax checks, executable-bit checks" |
| F06 | F | deny rules: `.env` reads, terraform apply/destroy, force push, a destructive AWS command; hooks: PreToolUse(Bash) guard, Stop, PostToolUse(Edit/Write) | Phase 0 floor invariants |
| F07 | F | secret-looking `.mcp.json` env/headers use `${VAR}`, optionally after an auth scheme (`Bearer ${VAR}`) | ".mcp.json with secret values omitted" |
| O01 | F/W | every writer named in the ownership map has an agent file (F); AI citations verified; a table the parser can't read = W (suggests `--ai-ownership`); owners may be **bold** or plain agent names; tables about who runs, reviews or decides are not ownership; the orchestrator (main session) and the human need no agent file | authority matrix |
| O02 | W | artifacts with >1 writer, or a path inside another's (needs "documented control") | "overlapping write ownership without documented control" |
| O03 | W | agents said to write files have Write/Edit | ownership vs tool fence |
| O04 | I | agents that write nothing | — |
| O05 | I | ambiguities the AI flagged (AI step only) | — |
| O06 | F/W | writer names match agent files; AI mappings shown, not trusted | — |
| R01 | F | hooks guard-dangerous, format-scala, verify-tests-ran, validate-agent-files | "Required factory artifacts" |
| R02 | F | commands deploy, rollback, incident, run-pipeline, experiment | same |
| R03 | F | guard-dangerous.sh names all 8 categories (AWS, Terraform, Git, database, S3, Neptune, DynamoDB, vector index) on non-comment lines, or within 3 consecutive lines (patterns split across array entries); regex syntax (`\b`, `\s+`, `[[:space:]]`) is read as the words it stands for | "Blocks destructive AWS, Terraform, Git, database, S3, Neptune, DynamoDB, and vector-index commands" |
| R04 | F | settings.json: allow and deny rules; PreToolUse, PostToolUse, Stop hooks | same table |
| R05 | F/W | deploy→deploy-engineer, incident→incident-responder, experiment→experiment-engineer exist; scripts commands run exist (W) | same table |
| R06 | F | CLAUDE.md names ScholarChain/DBLP and has `@docs/agents.md` | "Project identity ... and import of docs/agents.md" |
| R07 | W | .mcp.json has GitHub, AWS API (aws-api or AWS's managed `aws-mcp`), Terraform, documentation servers; `@latest` flagged | ".mcp.json: Read-only or least-privilege ..." |
| R08 | W | docs/agents.md mentions ownership, routing, authority, escalation, human gates | docs/agents.md contents |

### Phase 2 and 11

| ID | Lvl | Checks | Source |
|---|---|---|---|
| K04 | F | `.gitignore` present | "Include a complete .gitignore" |
| T01 | F | ≥ 25 meaningful tests; a test with no assertion or only non-null/true assertions doesn't count | "Required test inventory" |

### Table checks (data/phase_requirements.json; README commit a139f4a)

| ID | Due | Lvl | Checks | README source |
|---|---|---|---|---|
| B01 | 2 | F/W | `build.sbt`, `project/build.properties`, `project/plugins.sbt` | Phase 2 work order |
| M01 | 3 | F/W | `datasets/dataset-manifest.yaml` exists, readable, has dataset entries | "Create datasets/dataset-manifest.yaml ..." |
| M02 | 3 | F | DBLP plus at least 3 other datasets in the manifest | Baseline submission |
| M03 | 3 | F/W | `datasets/scripts`, `samples`, `schemas` have files (a `.gitkeep` alone doesn't count) | Phase 3 work order |
| M04 | 3 | F | the 20 named Scala records are defined (a definition, not a comment) | "Create immutable Scala domain records for WorkRecord, ..." |
| W01 | 17 | F/W | README.md and the 8 documents at the paths Phase 17 names | Phase 17 work order |
| W02 | 17 | F | README has a heading "Reproducing the agentic workflow" | "a subsection named `Reproducing the agentic workflow`" |

### Code checks tied to large deductions

| ID | Due | Lvl | Checks | README deduction |
|---|---|---|---|---|
| H01 | 4 | F/W | classes extending Hadoop `Mapper` and `Reducer` exist (FAIL: no Hadoop MapReduce code at all; WARN: Hadoop used but no Mapper/Reducer, e.g. streaming) | "Hadoop requirement replaced by a local loop, Spark operation, or managed import: up to 3 points" |
| A01 | 6 | W | Spark code calling `.collect`, `.collectAsList`, `.collectAsMap`, `.toLocalIterator`, `.toPandas` (file:line; collecting a small summary is legitimate) | "Spark ... performed by collecting the graph to one process: up to 3 points" |
| V01 | 4 | W | literal S3 bucket names (`"s3://my-bucket/…"`; not `s"s3://$bucket"`, `startsWith("s3://")` or the public `s3://openalex`, `s3://arxiv`), complete literal ARNs (not a prefix built from parts), AWS endpoints, account IDs (not placeholders like `000000000000`), model IDs in production code (tests, config, docs excluded; value never printed) | "Hardcoded buckets, endpoints, account IDs, thresholds, or model IDs without configuration rationale: up to 1 point" |
| U01 | 13 | W | every `scripts/*.sh` sets -e, -u and pipefail (short or long form, anywhere in the file), itself or through a sourced library; libraries that other scripts source are exempt | Phase 13: "Bash strict mode or an equivalently strict scripting language configuration" |

These show that something EXISTS or APPEARS, with file and line. Whether the Hadoop job is right,
or a `collect()` is harmful, is for a human or the AI step. Comment lines never count.

### Observations (always `info`)

| ID | Records | Decides later |
|---|---|---|
| X01 | manifest field NAMES per dataset (never values) | which names to accept for the 17 prose fields |
| X02 | which of the 9 named scripts exist; other script names in `scripts/` | "required scripts or equivalent commands" |
| X03 | per phase report: which "Report ..." items appear (yes/no; all significant words present) | how strictly to match report wording |
| X04 | tutorial similarity of each control-plane file | the 80% / 50% copy cut-offs |
| X05 | test counts | the 25-test check |
| X06 | folders to depth 2 with file counts (no file names) | where students put modules (Phase 4-10 checks) |
| X07 | report label styles recognised (colon, bold, heading, table: counts) | which styles to support next |

## 8. Key mechanisms

### 8.1 A phase = the set of its commits (E-checks)

Phases are not one commit each in practice. A phase's commits are:
**every commit whose message starts with `phase-NN`** + **the commit(s) in `phase-NN/commit.txt`** +
(1.0.7) **every commit after the previous phase's accepted commit, up to this phase's accepted
commit** (git ancestry, from the commit.txt files; not for the first recorded phase, whose earlier
history is setup). So these are all fine: several commits per phase, unlabelled work commits ("wip",
"fix tests") before the recorded one, a labelled repair commit, a small fix to a phase-01 file committed
after phase-02 (E07 reports it as information). A phase without a commit record has its work counted
with the next recorded phase.

From that set: `touched` = all files those commits changed; for E04/E05 minus `docs/agent-runs/**`
(evidence, not work). Then:
- E03: each claimed path must be in `touched`, evidence included (a claimed folder covers files under
  it). FAIL when no commit supports it; WARN when another phase's commits changed it (the work exists:
  which phase it belongs to is for a human) or when it is gitignored and was never committed.
- E04: each touched file should be claimed.
- E05: each touched file should match an ownership pattern of OWNER (if it matches any pattern).

### 8.2 Copy detection

`data/tutorial_fingerprints.json` holds a hash of every normalized line of every tutorial file at a
pinned commit (`4372cf07b5de`); only hashes are shipped, not the tutorial's text. Normalization
(`fingerprints.py`): lowercase, collapse whitespace, map TaskForge/ScholarChain to `<project>`,
drop lines under 12 characters. So renaming the project doesn't hide a copy.

For every tracked file (not only the tutorial's paths, so moving a file doesn't hide it):
similarity = share of the file's normalized lines found in the closest tutorial file.
Thresholds: **copied ≥ 80%** (C01), **mostly copied > 50% of control-plane files** (C02).
Both are judgement calls (a tutorial settings.json extended with 5 rules scored 76%).

### 8.3 Ownership: two sources, one set of checks

Rows: one per (artifact path, writing agent). Sources:
- **Built-in parser** (default): the docs/agents.md table: paths in backticks (column 1), owners in
  bold or plain agent names (column 2). Misses writers in prose ("and implementer") or other columns ("Version bumps by").
  Tables whose second column is about running, invoking, escalating, deciding, reviewing or gating are
  skipped, and **bold words** in column 1 ("**Security change**") are not paths (1.0.4).
- **AI extraction** (`--ai-ownership`): Claude returns rows with `source_file`, `source_line`, an exact
  `quote`, and `name_as_written`. Code rejects a row unless the file exists, the line exists, and
  the quote and name are on that line (an agent's own file may omit its own name).
  `name_as_written` exists because the AI once silently "repaired" a wrong owner name.

Path patterns: `**` any depth, `*` one folder level, a plain folder = everything under it.

### 8.4 Secrets

Specific token shapes FAIL; generic `password = '...'` WARNs. Current files (K01) and every line ever
added on any branch (K02): a secret deleted later is still in history. Values are never printed.

Redaction and secret-scanning tests contain secret-SHAPED values on purpose, so the value is classified
first (1.0.4):

| Value | Where | Result |
|---|---|---|
| placeholder: contains EXAMPLE/FAKE/TEST/DUMMY/SAMPLE/XXXX, one repeated character, an alphabet or digit sequence (`ABCDEFGH`), or a `BEGIN PRIVATE KEY` header with no key body on the next line | anywhere | not a finding (counted in one line) |
| realistic | a test or fixture file, or `docs/agent-runs/` | WARN: confirm it's not a real key |
| realistic | anywhere else | FAIL |

### 8.5 Where files are looked for (table checks)

- **Exact path in the README** (e.g. `docs/runbook.md`): checked there. Missing there but a tracked
  file with the same name exists elsewhere: `warn`, naming where it was found. Missing everywhere: FAIL.
- **Names without a location** (the Phase 3 records): every tracked `.scala` file is searched for a
  definition (`case class`, `class`, `trait`, `object`, `enum`, `type`, with modifiers); commented-out
  lines don't count.
- **"Or equivalent"** (scripts): never judged; recorded as an observation (X02).
- **Scope: files tracked by git only**, i.e. what you submit. Untracked and ignored files (downloads,
  build output, `.env`) are never read.

### 8.6 The dataset manifest reader

The manifest is your YAML, and YAML anchors/aliases can make a parser expand a small file into
gigabytes. So: files over 200 KB aren't parsed; PyYAML `safe_load` is used only when installed and
the file has no anchors/aliases; otherwise a small built-in reader reads the `datasets:` block
(mapping or list form) without expanding anything. Both give the same result on both forms (tested).
Only dataset names and field names are kept; values are read only to recognise DBLP.

### 8.7 Phase evidence written in different styles (1.0.1)

Students and their agents write the same evidence differently, and V1 must not FAIL a valid style.
`evidence.py` + `data/evidence_formats.json` (edit the data, not the code, to add a variant):

- **Folders**: `phase-03`, `phase_03`, `phase03`, `Phase-3`.
- **File names**: compared after lowercasing and removing spaces, `-`, `_`: `agent-report.md`,
  `agent-report-01.md`, `Agent_Report_2.md`, `final-report.md`, `phase-10-agent-report.md` (name parts);
  the phase folder and one subfolder are searched (`reports/`, `repair-01/`). An agent report is also
  recognised by its CONTENT: STATUS, OWNER and at least 7 of the 14 fields, whatever its name
  (review and test reports excluded by name); `human-gate*`, `gate*` (for E06, `human-gate*`
  files are read first; other `gate*` files only if there is none);
  `commit.txt`, `commit-hash.txt`. All of a phase's reports are read together.
- **Field labels**: `FILES CREATED:`, `**Files created:**`, `## Files Created`, a table row
  `| Files created | ... |`, a note in brackets (`FILES CREATED (all under modules/):`), an ALL-CAPS
  label alone on its line (`FILES MODIFIED`), and synonyms ("Created files", "Commands executed", ...). A section
  ends at the next label or any heading, so one unknown label can't swallow the rest.
- **Claimed paths**: a token counts only if it's a path that exists in the repo now or in history,
  or is clearly file-shaped (`folder/name.ext`). Prose (`.collect()`, `Spark/Hadoop`) is ignored.
  Absolute paths are reduced to the part inside the repo, or skipped. A partial path from a file tree
  (`modules/` then `  storage/README.md`) is matched to the ONE real path that ends with it; with none or
  several, it stays as written (so a made-up file is still reported). **Only validated paths are
  ever printed**, never free text from your files.
- **Commit hashes**: plain, in backticks, or inside a GitHub `.../commit/<hash>` URL.
- **Severity**: a format the checker doesn't recognise is a `warn` about the checker, never a FAIL.
  FAIL stays for facts: a file missing under every accepted name, a claimed file never changed,
  a phase whose gate and commit.txt name no commit at all, an essentially empty report.

## 9. Safety model

The checker runs on repositories it doesn't trust (and later, the instructor will run it on all
submissions). Every threat below was demonstrated with a control run (the attack succeeding without the
defence) before the defence was trusted.

| Threat | Defence |
|---|---|
| Student code executed by the checker | nothing is run; `bash -n` only parses |
| `.git/config` makes git run commands (fsmonitor, textconv, pager, external diff) | every git call overrides them (`repo.py`); experiment 3: plain `git status` ran a planted command, the checker didn't |
| Symlink to files outside the repo | `repo.read()` refuses paths that resolve outside; S01 reports them |
| A file in the student's folder hijacking a Python import | `python3 -I` (isolated mode) |
| Results written into the submission | `selfcheck.sh` refuses `--out` inside the repo |
| AI step: student's CLAUDE.md, hooks, settings, MCP servers | `--restricted` + `--strict-mcp-config` + `--tools Read Glob`; experiments 1-2 showed hooks and MCP servers run without these flags and don't with them |
| AI step: instructions planted in repo files | system prompt treats repo as data; code verifies every citation; the AI never decides a status |
| Leaking the student's identity in shared results | JSON/CSV record the folder name only; no git authors, emails or absolute paths |
| The file index listing a student's whole project | it's in the JSON only, which stays on the student's machine; only the CSV is shared |
| Free text from a student's files appearing in output (e.g. a local home path in a report) | only validated repo paths, counts and labels are printed (section 8.7) |
| Observations exposing your work | names, counts and yes/no only: never file contents, manifest values, report text or headings, or file names in the layout |
| YAML expansion attack in the manifest | size limit; anchors/aliases force the non-expanding reader |

## 10. Optional AI step (`--ai-ownership`)

Off by default. `selfcheck.sh` states that it uses the student's Claude usage and sends repository
content to Anthropic under their account, then asks (or requires `--yes` in scripts).
`extract_ownership.sh` runs `claude -p` with `--restricted --strict-mcp-config --tools Read Glob`,
`--json-schema ownership.schema.json`, saves the trace next to the output, and passes the rows to
the checker with `--ownership`. Default model `claude-opus-5-5` (`--model` to change).

## 11. Known limitations

- **Static only.** R03 shows the guard *names* each category, not that it blocks. Behaviour tests
  need a sandbox that runs student hooks.
- **Thresholds** (80% / 50% copy, 25 tests) and **name conventions** (reviewers contain "review";
  munit/ScalaTest/pytest test syntax; ownership table layout) were tuned on the tutorial's style.
  Real student repos will show where they're wrong.
- **Phases 4-16: no correctness checks.** H01, A01, V01, U01 find code patterns tied to deductions
  (file:line), but can't tell whether the code is right. Thresholds aren't recognisable by pattern
  (V01 doesn't check them).
- **One owner per phase is not assumed**: an OWNER line may list several agents ("a, b").
- Opened ≠ understood: E03 shows a file changed, not that it's correct.
- Copy detection compares with the tutorial at commit `4372cf07b5de`.
