# V2 rubric (version 2.3.2)

Generated from the rubric files in `judge/rubric/` that the AI judge uses, so this page and the judge always
agree. Every item quotes the ScholarChain README (commit a139f4a).
V2 is advisory: it gives verdicts, not points.

## How every item is judged

- **Verdicts:** `met`, `partial`, `missing`, or `cannot_tell` (the judge could not decide: a human looks).
- **Evidence, not claims:** every `met`/`partial` must cite a file, lines and an exact quote, which code checks
  against your repository. A `missing` must be backed by searches the judge really ran. What reports or
  READMEs *claim* counts only if the code is there.
- **Deductions:** `applies` yes/no with a severity: `minor` (one contained occurrence; results still produced),
  `partial` (some of the category's work affected), `full` (its core affected).
- **One problem, one place:** a weakness is judged in the item or deduction it belongs to, not counted twice
  (unless an item's own wording also covers it).
- **Implementation counts:** code is judged on what it implements. If nothing seems to call it, the item is
  flagged for a human (another entry point may call it), not marked down.
- **Text addressed to the grader** in your repository is reported, never obeyed.

## Categories in this version

| Category | Points | Judged from phase | Items | Deductions |
|---|---:|---:|---:|---:|
| Dataset engineering (`dataset_engineering`) | 1.0 | 3 | 8 | 1 |
| Hadoop MapReduce (`hadoop_mapreduce`) | 2.0 | 4 | 12 | 3 |
| Spark coauthorship analytics (`spark_analytics`) | 3.0 | 6 | 11 | 3 |

## Dataset engineering: 1.0 points, phase 3

README full-credit evidence: *DBLP plus at least three real linked datasets, manifest, licenses, checksums, schemas, and bounded scripts*

| ID | What is judged | README source |
|---|---|---|
| DATA-01 | Dataset portfolio as listed. met: datasets/dataset-manifest.yaml lists DBLP plus at least three additional real public scholarly datasets, each with a stated purpose or analytical role. partial: DBLP plus one or two additional datasets, or roles missing. missing: no manifest, or DBLP absent. Judge only what the manifest lists here; whether each dataset is actually used is the deduction DATASETS-FEWER-THAN-THREE. | 'Dataset portfolio': DBLP is mandatory, at least three additional datasets; Phase 3: 'Create datasets/dataset-manifest.yaml for DBLP and every selected enrichment dataset' |
| DATA-02 | Manifest descriptive fields. Each dataset entry should give these 15 (field names may differ; judge meaning): name and purpose, official source and documentation links, snapshot or retrieval date, retrieval command or script, file format and compression, expected and observed size, S3 raw prefix, schema version, selected subset rule, incremental update strategy, linkage fields, personal data and privacy considerations, known omissions or limitations, validation commands, owning agent. Placeholders (TBD, YYYY-MM-DD, <...>, empty values) count as missing. met: every entry is missing at most 2 of the 15. partial: entries exist but at least one entry is missing more than 2. missing: no manifest entries. Licenses and checksums are judged in DATA-03 and DATA-04, not here. | 'Dataset manifest': each dataset entry must contain ...; 'The dataset manifest must record actual availability, snapshot dates, ... A dead endpoint is not a dataset strategy.' |
| DATA-03 | Licenses. met: every dataset entry names concrete license or reuse terms (a named license such as 'CC0 1.0' or 'ODC-BY 1.0', or the provider's named terms) and gives a link to those terms. partial: only some datasets, or vague wording ('open', 'free for research', 'public') without named terms. missing: no license information. Judge presence and specificity only; do not judge whether a stated license is correct for that dataset (a human checks that). | Manifest field 'License or reuse terms'; rubric 'licenses'; Phase 3 gate: 'no dataset license, identifier, or source is invented' (truth -> human checklist) |
| DATA-04 | Integrity records. met: every dataset has a SHA-256 value or checksum file, an ETag policy, or an equivalent stated integrity rule, plus a validation command that uses it (for example 'sha256sum -c ...' or a script step that compares checksums). partial: only some datasets, or integrity fields that are placeholders, or no validation command uses them. missing: no integrity records. | Manifest field 'SHA-256 checksum, ETag policy, or equivalent integrity record' and 'Validation commands'; rubric 'checksums' |
| DATA-05 | Schema notes. met: files under datasets/schemas describe, for DBLP and each enrichment dataset, the fields used with their types or meanings, a schema version, and which fields are linkage keys. partial: only some datasets, or field names without types or meanings. missing: no schema notes. | Phase 3: 'Create schema notes under datasets/schemas'; manifest fields 'Schema version' and 'Linkage fields'; rubric 'schemas' |
| DATA-06 | Bounded, idempotent retrieval scripts. Judge by reading the scripts; they are never run. met: download and sample-generation scripts under datasets/scripts cover every dataset in the manifest; by default each fetches a bounded subset (an explicit size, record or file limit, with a full corpus only behind an explicit flag or confirmation); and running a script again does not repeat or corrupt finished work (for example it skips existing files or verifies checksums). partial: only some datasets, or no visible default bound, or no visible idempotency. missing: no retrieval scripts. | Phase 3: 'Create bounded download and sample-generation scripts under datasets/scripts', 'Scripts must be idempotent and must not download a full corpus by default'; gate: 'Sample scripts do not silently fetch large files' |
| DATA-07 | Sample files. met: small sample files under datasets/samples for DBLP and each enrichment dataset, whose structure matches that dataset's schema notes or source format. partial: samples for only some datasets, or samples whose structure does not match the schema notes. missing: no samples. If sample content looks invented (placeholder names, fake identifiers such as 10.1234/...), keep the verdict and add an integrity note; you cannot prove where a sample came from. | Phase 3: 'Create representative legal sample files under datasets/samples, small enough for the repository'; deliverable D05; final report 'A dataset manifest and actual source samples' |
| DATA-08 | Dataset validation. A check counts only if it asserts specific expected outcomes. met: a test or validation script checks the manifest beyond parsing: required fields present, checksum or integrity format, and that each dataset has its sample and schema (or equivalent checks). partial: it only checks that the manifest parses or that files exist. missing: no dataset or manifest validation. | Agent table: dataset-engineer verification 'Dataset validation tests and manifest review'; Phase 3 gate: 'Dataset manifest validation passes' |

| Deduction | Up to | README text |
|---|---:|---|
| DATASETS-FEWER-THAN-THREE | 2 pts | Fewer than three actual enrichment datasets: up to 2 points lost. (Judge here: an enrichment dataset counts as actual when it has a manifest entry, a retrieval or sample script, a sample file, and pipeline code outside datasets/ (for example a normalizer, parser or loader) that reads its records; the retrieval and sample scripts under datasets/ do not count as that code. Being listed in the manifest alone does not count; listing is judged in DATA-01. Whether the datasets were processed in a real run cannot be confirmed from the repository; a human checks that.) |

**Our interpretations** (where the README gives no threshold; approved by the instructor):

- **DATA-02:** "Most fields" is read as: each dataset entry may miss at most 2 of the 15 descriptive fields; placeholders (TBD, YYYY-MM-DD, <...>) count as missing.
- **DATA-03:** Only presence and specificity of license terms are judged here; whether a stated license is correct is checked by a human.
- **DATASETS-FEWER-THAN-THREE:** "Actual" dataset = manifest entry + retrieval or sample script + sample file + pipeline code outside datasets/ that reads its records. Listing alone is judged in DATA-01.

## Hadoop MapReduce: 2.0 points, phase 4

README full-credit evidence: *Correct distributed parsing, normalization, researcher/work blocking, author-team extraction, coauthor-pair preparation, counters, rejects, tests, and EMR run*

| ID | What is judged | README source |
|---|---|---|
| HADOOP-01 | Real MapReduce jobs. met: at least two jobs, each with a driver that configures Mapper and Reducer classes (or Hadoop Streaming with a job configuration). partial: exactly one such job. missing: no real MapReduce job. | Phase 4 gate: 'At least two real MapReduce jobs execute, not local collection operations disguised as MapReduce' |
| HADOOP-02 | DBLP parsing. met: an XML input format or record reader that keeps each top-level DBLP record whole across input splits, and extraction of key, title, ordered authors, year, venue fields, ee links, URLs and record type into WorkRecord/AuthorMention records. partial: records parsed but the reader assumes byte splits align with records, or only some fields are extracted. | Phase 4 work order job 1; 'Detailed Hadoop requirements': must not assume arbitrary byte splits align with publication elements |
| HADOOP-03 | External source normalization. met: one normalizer per selected dataset, mapping into shared contracts while keeping source-specific IDs, and normalizing identifiers (DOI, arXiv, ORCID, OpenAlex, Semantic Scholar, ...) with duplicate or conflict counting. partial: only some selected datasets, or source IDs lost. | Phase 4 work order jobs 2 and 3 |
| HADOOP-04 | Bounded blocking and match candidates. met: blocking keys with a maximum block size, fallback keys, an oversize-group policy and an oversize counter, producing MatchCandidate records with deterministic match features, AND the size bound takes effect before a whole oversize group reaches a single reducer (for example a pre-pass that counts block sizes and re-keys oversize groups in the mapper, composite or salted keys, or sampling). partial: blocking without a size bound or oversize policy; or a bound applied only after one reducer has received and loaded the whole oversize group; or no MatchCandidate output. ('Simply allocating a larger reducer is not a strategy.') | Phase 4 work order jobs 4 and 5; 'Detailed Hadoop requirements' on giant reducer groups |
| HADOOP-05 | Publication-team extraction: one team record per retained work with ordered author mentions, and author-paper records keyed by author mention and work ID. An author mention is identified by an author-mention ID or by the pair (work ID, author position); a record keyed by the author's name alone does not identify the mention. | Phase 4 work order job 6 |
| HADOOP-06 | Coauthor-pair preparation. met: unordered pairs, n*(n-1)/2 per paper with n authors, no self-pairs, every pair keeping work ID, year, author position and source provenance, and unusually large teams counted and reported. partial: pairs produced but missing provenance fields or large-team counting. | Phase 4 work order job 6; gate: 'Pair generation passes hand-checkable papers with 1, 2, 3, and larger author lists' |
| HADOOP-07 | Hadoop counters. met: counters for at least 6 of the 10 listed kinds (input, accepted, rejected, duplicate, conflict, oversize block, oversize author team, emitted pair, missing key, schema failure). partial: 1 to 5 of them. missing: no counters. | Phase 4 work order 'Required operational behavior' |
| HADOOP-08 | Reject outputs. met: malformed and unsupported records written to versioned reject outputs. partial: rejects only counted or logged, or outputs not versioned, or some kinds of bad records (for example unsupported record types) are skipped instead of written to the reject outputs. | Phase 4 work order job 2; gate: 'Counters and reject outputs are visible' |
| HADOOP-09 | Operational discipline: explicit partition strategy, idempotent output paths containing run ID and dataset snapshot, compressed intermediate outputs, deterministic outputs for deterministic inputs. Deterministic means the output does not depend on the order in which values reach a reducer or on task scheduling (for example values or pairs are sorted, a secondary sort is used, or pair IDs are put in a canonical order). met: all four. partial: some. | Phase 4 work order 'Required operational behavior' |
| HADOOP-10 | Hadoop tests. A test counts only if it asserts specific expected values. met: tests for the parser, pair generation with 1, 2, 3 and larger author lists, normalization, and key functions, plus at least one local or mini-cluster integration test of a representative job. partial: only some of these, or tests that only check that code runs. missing: no Hadoop tests. | Phase 4 work order required tests and gate; 'Required test inventory': Hadoop mapper and reducer tests |
| HADOOP-11 | Job contracts documented: for each job, input format, input/mapper-output/reducer key and value types, combiner and partitioner behavior, counters, reject conditions, expected reducers, S3 input and output prefixes, compression codec, idempotency rule and test fixture. met: most jobs with most of these. partial: some jobs or few fields. ('A diagram that says Hadoop processes DBLP is insufficient.') | 'Detailed Hadoop requirements': document every mapper and reducer contract |
| HADOOP-12 | EMR run. met: a bounded EMR smoke-run script and committed evidence of an EMR run (counters, logs or a run report). partial: script only, or evidence without a script. Run evidence cannot be confirmed from the repository alone, so describe what you found. **(always confirmed by a human)** | Evaluation rubric 'EMR run'; Phase 4 work order: 'A bounded EMR smoke-run script owned by the infrastructure workflow' |

| Deduction | Up to | README text |
|---|---:|---|
| HADOOP-REPLACED | 3 pts | Hadoop requirement replaced by a local loop, Spark operation, or managed import: up to 3 points lost. |
| HADOOP-PAIRS-WRONG | 2 pts | Coauthor-pair preparation is missing or incorrect for large author teams: up to 2 points lost. (Judge here: applies when pairs for large teams are wrong, dropped or not produced. Missing large-team counting or reporting alone is judged in HADOOP-06, not here.) |
| HADOOP-MUTABLE-STATE | 1 pts | Unjustified mutable shared state in distributed or concurrent code: up to 1 point lost. (Judge Hadoop code only here; Spark code is judged in its own category.) |

**Our interpretations** (where the README gives no threshold; approved by the instructor):

- **HADOOP-04:** The size bound must take effect BEFORE a whole oversize group reaches one reducer (for example a pre-pass that counts block sizes and re-keys oversize keys in the mapper, composite or salted keys, or sampling). A bound applied only after one reducer has received and loaded the whole group is partial ("Simply allocating a larger reducer is not a strategy").
- **HADOOP-05:** An author mention is identified by an author-mention ID or by (work ID, author position); a record keyed by the author's name alone does not identify the mention.
- **HADOOP-07:** Met = counters for at least 6 of the 10 kinds the README lists.
- **HADOOP-08:** Partial also when some kinds of bad records (for example unsupported DBLP record types, or bad records in the source normalizers) are skipped or only counted instead of written to the versioned reject outputs.
- **HADOOP-09:** "Deterministic" = the output does not depend on the order in which values reach a reducer or on task scheduling (sorted values, a secondary sort, or canonically ordered pair IDs).
- **HADOOP-12:** Run evidence cannot be confirmed from a repository alone: this item always goes to a human.
- **HADOOP-PAIRS-WRONG:** Applies when pairs for large teams are wrong, dropped or not produced. Missing large-team counting or reporting alone is judged in HADOOP-06, not here.

## Spark coauthorship analytics: 3.0 points, phase 6

README full-credit evidence: *Correct temporal weighted graph, distinct and weighted degree, team-size metrics, components, paths, communities, bridge measure, k-core or equivalent, temporal analysis, tests, and distributed execution.*

| ID | What is judged | README source |
|---|---|---|
| SPARK-01 | Temporal weighted coauthorship graph: edges weighted by joint publications, with first and last collaboration year | Evaluation rubric; 'What must be measured': jointPublicationCount, firstCollaborationYear, lastCollaborationYear |
| SPARK-02 | Distinct coauthor count and weighted degree per researcher | Evaluation rubric; 'What must be measured': C_r distinct coauthors, W_r weighted degree |
| SPARK-03 | Team-size metrics: average and maximum coauthors per publication, and the publications behind the maximum | Evaluation rubric; 'What must be measured': A_r, M_r; 'Required final capability': publications that produced each maximum team size |
| SPARK-04 | Connected components: component id and size per researcher | Evaluation rubric; 'What must be measured': componentId(r), componentSize(r) |
| SPARK-05 | Shortest coauthorship paths between researchers | Evaluation rubric; 'What must be measured': d(u,v) |
| SPARK-06 | Community detection: a documented community assignment | Evaluation rubric; 'What must be measured': a documented community assignment |
| SPARK-07 | At least one bridge measure (betweenness or an approximation, participation coefficient, cross-community degree, or similar) | Evaluation rubric; 'What must be measured': at least one bridge measure |
| SPARK-08 | k-core / coreness, or a justified equivalent | Evaluation rubric: 'k-core or equivalent' |
| SPARK-09 | Temporal analysis ("All metrics must be time-aware"). met: the metrics are computed per time period, and the periods are either one per year or come from configuration or job arguments. partial: metrics are computed per period, but the periods are fixed in code, or only some metrics are time-aware. missing: no per-period computation. | Evaluation rubric; 'What must be measured': 'All metrics must be time-aware'; README lines on 'configurable windows' and 'time-window configuration'; definition set after held-out review |
| SPARK-10 | Tests of the analytics. A metric counts as tested only if a test asserts a specific, hand-checked expected value for it on small fixed data (e.g. a small known graph). met: at least 5 of the 9 metric items SPARK-01..SPARK-09 are tested this way. partial: tests exist, but fewer than 5 metrics are tested this way, or the tests only check that code runs (counts above zero, non-null results). missing: no tests of the analytics. | Evaluation rubric: tests; 'Required test inventory': small known-graph Spark tests |
| SPARK-11 | Distributed execution: analytics run in Spark, not by collecting the graph into one process | Evaluation rubric: distributed execution; Phase 6 work order |

| Deduction | Up to | README text |
|---|---:|---|
| SPARK-ABSENT-OR-COLLECT | 3 pts | Spark coauthorship analytics absent or performed by collecting the graph to one process: up to 3 points lost. |
| SPARK-METRICS-MISSING | 2 pts | Distinct coauthor count, team-size statistics, connected components, communities, bridge analysis, or k-core or justified equivalent missing: up to 2 points lost depending on scope. |
| SPARK-MUTABLE-STATE | 1 pts | Unjustified mutable shared state in distributed or concurrent code: up to 1 point lost. |

**Our interpretations** (where the README gives no threshold; approved by the instructor):

- **SPARK-09:** "Configurable" = one period per year, or periods taken from configuration or job arguments (not fixed in code).
- **SPARK-10:** Met = at least 5 of the 9 metric items SPARK-01..09 tested with hand-checked expected values on small fixed data.

## Not judged by the AI (a human checks these)

- Whether DBLP was actually processed in a real run (README deduction, up to 5 points).
- Whether stated dataset licenses are correct.
- AWS / EMR run evidence, the demonstration and the oral explanation.
- Anything in a category not listed above (more categories come in later versions).
