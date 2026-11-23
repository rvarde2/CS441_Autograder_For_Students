"""
requirements.py: the TABLE MODULE. Checks defined as rows in data/phase_requirements.json.

Each row has an id, the phase it's due, a kind, a level (FAIL or WARN when not met), a title, and
the README sentence it enforces (`rule`). This code knows how to check each KIND; the rows say
WHAT to check. A README change means editing a row, not this file.

Where files are looked for:
  - an exact path from the README is checked at that path. If it's missing there but a tracked
    file with the same NAME exists elsewhere, that's a WARN saying where it was found
    ("Directory names may change", but the work order named this path).
  - names without a location (Scala records) are searched in every tracked .scala file.
  - only files tracked by git are searched: what the student submits. Nothing else is read.
"""
import json
import re
from pathlib import Path, PurePosixPath

from ..manifest import CHECKER_LIMIT, read_manifest
from ..registry import check_group

TABLE = json.loads((Path(__file__).resolve().parent.parent / "data" / "phase_requirements.json").read_text())


def _tracked_set(repo):
    return set(repo.tracked)


def _find_by_name(repo, path):
    """Tracked files elsewhere with the same file name as `path` (for 'found at X instead')."""
    name = PurePosixPath(path).name
    return sorted(t for t in repo.tracked if PurePosixPath(t).name == name and t != path)


def _dir_files(repo, d):
    d = d.rstrip("/") + "/"
    return [t for t in repo.tracked if t.startswith(d) and PurePosixPath(t).name != ".gitkeep"]


def _locate(repo, path):
    """-> (status 'here'|'elsewhere'|'missing', where)"""
    if path in _tracked_set(repo):
        return "here", path
    other = _find_by_name(repo, path)
    return ("elsewhere", other) if other else ("missing", None)


def k_paths(repo, row):
    bad, moved = [], []
    for p in row["paths"]:
        st, where = _locate(repo, p)
        if st == "elsewhere":
            moved.append(f"{p}: not there, but found at {', '.join(where[:3])} (the work order names {p})")
        elif st == "missing":
            bad.append(f"{p}: missing")
    return ("FAIL" if bad else "WARN" if moved else "PASS"), bad + moved


def k_dirs_not_empty(repo, row):
    bad, moved = [], []
    for d in row["paths"]:
        if _dir_files(repo, d):
            continue
        last = PurePosixPath(d).name
        others = sorted({str(PurePosixPath(t).parent) for t in repo.tracked
                         if PurePosixPath(t).parent.name == last and str(PurePosixPath(t).parent) != d})
        if others:
            moved.append(f"{d}/: empty or missing, but {', '.join(o + '/' for o in others[:3])} has files")
        else:
            bad.append(f"{d}/: missing or has no files (a .gitkeep alone doesn't count)")
    return ("FAIL" if bad else "WARN" if moved else "PASS"), bad + moved


def scala_definitions(repo, names):
    """{name: "file:line"} of the first definition of each name in tracked .scala files.
    A definition, not a mention: optional modifiers, the keyword, the exact name; comments skipped."""
    found = {}
    defn = re.compile(r"^\s*(?:(?:final|sealed|abstract|private|protected|implicit|opaque|case)\s+)*"
                      r"(?:class|trait|object|enum|type)\s+(" + "|".join(map(re.escape, names)) + r")\b")
    for t in repo.tracked:
        if not t.endswith(".scala"):
            continue
        for i, line in enumerate((repo.read(t) or "").splitlines(), 1):
            if line.lstrip().startswith(("//", "*", "/*")):
                continue                            # commented out: doesn't count
            if (m := defn.match(line)) and m.group(1) not in found:
                found[m.group(1)] = f"{t}:{i}"
    return found


def k_scala_defines(repo, row):
    found = scala_definitions(repo, row["names"])
    missing = [n for n in row["names"] if n not in found]
    return ("FAIL" if missing else "PASS"), (
        [f"not defined in any tracked .scala file: {', '.join(missing)}"] if missing else []) + [
        f"{len(row['names']) - len(missing)} of {len(row['names'])} defined"]


def k_markdown_heading(repo, row):
    text = repo.read(row["path"])
    if text is None:
        return "FAIL", [f"{row['path']} missing"]
    rx = re.compile(r"^\s{0,3}#{1,6}\s*" + re.escape(row["heading"]) + r"\s*#*\s*$", re.I | re.M)
    return ("PASS", []) if rx.search(text) else ("FAIL", [f"no heading named '{row['heading']}' in {row['path']}"])


def manifest_file(repo):
    """The manifest's location: the README's path, else a same-named tracked file elsewhere."""
    st, where = _locate(repo, "datasets/dataset-manifest.yaml")
    return {"here": where, "elsewhere": (where or [None])[0], "missing": None}[st], st


def k_manifest(repo, row):
    path, st = manifest_file(repo)
    if path is None:
        return "FAIL", [f"{row['path']}: missing"]
    sets, _, reader, err = read_manifest(repo.read(path) or "")
    msgs = [] if st == "here" else [f"found at {path} instead of {row['path']}"]
    if err:
        return ("WARN" if err.startswith(CHECKER_LIMIT) else "FAIL"), msgs + [f"{path}: {err} (reader: {reader})"]
    if not sets:
        return "FAIL", msgs + [f"{path}: 'datasets:' has no entries (reader: {reader})"]
    return ("WARN" if msgs else "PASS"), msgs + [f"{len(sets)} dataset entries (reader: {reader})"]


def k_manifest_datasets(repo, row):
    path, _ = manifest_file(repo)
    if path is None:
        return "FAIL", ["no manifest (see M01)"]
    sets, has_dblp, reader, err = read_manifest(repo.read(path) or "")
    if err:
        return (("WARN", ["the checker could not read the manifest (see M01): a human checks the datasets"])
                if err.startswith(CHECKER_LIMIT) else ("FAIL", ["manifest not readable (see M01)"]))
    problems = []
    if not has_dblp:
        problems.append("no DBLP entry")
    if len(sets) < row["min_datasets"]:
        problems.append(f"{len(sets)} dataset entries; need DBLP plus at least {row['min_datasets'] - 1} more")
    return ("FAIL" if problems else "PASS"), problems + [f"entries: {', '.join(sorted(sets))}"]


def index_value(repo, row):
    """What a table row found, for the JSON file index: locations, never contents."""
    kind = row["kind"]
    if kind == "paths":
        return {p: (where if st == "here" else where[0] if st == "elsewhere" else None)
                for p in row["paths"] for st, where in [_locate(repo, p)]}
    if kind == "dirs_not_empty":
        return {d: _dir_files(repo, d) for d in row["paths"]}
    if kind == "scala_defines":
        found = scala_definitions(repo, row["names"])
        return {n: found.get(n) for n in row["names"]}
    if kind == "markdown_heading":
        return {"file": row["path"] if repo.is_file(row["path"]) else None,
                "found": k_markdown_heading(repo, row)[0] == "PASS"}
    if kind == "manifest":
        path, _ = manifest_file(repo)
        sets = read_manifest(repo.read(path) or "")[0] if path else {}
        return {"path": path, "datasets": sets}           # dataset names and FIELD NAMES only
    return None


KINDS = {"paths": k_paths, "dirs_not_empty": k_dirs_not_empty, "scala_defines": k_scala_defines,
         "markdown_heading": k_markdown_heading, "manifest": k_manifest, "manifest_datasets": k_manifest_datasets}


@check_group(phase=0)          # the real phase comes from each row (due=...)
def table_checks(repo, out):
    for row in TABLE["checks"]:
        status, details = KINDS[row["kind"]](repo, row)
        if status == "FAIL" and row.get("level") == "WARN":
            status = "WARN"
        if status != "PASS":
            details = details + [f"README: \"{row['rule']}\""]
        out.add(row["id"], row["title"], status, details, due=row["phase"])
        if row.get("index"):
            out.record(*row["index"], value=index_value(repo, row))
