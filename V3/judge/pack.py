"""
pack.py (V2): the EVIDENCE PACK for one category: which files the judge should start with.

Built deterministically from V1's file index (no AI, no searching by the model). The rubric's
"evidence" section says where to look:
    "sources": [{"key": ["spark", "files"]}, {"key": ["tests", "files"], "contains": "spark"}, ...],
    "phases":  [6],          # that phase's evidence files (reports, gate)
    "max_files": 60          # cost cap; the judge may still read beyond the pack (and must, for "missing")

The pack is DATA derived from the student's repo (file names are student-controlled), so it goes
into the user message only, never into the system prompt.
"""
import re


def _get(index, key):
    v = index
    for k in key:
        v = v.get(k, {}) if isinstance(v, dict) else {}
    return v


def _paths(value):
    """Paths from an index value: a list of paths or 'path:line' strings, or a dict keyed by path."""
    items = value.keys() if isinstance(value, dict) else value if isinstance(value, list) else []
    return [re.sub(r":\d+(?::.*)?$", "", str(x)) for x in items if isinstance(x, str)]


def build(index, rubric, tracked):
    ev = rubric["evidence"]
    tracked = set(tracked)
    out = []
    for src in ev.get("sources", []):
        if "tracked_contains" in src:               # every tracked code file whose path names the area
            out += sorted(p for p in tracked if src["tracked_contains"].lower() in p.lower()
                          and p.endswith(tuple(src.get("suffixes", [".scala", ".java", ".py"]))))
            continue
        for p in _paths(_get(index, src["key"])):
            if src.get("contains") and src["contains"].lower() not in p.lower():
                continue
            out.append(p)
    for n in ev.get("phases", []):
        for name, ph in (index.get("phases") or {}).items():
            if isinstance(ph, dict) and ph.get("number") == n:
                for k in ("agent_report", "human_gate", "prompt"):
                    out += ph.get(k, [])
    seen, pack = set(), []
    for p in out:                                   # keep order, drop duplicates and non-tracked paths
        if p in tracked and p not in seen:
            seen.add(p)
            pack.append(p)
    return pack[: ev.get("max_files", 60)]
