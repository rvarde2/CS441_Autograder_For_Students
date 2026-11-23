"""
Checks due from PHASE 0: they apply from the student's first commit, whatever phase they're in.

  S01        repository safety (symlinks)
  F02        the seed agent (Phase 0 creates .claude/agents/factory-engineer.md)
  P01        phase evidence folders
  G01-G03    git history and phase commits
  K01-K03    secrets and forbidden files
  E01-E07    phase reports checked against git
  C01-C03    copied from the tutorial
  X04        observation: tutorial similarity of each control-plane file (computed with C01)
  X07        observation: report label styles recognised (computed with E01)

Phase evidence (P01, G02, E01-E07) is read through ../evidence.py, which accepts file-name and
label-style variants (1.0.1, after a student's agent-report-01.md files were reported missing).

Rule sources (ScholarChain README): "How to execute the agentic build" (report fields),
"Agent-generated deliverable evidence" (phase folder contents), "Git logistics", "Academic
integrity", and the deductions list ("Agent reports claim commands or tests that were not
actually run", "Secrets committed", "a generic agent tutorial fork with TaskForge renamed: zero").
"""
import json
import re
from collections import Counter
from pathlib import Path

from .. import evidence as ev
from ..fingerprints import fingerprint
from ..ownership import owner_matchers
from ..registry import check_group
from ..repo import PHASE_MSG



# ======================================================================= S01: repo safety
@check_group(phase=0)
def safety(repo, out):
    # A symlink to outside the repo could make a reader (us, or an AI grader) read the grader's
    # own machine. repo.read() already refuses them; this check reports them.
    escaping = repo.escaping_symlinks()
    out.add("S01", "No symlinks pointing outside the repo",
            "FAIL" if escaping else "PASS", [f"{p} -> outside the repo" for p in escaping])


# ======================================================================= F02: seed agent
@check_group(phase=0)
def seed_agent(repo, out):
    # Phase 0 work order: frontmatter must have name, description and an explicit tools field.
    # "Require least privilege and explicit tools fields." Applies to every agent file present.
    out.add("F02", "Every agent has name, description and an EXPLICIT tools field (least privilege)",
            "FAIL" if repo.agent_problems else "PASS", repo.agent_problems)


# ======================================================================= P01: evidence folders
EVIDENCE_KINDS = ["prompt", "agent-report", "human-gate", "commit.txt"]
INDEX_KEY = {"prompt": "prompt", "agent-report": "agent_report", "human-gate": "human_gate", "commit.txt": "commit_record"}


@check_group(phase=0)
def phase_evidence(repo, out):
    # "For each phase, docs/agent-runs/phase-NN/ must contain: prompt.md, agent-report.md,
    #  human-gate.md, commit.txt". Name variants are accepted (evidence.py, data/evidence_formats.json):
    #  agent-report-01.md, phase_03/, Human_Gate.md, ... A missing file is FAIL in every phase (1.0.5: the
    #  highest phase was a WARN, 'in progress?', which in final grading hid a missing gate or commit record).
    title = "Phase evidence folders docs/agent-runs/phase-NN/"
    if not repo.phases:
        out.add("P01", title, "FAIL",
                ["docs/agent-runs/ has no phase-NN folders (rubric: 'no agent evidence' fails the workflow requirement)"])
        return
    fail, warn = [], []
    for d in repo.phases:
        for k in EVIDENCE_KINDS:                       # index: the actual evidence file names
            out.record("phases", d.name, INDEX_KEY[k], value=[repo.rel(p) for p in ev.evidence_files(repo, d, k)])
        out.record("phases", d.name, "number", value=repo.phase_number(d))
        missing = [k for k in EVIDENCE_KINDS if not ev.evidence_files(repo, d, k)]
        if len(missing) == len(EVIDENCE_KINDS):
            # No evidence of its own. It may be missing, skipped, or recorded together with another phase:
            # the checker can't tell which (wording varies too much to detect), so it says so (1.0.6).
            # Other files left in the folder (a note?) are pointed out for the human: a fact, not a reading.
            found = {p for k in EVIDENCE_KINDS for p in ev.evidence_files(repo, d, k)}
            tracked = set(repo.tracked)
            others = [r for p in ev._phase_files(repo, d) if p not in found and (r := repo.rel(p)) in tracked]
            fail.append(f"{repo.rel(d)}/ has no evidence of its own (prompt, agent report, human gate, commit record); "
                        f"if this phase was combined with another one, a human checks that phase's record"
                        + (f"; the folder holds {len(others)} other file(s), a human should read them: "
                           f"{', '.join(others[:3])}" + (" ..." if len(others) > 3 else "") if others else ""))
        elif missing:
            fail.append(f"{repo.rel(d)}/: missing {', '.join(missing)} (name variants are accepted, e.g. agent-report-01.md, Human_Gate.md)")
    nums = sorted({repo.phase_number(d) for d in repo.phases})
    fail += [f"phase-{n:02d} has no folder in docs/agent-runs (missing, skipped, or combined with another phase: "
             f"a human checks)" for n in range(nums[0], nums[-1] + 1) if n not in nums]
    # commits labelled phase-NN for a phase that has no evidence folder (e.g. phase-00 work, no phase-00/)
    labelled = {int(m.group(1)) for s_ in repo.subjects if (m := PHASE_MSG.match(s_.split(" ", 1)[-1]))}
    warn += [f"commits are labelled phase-{n:02d}, but docs/agent-runs has no folder for it" for n in sorted(labelled - set(nums))]
    out.add("P01", title, "FAIL" if fail else ("WARN" if warn else "PASS"),
            [f"phases found: {', '.join(d.name for d in repo.phases)}"] + fail + warn)


# ======================================================================= G01-G03: git
@check_group(phase=0)
def git_history(repo, out):
    if not repo.is_git:
        out.add("G01", "Submission is a git repository with history", "FAIL",
                ["no .git folder: commit history, phase commits and secrets history cannot be checked"])
        return
    subjects = repo.subjects
    out.add("G01", "Submission is a git repository with history", "PASS" if subjects else "FAIL",
            [f"{len(subjects)} commits"])

    # G02: every phase-NN/commit.txt names a commit that really exists (a claim checked against git).
    g2 = []
    for d in repo.phases:
        if not ev.evidence_files(repo, d, "commit.txt"):
            continue                      # P01 already reports the missing file
        # A digits-only token is a hash only if it IS a commit: digits are valid hex, so run IDs, dates and
        # counts ("run id 000011112222") were reported as missing commits (1.0.6).
        hashes = [h for h in ev.hashes_in(ev.evidence_text(repo, d, "commit.txt"))
                  if not h.isdigit() or repo.resolve_commit(h)]
        if not hashes:
            g2.append(f"{repo.rel(d)}/commit.txt: no commit hash in it")
        for h in hashes:
            if repo.git("cat-file", "-e", f"{h}^{{commit}}") is None:
                g2.append(f"{repo.rel(d)}/commit.txt: {h} is not a commit in this repo")
    out.add("G02", "Each phase's commit.txt names a commit that exists",
            "FAIL" if g2 else ("PASS" if repo.phases else "INFO"),
            g2 or (["no phase folders yet"] if not repo.phases else [f"{len(repo.phases)} phases checked"]))

    # G03: "Use commit messages that identify the phase and owning agent", recommended form
    # "phase-06 spark-engineer: ...". Every phase folder needs at least one such commit.
    def msg_phase(s):   # s = '<hash> <subject>'
        m = PHASE_MSG.match(s.split(" ", 1)[1] if " " in s else "")
        return int(m.group(1)) if m else None

    named = [s for s in subjects if msg_phase(s) is not None]
    no_commit = [f"{d.name}: no commit message names it (if it was combined with another phase, a human checks "
                 f"that phase's commits)" for d in repo.phases
                 if (n := repo.phase_number(d)) is not None and not any(msg_phase(s) == n for s in subjects)]
    out.add("G03", "Commit messages identify the phase (e.g. 'phase-06 spark-engineer: ...')",
            "FAIL" if no_commit or (repo.phases and not named) else ("PASS" if repo.phases else "INFO"),
            [f"{len(named)} of {len(subjects)} commit messages name a phase"] + no_commit)


# ======================================================================= K01-K03: secrets
# Specific token shapes are FAILs. A generic "password = '...'" is a WARN (often a local default).
# Values are NEVER printed: only the kind of secret, the file and the line.
SECRET_PATTERNS = {
    "AWS access key id": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "AWS secret access key": re.compile(r"aws_secret_access_key\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40}", re.I),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}|\bgithub_pat_[A-Za-z0-9_]{50,}"),
    "Anthropic API key": re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"),
    "OpenAI-style API key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{32,}"),
    "private key": re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
}
GENERIC_SECRET = re.compile(r"(?i)\b(password|passwd|secret|api_?key|token)\b\s*[=:]\s*['\"]([^'\"\s${}]{8,})['\"]")
FORBIDDEN_FILES = [(r"(^|/)\.env(\..*)?$", ".env file"),
                   (r"\.tfstate(\.backup)?$", "Terraform state"),
                   (r"\.pem$|(^|/)id_(rsa|ed25519)$", "private key file")]
# The README forbids state "containing sensitive values", not variables files in general:
# a committed .tfvars is a WARN (check it holds no secrets). K01/K02 still catch real secrets in it.
REVIEW_FILES = [(r"(?<!example)\.tfvars$", "Terraform variables file: make sure it holds no secrets")]


# 1.0.4 (student feedback): redaction and secret-scanning tests, and review reports about them, contain
# secret-SHAPED values on purpose. The VALUE is classified first, then the location:
#   placeholder (EXAMPLE/FAKE/TEST..., one repeated character, an alphabet or digit sequence,
#     a private-key header with no key body)                     -> not a finding (counted only)
#   realistic value in a test/fixture file or docs/agent-runs/   -> WARN: a human confirms it's not real
#   realistic value anywhere else                                 -> FAIL
PLACEHOLDER_WORDS = re.compile(r"EXAMPLE|FAKE|DUMMY|TEST|SAMPLE|PLACEHOLDER|REDACTED|XXXX|CHANGEME", re.I)
KEY_PREFIX = re.compile(r"^(?:AKIA|ASIA|gh[pousr]_|github_pat_|sk-ant-|sk-(?:proj-)?|xox[baprs]-)")
KEY_BODY = re.compile(r"^[A-Za-z0-9+/=]{40,}$")          # a line of a real PEM key's base64 body
TEST_PATH = re.compile(r"(^|/)(src/test|tests?|fixtures?|testdata|__tests__|spec)/|"
                       r"(Spec|Test|Tests|Suite|IT)\.(scala|java)$|_test\.py$|(^|/)test_\w+\.py$", re.I)


def is_placeholder(kind, value, next_line=""):
    if kind == "private key":                           # a header alone is a detector string, not a key
        return not KEY_BODY.match(next_line.strip().lstrip("+").strip())
    if PLACEHOLDER_WORDS.search(value):
        return True
    body = KEY_PREFIX.sub("", value.split("=")[-1].split(":")[-1].strip(" '\""))
    if len(set(body)) <= 3:                              # 0000..., AAAA..., 1111...
        return True
    run = best = 1                                       # ABCDEFGH..., 12345678...
    for a, b in zip(body, body[1:]):
        run = run + 1 if ord(b) == ord(a) + 1 else 1
        best = max(best, run)
    return best >= 6


def where_soft(path):
    """Why a realistic value in this file is only a WARN, or None if it's a FAIL."""
    if TEST_PATH.search(path):
        return "test/fixture file: confirm it's not a real key"
    if path.startswith("docs/agent-runs/"):
        return "phase evidence: confirm it's not a real key"
    return None


def classify(path, kind, value, next_line, hard, soft, ignored, label):
    if is_placeholder(kind, value, next_line):
        ignored[kind] = ignored.get(kind, 0) + 1
    elif (why := where_soft(path)):
        soft.append(f"{label}: {kind} ({why})")
    else:
        hard.append(f"{label}: {kind}")


def ignored_note(ignored):
    return ([f"ignored as placeholders (documentation examples, FAKE/TEST values, sequences, a key header without "
             f"a key): {', '.join(f'{k} x{n}' for k, n in sorted(ignored.items()))}"] if ignored else [])


@check_group(phase=0)
def secrets(repo, out):
    # K01: current content of tracked files (binary and >2 MB files skipped).
    hard, soft, generic, ignored = [], [], [], {}
    for t in repo.tracked:
        raw = repo.read_bytes(t, max_bytes=2_000_000)     # None: missing, symlink, outside, or > 2 MB
        if raw is None or b"\0" in raw[:8000]:              # binary files skipped
            continue
        lines = raw.decode(errors="replace").splitlines()
        for i, line in enumerate(lines, 1):
            for kind, rx in SECRET_PATTERNS.items():
                if (m := rx.search(line)):
                    classify(t, kind, m.group(0), lines[i] if i < len(lines) else "", hard, soft, ignored, f"{t}:{i}")
            if (m := GENERIC_SECRET.search(line)):
                generic.append(f"{t}:{i}: possible hard-coded {m.group(1)}")
    out.add("K01", "No secrets in the current files (tracked by git)",
            "FAIL" if hard else ("WARN" if soft or generic else "PASS"), hard + soft + generic + ignored_note(ignored))

    # K02: every line ever ADDED in any commit on any branch. A secret deleted later is still
    # in history, so it's still leaked. --no-ext-diff/--no-textconv: no repo diff programs.
    if repo.is_git:
        log = (repo.git("log", "--all", "-p", "--no-color", "--no-ext-diff", "--no-textconv",
                        "--format=@@COMMIT %h", timeout=300) or "").splitlines()
        hard, soft, ignored, seen, commit, fname = [], [], {}, set(), "?", "?"
        for n, line in enumerate(log):
            if line.startswith("@@COMMIT "):
                commit = line.split()[1]
            elif line.startswith("+++ "):
                fname = line[6:] if line.startswith("+++ b/") else line[4:]
            elif line.startswith("+") and not line.startswith("+++"):
                for kind, rx in SECRET_PATTERNS.items():
                    if (m := rx.search(line)) and (commit, fname, kind, m.group(0)) not in seen:
                        seen.add((commit, fname, kind, m.group(0)))
                        classify(fname, kind, m.group(0), log[n + 1] if n + 1 < len(log) else "",
                                 hard, soft, ignored, f"commit {commit}, {fname}")
        hard, soft = sorted(set(hard)), sorted(set(soft))
        out.add("K02", "No secrets anywhere in git history (deleted secrets are still leaked)",
                "FAIL" if hard else ("WARN" if soft else "PASS"), hard + soft + ignored_note(ignored))

    # K03: "Do not commit secrets, .env files, Terraform state containing sensitive values ..."
    bad = [f"{t}: {why}" for t in repo.tracked for rx, why in FORBIDDEN_FILES if re.search(rx, t)]
    review = [f"{t}: {why}" for t in repo.tracked for rx, why in REVIEW_FILES if re.search(rx, t)]
    out.add("K03", "No .env, Terraform state or key files committed (tfvars: review)",
            "FAIL" if bad else ("WARN" if review else "PASS"), bad + review)


# ======================================================================= E01-E07: reports vs git
# A phase's work = the SET of its commits, wherever they sit in history:
#   every commit whose message starts "phase-NN"  +  the commit(s) named in phase-NN/commit.txt.
# Several commits per phase, labelled repairs, and small late fixes committed after a later phase
# are all allowed (E07 reports them; nothing fails because of order).
PLACEHOLDER_FILES = {".gitkeep", ".keep", ".gitkeep.md"}
REPORT_FIELDS = list(ev.FORMATS["report_fields"])   # README: "Required agent report fields" (14)
# Recognising fields in a style we don't know: with fewer than this many fields recognised, missing
# fields are a WARN ("format not recognised?"), not a FAIL.
RECOGNISED_ENOUGH = 7
DECISION = re.compile(r"accept|approv|ratif|reject|declin|refus", re.I)


def owners_of_report(rep):
    owner = ev.first_value(rep.get("OWNER"))
    return [o.strip("`* ") for o in re.split(r"\s*(?:,|;|&|\band\b)\s*", owner) if o.strip("`* ")]


@check_group(phase=0)
def reports_vs_git(repo, out):
    if not (repo.is_git and repo.phases):
        return                    # P01 / G01 already report why there's nothing to compare
    agents = repo.agents
    matchers = owner_matchers(repo)

    # All commits oldest-first, their position (for "late fix" detection), and phase-NN commits.
    log = (repo.git("log", "--all", "--reverse", "--format=%H%x09%s") or "").splitlines()
    log = [line.split("\t", 1) for line in log if "\t" in line]
    order = {h: i for i, (h, _) in enumerate(log)}
    phase_commits = {}
    for h, subj in log:
        if (m := PHASE_MSG.match(subj)):
            phase_commits.setdefault(int(m.group(1)), set()).add(h)

    files_of = {}

    def changed(h):               # files a commit changed (cached; renames as add+delete)
        if h not in files_of:
            files_of[h] = set((repo.git("show", "--name-only", "--format=", "--no-renames", h) or "").split())
        return files_of[h]

    e1, e2, e3, e4, e5, e6, e7 = ([] for _ in range(7))
    e1w, e6w, style_seen = [], [], Counter()        # WARN-level findings; report label styles seen
    for d in repo.phases:
        n = repo.phase_number(d)
        if n is None:
            continue
        tag = d.name
        listed = [c for x in ev.hashes_in(ev.evidence_text(repo, d, "commit.txt")) if (c := repo.resolve_commit(x))]
        commits = phase_commits.get(n, set()) | set(listed)
        touched = set().union(*(changed(h) for h in commits)) if commits else set()
        touched = {f for f in touched if not f.startswith("docs/agent-runs/")}   # evidence isn't "work"
        out.record("phases", d.name, "commits", value=sorted(commits, key=lambda h: order.get(h, 0)))
        out.record("phases", d.name, "files_changed", value=sorted(touched))

        # ---- E01: required fields and a valid STATUS. All of the phase's reports are read together
        #      (agent-report.md, agent-report-01.md, ...); labels in several styles (evidence.py).
        reports = ev.evidence_files(repo, d, "agent-report")
        if not reports:
            continue                      # P01 reports the missing report
        rep, styles = ev.parse_report(ev.evidence_text(repo, d, "agent-report"))
        style_seen.update(styles)
        found = [f for f in REPORT_FIELDS if f in rep]
        if (missing := [f for f in REPORT_FIELDS if f not in rep]):
            msg = f"{tag}: missing field(s) {', '.join(missing)}"
            body = re.sub(r"\s+", "", ev.evidence_text(repo, d, "agent-report"))
            if len(found) >= RECOGNISED_ENOUGH:
                e1.append(msg)
            elif not found and len(body) < 200:          # a stub, not an unknown style: a fact
                e1.append(f"{tag}: the agent report is essentially empty (no fields, under 200 characters)")
            else:
                e1w.append(msg + f" (only {len(found)} of {len(REPORT_FIELDS)} labels recognised: the report may "
                                 f"use a style the checker doesn't know; use the README's field names, e.g. 'FILES CREATED:')")
        status = ev.first_value(rep.get("STATUS"))
        if "STATUS" in rep and not ev.status_ok(status):
            e1.append(f"{tag}: STATUS is {status[:30]!r}, not COMPLETE | BLOCKED-ON | FAILED")

        # ---- E02: OWNER is a real agent. A phase can have several owners: Phase 3 is "the
        #      dataset-engineer and domain-engineer, in separate delegated work orders".
        owner = ev.first_value(rep.get("OWNER"))
        owners = [o.strip("`* ") for o in re.split(r"\s*(?:,|;|&|\band\b)\s*", owner) if o.strip("`* ")]
        if "OWNER" in rep:
            unknown = [o for o in owners if o not in agents] or ([] if owners else [owner])
            for o in unknown:
                e2.append(f"{tag}: OWNER {o!r} has no file in .claude/agents/")

        # ---- E03: every claimed file was changed by one of this phase's commits
        #      Only real repo paths (now or in history) or clearly file-shaped tokens count as claims;
        #      prose like '.collect' or 'Spark/Hadoop' is ignored and never echoed (evidence.claimed_paths).
        claimed = ev.claimed_paths(repo, rep.get("FILES CREATED")) + ev.claimed_paths(repo, rep.get("FILES MODIFIED"))
        out.record("phases", tag, "files_claimed", value=claimed)
        out.record("phases", tag, "owners", value=owners_of_report(rep))

        def covered(t, c):        # a claimed folder covers the files under it
            return t == c or t.startswith(c.rstrip("/") + "/")

        for c in sorted(set(claimed)):
            if not any(covered(t, c) for t in touched):
                elsewhere = sorted({f"phase-{k:02d}" for k, hs in phase_commits.items() for h in hs if c in changed(h)})
                e3.append(f"{tag}: report claims {c}, but no {tag} commit changed it"
                          + (f" (changed in {', '.join(elsewhere)})" if elsewhere else
                             "" if c in repo.history_paths else " (this path never existed in the repo)")
                          + ("" if commits else "  [this phase has no commits]"))

        # ---- E04: changed but not reported (manual edits must be disclosed in human-gate.md)
        unlisted = sorted(t for t in touched if not any(covered(t, c) for c in claimed))
        if unlisted:
            e4.append(f"{tag}: changed but not in the report: {', '.join(unlisted[:8])}"
                      + (f" (+{len(unlisted) - 8} more)" if len(unlisted) > 8 else ""))

        # ---- E05: one writer in practice: changed files belong to an OWNER per the ownership map
        if owners and all(o in agents for o in owners) and matchers:
            for t in sorted(touched):
                # Not one-writer breaks (1.0.6): empty placeholders that keep a folder in git, and files of a test
                # agent (the README's phase sequence, step 6, invokes test agents inside the owning agent's phase).
                if t.rsplit("/", 1)[-1] in PLACEHOLDER_FILES:
                    continue
                own = {a for rx, a in matchers if rx.match(t)}
                if own and all("test" in a for a in own):
                    continue
                if own and not own & set(owners):
                    e5.append(f"{tag}: {owner} changed {t}, owned by {', '.join(sorted(own))}")

        # ---- E06: human gate states a decision and the accepted commit (same as commit.txt).
        #      Gate written before the commit existed (no hash, but commit.txt is valid): WARN.
        #      A gate that mentions other commits but not commit.txt's: WARN (1.0.4; was FAIL). Gates
        #      mention commits in context (a disclosed manual commit, a run folder named after a commit),
        #      and commit.txt, the record G02 verifies, is what names the accepted commit.
        #      FAIL only when neither the gate nor commit.txt names an existing commit.
        if ev.evidence_files(repo, d, "human-gate"):
            hg = ev.gate_text(repo, d)
            accepted = list(dict.fromkeys(c for x in ev.hashes_in(hg) if (c := repo.resolve_commit(x))))
            if not accepted:
                (e6w if listed else e6).append(
                    f"{tag}: the human gate names no existing commit" + (
                        f" (commit.txt has {listed[0][:10]}; the README asks the gate to state the accepted hash too)"
                        if listed else " and commit.txt names none either"))
            elif listed and not set(accepted) & set(listed):
                e6w.append(f"{tag}: the human gate mentions {', '.join(c[:10] for c in accepted[:3])} but not the "
                           f"accepted commit {listed[0][:10]} from commit.txt (the README asks the gate to state it)")
            if not DECISION.search(hg):
                e6w.append(f"{tag}: the human gate doesn't state a decision (accepted / approved / rejected ...)")

        # ---- E07: information only: commits, repairs, and commits made after a later phase's
        repairs = sum(1 for p in repo.glob(d, "*") if ev.norm(p.name).startswith("repair"))
        late = sorted((h for h in commits if h in order and any(
            order[h] > order[x] for k, xs in phase_commits.items() if k > n for x in xs)), key=order.get)
        e7.append(f"{tag}: {len(commits)} commit(s), {repairs} repair record(s)"
                  + (f"; {len(late)} came after a later phase's commit ({', '.join(h[:7] for h in late)})" if late else ""))

    out.add("E01", "Agent reports have every required field and a valid STATUS",
            "FAIL" if e1 else ("WARN" if e1w else "PASS"), e1 + e1w)
    out.add("E02", "Each report's OWNER is an existing agent", "FAIL" if e2 else "PASS", e2)
    out.add("E03", "Files a report claims were really changed by that phase's commits", "FAIL" if e3 else "PASS", e3)
    out.add("E04", "Files the phase changed but its report doesn't list (undisclosed manual edits?)",
            "WARN" if e4 else "PASS", e4)
    out.add("E05", "Files changed in a phase belong to its OWNER (one writer, in practice)",
            "WARN" if e5 else ("PASS" if matchers else "INFO"),
            e5 or ([] if matchers else ["no ownership map to compare with"]))
    out.add("E06", "human-gate.md states a decision and the accepted commit, matching commit.txt",
            "FAIL" if e6 else ("WARN" if e6w else "PASS"), e6 + e6w)
    # X07 (observation): which report label styles were recognised, to learn students' formats
    out.add("X07", "Observation: report label styles recognised (colon, bold, heading, table, bare label)", "INFO",
            [", ".join(f"{k}: {v}" for k, v in sorted(style_seen.items())) or "none recognised"],
            data=dict(sorted(style_seen.items())))
    out.add("E07", "Commits per phase (several commits, repairs and late fixes are allowed)", "INFO", e7)


# ======================================================================= C01-C03: copying
# Students are told to FOLLOW the tutorial, so one copied generic file is fine (C01 is a WARN).
# What the rubric gives zero is a fork that is mostly the tutorial, renamed or not (C02), or one
# that still mentions TaskForge (C03). Thresholds are judgement calls, to tune with real repos.
COPY_AT = 0.80      # a file is "copied" if >= 80% of its lines are in ONE tutorial file
MOSTLY = 0.50       # the control plane is "mostly copied" if > 50% of its files are copied
DATA = Path(__file__).resolve().parent.parent / "data"


SCRIPT_EXT = (".sh", ".bash", ".py")
ENFORCING = re.compile(r"\b(?:grep|egrep|rg|ag|findstr)\b|=~|re\.(?:search|match|compile)|\b(?:deny|denied|forbid|"
                       r"forbidden|reject|block|blocked|leftovers?|must not)\b", re.I)


def is_control(path):
    """The agent control plane: what Phase 0-1 must write for ScholarChain."""
    return path in ("CLAUDE.md", "docs/agents.md", ".mcp.json") or path.startswith(".claude/")


@check_group(phase=0)
def copy_detection(repo, out):
    fp = json.loads((DATA / "tutorial_fingerprints.json").read_text())
    tutorial = {k: set(v) for k, v in fp["files"].items()}

    def best_match(path):     # (share of my lines found in the closest tutorial file, its name, my line count)
        text = repo.read(path)
        mine = fingerprint(text) if text is not None else set()
        if not mine:
            return None
        name, shared = max(((k, len(mine & v)) for k, v in tutorial.items()), key=lambda kv: kv[1])
        return shared / len(mine), name, len(mine)

    # Every tracked file is compared, not only the tutorial's paths: moving a file must not hide it
    # (an earlier version missed 14 Scala files moved from com/taskforge to com/scholarchain).
    candidates = sorted(t for t in repo.tracked if (repo.size(t) or 0) <= 200_000 and repo.is_file(t))
    sims = {t: m for t in candidates if (m := best_match(t))}
    copied = {t: m for t, m in sims.items() if m[0] >= COPY_AT}
    out.record("copied_from_tutorial", value={t: {"similarity": round(m[0], 2), "tutorial_file": m[1]}
                                              for t, m in sorted(copied.items())})

    others = Counter(t.split("/")[0] if "/" in t else "(root)" for t in copied if not is_control(t))
    out.add("C01", "Files copied from the tutorial (>= 80% of their lines; one generic file is fine)",
            "WARN" if copied else "PASS",
            [f"{t}: {m[0]:.0%} of {m[2]} lines match tutorial {m[1]}" + ("" if m[1] == t else "  (renamed)")
             for t, m in sorted(copied.items()) if is_control(t)]
            + ([f"{sum(others.values())} other copied file(s): "
                + ", ".join(f"{d}/ {c}" for d, c in sorted(others.items()))] if others else [])
            + [f"fingerprints: tutorial commit {fp['commit'][:12]}"])

    # X04 (observation): similarity of every control-plane file, to tune the 80% / 50% cut-offs.
    out.add("X04", "Observation: tutorial similarity of each control-plane file (to tune C01/C02 cut-offs)", "INFO",
            [", ".join(f"{t} {m[0]:.0%}" for t, m in sorted(sims.items()) if is_control(t)) or "no control-plane files"],
            data={t: round(m[0], 2) for t, m in sorted(sims.items()) if is_control(t)})

    ctl = [t for t in sims if is_control(t)]
    ctl_copied = [t for t in ctl if t in copied]
    ratio = len(ctl_copied) / len(ctl) if ctl else 0
    out.add("C02", "Agent control plane is written for ScholarChain, not mostly copied from the tutorial",
            "FAIL" if ctl and ratio > MOSTLY else ("WARN" if ctl_copied else "PASS"),
            [f"{len(ctl_copied)} of {len(ctl)} control-plane files are tutorial copies "
             f"({ratio:.0%}; FAIL above {MOSTLY:.0%})"])

    # C03: TaskForge left in the control plane or code is a FAIL; in other docs (a README credit) a WARN.
    # A line that SEARCHES for or BLOCKS the name ("grep -qi taskforge ... leftover") enforces the rule; it is
    # listed separately and never fails (1.0.6: a student's validate-agent-files.sh FAILed C03 for this).
    leftover, enforcing = {}, {}
    for t in repo.tracked:
        if not (is_control(t) or t.endswith((".scala", ".sbt", ".sh", ".tf", ".md", ".json", ".yml", ".yaml", ".conf"))):
            continue
        for line in (repo.read(t) or "").splitlines():
            if (n := len(re.findall(r"task\s*forge", line, re.I))):
                book = enforcing if t.endswith(SCRIPT_EXT) and ENFORCING.search(line) else leftover   # scripts only: prose isn't enforcement
                book[t] = book.get(t, 0) + n
    bad = {t for t in leftover if is_control(t) or t.endswith((".scala", ".sbt", ".sh", ".tf"))}
    out.add("C03", "No TaskForge leftovers in the control plane or code (README attribution is fine)",
            "FAIL" if bad else ("WARN" if leftover else "PASS"),
            [f"{t}: {n} mention(s) of TaskForge" for t, n in sorted(leftover.items(), key=lambda kv: -kv[1])][:15]
            + ([f"... and {len(leftover) - 15} more files"] if len(leftover) > 15 else [])
            + ([f"not counted, they check for or block the name: {', '.join(sorted(enforcing))}"] if enforcing else []))
