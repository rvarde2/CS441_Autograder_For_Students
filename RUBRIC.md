# ScholarChain grading: weights and deductions

How the autograder turns its results into points (scoring version 4.0.0, weights sha `0162d8174ce40d2a`). Generated from the scoring data, so it always matches what is used.

## How a score is reported

- **Points gained** and **points deducted** are two separate numbers, plus a **score** (gained minus deducted), per phase and overall.
- The autograder scores **9.0 of the 20 points** (the four categories below) and the deductions listed here. The other categories and deductions of the assignment README are graded by the instructor.
- Every row of a score sheet carries its reason: the judge's reason with the cited file and line, or the deterministic check's finding.
- A verdict the judge could not decide (`cannot_tell`) is never scored automatically: the instructor decides it.
- Exactly what each item requires (its met / partial / missing definitions): [`V2/RUBRIC.md`](V2/RUBRIC.md) for datasets, Hadoop and Spark, [`V3/RUBRIC.md`](V3/RUBRIC.md) for the agentic factory. What each deterministic check looks for: [`V1/README.md`](V1/README.md) and [`V1/DESIGN.md`](V1/DESIGN.md).

## Turning a verdict into points

| Verdict | Share of the item's points |
|---|---:|
| met | 1 |
| partial | 0.5 |
| missing | 0 |
| cannot_tell | decided by the instructor |

A deduction takes its README maximum times the severity the judge gives:

| Severity | Share of the maximum |
|---|---:|
| none | 0 |
| minor | 0.25 |
| partial | 0.5 |
| full | 1 |

Inside a category, items are weighted by importance (the category total is the README's):

| Weight | Meaning |
|---|---|
| Core (3) | what the README's full-credit sentence leads with, or what the rest of the category depends on |
| Standard (2) | the other things that sentence names |
| Minor (1) | work-order detail the sentence does not name |
| Zero (0) | a failure here is already a README deduction, so it is counted once, there |

## Agentic factory and agent reproducibility (3 points, judged by V3)

| Item | What | Weight | Points | Phase | Why |
|---|---|---|---:|---:|---|
| FACTORY-01 | Control model | Core | 0.47 | 01 | full credit leads with 'correct orchestrator and subagent model' |
| FACTORY-02 | Role files | Standard | 0.32 | 01 | role files: the subagent model's content |
| FACTORY-03 | Authority separation | Standard | 0.32 | 01 | authority separation (required roles). The reviewer/test-agent separation is judged in the deduction FACTORY-NO-INDEPENDENT-REVIEW, not here (each problem is counted in one place) |
| FACTORY-04 | Ownership map | Standard | 0.32 | 01 | full credit: 'one-writer ownership'. Uncontrolled overlap is judged in the deduction FACTORY-OVERLAP-UNCONTROLLED, not here |
| FACTORY-05 | Hooks enforce the floor (judged by reading the scripts; they are never run) | Core | 0.47 | 01 | full credit: 'hooks, permissions'; the safety floor every phase relies on |
| FACTORY-06 | MCP policy and commands | Standard | 0.32 | 01 | full credit: 'permissions' (MCP policy, commands) |
| FACTORY-07 | Phase records | Standard | 0.32 | 01 | full credit: 'reports, human gates' |
| FACTORY-08 | Repair loops and ratification | Standard | 0.32 | 01 | full credit: 'repair loops, human gates' (ratification) |
| FACTORY-09 | Agent catalog | Minor | 0.16 | 17 | agent catalog: README section 'Agent submission and reproducibility', not in the full-credit sentence |
| FACTORY-10 | Reproduction instructions | Zero | 0.00 | 17 | replay instructions missing/insufficient = the deduction FACTORY-REPLAY-INSUFFICIENT (up to 2): counted once, there |

| Deduction | README text | Up to | Applied | Why |
|---|---|---:|---|---|
| FACTORY-NO-INDEPENDENT-REVIEW | No independent reviewer or test-agent separation: up to 1.5 points lost. | 1.5 | yes | judged only here (FACTORY-03 does not score it) |
| FACTORY-AGENTS-NOT-SUBMITTED | Not all agents used by the project are submitted: up to 2 points lost. | 2 | yes | full credit: 'submission of every agent'; no item covers it |
| FACTORY-REPLAY-INSUFFICIENT | Agent invocation and replay instructions are missing or insufficient for a grader to reproduce a bounded phase: up to 2 points lost. | 2 | yes | carries replay instructions (FACTORY-10 is zero) |
| FACTORY-OVERLAP-UNCONTROLLED | Agents share overlapping write ownership without documented control: up to 1 point lost. | 1 | yes | judged only here (FACTORY-04 does not score it) |

## Dataset engineering (1 point, judged by V2)

| Item | What | Weight | Points | Phase | Why |
|---|---|---|---:|---:|---|
| DATA-01 | Dataset portfolio as listed | Core | 0.20 | 03 | full credit leads with 'DBLP plus at least three real linked datasets' |
| DATA-02 | Manifest descriptive fields | Standard | 0.13 | 03 | full credit: 'manifest' |
| DATA-03 | Licenses | Standard | 0.13 | 03 | full credit: 'licenses' |
| DATA-04 | Integrity records | Standard | 0.13 | 03 | full credit: 'checksums' |
| DATA-05 | Schema notes | Standard | 0.13 | 03 | full credit: 'schemas' |
| DATA-06 | Bounded, idempotent retrieval scripts | Standard | 0.13 | 03 | full credit: 'bounded scripts' |
| DATA-07 | Sample files | Minor | 0.07 | 03 | samples: Phase 3 work order, not in the full-credit sentence |
| DATA-08 | Dataset validation | Minor | 0.07 | 03 | manifest validation: Phase 3 work order, not in the full-credit sentence |

| Deduction | README text | Up to | Applied | Why |
|---|---|---:|---|---|
| DATASETS-FEWER-THAN-THREE | Fewer than three actual enrichment datasets: up to 2 points lost. | 2 | yes | about datasets actually USED (reader code); DATA-01 is about datasets LISTED: different failures, no overlap |

## Hadoop MapReduce (2 points, judged by V2)

| Item | What | Weight | Points | Phase | Why |
|---|---|---|---:|---:|---|
| HADOOP-01 | Real MapReduce jobs | Zero | 0.00 | 04 | no real MapReduce jobs = the deduction HADOOP-REPLACED (up to 3): counted once, there |
| HADOOP-02 | DBLP parsing | Core | 0.27 | 04 | full credit leads with 'correct distributed parsing'; every later job reads its output |
| HADOOP-03 | External source normalization | Standard | 0.18 | 04 | full credit: 'normalization' |
| HADOOP-04 | Bounded blocking and match candidates | Standard | 0.18 | 04 | full credit: 'researcher/work blocking' |
| HADOOP-05 | Publication-team extraction | Standard | 0.18 | 04 | full credit: 'author-team extraction' |
| HADOOP-06 | Coauthor-pair preparation | Core | 0.27 | 04 | full credit: 'coauthor-pair preparation'; the Spark graph is built from these pairs. Wrong or dropped pairs for large teams are the deduction HADOOP-PAIRS-WRONG; this item scores everything else |
| HADOOP-07 | Hadoop counters | Standard | 0.18 | 04 | full credit: 'counters' |
| HADOOP-08 | Reject outputs | Standard | 0.18 | 04 | full credit: 'rejects' |
| HADOOP-09 | Operational discipline | Minor | 0.09 | 04 | partitioner, idempotent paths, compression, determinism: Phase 4 work-order detail |
| HADOOP-10 | Hadoop tests | Standard | 0.18 | 04 | full credit: 'tests' |
| HADOOP-11 | Job contracts documented | Minor | 0.09 | 04 | job contracts documented: Phase 4 work-order detail |
| HADOOP-12 | EMR run | Standard | 0.18 | 04 | full credit: 'EMR run'. The instructor confirms the cloud run (a repository alone cannot prove it ran on EMR) |

| Deduction | README text | Up to | Applied | Why |
|---|---|---:|---|---|
| HADOOP-REPLACED | Hadoop requirement replaced by a local loop, Spark operation, or managed import: up to 3 points lost. | 3 | yes | carries the 'no real MapReduce' failure (HADOOP-01 is zero) |
| HADOOP-PAIRS-WRONG | Coauthor-pair preparation is missing or incorrect for large author teams: up to 2 points lost. | 2 | yes | wrong/dropped large-team pairs; HADOOP-06 does not score this part |
| HADOOP-MUTABLE-STATE | Unjustified mutable shared state in distributed or concurrent code: up to 1 point lost. (Judge Hadoop code only here; Spark code is judged in its own category.) | 1 | yes | no item covers it |

## Spark coauthorship analytics (3 points, judged by V2)

| Item | What | Weight | Points | Phase | Why |
|---|---|---|---:|---:|---|
| SPARK-01 | Temporal weighted coauthorship graph | Core | 0.41 | 06 | full credit leads with 'correct temporal weighted graph'; every metric is computed from it |
| SPARK-02 | Distinct coauthor count and weighted degree per researcher | Standard | 0.27 | 06 | full credit: 'distinct and weighted degree' |
| SPARK-03 | Team-size metrics | Standard | 0.27 | 06 | full credit: 'team-size metrics' |
| SPARK-04 | Connected components | Standard | 0.27 | 06 | full credit: 'components' |
| SPARK-05 | Shortest coauthorship paths between researchers | Standard | 0.27 | 06 | full credit: 'paths' |
| SPARK-06 | Community detection | Standard | 0.27 | 06 | full credit: 'communities' |
| SPARK-07 | At least one bridge measure (betweenness or an approximation, participation coefficient ... | Standard | 0.27 | 06 | full credit: 'bridge measure' |
| SPARK-08 | k-core / coreness, or a justified equivalent | Standard | 0.27 | 06 | full credit: 'k-core or equivalent' |
| SPARK-09 | Temporal analysis ("All metrics must be time-aware") | Core | 0.41 | 06 | full credit: 'temporal analysis'; README: 'All metrics must be time-aware' |
| SPARK-10 | Tests of the analytics | Standard | 0.27 | 06 | full credit: 'tests' |
| SPARK-11 | Distributed execution | Zero | 0.00 | 06 | collecting the graph to one process = the deduction SPARK-ABSENT-OR-COLLECT (up to 3): counted once, there |

| Deduction | README text | Up to | Applied | Why |
|---|---|---:|---|---|
| SPARK-ABSENT-OR-COLLECT | Spark coauthorship analytics absent or performed by collecting the graph to one process: up to 3 points lost. | 3 | yes | carries distributed execution (SPARK-11 is zero) |
| SPARK-METRICS-MISSING | Distinct coauthor count, team-size statistics, connected components, communities, bridge analysis, or k-core or justified equivalent missing: up to 2 points lost depending on scope. | 2 | no (counted once in the items) | counted once: SPARK-02..08 each lose their own points for a missing metric (together about 1.9 of the deduction's 2) |
| SPARK-MUTABLE-STATE | Unjustified mutable shared state in distributed or concurrent code: up to 1 point lost. | 1 | yes | no item covers it |

## Deductions from the deterministic checks (V1)

V1's checks give no points of their own: they record structure and process facts, and feed these deductions.

| Deduction | Checks | Up to | Rule | README |
|---|---|---:|---|---|
| secrets | K01, K02, K03 | 4 | a key-shaped value in project files or history -> proposed -4, which the instructor confirms (the value must be a real secret); a value only in tests or phase evidence -> the instructor looks | README: 'Secrets committed or displayed: up to 4 points lost'. Obvious placeholders (documentation examples, FAKE/TEST values) are ignored |
| tests | T01 | 2 | max x (25 - counted) / 25 when fewer than 25 meaningful tests, else 0 | README: 'Fewer than 25 meaningful ... tests: up to 2 points lost'; scaled by how far short |
| hardcoded | V01 | 1 | found -> the instructor decides (a value with a configuration rationale is allowed) | README: 'Hardcoded buckets, endpoints, account IDs, thresholds, or model IDs without configuration rationale: up to 1 point' |
| claims not done | E03 | 2 | a claimed file that no commit supports -> the instructor decides (never automatic: academic-integrity implications) | README: 'Agent reports claim commands or tests that were not actually run: up to 2 points lost and possible academic-integrity review' |
| taskforge fork | C02, C03 | grade may be zero | control plane mostly copied from the tutorial -> the instructor decides | README: 'Only a generic agent tutorial fork with TaskForge renamed ...: zero' |

## Graded by the instructor

Everything the autograder cannot judge from the repository is graded by the instructor, following the assignment README:

| Category | Points |
|---|---:|
| Entity resolution | 1.5 |
| Storage architecture | 1.5 |
| Runtime agentic collaboration analysis | 2.0 |
| Microservices and APIs | 1.0 |
| Terraform and cloud security | 1.5 |
| Reproducible build and deployment automation | 0.5 |
| Elasticity, observability, and resilience | 1.0 |
| Evaluation quality | 1.0 |
| Documentation and demonstration | 1.0 |
| **Total** | **11.0** |

All README deductions not listed above (for example: DBLP not actually processed, the program does not build, destructive operations without approval, results without raw evidence, not being able to explain the system in the demonstration) are also decided by the instructor. Rows the autograder marks for the instructor (cannot_tell, flagged verdicts, possible secrets) are reviewed before any points are final.

## Decisions

- **absent category**: A category that is completely absent (no Spark at all; Hadoop replaced by a local loop) earns none of its points AND takes its README deduction: the deduction is for missing a required component, on top of not earning its points.
- **secrets**: A possible secret is never deducted automatically: the instructor confirms the value is real first.
- **tests**: Fewer than 25 meaningful tests: the deduction grows with how far short you are, 2 x (25 - counted) / 25.
- **flags**: If the automatic verifier flags a verdict (for example: the cited code is not called by the job, or it contradicts a deterministic check), the verdict still counts and the instructor takes a look. Only a verdict the judge could not decide (cannot_tell) is left to the instructor entirely.
