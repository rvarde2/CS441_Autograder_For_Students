"""
Checks due by PHASE 1, "the factory builds the ScholarChain factory": the agent control plane.

  F01, F03-F07   control-plane files, reviewers, JSON, hooks, floor invariants, MCP secrets
  O01-O06        ownership map: one writer per artifact
  R01-R08        ScholarChain-specific content (things the TaskForge tutorial does NOT have)

Rule sources (ScholarChain README): "Phase 0" work order (floor invariants), "Required factory
artifacts" table, "Required hook and permission behavior", "Agent authority and ownership matrix",
deductions "Agents share overlapping write ownership without documented control" and
"Reviewer modifies production code".

Note: F01/F02/F04/F05 alone can be passed by copying the tutorial. They only report presence;
the C-checks (always.py) and R-checks below are what a copy can't pass.
"""
import json
import re

from ..ownership import covers
from ..registry import check_group
from ..repo import WRITE_TOOLS


# ======================================================================= F: control plane
@check_group(phase=1)
def control_plane(repo, out):
    # F01: the files every ScholarChain repo must contain.
    required = ["CLAUDE.md", "docs/agents.md", ".claude/settings.json", ".mcp.json"]
    missing = [f for f in required if repo.read(f) is None]
    if not repo.agent_files:
        missing.append(".claude/agents/*.md")
    if not repo.hook_files:
        missing.append(".claude/hooks/*")
    out.add("F01", "Control-plane files present (CLAUDE.md, docs/agents.md, settings, .mcp.json, agents, hooks)",
            "FAIL" if missing else "PASS",
            [f"missing: {m}" for m in missing]
            + [f"{len(repo.agent_files)} agents, {len(repo.hook_files)} hooks, {len(repo.command_files)} commands"])

    # F03: "Forbid reviewer agents from receiving write tools." A reviewer is any agent with
    # "review" in its name. Bash can write files too, so it's a WARN for a human to judge.
    fail, warn = [], []
    reviewers = [n for n in repo.agents if "review" in n.lower()]
    for name in reviewers:
        a = repo.agents[name]
        if (w := WRITE_TOOLS & set(a["tools"])):
            fail.append(f"{name} ({a['file']}) has write tools: {', '.join(sorted(w))}")
        if "Bash" in a["tools"]:
            warn.append(f"{name} ({a['file']}) has Bash, which can write files; check its body forbids that")
    out.add("F03", "Reviewer agents have no write tools",
            "FAIL" if fail or not reviewers else ("WARN" if warn else "PASS"),
            fail + warn + ([] if reviewers else ["no agent with 'review' in its name"]))

    # F04: "Require JSON parsing". settings.local.json is optional, so only its syntax matters.
    bad = []
    for f in [".claude/settings.json", ".mcp.json", ".claude/settings.local.json"]:
        _, err = repo.load_json(f)
        if err and not (err == "missing" and f.endswith("local.json")):
            bad.append(f"{f}: {err}")
    out.add("F04", "Settings and MCP config are valid JSON", "FAIL" if bad else "PASS", bad)

    # F05: "shell syntax checks, executable-bit checks". Every hook script referenced from
    # settings.json must exist, be executable, and parse. `bash -n` PARSES, it never runs the script.
    problems = []
    for event, entries in repo.hook_cfg.items():
        for e in entries or []:
            for h in e.get("hooks", []) or []:
                cmd = (h.get("command") or "").strip()
                first = cmd.split()[0] if cmd else ""
                if not (first.endswith(".sh") or first.startswith((".claude/", "./"))):
                    problems.append(f"{event}: inline command (not a script file): {cmd[:80]}")
                    continue
                rel = first.replace("$CLAUDE_PROJECT_DIR/", "").replace('"', "")
                if not repo.is_file(rel):
                    problems.append(f"{event}: {first} does not exist")
                    continue
                if not repo.is_executable(rel):
                    problems.append(f"{event}: {first} is not executable")
                if (err := repo.bash_syntax_error(rel)):
                    problems.append(f"{event}: {first} has a shell syntax error: {err[:120]}")
    hard = any(k in x for x in problems for k in ("does not exist", "not executable", "syntax"))
    out.add("F05", "Hook scripts exist, are executable, and pass `bash -n`",
            "FAIL" if hard else ("WARN" if problems else "PASS"), problems)

    # F06: Phase 0 "floor invariants": deny rules and hooks that must always exist.
    deny = repo.permissions.get("deny", []) or []

    def has_deny(*words):
        return any(all(w in d for w in words) for d in deny)

    def has_hook(event, matcher_word=None):
        return any(matcher_word is None or matcher_word in (e.get("matcher") or "")
                   for e in repo.hook_cfg.get(event, []) or [])

    floors = {
        "deny: secret reads (.env)": has_deny("Read", ".env"),
        "deny: terraform apply": has_deny("terraform apply"),
        "deny: terraform destroy": has_deny("terraform destroy"),
        "deny: force push": has_deny("git push", "--force") or has_deny("git push", "-f"),
        "deny: a destructive AWS command": any(d.startswith("Bash(aws") and re.search(r"delete|terminate|destroy", d)
                                               for d in deny),
        "hook: dangerous-command guard (PreToolUse on Bash)": has_hook("PreToolUse", "Bash"),
        "hook: test gate (Stop)": has_hook("Stop"),
        "hook: formatter (PostToolUse on Edit/Write)": has_hook("PostToolUse", "Edit") or has_hook("PostToolUse", "Write"),
    }
    gaps = [k for k, ok in floors.items() if not ok]
    out.add("F06", "Floor invariants present (deny rules + guard/test/format hooks)",
            "FAIL" if gaps else "PASS", [f"missing {g}" for g in gaps])

    # F07: ".mcp.json with secret values omitted and environment-variable names preserved".
    # Only settings whose NAME looks secret are checked: ALLOW_WRITE=false is just config.
    secretish = re.compile(r"key|token|secret|passw|auth|credential|url|dsn", re.I)
    env_ref = re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*(:-[^}]*)?\}")
    literal = [f"server '{s}', {field} '{k}' looks secret but is a literal value; value not shown"
               for s, cfg in (repo.mcp.get("mcpServers", {}) or {}).items()
               for field in ("env", "headers") for k, v in (cfg.get(field) or {}).items()
               if isinstance(v, str) and secretish.search(k) and not env_ref.fullmatch(v.strip())]
    out.add("F07", ".mcp.json: secret-looking settings use ${VAR} references, not literal values",
            "FAIL" if literal else "PASS", literal)


# ======================================================================= O: ownership
@check_group(phase=1)
def ownership(repo, out):
    own = repo.ownership
    rows, agents = own["rows"], repo.agents
    if not rows:
        out.add("O01", "Ownership map found and readable", "FAIL",
                [f"source: {own['source']}", "no writer rows found"] + own["rejected"])
        return

    # O01: the map exists and every writer it names has an agent file.
    unknown = sorted({r["agent"] for r in rows if r["agent"] not in agents})
    out.add("O01", "Ownership map found and readable; every writer has an agent file",
            "FAIL" if unknown or own["rejected"] else "PASS",
            [f"source: {own['source']}",
             f"{len(rows)} writer rows, {len({r['path'] for r in rows})} artifacts, "
             f"{len({r['agent'] for r in rows})} writing agents"]
            + [f"writer '{u}' has no file in .claude/agents/" for u in unknown]
            + [f"REJECTED (citation failed): {x}" for x in own["rejected"]])

    # O02: one writer per artifact. Overlaps are allowed only with "documented control", which
    # code can't judge, so they're WARNs. Exact duplicates (same path, 2 agents) and nested
    # patterns (db/migration inside src/main/**) are both reported.
    by_path = {}
    for r in rows:
        if r["kind"] == "files":
            by_path.setdefault(r["path"], []).append(r)

    def who(rs):
        return ", ".join(f"{r['agent']} ({r['role']}{': ' + r['condition'] if r['condition'] else ''}; {r['where']})"
                         for r in rs)

    overlaps = [f"`{p}` has {len({r['agent'] for r in rs})} writers: {who(rs)}"
                for p, rs in by_path.items() if len({r["agent"] for r in rs}) > 1]
    for outer in by_path:
        for inner in by_path:
            oa, ia = {r["agent"] for r in by_path[outer]}, {r["agent"] for r in by_path[inner]}
            if covers(outer, inner) and ia - oa:
                overlaps.append(f"`{inner}` ({', '.join(sorted(ia))}) lies inside `{outer}` ({', '.join(sorted(oa))})")
    out.add("O02", "One writer per artifact (each overlap must have documented control; judge below)",
            "WARN" if overlaps else "PASS", overlaps)

    # O03: an agent said to write files needs a tool that can write (ownership vs tool fence).
    fence = []
    for name in sorted({r["agent"] for r in rows if r["kind"] == "files" and r["agent"] in agents}):
        tools = set(agents[name]["tools"])
        if not tools & WRITE_TOOLS:
            how = "only via Bash" if "Bash" in tools else "no tool can write"
            fence.append(f"{name} is said to write files but has no Write/Edit ({how}); tools: {', '.join(sorted(tools))}")
    out.add("O03", "Writers have write tools (ownership matches the tool fence)", "WARN" if fence else "PASS", fence)

    # O06: names as written vs mapped by the AI. A name that looks like an agent name but has no
    # file is a FAIL; a short form in prose ("implementer") mapped by the AI is a WARN.
    mapped = sorted({(r["name_as_written"], r["agent"], r["where"]) for r in rows
                     if r.get("name_as_written") and r["name_as_written"] != r["agent"]})
    no_file = [m for m in mapped if re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)+", m[0]) and m[0] not in agents]
    out.add("O06", "Writer names as written match an agent file (AI mappings are shown, not trusted)",
            "FAIL" if no_file else ("WARN" if mapped else "PASS"),
            [f"{w}: '{a}' looks like an agent name but has no file; AI mapped it to '{b}'" for a, b, w in no_file]
            + [f"{w}: '{a}' mapped by the AI to '{b}'" for a, b, w in mapped if (a, b, w) not in no_file])

    # O04, O05: information only.
    writing = {r["agent"] for r in rows}
    out.add("O04", "Agents that write nothing (fine for reviewers/operators)", "INFO",
            sorted(n for n in agents if n not in writing) or ["none"])
    if own["notes"]:
        out.add("O05", "Ambiguities the AI flagged for a human", "INFO", own["notes"])


# ======================================================================= R: ScholarChain content
REQUIRED_HOOKS = ["guard-dangerous.sh", "format-scala.sh", "verify-tests-ran.sh", "validate-agent-files.sh"]
# command -> the agent the README says it routes to (None: README names no agent)
REQUIRED_COMMANDS = {"deploy": "deploy-engineer", "rollback": None, "incident": "incident-responder",
                     "run-pipeline": None, "experiment": "experiment-engineer"}
# "Blocks destructive AWS, Terraform, Git, database, S3, Neptune, DynamoDB, and vector-index commands."
GUARD_CATEGORIES = {
    "AWS (delete/terminate)": r"\baws\b.*\b(delete|terminate|rb\b)",
    "Terraform":              r"terraform.*\b(destroy|apply)",
    "Git":                    r"\bgit\b.*(push.*(-f\b|force)|reset\s+--hard|clean\s+-|branch\s+-D)",
    "database":               r"drop\s*\(?\s*(table|database)|truncate|delete\s+from",
    "S3":                     r"\bs3\b.*\b(rb|rm)\b|delete-bucket|s3api\s+delete",
    "Neptune":                r"neptune.*delete|delete.*neptune",
    "DynamoDB":               r"dynamodb.*delete|delete-table",
    "vector index":           r"s3vectors.*delete|delete-(index|vector-bucket)|vector.*delete",
}


def code_lines(text):
    """Non-comment lines: '# TODO: block neptune' must not count as blocking Neptune."""
    return [l for l in (text or "").splitlines() if l.strip() and not l.strip().startswith("#")]


@check_group(phase=1)
def scholarchain_content(repo, out):
    # R01: the four hooks the "Required factory artifacts" table names.
    miss = []
    for h in REQUIRED_HOOKS:
        if not repo.is_file(f".claude/hooks/{h}"):
            miss.append(f".claude/hooks/{h}: missing")
        elif not repo.is_executable(f".claude/hooks/{h}"):
            miss.append(f".claude/hooks/{h}: not executable")
    out.add("R01", "Required hooks: guard-dangerous, format-scala, verify-tests-ran, validate-agent-files",
            "FAIL" if miss else "PASS", miss)

    # R02: the five commands the table names.
    miss = [f".claude/commands/{c}.md: missing" for c in REQUIRED_COMMANDS if repo.read(f".claude/commands/{c}.md") is None]
    out.add("R02", "Required commands: deploy, rollback, incident, run-pipeline, experiment",
            "FAIL" if miss else "PASS", miss)

    # R03: the guard hook mentions every category, on non-comment lines. STATIC only: proving it
    # really blocks means running the hook, which runs student code (needs a sandbox; not in V1).
    guard = repo.read(".claude/hooks/guard-dangerous.sh")
    if guard is None:
        out.add("R03", "guard-dangerous.sh covers every destructive category ScholarChain names", "FAIL",
                ["guard-dangerous.sh missing"])
    else:
        lines = code_lines(guard)
        gaps = [c for c, rx in GUARD_CATEGORIES.items() if not any(re.search(rx, l, re.I) for l in lines)]
        out.add("R03", "guard-dangerous.sh covers every destructive category ScholarChain names",
                "FAIL" if gaps else "PASS",
                [f"no pattern for: {c}" for c in gaps]
                + [f"{len(GUARD_CATEGORIES) - len(gaps)} of {len(GUARD_CATEGORIES)} categories present (static; not run)"])

    # R04: "Explicit allow and deny rules plus PreToolUse, PostToolUse, and Stop hooks".
    problems = [f"no {k} rules" for k in ("allow", "deny") if not repo.permissions.get(k)]
    problems += [f"no {e} hook" for e in ("PreToolUse", "PostToolUse", "Stop") if not repo.hook_cfg.get(e)]
    out.add("R04", "settings.json has explicit allow AND deny rules, and PreToolUse, PostToolUse, Stop hooks",
            "FAIL" if problems else "PASS", problems)

    # R05: commands route to agents that exist; scripts they run exist (WARN: often a later phase).
    fail, warn = [], []
    agent_ref = re.compile(r"\b([a-z0-9]+(?:-[a-z0-9]+)*-(?:engineer|responder|reviewer|agent|updater|migrator|implementer))\b")
    for c, target in REQUIRED_COMMANDS.items():
        text = repo.read(f".claude/commands/{c}.md")
        if text is None:
            continue                      # R02 reports it
        if target and target not in text:
            fail.append(f"{c}.md does not route to {target} (README: routes to `{target}`)")
        elif target and target not in repo.agents:
            fail.append(f"{c}.md routes to {target}, but .claude/agents/{target}.md does not exist")
        fail += [f"{c}.md mentions agent '{ref}', which has no file"
                 for ref in agent_ref.findall(text) if ref not in repo.agents and ref != target]
        warn += [f"{c}.md runs {s}, which doesn't exist yet"
                 for s in re.findall(r"\b(scripts/[\w./-]+\.sh)\b", text) if not repo.is_file(s)]
    out.add("R05", "Commands route to agents that exist (deploy, incident, experiment are named by the README)",
            "FAIL" if fail else ("WARN" if warn else "PASS"), sorted(set(fail)) + warn)

    # R06: CLAUDE.md: "Project identity ... and import of docs/agents.md".
    cm = repo.read("CLAUDE.md")
    problems = []
    if cm is None:
        problems.append("CLAUDE.md missing")
    else:
        if not re.search(r"^\s*@docs/agents\.md\b", cm, re.M):
            problems.append("does not import docs/agents.md (a line '@docs/agents.md')")
        if not re.search(r"scholar\s*chain|dblp", cm, re.I):
            problems.append("does not identify the project (no 'ScholarChain' or 'DBLP')")
    out.add("R06", "CLAUDE.md identifies ScholarChain and imports docs/agents.md", "FAIL" if problems else "PASS", problems)

    # R07: ".mcp.json: Read-only or least-privilege GitHub, AWS API, Terraform, and documentation
    # tools". Presence only (least privilege needs judgement). Unpinned @latest servers can change.
    servers = repo.mcp.get("mcpServers", {}) or {}
    blob = [(n + " " + json.dumps(s)).lower() for n, s in servers.items()]
    want = {"GitHub": r"github", "AWS API": r"aws-api|aws_api|call_aws",   # not '\baws\b': that matched aws-documentation
            "Terraform": r"terraform", "documentation": r"doc"}
    problems = [f"no {k} server" for k, rx in want.items() if not any(re.search(rx, b) for b in blob)]
    problems += [f"server '{n}' uses @latest: it can change under you (pin a version)"
                 for n, s in servers.items() if "@latest" in json.dumps(s)]
    out.add("R07", ".mcp.json has GitHub, AWS API, Terraform and documentation servers (least privilege: judged later)",
            "WARN" if problems else "PASS", problems)

    # R08: docs/agents.md: "One-writer ownership map, lifecycle routing table, authority
    # boundaries, escalation policy, and human gates". Wording varies: keyword hints only.
    da = (repo.read("docs/agents.md") or "").lower()
    parts = {"ownership map": r"owner", "routing/lifecycle table": r"routing|lifecycle",
             "authority boundaries": r"authority|boundar|may not|never", "escalation policy": r"escalat",
             "human gates": r"human"}
    problems = [f"no sign of: {k}" for k, rx in parts.items() if not re.search(rx, da)]
    out.add("R08", "docs/agents.md covers ownership, routing, authority, escalation, human gates (keyword hint)",
            "WARN" if problems else "PASS", problems)
