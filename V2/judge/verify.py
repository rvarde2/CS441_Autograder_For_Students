"""
verify.py (V2): code checks on ONE AI answer. Trusts only the repository and the trace, never the
model's word. Verdicts can only move TOWARDS cannot_tell (never upgraded), so code can't invent credit.

  V1  answer valid against the category schema (re-checked here, not left to the AI tool)  -> reject run
  V2  every item judged exactly once; every deduction answered once                         -> reject run
  V3  each citation: file inside the repo, lines exist, quote really on those lines         -> citation dropped
      (lines off by up to 2 are accepted and noted: models miscount)
  V4  met/partial with no verified citation left                                            -> cannot_tell
      deduction "applies: yes" with no verified citation                                    -> cannot_tell
  V5  missing: absence_check written AND at least one Grep/Glob in the trace                -> else cannot_tell
      (if searches exist but none appears in absence_check: kept, flagged)
  V6  every HIGH pre-scan finding in a file the judge opened or was given must be in
      integrity_notes (same file; line within 2, or any line for file-name findings)        -> flag
  V7  known links to V1 facts (rubric "v1_links") contradicted                              -> flag (not overruled)
  V8  coverage: share of the evidence pack the judge actually opened                        -> flag if < 50%
  V9  low confidence, cannot_tell, any flag                                                 -> human queue
"""
import re
import sys
from pathlib import Path, PurePosixPath

import jsonschema

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))     # V1's autograder package (our code)

WS = re.compile(r"\s+")
LINE_SLACK = 2


def _norm(s):
    return WS.sub(" ", s).strip()


def _rel(repo, f):
    """Repo-relative path for a cited file, or None if it is outside the repo / not a file."""
    p = PurePosixPath(str(f).replace("\\", "/"))
    if p.is_absolute():
        try:
            p = PurePosixPath(Path(str(p)).resolve().relative_to(repo.root))
        except ValueError:
            return None
    s = str(p)
    s = s[2:] if s.startswith("./") else s
    return s if repo.is_file(s) else None


def check_citation(repo, c):
    """-> (ok, note). ok only if the exact quote is in the cited lines (+-LINE_SLACK)."""
    rel = _rel(repo, c["file"])
    if rel is None:
        return False, f"{c['file']}: not a file in this repository"
    lines = (repo.read(rel) or "").splitlines()
    a, b = c["line_start"], c["line_end"]
    if a > b or a < 1 or a > len(lines):
        return False, f"{rel}:{a}-{b}: lines don't exist (file has {len(lines)})"
    q = _norm(c["quote"])
    if not q:
        return False, f"{rel}:{a}-{b}: empty quote"
    if q in _norm(" ".join(lines[a - 1:b])):
        return True, ""
    lo, hi = max(1, a - LINE_SLACK), min(len(lines), b + LINE_SLACK)
    if q in _norm(" ".join(lines[lo - 1:hi])):
        return True, f"{rel}: quote found within {LINE_SLACK} lines of {a}-{b}"
    return False, f"{rel}:{a}-{b}: quote not found on those lines"


def _absence_ok(absence_check, searches):
    if not absence_check.strip():
        return "none"
    if not searches:
        return "no_search"
    text = absence_check.lower()
    for _tool, pattern, _path in searches:
        words = [w for w in re.split(r"[^a-z0-9_]+", pattern.lower()) if len(w) >= 3]
        if pattern.lower() in text or any(w in text for w in words):
            return "matched"
    return "unmatched"


def verify(answer, schema, rubric, repo, opened, searches, prescan, pack, v1_results, v1_index):
    report = {"rejected": [], "items": {}, "deductions": {}, "integrity": {}, "flags": [], "coverage": None}

    # V1, V2: shape and completeness
    errs = [e.message[:160] for e in jsonschema.Draft202012Validator(schema).iter_errors(answer)]
    if errs:
        report["rejected"] = [f"schema: {e}" for e in errs[:10]]
        return report
    item_ids = [i["id"] for i in rubric["items"]]
    got = [i["item_id"] for i in answer["items"]]
    if sorted(got) != sorted(item_ids):
        report["rejected"].append(f"items judged {got}, expected each of {item_ids} once")
    ded_ids = [d["id"] for d in rubric["deductions"]]
    if sorted(d["deduction_id"] for d in answer["deductions"]) != sorted(ded_ids):
        report["rejected"].append("deductions not answered exactly once each")
    if report["rejected"]:
        return report

    # V3-V5: items
    for it in answer["items"]:
        notes, good = [], []
        for c in it["citations"]:
            ok, note = check_citation(repo, c)
            (good.append(c) if ok else None)
            if note:
                notes.append(("" if ok else "dropped: ") + note)
        verdict, flags = it["verdict"], []
        if verdict in ("met", "partial") and not good:
            verdict, flags = "cannot_tell", ["unsupported: no verified citation"]
        if it["verdict"] == "missing":
            a = _absence_ok(it["absence_check"], searches)
            if a in ("none", "no_search"):
                verdict, flags = "cannot_tell", [f"absence not checked ({'no absence_check' if a == 'none' else 'no Grep/Glob in the trace'})"]
            elif a == "unmatched":
                flags.append("absence_check doesn't match any search in the trace")
        if verdict in ("met", "partial") and it.get("called_by_job") in ("no", "unclear"):
            flags.append(f"not called by the job ({it['called_by_job']}, per AI): confirm entry points")
        report["items"][it["item_id"]] = {
            "ai_verdict": it["verdict"], "verdict": verdict, "confidence": it["confidence"],
            "reason": it["reason"], "citations_verified": len(good), "citation_notes": notes, "flags": flags}

    for d in answer["deductions"]:
        good = [c for c in d["citations"] if check_citation(repo, c)[0]]
        applies, flags = d["applies"], []
        if applies == "yes" and not good:
            applies, flags = "cannot_tell", ["applies=yes without a verified citation"]
        report["deductions"][d["deduction_id"]] = {
            "ai_applies": d["applies"], "applies": applies, "severity": d["severity"] if applies == "yes" else "none",
            "ai_severity": d["severity"], "reason": d["reason"], "citations_verified": len(good), "flags": flags}

    # V6: injections the pre-scan found (HIGH) in files the judge opened or was given
    seen = set(opened) | set(pack)
    noted = [(n["file"][2:] if n["file"].startswith("./") else n["file"], n["line"])   # not lstrip: keeps ".claude"
             for n in answer["integrity_notes"]]
    missed = []
    for f in prescan:
        if f["severity"] != "HIGH" or f["file"] not in seen:     # only what the judge could have seen
            continue
        hit = any(nf == f["file"] and (f["line"] == 0 or abs(nl - f["line"]) <= LINE_SLACK) for nf, nl in noted)
        if not hit:
            missed.append(f"{f['file']}:{f['line']} {f['kind']}")
    report["integrity"] = {"notes": answer["integrity_notes"], "prescan_high_missed": missed}
    if missed:
        report["flags"].append(f"AI missed {len(missed)} injection attempt(s) found by the pre-scan")

    # V7: links to V1 facts
    status = {r["id"]: r["status"] for r in v1_results}
    for link in rubric.get("v1_links", []):
        v = report["items"].get(link["item"], {}).get("verdict")
        if v not in link["if_verdict"]:
            continue
        hit = False
        if "check" in link:
            hit = status.get(link["check"]) in link["if_status"]
        if "index_empty" in link:
            val = v1_index
            for k in link["index_empty"]["key"]:
                val = val.get(k, {}) if isinstance(val, dict) else {}
            paths = val.keys() if isinstance(val, dict) else val if isinstance(val, list) else []
            hit = not [p for p in paths if link["index_empty"].get("contains", "").lower() in str(p).lower()]
        if hit:
            report["items"][link["item"]]["flags"].append(f"V1 contradiction: {link['note']}")

    # V8: coverage
    if pack:
        cov = len(set(pack) & set(opened)) / len(pack)
        report["coverage"] = round(cov, 2)
        if cov < 0.5:
            report["flags"].append(f"judge opened only {cov:.0%} of the evidence pack")

    # V9: human queue (+ items the rubric says a human always confirms, e.g. evidence of a cloud run)
    for i in rubric.get("always_human", []):
        if i in report["items"]:
            report["items"][i]["flags"].append("always confirmed by a human (rubric): cannot be verified from the repo alone")
    report["human_queue"] = sorted(i for i, r in report["items"].items()
                                   if r["verdict"] == "cannot_tell" or r["confidence"] == "low" or r["flags"])
    return report
