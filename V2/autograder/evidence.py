"""
evidence.py: TOLERANT reading of phase evidence (docs/agent-runs/phase-NN/...).

Students and their agents write the same evidence in different styles. This module recognises the
styles listed in data/evidence_formats.json, so a valid variant never FAILs:

  file names     agent-report.md, agent-report-01.md, Agent_Report_2.md, final-report.md, ...
                 (all of a phase's reports are read together, in name order)
  field labels   FILES CREATED:   **Files created:**   ## Files Created   | Files created | ... |
                 plus synonyms ("Created files", "Commands executed", ...)
  claimed paths  `path`, ./path, [text](path), trailing punctuation; absolute paths are reduced to
                 the part inside this repo, or skipped
  commit hashes  plain, in backticks, or inside a GitHub .../commit/<hash> URL

Principles (DESIGN.md "Where files are looked for" and "Phase evidence"):
  - accept variants; when a format can't be recognised, the caller reports WARN, never FAIL
  - NEVER echo free text from a student's file: only validated repo paths, counts and labels
"""
import json
import re
from pathlib import Path, PurePosixPath

FORMATS = json.loads((Path(__file__).resolve().parent / "data" / "evidence_formats.json").read_text())
HASH = re.compile(r"\b[0-9a-f]{7,40}\b")


def norm(name):
    """'Agent_Report-01' -> 'agentreport01' (lowercase; spaces, - _ / removed)."""
    return re.sub(r"[\s\-_/]+", "", name.lower())


# ---------------------------------------------------------------------- evidence files
def evidence_files(repo, phase_dir, kind):
    """All files in a phase folder that are this kind of evidence (name variants accepted)."""
    spec = FORMATS["evidence_files"][kind]
    out = []
    for p in repo.glob(phase_dir, "*"):
        if not repo.is_file(p):
            continue
        stem, ext = (p.stem, p.suffix.lower()) if p.suffix else (p.name, "")
        if ext in spec["exts"] and any(norm(stem).startswith(s) for s in spec["stems"]):
            out.append(p)
    return sorted(out, key=lambda p: p.name)


def evidence_text(repo, phase_dir, kind):
    """Text of every file of this kind, joined (several numbered reports read as one)."""
    return "\n\n".join(repo.read(p) or "" for p in evidence_files(repo, phase_dir, kind))


# ---------------------------------------------------------------------- report fields
_LABELS = {norm(syn): field for field, syns in FORMATS["report_fields"].items() for syn in syns + [field]}
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
_COLON = re.compile(r"^\s*(?:[>*\-+]\s*)*(?:\*\*|__)?\s*([A-Za-z][A-Za-z \-_/]{1,40}?)\s*(?:\*\*|__)?\s*:\s*(?:\*\*|__)?\s*(.*)$")


def _label(text):
    """The canonical field name for a label text, or None. Tolerates trailing ':' and **bold**."""
    t = re.sub(r"[*_`:]+", " ", text).strip()
    return _LABELS.get(norm(t))


def parse_report(text):
    """-> ({FIELD: section text}, {style: count}). A section runs until the next recognised label
    or ANY heading, so one unrecognised label can't swallow the rest of the report."""
    fields, styles, cur = {}, {}, None

    def start(field, value, style):
        nonlocal cur
        cur = field
        fields[field] = (fields.get(field, "") + "\n" + value).strip("\n") if field in fields else value
        styles[style] = styles.get(style, 0) + 1

    for line in text.splitlines():
        if (h := _HEADING.match(line)):
            field = _label(h.group(1))
            if field:
                start(field, "", "heading")
            else:
                cur = None                      # an unrelated heading ends the current section
            continue
        if line.lstrip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and (field := _label(cells[0])):
                start(field, " | ".join(cells[1:]), "table")
                cur = None                      # a table row is self-contained
                continue
        if (m := _COLON.match(line)) and (field := _label(m.group(1))):
            start(field, m.group(2).strip(), "bold" if "**" in line or "__" in line else "colon")
            continue
        if cur:
            fields[cur] += "\n" + line
    return fields, styles


def first_value(section):
    """First non-empty line of a section, without markdown decoration."""
    for line in (section or "").splitlines():
        v = re.sub(r"[*_`>#]|^\s*[-+]\s+", "", line).strip(" .")
        if v:
            return v
    return ""


def status_ok(value):
    v = re.sub(r"\s+", " ", value.upper())
    return any(v.startswith(s) for s in FORMATS["status_values"])


# ---------------------------------------------------------------------- claimed paths
_TOKEN = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)|`([^`\n]+)`|([^\s`|,;()\[\]<>\"']+)")
_FILE_SHAPED = re.compile(r"^(?:[\w.\-]+/)+[\w\-][\w.\-]*\.[A-Za-z0-9]{1,10}$")


def claimed_paths(repo, section):
    """Repo paths a report section claims. A token counts only if it IS a path that exists in this
    repo now or in its history, or is strongly file-shaped (folder/name.ext), so a fabricated
    'modules/x/Y.scala' still counts but prose ('.collect', 'Spark/Hadoop') never does.
    Absolute paths are reduced to the part inside this repo (by its folder name) or skipped:
    they would otherwise echo a student's local folders into the report."""
    known = repo.history_paths
    found = []
    for m in _TOKEN.finditer(section or ""):
        # strip quotes on both ends, punctuation only at the END: a leading "." belongs to ".claude/"
        tok = (m.group(1) or m.group(2) or m.group(3) or "").strip().strip("'\"").rstrip(".,;:/")
        tok = re.sub(r"\s*\(.*$", "", tok)                     # "path (repair-01)" -> path
        if not tok or "://" in tok:
            continue
        if tok.startswith(("/", "~")) or re.match(r"^[A-Za-z]:[\\/]", tok):
            parts = PurePosixPath(tok.replace("\\", "/")).parts
            if repo.root.name in parts:
                tok = "/".join(parts[len(parts) - parts[::-1].index(repo.root.name):])
            else:
                continue                                       # outside this repo: ignore, never echo
        tok = tok[2:] if tok.startswith("./") else tok
        if tok in known or _FILE_SHAPED.match(tok):
            found.append(tok)
    return list(dict.fromkeys(found))


# ---------------------------------------------------------------------- commit hashes
def hashes_in(text):
    return HASH.findall((text or "").lower())
