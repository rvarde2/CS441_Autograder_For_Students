"""
score.py (V4, instructor only, NOT shipped): turn V1 facts and V2/V3 verdicts into POINTS GAINED and POINTS
DEDUCTED, two separate numbers, per phase, with a reason on every row. Weights: weights.json (its sha is printed).

    python3 -I score.py --batch <folder> [--out <folder>]
        <folder>/<student>/ holds any of:
          V1:     selfcheck-results.json | v1.json | selfcheck-*.csv
          judge:  folders containing result.json (one per category, any depth) | v2-*.csv | v3-*.csv
        result.json folders give reasons and citations; the CSVs give verdicts only (a preview).

Writes <out>/<student>.md and <student>.csv (one row per item/deduction), <out>/class.csv (one row per student)
and <out>/phases.csv (one row per student and phase). Every CSV row repeats student, commit, v4_version, weights_sha.
Nothing here asks an AI or reads a student repository: it only combines results that already exist.

Rules (weights.json "decisions"): an item's points = its tier share of the README category budget x verdict
(met 1, partial 1/2, missing 0); cannot_tell -> PENDING (unscored, points at stake shown); verifier flags ->
scored but CHECK; a deduction = README max x severity (minor 1/4, partial 1/2, full 1); applies=cannot_tell ->
PENDING. V1 gives no gain points; it feeds deductions (secrets = CONFIRM, a human checks the value).
"""
import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V4_VERSION = (HERE / "VERSION").read_text().strip() if (HERE / "VERSION").exists() else "dev"
# rubric files: the copy shipped next to this script (student package), else the instructor's source folders
RUBRIC_DIRS = [HERE / "rubric"] if (HERE / "rubric").is_dir() else [HERE.parent / "v2" / "rubric", HERE.parent / "v3" / "rubric"]
CHECK_TEXT = {"citation_mismatch": "a citation did not match the file", "absence_unchecked": "absence not checked",
              "absence_unverified": "absence check not matched to a search", "not_called": "not called by the job (per AI)",
              "v1_contradiction": "contradicts a V1 fact", "always_human": "always confirmed by a human",
              "low_confidence": "judge's confidence low", "other": "verifier flag"}


def safe(v):
    if isinstance(v, (int, float)):            # our own numbers: a negative score must stay a number
        return str(v)
    v = "" if v is None else str(v)
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v


# ------------------------------------------------------------------ loading
def load_v1(folder):
    """-> {'results': {id: {...}}, 'commit': str, 'phase_of_commit': {short: phase}} or None"""
    js = [p for n in ("selfcheck-results.json", "v1.json") for p in folder.rglob(n)]
    if js:
        d = json.loads(js[0].read_text())
        idx = d.get("index") or {}
        poc = {h[:12]: ph.get("number") for ph in (idx.get("phases") or {}).values() if isinstance(ph, dict)
               for h in ph.get("commits", [])}
        return {"results": {r["id"]: r for r in d["results"]}, "commit": idx.get("commit") or "", "phase_of_commit": poc,
                "source": js[0].name, "version": d.get("version", "")}
    cs = sorted(folder.rglob("selfcheck-*.csv"))
    if cs:
        res, commit, ver = {}, "", ""
        with open(cs[0], newline="", encoding="utf-8-sig", errors="replace") as f:
            for r in csv.DictReader(f):
                if not re.fullmatch(r"[A-Z]\d{2}", r.get("check_id") or ""):
                    continue
                data = None
                try:
                    data = json.loads(r["observed"]) if r.get("observed") else None
                except json.JSONDecodeError:
                    pass
                res[r["check_id"]] = {"id": r["check_id"], "status": r["status"], "details": (r.get("details") or "").split(" | "),
                                      "data": data, "due_phase": r.get("due_phase")}
                commit, ver = r.get("commit", commit) or commit, r.get("version", ver)
        return {"results": res, "commit": commit, "phase_of_commit": {}, "source": cs[0].name, "version": ver}
    return None


def load_judged(folder):
    """-> {category: {'items': {id: {...}}, 'deductions': {id: {...}}, 'commit', 'prov'}}"""
    out = {}
    for rj in folder.rglob("result.json"):
        r = json.loads(rj.read_text())
        prov = r.get("provenance") or {}
        if "items" not in r or not prov.get("category") or prov.get("dry_run"):
            continue
        ans = {}
        if (rj.parent / "run-1.answer.json").exists():
            ans = json.loads((rj.parent / "run-1.answer.json").read_text())
        dropped = set()
        if (rj.parent / "run-1.verified.json").exists():
            ver = json.loads((rj.parent / "run-1.verified.json").read_text())
            for it in (ver.get("items") or {}).values():
                dropped |= {n.split(":", 1)[0].replace("dropped: ", "").strip() for n in it.get("citation_notes", []) if n.startswith("dropped")}

        def cite(entry):
            for c in entry.get("citations", []) if entry else []:
                if c["file"] not in dropped:
                    return f"{c['file']}:{c['line_start']}" + (f"-{c['line_end']}" if c["line_end"] != c["line_start"] else "")
            return ""
        a_items = {i["item_id"]: i for i in ans.get("items", [])}
        a_ded = {d["deduction_id"]: d for d in ans.get("deductions", [])}
        cat = {"items": {}, "deductions": {}, "commit": prov.get("commit", ""), "prov": prov}
        for k, v in r["items"].items():
            cat["items"][k] = {"verdict": v["verdict"], "checks": [f for f in v.get("flags", [])] +
                               (["judge's confidence low"] if "low" in v.get("confidence", []) else []),
                               "reason": v.get("reason", ""), "cite": cite(a_items.get(k))}
        for k, v in r["deductions"].items():
            cat["deductions"][k] = {"applies": v["applies"], "severity": v["severity"],
                                    "reason": (a_ded.get(k) or {}).get("reason", ""), "cite": cite(a_ded.get(k))}
        cat["date"] = prov.get("date", "")
        old = out.get(prov["category"])
        if old is None or old.get("from") == "csv" or cat["date"] > old.get("date", ""):   # several runs: the LATEST one
            out[prov["category"]] = cat
    for cp in sorted(list(folder.rglob("v2-*.csv")) + list(folder.rglob("v3-*.csv"))):
        with open(cp, newline="", encoding="utf-8-sig", errors="replace") as f:
            for r in csv.DictReader(f):
                c = r.get("category")
                if not c or c in out and out[c].get("from") != "csv":
                    continue                       # a result.json for this category wins over a CSV
                cat = out.setdefault(c, {"items": {}, "deductions": {}, "commit": r.get("commit", ""), "from": "csv",
                                         "prov": {"model": r.get("model"), "prompt_version": r.get("prompt_version"),
                                                  "rubric_sha": r.get("rubric_sha"), "version": r.get("v2_version")}})
                checks = [CHECK_TEXT.get(x, x) for x in (r.get("human_reasons") or "").split(";") if x and x != "cannot_tell"]
                if r.get("kind") == "item":
                    cat["items"][r["id"]] = {"verdict": r["verdict"], "checks": checks,
                                             "reason": "(verdict only: reasons are in the student's result.json)", "cite": ""}
                else:
                    cat["deductions"][r["id"]] = {"applies": r["verdict"], "severity": r.get("severity") or "none",
                                                  "reason": "(verdict only)", "cite": ""}
    return out


# ------------------------------------------------------------------ scoring
def item_points(w, cat):
    units = w["tier_units"]
    total = sum(units[i["tier"]] for i in cat["items"].values())
    return {k: cat["points"] * units[i["tier"]] / total for k, i in cat["items"].items()}


def score_student(student, folder, w, wsha):
    v1, judged = load_v1(folder), load_judged(folder)
    rows, notes = [], []
    rubric = {}
    for cdir in RUBRIC_DIRS:
        for f in cdir.glob("*.json"):
            r = json.loads(f.read_text())
            rubric.update({i["id"]: i["text"].split(".")[0][:60] for i in r["items"]})
            rubric.update({d["id"]: d["quote"].split(":")[0][:60] for d in r["deductions"]})

    def add(phase, source, rid, result, gained=None, mx=None, deducted=None, up_to=None, status="auto", reason=""):
        if isinstance(phase, int):
            phase = f"{phase:02d}"
        if "," in str(phase):                  # a finding in several phases: one clean key, the list in the reason
            reason, phase = f"phases {phase}: {reason}", "multiple"
        rows.append({"phase": phase, "source": source, "id": rid, "what": rubric.get(rid, ""), "result": result,
                     "gained": gained, "max": mx, "deducted": deducted, "up_to": up_to, "status": status,
                     "reason": reason})

    for cid, cw in w["categories"].items():
        pts = item_points(w, cw)
        j = judged.get(cid)
        src = "V3" if cid.startswith("factory") else "V2"
        if j is None:
            notes.append(f"{cid}: no judge result found ({cw['points']} points not scored)")
            for k in cw["items"]:
                add(cw["items"][k].get("phase", cw["phase"]), src, k, "not judged", None, round(pts[k], 3), status="PENDING",
                    reason="no judge result for this category")
            continue
        for k, iw in cw["items"].items():
            ph = iw.get("phase", cw["phase"])
            it = j["items"].get(k)
            if it is None:
                add(ph, src, k, "absent from result", None, round(pts[k], 3), status="PENDING", reason="item missing from the judge result")
                continue
            why = it["reason"] + (f" [{it['cite']}]" if it["cite"] else "")
            if iw["tier"] == "zero":
                add(ph, src, k, it["verdict"], 0.0, 0.0, status="zero weight", reason=f"{iw['why']}; judge: {why}")
            elif it["verdict"] == "cannot_tell":
                add(ph, src, k, "cannot_tell", None, round(pts[k], 3), status="PENDING", reason=f"judge could not decide; {why}")
            else:
                g = pts[k] * w["verdict_fraction"].get(it["verdict"], 0.0)
                st = "CHECK: " + "; ".join(dict.fromkeys(it["checks"])) if it["checks"] else "auto"
                add(ph, src, k, it["verdict"], round(g, 3), round(pts[k], 3), status=st, reason=why)
        for k, dw in cw["deductions"].items():
            ph = dw.get("phase", cw["phase"])
            d = j["deductions"].get(k)
            mx = next((x["max_points"] for f in RUBRIC_DIRS
                       for p in f.glob("*.json") for x in json.loads(p.read_text())["deductions"] if x["id"] == k), None)
            if not dw["apply"]:
                add(ph, src, k, d["applies"] if d else "", None, None, 0.0, mx, status="not applied", reason=dw["why"])
            elif d is None:
                add(ph, src, k, "absent from result", None, None, None, mx, status="PENDING", reason="deduction missing from the judge result")
            elif d["applies"] == "cannot_tell":
                add(ph, src, k, "cannot_tell", None, None, None, mx, status="PENDING", reason=f"judge could not decide; {d['reason']}")
            else:
                ded = mx * w["severity_fraction"].get(d["severity"], 0.0) if d["applies"] == "yes" else 0.0
                add(ph, src, k, f"{d['applies']}/{d['severity']}", None, None, round(ded, 3), mx,
                    reason=d["reason"] + (f" [{d['cite']}]" if d["cite"] else ""))

    # ---- V1 deductions
    if v1 is None:
        notes.append("no V1 result found: V1 deductions not computed")
    else:
        R = v1["results"]
        poc = v1["phase_of_commit"]
        st = lambda i: (R.get(i) or {}).get("status", "")
        det = lambda i: [d for d in (R.get(i) or {}).get("details", []) if d]
        # secrets: FAIL -> proposed full deduction for a human to confirm
        hard = [d for i in ("K01", "K02", "K03") if st(i) == "FAIL" for d in det(i)
                if not d.startswith("ignored as placeholders") and "confirm it's not a real key" not in d
                and "possible hard-coded" not in d and "make sure it holds no secrets" not in d]
        phases = sorted({poc.get(m.group(1)[:12]) for d in hard if (m := re.match(r"commit (\w+)", d)) and poc.get(m.group(1)[:12]) is not None})
        if hard:
            add(",".join(f"{p:02d}" for p in phases) or "—", "V1", "SECRETS", "FAIL", None, None, None, 4, status="CONFIRM",
                reason="proposed -4: a human confirms the value is a real secret: " + " | ".join(hard[:4]) + (" ..." if len(hard) > 4 else ""))
        soft = [d for i in ("K01", "K02", "K03") if st(i) == "WARN" for d in det(i) if not d.startswith("ignored as placeholders")]
        if soft and not hard:
            add("—", "V1", "SECRETS", "WARN", None, None, None, 4, status="PENDING", reason="look: " + " | ".join(soft[:3]))
        # tests: scaled
        counted = ((R.get("X05") or {}).get("data") or {}).get("counted")
        if counted is None and (m := re.search(r"(\d+) counted", " ".join(det("T01")))):
            counted = int(m.group(1))
        if counted is not None:
            tw = w["v1_deductions"]["TESTS"]
            ded = tw["max"] * max(0, 25 - counted) / 25
            add("11", "V1", "TESTS", f"{counted} meaningful tests", None, None, round(ded, 3), tw["max"],
                reason=f"{counted} meaningful tests (25 required)" + ("" if ded else ": enough"))
        if st("V01") == "WARN":
            add("04", "V1", "HARDCODED", "WARN", None, None, None, 1, status="PENDING",
                reason="a human checks for a configuration rationale: " + " | ".join(det("V01")[:3]))
        e3 = [d for d in det("E03") if "but no" in d]
        if st("E03") == "FAIL" and e3:
            ph = sorted({m.group(1) for d in e3 if (m := re.match(r"phase-(\d+)", d))})
            add(",".join(ph), "V1", "CLAIMS_NOT_DONE", "FAIL", None, None, None, 2, status="PENDING",
                reason="never automatic (integrity): " + " | ".join(e3[:3]) + (" ..." if len(e3) > 3 else ""))
        if st("C02") == "FAIL":
            add("01", "V1", "TASKFORGE_FORK", "FAIL", None, None, None, "grade may be 0", status="PENDING",
                reason="control plane mostly copied from the tutorial: " + " | ".join(det("C02")))
        e1w = [d for d in det("E01") if "labels recognised" in d]
        if e1w:
            notes.append(f"E01: {len(e1w)} report(s) in a style V1 cannot read: E03 did NOT check their claims (read them first)")

    # ---- provenance and consistency
    commits = {("V1", v1["commit"])} if v1 and v1["commit"] else set()
    commits |= {(c, j["commit"]) for c, j in judged.items() if j.get("commit")}
    if len({c for _, c in commits}) > 1:
        notes.append("DIFFERENT COMMITS: " + ", ".join(f"{s} {c[:10]}" for s, c in sorted(commits)) + " (scores mix versions of the repo)")
    distinct = {c for _, c in commits}
    graded_commit = next(iter(distinct)) if len(distinct) == 1 else ("mixed" if distinct else "")
    models = {j["prov"].get("model") for j in judged.values() if j["prov"].get("model")}
    sources = {c: ("result.json" if j.get("from") != "csv" else "CSV, verdicts only") for c, j in judged.items()}

    num = lambda k: sum(r[k] for r in rows if isinstance(r[k], (int, float)) and r["status"] not in ("PENDING", "CONFIRM"))
    tot = {"gained": round(num("gained"), 2), "gain_max": round(sum(c["points"] for c in w["categories"].values()), 2),
           "deducted": round(num("deducted"), 2),
           "to_confirm": round(sum(r["up_to"] for r in rows if r["status"] == "CONFIRM" and isinstance(r["up_to"], (int, float))), 2),
           "pending": sum(r["status"] == "PENDING" for r in rows),
           "pending_gain_at_stake": round(sum(r["max"] for r in rows if r["status"] == "PENDING" and isinstance(r["max"], (int, float))), 2),
           "check": sum(r["status"].startswith("CHECK") for r in rows)}
    # score = gained - deducted (deductions are stored as positive amounts); pending and to-confirm rows excluded
    tot["score"] = round(tot["gained"] - tot["deducted"], 2)
    tot["score_if_confirmed"] = round(tot["score"] - tot["to_confirm"], 2)
    return {"student": student, "rows": rows, "notes": notes, "totals": tot, "weights_sha": wsha, "commit": graded_commit,
            "v1": (v1 or {}).get("source", ""), "sources": sources, "models": sorted(models)}


# ------------------------------------------------------------------ output
def phase_key(r):
    m = re.match(r"(\d+)", str(r["phase"]))
    return (int(m.group(1)) if m else 99, r["source"], r["id"])


def by_phase(rows):
    """{phase: [gained, deducted, pending rows, to confirm]} in phase order; pending/confirm rows not in the sums."""
    byp = {}
    for r in sorted(rows, key=phase_key):
        g = byp.setdefault(str(r["phase"]), [0.0, 0.0, 0, 0.0])
        if r["status"] == "PENDING":
            g[2] += 1
        elif r["status"] == "CONFIRM":
            g[3] += r["up_to"] if isinstance(r["up_to"], (int, float)) else 0.0
        else:
            g[0] += r["gained"] or 0.0
            g[1] += r["deducted"] or 0.0
    return byp


ID_COLS = ["student", "commit", "v4_version", "weights_sha"]     # repeated on every row, as in the V1-V3 CSVs


def write(sheet, out):
    s, t = sheet, sheet["totals"]
    rows = sorted(s["rows"], key=phase_key)
    ident = [s["student"], s["commit"], V4_VERSION, s["weights_sha"]]
    cols = ["phase", "source", "id", "what", "result", "gained", "max", "deducted", "up_to", "status", "reason"]
    with open(out / f"{s['student']}.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(ID_COLS + cols)
        for r in rows:
            wr.writerow([safe(x) for x in ident] + [safe("" if r[c] is None else r[c]) for c in cols])
    fmt = lambda v: "" if v is None else (f"{v:.2f}" if isinstance(v, float) else str(v))
    L = [f"# Score sheet: {s['student']}", "",
         f"**Points gained: {t['gained']:.2f} of {t['gain_max']:.1f}** (automatic categories only)  ",
         f"**Points deducted: {t['deducted']:.2f}**  ",
         f"**Score (gained - deducted): {t['score']:.2f}**" + (f" ({t['score_if_confirmed']:.2f} if the proposed deductions are confirmed)" if t['to_confirm'] else "") + "  ",
         f"Proposed deductions to confirm: {t['to_confirm']:.2f}; pending human: {t['pending']} row(s), "
         f"{t['pending_gain_at_stake']:.2f} gain points at stake; marked CHECK: {t['check']}", "",
         f"V4 {V4_VERSION}; commit {s['commit'] or '?'}; weights sha {s['weights_sha']}; V1: {s['v1'] or 'none'}; judge: " +
         ", ".join(f"{c} ({v})" for c, v in sorted(s["sources"].items())) + f"; model {', '.join(s['models']) or '?'}", ""]
    if s["notes"]:
        L += ["**Notes:**"] + [f"- {n}" for n in s["notes"]] + [""]
    L += ["## By phase", "", "| Phase | Gained | Deducted | Score |", "|---|---:|---:|---:|"]
    L += [f"| {p} | {g:.2f} | {d:.2f} | {g - d:.2f} |" for p, (g, d, _, _) in by_phase(rows).items()]
    L.append(f"| **all** | **{t['gained']:.2f}** | **{t['deducted']:.2f}** | **{t['score']:.2f}** |")
    L += ["", "## Rows", "", "| Phase | Src | Item | Result | Gained | Max | Deducted | Up to | Status | Reason |",
          "|---|---|---|---|---:|---:|---:|---:|---|---|"]
    for r in rows:
        L.append("| " + " | ".join(str(x).replace("|", "/").replace("\n", " ") for x in
                                    [r["phase"], r["source"], r["id"], r["result"], fmt(r["gained"]), fmt(r["max"]),
                                     fmt(r["deducted"]), fmt(r["up_to"]), r["status"], r["reason"][:300]]) + " |")
    (out / f"{s['student']}.md").write_text("\n".join(L) + "\n")


def student_mode(a, w, wsha):
    """One student: score the latest results of their own V1/V2/V3 runs and print the summary."""
    import datetime
    root = Path(a.autograder).resolve()
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", a.student):
        sys.exit("--student: letters, digits, '.', '_' or '-' only (your NetID)")
    s = score_student(a.student, root, w, wsha)
    if not (s["v1"] or s["sources"]):
        sys.exit(f"no V1/V2/V3 results found under {root}: run V1 (and V2/V3) first, see HOW_TO_RUN.md")
    out = Path(a.out) if a.out else root / "V4" / "results" / datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    write(s, out)
    with open(out / "phases.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(ID_COLS + ["phase", "gained", "deducted", "score", "pending_rows", "to_confirm"])
        for ph, (g, d, pend, conf) in by_phase(s["rows"]).items():
            wr.writerow([safe(x) for x in [s["student"], s["commit"], V4_VERSION, s["weights_sha"], ph,
                                            round(g, 3), round(d, 3), round(g - d, 3), pend, round(conf, 3)]])
    t = s["totals"]
    print(f"ScholarChain V4 {V4_VERSION} (weights {wsha})   commit: {s['commit'] or '?'}")
    print(f"  results used: V1 {s['v1'] or 'none'}; " + ", ".join(f"{c} ({v})" for c, v in sorted(s["sources"].items())))
    print(f"\n  points gained  {t['gained']:5.2f} of {t['gain_max']:.1f}")
    print(f"  points deducted {t['deducted']:5.2f}")
    print(f"  score          {t['score']:5.2f}" + (f"   ({t['score_if_confirmed']:.2f} if the proposed deductions are confirmed)" if t["to_confirm"] else ""))
    print(f"  for the instructor: {t['pending']} pending row(s) ({t['pending_gain_at_stake']:.2f} points at stake), {t['check']} marked CHECK\n")
    print("  phase   gained  deducted   score")
    for ph, (g, d, _, _) in by_phase(s["rows"]).items():
        print(f"  {ph:>6}  {g:6.2f}  {d:8.2f}  {g - d:6.2f}")
    for n in s["notes"]:
        print(f"  note: {n}")
    print(f"\nSaved: {out / (s['student'] + '.md')}  (every row with its reason)\n       {out / (s['student'] + '.csv')}, {out / 'phases.csv'}")
    print("This uses the same weights as grading, on YOUR latest runs; the grading run is made on your submitted tag.")
    return 0


def main():
    ap = argparse.ArgumentParser(description="V4 scorer: gains and deductions per phase, with reasons.")
    ap.add_argument("--batch", help="instructor: folder with one subfolder per student")
    ap.add_argument("--autograder", help="student: the CS441_Autograder_For_Students folder; scores the latest V1/V2/V3 "
                                         "results found in it (V1/selfcheck-results, V2/results, V3/results)")
    ap.add_argument("--student", default="student", help="with --autograder: your NetID (labels the sheet)")
    ap.add_argument("--out", help="output folder (default: scores; with --autograder: <autograder>/V4/results/<time>)")
    ap.add_argument("--weights", default=str(HERE / "weights.json"))
    a = ap.parse_args()
    if bool(a.batch) == bool(a.autograder):
        ap.error("give exactly one of --batch (instructor) or --autograder (student)")
    raw = Path(a.weights).read_bytes()
    w, wsha = json.loads(raw), hashlib.sha256(raw).hexdigest()[:16]
    if a.autograder:
        return student_mode(a, w, wsha)
    out = Path(a.out or "scores")
    out.mkdir(parents=True, exist_ok=True)
    sheets = []
    for d in sorted(p for p in Path(a.batch).iterdir() if p.is_dir()):
        s = score_student(d.name, d, w, wsha)
        if s["v1"] or s["sources"]:
            write(s, out)
            sheets.append(s)
    with open(out / "class.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(ID_COLS + ["gained", "gain_max", "deducted", "score", "to_confirm", "score_if_confirmed", "pending_rows",
                               "pending_gain_at_stake", "check_rows", "notes"])
        for s in sheets:
            t = s["totals"]
            wr.writerow([safe(x) for x in [s["student"], s["commit"], V4_VERSION, s["weights_sha"], t["gained"], t["gain_max"],
                                            t["deducted"], t["score"], t["to_confirm"], t["score_if_confirmed"], t["pending"],
                                            t["pending_gain_at_stake"], t["check"], " | ".join(s["notes"])]])
    with open(out / "phases.csv", "w", newline="") as f:        # one row per student and phase
        wr = csv.writer(f)
        wr.writerow(ID_COLS + ["phase", "gained", "deducted", "score", "pending_rows", "to_confirm"])
        for s in sheets:
            for ph, (g, d, pend, conf) in by_phase(s["rows"]).items():
                wr.writerow([safe(x) for x in [s["student"], s["commit"], V4_VERSION, s["weights_sha"], ph,
                                                round(g, 3), round(d, 3), round(g - d, 3), pend, round(conf, 3)]])
    print(f"{len(sheets)} students scored -> {out}/class.csv, phases.csv and one sheet per student (V4 {V4_VERSION}, weights sha {wsha})")


if __name__ == "__main__":
    sys.exit(main())
