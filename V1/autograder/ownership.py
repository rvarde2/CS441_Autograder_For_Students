"""
ownership.py: who may write what, as ROWS. Used by the phase-1 O-checks and by E05 (did the
files a phase changed belong to the agent that did the phase?).

A row = {path, kind, agent, role, condition, where[, name_as_written]}; one row per
(artifact path, writing agent). An artifact with two writers has two rows.

Two sources, ONE set of checks on top:
  1. AI extraction (--ownership FILE, made by extract_ownership.sh). Claude reads docs/agents.md,
     CLAUDE.md and the agent files, and returns rows in ownership.schema.json's shape, each citing
     file + line + an exact quote. The AI only READS; this module VERIFIES every citation
     (file exists, line in range, quote and name on that line) and rejects rows that fail.
     `name_as_written` is copied exactly from the source, so the AI can't silently "repair" a
     wrong agent name (it did once: oncall-agent -> incident-responder).
  2. Built-in parser (default): the markdown table in docs/agents.md, paths in backticks in
     column 1, owners in **bold** in column 2. Misses writers named in prose or other columns.
"""
import json
import re
from pathlib import Path


def build(repo):
    """Returns {rows, rejected, source, notes}."""
    if repo.ownership_file:
        return _from_ai(repo, json.loads(Path(repo.ownership_file).read_text()))
    return _from_table(repo)


def _from_ai(repo, data):
    rows, rejected = [], []
    agents = repo.agents
    for r in data.get("writers", []):
        text = repo.read(r["source_file"])
        lines = text.splitlines() if text is not None else []
        n = r["source_line"]
        where = f"{r['source_file']}:{n}"
        if text is None:
            rejected.append(f"{where}: cited file does not exist")
        elif not (1 <= n <= len(lines)):
            rejected.append(f"{where}: line out of range (file has {len(lines)} lines)")
        elif r["quote"].strip() not in lines[n - 1]:
            rejected.append(f"{where}: quote not found on that line: {r['quote'][:60]!r}")
        elif (r.get("name_as_written") and r["name_as_written"] not in lines[n - 1]
              # an agent's own file says "you own X" without naming itself: that's fine
              and not (r["name_as_written"] == r["agent"] in agents
                       and agents[r["agent"]]["file"] == r["source_file"])):
            rejected.append(f"{where}: name_as_written {r['name_as_written']!r} is not on that line")
        else:
            rows.append({**r, "where": where})
    return {"rows": rows, "rejected": rejected, "notes": data.get("notes", []),
            "source": f"AI extraction ({Path(repo.ownership_file).name}), citations verified by code"}


def _from_table(repo):
    rows = []
    for i, line in enumerate((repo.read("docs/agents.md") or "").splitlines(), 1):
        if not line.startswith("|") or "---" in line:
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 2:
            continue
        for p in re.findall(r"`([^`]+)`", cols[0]):
            for name in re.findall(r"\*\*([a-z0-9-]+)\*\*", cols[1]):
                rows.append({"path": p, "kind": "files", "agent": name, "role": "owner",
                             "condition": "", "where": f"docs/agents.md:{i}"})
    return {"rows": rows, "rejected": [], "notes": [],
            "source": "fallback parse of docs/agents.md table (misses prose and secondary columns)"}


# ---------------------------------------------------------------------- path patterns
def prefix(p):
    """Literal part of a pattern before its first wildcard: 'src/main/**' -> 'src/main/'."""
    return re.split(r"[*?\[]", p)[0]


def covers(outer, inner):
    """True if pattern `outer` (like 'src/main/**') contains pattern `inner` (like 'src/main/x/*.sql')."""
    return outer != inner and outer.endswith("**") and prefix(inner).startswith(prefix(outer))


def glob_rx(repo, pat):
    """Ownership pattern -> regex over repo-relative file paths.
    '**' = any depth, '*' = within one folder. A plain folder name means everything under it.
    Careful: strip a leading './' only. lstrip('./') would also eat the dot of '.claude/'
    (a real bug in an earlier version: no '.claude/**' pattern ever matched)."""
    pat = pat.strip()
    pat = pat[2:] if pat.startswith("./") else pat
    if not re.search(r"[*?]", pat) and (pat.endswith("/") or repo.is_dir(pat)):
        pat = pat.rstrip("/") + "/**"
    rx = (re.escape(pat).replace(r"\*\*", "\0").replace(r"\*", "[^/]*")
          .replace(r"\?", "[^/]").replace("\0", ".*"))
    return re.compile(rx + r"$")


def owner_matchers(repo):
    """[(regex, agent)] for every file-kind ownership row."""
    return [(glob_rx(repo, r["path"]), r["agent"]) for r in repo.ownership["rows"]
            if r.get("kind", "files") == "files"]
