"""
manifest.py: read datasets/dataset-manifest.yaml SAFELY and return only its structure.

Returns {dataset name: [field names]}. Values are read only to recognise DBLP and are never
returned or printed (they can hold bucket names, account IDs, URLs).

Safety: the file is written by the student. YAML "anchors/aliases" (&a / *a) let a few lines
expand into gigabytes in a full parser ("billion laughs"). So:
  - files with anchors/aliases are never given to a full parser (the built-in reader below never expands)
  - size: up to 200 KB with anchors, up to 5 MB without (1.0.8: a student's 200+ KB manifest without
    anchors was "not readable", a FAIL about the checker, not the student). Larger: CHECKER_LIMIT, a WARN.
  - PyYAML's safe_load is used only if it's installed AND the file has no anchors/aliases
  - otherwise a small built-in reader handles the two shapes the README's example implies:
        datasets:                 datasets:
          dblp:                     - name: dblp
            purpose: ...              purpose: ...
    It never expands anything. The result says which reader was used.
"""
import os
import re

MAX_BYTES = 200_000            # with anchors/aliases
MAX_PLAIN = 5_000_000          # without: nothing can expand
ANCHOR = re.compile(r"(^|[\s\[{,:-])[&*][A-Za-z0-9_-]")
CHECKER_LIMIT = "too large for the checker to read"   # callers report this as a WARN, never a FAIL


def read_manifest(text):
    """-> (datasets {name: [fields]}, has_dblp: bool, reader: str, error: str|None)"""
    size, anchors = len(text.encode()), bool(ANCHOR.search(text))
    if size > (MAX_BYTES if anchors else MAX_PLAIN):
        return {}, False, "none", f"{CHECKER_LIMIT} ({size // 1000} KB{', with YAML anchors' if anchors else ''}); not parsed"
    use_yaml = not anchors and not os.environ.get("SELFCHECK_NO_YAML")
    if use_yaml:
        try:
            import yaml
        except ImportError:
            use_yaml = False
    if use_yaml:
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as e:
            mark = getattr(e, "problem_mark", None)
            return {}, False, "PyYAML", f"YAML error{f' at line {mark.line + 1}' if mark else ''}"
        sets = (data or {}).get("datasets") if isinstance(data, dict) else None
        out = {}
        if isinstance(sets, dict):
            out = {str(k): sorted(map(str, v)) if isinstance(v, dict) else [] for k, v in sets.items()}
        elif isinstance(sets, list):
            for i, v in enumerate(sets):
                if isinstance(v, dict):
                    out[str(v.get("name") or v.get("id") or f"#{i + 1}")] = sorted(map(str, v))
        has_dblp = "dblp" in " ".join(out).lower() or "dblp" in str(sets).lower()
        return out, has_dblp, "PyYAML (safe_load)", None if sets is not None else "no top-level 'datasets:'"
    return _simple(text) + ("built-in reader", None) if "datasets:" in text else ({}, False, "built-in reader", "no top-level 'datasets:'")


def _simple(text):
    """Indentation-based reader for the 'datasets:' block (mapping or list form). Keys only."""
    lines = [l for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    out, has_dblp, i = {}, "dblp" in text.lower(), 0
    while i < len(lines) and not re.match(r"^datasets:\s*$", lines[i]):
        i += 1
    block = []
    for l in lines[i + 1:]:
        if not l.startswith((" ", "\t", "-")):
            break                                  # back at the top level: block ended
        block.append(l)
    if not block:
        return out, has_dblp
    indent = lambda l: len(l) - len(l.lstrip())
    child = indent(block[0])
    current, field_indent = None, None
    for l in block:
        n, body = indent(l), l.strip()
        if n == child and body.startswith("- "):          # list form: "- name: dblp"
            m = re.match(r"-\s+([\w.-]+):\s*(.*)$", body)
            current = f"#{len(out) + 1}"
            out[current] = []
            field_indent = n + 2
            if m:
                out[current].append(m.group(1))
                if m.group(1) in ("name", "id") and m.group(2):
                    out[m.group(2).strip("'\"")] = out.pop(current)
                    current = m.group(2).strip("'\"")
        elif n == child and (m := re.match(r"([\w.-]+):\s*$", body)):   # mapping form: "dblp:"
            current, field_indent = m.group(1), None
            out[current] = []
        elif current is not None and (m := re.match(r"([\w.-]+):", body)):
            field_indent = field_indent if field_indent is not None else n
            if n == field_indent:
                out[current].append(m.group(1))
                if m.group(1) in ("name", "id") and current.startswith("#"):
                    val = body.split(":", 1)[1].strip().strip("'\"")
                    if val:
                        out[val] = out.pop(current)
                        current = val
    return {k: sorted(set(v)) for k, v in out.items()}, has_dblp
