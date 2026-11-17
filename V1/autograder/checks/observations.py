"""
observations.py: X-checks. They never pass or fail anyone (always INFO). They RECORD what students
actually do where the README is ambiguous, so the next version can decide those checks from data:

  X01  dataset-manifest field names per dataset      -> which names to accept for the 17 prose fields
  X02  which named scripts exist, other script names -> "required scripts or equivalent commands"
  X03  per phase report: which "Report ..." items are -> how strictly to match report wording
       found (loose word match)
  X06  folder layout: folders to depth 2 + counts    -> where students put modules (Phase 4-10 checks)
  (X04 copy similarity is in always.py, X05 test counts in phase11_tests.py: they reuse that work.)

PRIVACY: only names, counts, yes/no. Never file contents, manifest values, report text or
headings, individual file names in the layout, git authors, or absolute paths. Only files tracked
by git (what the student submits) are looked at.
"""
import re
from collections import Counter
from pathlib import PurePosixPath

from ..manifest import read_manifest
from ..registry import check_group
from .requirements import TABLE, manifest_file

STOP = {"and", "the", "with", "from", "known", "exact", "complete", "any", "for", "of"}


def words(phrase):
    """Significant words of a report item: lowercase, 4+ letters, not a stop word."""
    return [w for w in re.split(r"[^a-z0-9]+", phrase.lower()) if len(w) >= 4 and w not in STOP]


@check_group(phase=0)
def observe(repo, out):
    # X01: manifest field names (never values)
    path, _ = manifest_file(repo)
    if path:
        sets, _, reader, err = read_manifest(repo.read(path) or "")
        if not err:
            names = Counter(f for fields in sets.values() for f in fields)
            out.add("X01", "Observation: field names used in the dataset manifest", "INFO",
                    [f"{len(sets)} datasets; field names: {', '.join(sorted(names))}", f"reader: {reader}"],
                    data={"datasets": len(sets), "fields": sorted(names)})

    # X02: named scripts present/missing + other script names under scripts/ (names only)
    named = TABLE["observe"]["scripts"]["named"]
    present = [s for s in named if s in repo.tracked]
    others = sorted({PurePosixPath(t).name for t in repo.tracked
                     if t.startswith("scripts/") and t not in named and t.endswith((".sh", ".py", ".sc", ".bash"))})
    if present or others:
        out.add("X02", "Observation: scripts present (README: 'required scripts or equivalent commands')", "INFO",
                [f"{len(present)} of {len(named)} named scripts present"]
                + ([f"missing: {', '.join(PurePosixPath(s).name for s in named if s not in present)}"] if len(present) < len(named) else [])
                + ([f"other scripts: {', '.join(others[:15])}"] if others else []),
                data={"present": [PurePosixPath(s).name for s in present],
                      "missing": [PurePosixPath(s).name for s in named if s not in present],
                      "other": others[:30]})

    # X03: for each phase report, which of its work order's "Report ..." items appear.
    #      An item counts as found if all its significant words appear anywhere in the report.
    found_by_phase = {}
    for d in repo.phases:
        n = repo.phase_number(d)
        items = TABLE["observe"]["report_items"].get(str(n))
        text = repo.read(d / "agent-report.md")
        if not items or text is None:
            continue
        low = set(re.split(r"[^a-z0-9]+", text.lower()))
        found_by_phase[f"phase-{n:02d}"] = {it: all(w in low for w in words(it)) for it in items}
    if found_by_phase:
        out.add("X03", "Observation: report items from each phase's work order found in its agent-report.md", "INFO",
                [f"{p}: {sum(v.values())} of {len(v)} items" + (f"; not found: {', '.join(k for k, ok in v.items() if not ok)}"
                                                                if not all(v.values()) else "")
                 for p, v in sorted(found_by_phase.items())],
                data=found_by_phase)

    # X06: folder layout, depth <= 2, file counts. Folder names only; no file names.
    layout = Counter()
    for t in repo.tracked:
        parts = PurePosixPath(t).parts[:-1]
        if parts and not parts[0].startswith("."):
            layout["/".join(parts[:2])] += 1
    if layout:
        top = layout.most_common(40)
        out.add("X06", "Observation: folder layout (folders to depth 2, tracked file counts)", "INFO",
                [", ".join(f"{d}/ {c}" for d, c in sorted(top))], data=dict(sorted(top)))
