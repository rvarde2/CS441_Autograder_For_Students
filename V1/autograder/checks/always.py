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

Rule sources (ScholarChain README): "How to execute the agentic build" (report fields),
"Agent-generated deliverable evidence" (phase folder contents), "Git logistics", "Academic
integrity", and the deductions list ("Agent reports claim commands or tests that were not
actually run", "Secrets committed", "a generic agent tutorial fork with TaskForge renamed: zero").
"""
import json
import re
from collections import Counter
from pathlib import Path

from ..fingerprints import fingerprint
from ..ownership import owner_matchers
from ..registry import check_group
from ..repo import PHASE_MSG

PHASE_FILES_REQUIRED = ["prompt.md", "agent-report.md", "human-gate.md", "commit.txt"]
HASH = re.compile(r"\b[0-9a-f]{7,40}\b")


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
@check_group(phase=0)
def phase_evidence(repo, out):
    # "For each phase, docs/agent-runs/phase-NN/ must contain: prompt.md, agent-report.md,
    #  human-gate.md, commit.txt" (+ review/test/repair reports when applicable: not required here).
    if not repo.phases:
        out.add("P01", "Phase evidence folders docs/agent-runs/phase-NN/", "FAIL",
                ["docs/agent-runs/ has no phase-NN folders (rubric: 'no agent evidence' fails the "
                 "workflow requirement)"])
        return
    gaps = [f"{repo.rel(d)}/: missing {f}" for d in repo.phases for f in PHASE_FILES_REQUIRED
            if not repo.is_file(d / f)]
    nums = sorted(n for d in repo.phases if (n := repo.phase_number(d)) is not None)
    skipped = [n for n in range(nums[0], nums[-1] + 1) if n not in nums] if nums else []
    out.add("P01", "Phase evidence folders docs/agent-runs/phase-NN/",
            "FAIL" if gaps or skipped else "PASS",
            [f"phases found: {', '.join(d.name for d in repo.phases)}"] + gaps
            + [f"phase-{n:02d} is missing between others" for n in skipped])


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
        txt = repo.read(d / "commit.txt")
        if txt is None:
            continue                      # P01 already reports the missing file
        hashes = HASH.findall(txt)
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
    no_commit = [f"{d.name}: no commit message mentions it" for d in repo.phases
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
                   (r"(?<!example)\.tfvars$", "Terraform variables file"),
                   (r"\.pem$|(^|/)id_(rsa|ed25519)$", "private key file")]


@check_group(phase=0)
def secrets(repo, out):
    # K01: current content of tracked files (binary and >2 MB files skipped).
    hard, soft = [], []
    for t in repo.tracked:
        raw = repo.read_bytes(t, max_bytes=2_000_000)     # None: missing, symlink, outside, or > 2 MB
        if raw is None or b"\0" in raw[:8000]:              # binary files skipped
            continue
        for i, line in enumerate(raw.decode(errors="replace").splitlines(), 1):
            hard += [f"{t}:{i}: {kind}" for kind, rx in SECRET_PATTERNS.items() if rx.search(line)]
            if (m := GENERIC_SECRET.search(line)):
                soft.append(f"{t}:{i}: possible hard-coded {m.group(1)}")
    out.add("K01", "No secrets in the current files (tracked by git)",
            "FAIL" if hard else ("WARN" if soft else "PASS"), hard + soft)

    # K02: every line ever ADDED in any commit on any branch. A secret deleted later is still
    # in history, so it's still leaked. --no-ext-diff/--no-textconv: no repo diff programs.
    if repo.is_git:
        log = repo.git("log", "--all", "-p", "--no-color", "--no-ext-diff", "--no-textconv",
                       "--format=@@COMMIT %h", timeout=300) or ""
        hist, commit, fname = set(), "?", "?"
        for line in log.splitlines():
            if line.startswith("@@COMMIT "):
                commit = line.split()[1]
            elif line.startswith("+++ "):
                fname = line[6:] if line.startswith("+++ b/") else line[4:]
            elif line.startswith("+") and not line.startswith("+++"):
                hist |= {f"commit {commit}, {fname}: {k}" for k, rx in SECRET_PATTERNS.items() if rx.search(line)}
        out.add("K02", "No secrets anywhere in git history (deleted secrets are still leaked)",
                "FAIL" if hist else "PASS", sorted(hist))

    # K03: "Do not commit secrets, .env files, Terraform state containing sensitive values ..."
    bad = [f"{t}: {why}" for t in repo.tracked for rx, why in FORBIDDEN_FILES if re.search(rx, t)]
    out.add("K03", "No .env, Terraform state, tfvars or key files committed", "FAIL" if bad else "PASS", bad)


# ======================================================================= E01-E07: reports vs git
# A phase's work = the SET of its commits, wherever they sit in history:
#   every commit whose message starts "phase-NN"  +  the commit(s) named in phase-NN/commit.txt.
# Several commits per phase, labelled repairs, and small late fixes committed after a later phase
# are all allowed (E07 reports them; nothing fails because of order).
REPORT_FIELDS = ["STATUS", "OWNER", "WORK ORDER", "FILES CREATED", "FILES MODIFIED", "COMMANDS RUN",
                 "TEST RESULTS", "VALIDATION RESULTS", "ASSUMPTIONS", "RISKS", "MANUAL ACTION REQUIRED",
                 "BLOCKED-ON OWNER", "BLOCKED-ON EVIDENCE", "NEXT GATE"]   # README: "Required agent report fields"
# A field label at the start of a line, tolerating markdown decoration: "**STATUS:**", "- OWNER:", "## Files created:"
LABEL = re.compile(r"^\s*[#>*_\-\s]*(" + "|".join(re.escape(f) for f in REPORT_FIELDS)
                   + r")\s*[*_]*\s*:\s*(.*)$", re.I)
# Something that looks like a repo path: has a folder, or a file extension, or is a dotfile.
PATHLIKE = re.compile(r"`?((?:[\w.\-]+/)*[\w.\-]*[\w\-]\.[A-Za-z0-9]{1,10}|(?:[\w.\-]+/)+[\w.\-]+"
                      r"|(?<![\w/])\.[A-Za-z][\w\-]*)`?")


def parse_report(text):
    """{FIELD: text} for each labelled field; a field's text runs until the next label."""
    fields, cur = {}, None
    for line in text.splitlines():
        m = LABEL.match(line)
        if m:
            cur = m.group(1).upper()
            fields[cur] = m.group(2).strip()
        elif cur:
            fields[cur] += "\n" + line
    return fields


def paths_in(field_text):
    """Paths mentioned in a report field. Keeps leading dots (.claude/, .gitignore): an earlier
    version used strip('.')/lstrip('./'), which turned '.claude/x' into 'claude/x'."""
    found = []
    for tok in PATHLIKE.findall(field_text or ""):
        tok = tok.strip("`'\",;:()").rstrip(".")
        if "://" in tok or tok.lower() in ("none", "n/a") or tok.startswith(("http", "www.")):
            continue
        found.append(tok[2:] if tok.startswith("./") else tok)
    return found


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
    for d in repo.phases:
        n = repo.phase_number(d)
        if n is None:
            continue
        tag = d.name
        listed = [c for x in HASH.findall(repo.read(d / "commit.txt") or "") if (c := repo.resolve_commit(x))]
        commits = phase_commits.get(n, set()) | set(listed)
        touched = set().union(*(changed(h) for h in commits)) if commits else set()
        touched = {f for f in touched if not f.startswith("docs/agent-runs/")}   # evidence isn't "work"

        # ---- E01: required fields and a valid STATUS
        rep_text = repo.read(d / "agent-report.md")
        if rep_text is None:
            e1.append(f"{tag}: no agent-report.md")
            continue
        rep = parse_report(rep_text)
        if (missing := [f for f in REPORT_FIELDS if f not in rep]):
            e1.append(f"{tag}: missing field(s) {', '.join(missing)}")
        status = (rep.get("STATUS") or "").split("\n")[0].strip().upper()
        if "STATUS" in rep and not re.match(r"(COMPLETE|BLOCKED-ON|FAILED)\b", status):
            e1.append(f"{tag}: STATUS is {status[:30]!r}, not COMPLETE | BLOCKED-ON | FAILED")

        # ---- E02: OWNER is a real agent. A phase can have several owners: Phase 3 is "the
        #      dataset-engineer and domain-engineer, in separate delegated work orders".
        owner = (rep.get("OWNER") or "").split("\n")[0].strip().strip("`*")
        owners = [o.strip("`* ") for o in re.split(r"\s*(?:,|;|&|\band\b)\s*", owner) if o.strip("`* ")]
        if "OWNER" in rep:
            unknown = [o for o in owners if o not in agents] or ([] if owners else [owner])
            for o in unknown:
                e2.append(f"{tag}: OWNER {o!r} has no file in .claude/agents/")

        # ---- E03: every claimed file was changed by one of this phase's commits
        claimed = paths_in(rep.get("FILES CREATED")) + paths_in(rep.get("FILES MODIFIED"))

        def covered(t, c):        # a claimed folder covers the files under it
            return t == c or t.startswith(c.rstrip("/") + "/")

        for c in sorted(set(claimed)):
            if not any(covered(t, c) for t in touched):
                elsewhere = sorted({f"phase-{k:02d}" for k, hs in phase_commits.items() for h in hs if c in changed(h)})
                e3.append(f"{tag}: report claims {c}, but no {tag} commit changed it"
                          + (f" (changed in {', '.join(elsewhere)})" if elsewhere else "")
                          + ("" if commits else "  [this phase has no commits]"))

        # ---- E04: changed but not reported (manual edits must be disclosed in human-gate.md)
        unlisted = sorted(t for t in touched if not any(covered(t, c) for c in claimed))
        if unlisted:
            e4.append(f"{tag}: changed but not in the report: {', '.join(unlisted[:8])}"
                      + (f" (+{len(unlisted) - 8} more)" if len(unlisted) > 8 else ""))

        # ---- E05: one writer in practice: changed files belong to an OWNER per the ownership map
        if owners and all(o in agents for o in owners) and matchers:
            for t in sorted(touched):
                own = {a for rx, a in matchers if rx.match(t)}
                if own and not own & set(owners):
                    e5.append(f"{tag}: {owner} changed {t}, owned by {', '.join(sorted(own))}")

        # ---- E06: human gate states a decision and the accepted commit (same as commit.txt)
        hg = repo.read(d / "human-gate.md")
        if hg is None:
            e6.append(f"{tag}: no human-gate.md")
        else:
            accepted = [c for x in HASH.findall(hg) if (c := repo.resolve_commit(x))]
            if not accepted:
                e6.append(f"{tag}: human-gate.md names no existing commit (it must state the accepted hash)")
            elif listed and not set(accepted) & set(listed):
                e6.append(f"{tag}: human-gate.md accepts {accepted[0][:10]}, but commit.txt says {listed[0][:10]}")
            if not re.search(r"accept|reject", hg, re.I):
                e6.append(f"{tag}: human-gate.md doesn't say accepted or rejected")

        # ---- E07: information only: commits, repairs, and commits made after a later phase's
        repairs = len(repo.glob(d, "repair-*.md"))
        late = sorted((h for h in commits if h in order and any(
            order[h] > order[x] for k, xs in phase_commits.items() if k > n for x in xs)), key=order.get)
        e7.append(f"{tag}: {len(commits)} commit(s), {repairs} repair record(s)"
                  + (f"; {len(late)} came after a later phase's commit ({', '.join(h[:7] for h in late)})" if late else ""))

    out.add("E01", "Agent reports have every required field and a valid STATUS", "FAIL" if e1 else "PASS", e1)
    out.add("E02", "Each report's OWNER is an existing agent", "FAIL" if e2 else "PASS", e2)
    out.add("E03", "Files a report claims were really changed by that phase's commits", "FAIL" if e3 else "PASS", e3)
    out.add("E04", "Files the phase changed but its report doesn't list (undisclosed manual edits?)",
            "WARN" if e4 else "PASS", e4)
    out.add("E05", "Files changed in a phase belong to its OWNER (one writer, in practice)",
            "WARN" if e5 else ("PASS" if matchers else "INFO"),
            e5 or ([] if matchers else ["no ownership map to compare with"]))
    out.add("E06", "human-gate.md states a decision and the accepted commit, matching commit.txt",
            "FAIL" if e6 else "PASS", e6)
    out.add("E07", "Commits per phase (several commits, repairs and late fixes are allowed)", "INFO", e7)


# ======================================================================= C01-C03: copying
# Students are told to FOLLOW the tutorial, so one copied generic file is fine (C01 is a WARN).
# What the rubric gives zero is a fork that is mostly the tutorial, renamed or not (C02), or one
# that still mentions TaskForge (C03). Thresholds are judgement calls, to tune with real repos.
COPY_AT = 0.80      # a file is "copied" if >= 80% of its lines are in ONE tutorial file
MOSTLY = 0.50       # the control plane is "mostly copied" if > 50% of its files are copied
DATA = Path(__file__).resolve().parent.parent / "data"


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
    leftover = {}
    for t in repo.tracked:
        if not (is_control(t) or t.endswith((".scala", ".sbt", ".sh", ".tf", ".md", ".json", ".yml", ".yaml", ".conf"))):
            continue
        text = repo.read(t)
        if text and (n := len(re.findall(r"task\s*forge", text, re.I))):
            leftover[t] = n
    bad = {t for t in leftover if is_control(t) or t.endswith((".scala", ".sbt", ".sh", ".tf"))}
    out.add("C03", "No TaskForge leftovers in the control plane or code (README attribution is fine)",
            "FAIL" if bad else ("WARN" if leftover else "PASS"),
            [f"{t}: {n} mention(s) of TaskForge" for t, n in sorted(leftover.items(), key=lambda kv: -kv[1])][:15]
            + ([f"... and {len(leftover) - 15} more files"] if len(leftover) > 15 else []))
