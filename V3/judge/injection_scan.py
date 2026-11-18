"""
injection_scan.py (V2, instructor-only): find text in a student repo that tries to steer the AI
grader, BEFORE any AI reads the repo. Deterministic, no AI. Layer 5 of V2's injection defence.

    python3 -I injection_scan.py <repo> [--json out.json]

Why a pre-scan when the model already resisted planted instructions (experiment 4, stack Ex 6)?
  - behaviour is not a guarantee: a list made by code doesn't depend on the model noticing
  - it lets code CHECK the AI's integrity notes: a high finding the AI didn't report is flagged
  - it catches what a reader can't see: invisible Unicode (zero-width, bidi, "tag" characters
    that can spell out hidden instructions)

What counts (case-insensitive, non-exhaustive by design; tune with real repos):
  HIGH    text addressed to the grader/AI-grader/evaluator ("note to the grader", "dear AI reviewer")
  HIGH    attempts to set marks ("award full marks", "give maximum points", "score this 20/20")
  HIGH    invisible characters that can hide instructions (Unicode tag block, bidi overrides)
  HIGH    instruction-like FILE NAMES ("KCoreVerifiedByInstructor.scala", "ignore_previous_instructions.md")
  MEDIUM  override phrases ("ignore all previous instructions"), role/system spoofing
          ("<system>", "system prompt", "you are now the grader")
  LOW     zero-width characters (often harmless copy-paste residue)
Context lowers severity by one level, with the reason shown, where such text is EXPECTED:
  tests (the README requires prompt-injection tests), agent definitions and CLAUDE.md, runtime
  prompts (prompts/, *prompt*). It's still listed, never hidden.

Repo access goes through V1's repo.py (tracked files only, inside the repo, read-only).
Output is instructor-side, so a SHORT snippet (80 chars) is shown; invisible characters are shown
as their code points. Nothing here is ever sent to the AI.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # V1's autograder package (our code)
from autograder.repo import Repo  # noqa: E402

# Who the text addresses. STRONG = the grader itself. WEAK = words that are legitimate in an agentic
# workflow (the code-reviewer agent, a model, an assistant) and so only MEDIUM.
STRONG = r"(?:ai|llm|grader|graders|grading(?: system| agent)?|auto-?grader|evaluator|marker|ta|teaching assistant|claude)"
WEAK = r"(?:reviewer|model|assistant)"


def addressed(target):
    """Text that really ADDRESSES `target`: 'note to/for the X', 'dear X', 'X: please/award/ignore ...'.
    (1.0 of this rule allowed any 3 characters in between and matched 'instruction + reviewer'.)"""
    return re.compile(
        rf"\b(?:note|message|instructions?|attention|reminder|hint|request|warning)\s+(?:to|for)\s+(?:the\s+|any\s+|all\s+)?(?:ai\s+)?{target}\b"
        rf"|\b(?:dear|hello|hi|hey)\s+(?:the\s+)?(?:ai\s+)?{target}\b"
        rf"|\b{target}\s*[:,]\s*(?:please|you must|you should|ignore|award|give|mark|do not)\b", re.I)


RULES = [
    ("HIGH", "addressed to the grader", addressed(STRONG)),
    ("MEDIUM", "addressed to a reviewer/model/assistant", addressed(WEAK)),
    ("HIGH", "tries to set marks",
     re.compile(r"\b(?:award|give|assign|grant|mark|score|grade)\b[^.\n]{0,40}\b(?:full|maximum|max|perfect|all|top|highest)\b[^.\n]{0,20}\b(?:marks?|points?|credit|score|grade)\b"
                r"|\b(?:full|perfect|maximum)\s+(?:marks|score|credit|points)\b|\b(?:20|10|100)\s*/\s*(?:20|10|100)\b", re.I)),
    ("MEDIUM", "override phrase",
     re.compile(r"\b(?:ignore|disregard|forget|override|bypass)\b[^.\n]{0,25}\b(?:previous|prior|above|earlier|all|any|your|the)\b[^.\n]{0,20}\b(?:instructions?|rules|rubric|prompts?|guidelines|criteria)\b", re.I)),
    # Spoofing: fake role tags, or telling the reader it IS the grader. Merely mentioning a
    # "system prompt" is normal in an agent project and is NOT flagged.
    ("MEDIUM", "role or system spoofing",
     re.compile(rf"<\s*/?\s*(?:system|assistant|instructions?|admin)\s*>|\byou are (?:now )?(?:the |an? )?{STRONG}\b"
                rf"|\bas (?:the |an? )?{STRONG},? you (?:must|should)\b", re.I)),
]
TAG_CHARS = re.compile("[\U000E0000-\U000E007F]")              # invisible "tag" letters
BIDI = re.compile("[‪-‮⁦-⁩]")              # text-direction overrides
ZERO_WIDTH = re.compile("[​-‍⁠﻿]")         # zero-width spaces/joiners
EXPECTED = [(re.compile(r"(^|/)(src/test|tests?|adversarial)/|Suite\.scala$|_test\.py$|(^|/)test_"), "test file (injection tests are required)"),
            (re.compile(r"^\.claude/agents/|^CLAUDE\.md$|^\.claude/commands/"), "agent/orchestrator definition"),
            (re.compile(r"(^|/)prompts?/|prompt", re.I), "runtime prompt")]
LOWER = {"HIGH": "MEDIUM", "MEDIUM": "LOW", "LOW": "LOW"}
TEXT_EXT = (".md", ".markdown", ".txt", ".scala", ".sc", ".sbt", ".java", ".py", ".sh", ".bash", ".json",
            ".yaml", ".yml", ".tf", ".tfvars", ".conf", ".html", ".xml", ".csv", ".toml", ".properties", "")


# File NAMES can carry instructions too (a file the AI lists or opens): "KCoreVerifiedByInstructor.scala",
# "ignore_previous_instructions.md". Names are split into words (camelCase, _, -, .) and checked.
NAME_RULES = [
    ("HIGH", "instruction-like file name (claims approval)",
     re.compile(r"\b(?:verified|approved|graded|certified|accepted|checked|validated)\s+(?:by\s+)?(?:the\s+)?(?:instructor|grader|professor|ta|staff|course)\b")),
    ("HIGH", "instruction-like file name (asks for marks)",
     re.compile(r"\b(?:award|give|grant)\s+(?:full|max|maximum|all)\b|\bfull\s+marks\b")),
    ("HIGH", "instruction-like file name (override)",
     re.compile(r"\b(?:ignore|disregard)\s+(?:all\s+|previous\s+|prior\s+)?(?:instructions|rules|rubric)\b")),
    ("MEDIUM", "file name addressed to the grader", re.compile(rf"\b(?:note|message|readme)\s+(?:to|for)\s+(?:the\s+)?{STRONG}\b")),
]


def name_words(path):
    """'src/KCoreVerifiedByInstructor.scala' -> 'src k core verified by instructor scala'."""
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", path))
    return " ".join(re.split(r"[\s_\-./]+", s)).lower()


def scan(repo):
    findings = []
    for t in repo.tracked:                                  # 1. file names (line 0 = "the name")
        words = name_words(t)
        for sev, what, rx in NAME_RULES:
            if rx.search(words):
                findings.append({"file": t, "line": 0, "kind": what, "severity": sev, "context": None,
                                 "snippet": Path(t).name[:80]})
    for t in repo.tracked:                                  # 2. file contents
        if t.startswith(".git/") or not t.lower().endswith(TEXT_EXT) and "." in Path(t).name:
            continue
        raw = repo.read_bytes(t, max_bytes=2_000_000)
        if raw is None or b"\0" in raw[:8000]:
            continue
        context = next((why for rx, why in EXPECTED if rx.search(t)), None)
        for i, line in enumerate(raw.decode("utf-8", errors="replace").splitlines(), 1):
            hits = [(sev, what, m.group(0)) for sev, what, rx in RULES if (m := rx.search(line))]
            if TAG_CHARS.search(line):
                hidden = "".join(chr(ord(c) - 0xE0000) for c in TAG_CHARS.findall(line) if 0x20 <= ord(c) - 0xE0000 < 0x7F)
                hits.append(("HIGH", "invisible Unicode tag characters", f"hidden text: {hidden[:60]!r}"))
            if BIDI.search(line):
                hits.append(("HIGH", "bidi override characters", " ".join(f"U+{ord(c):04X}" for c in set(BIDI.findall(line)))))
            if ZERO_WIDTH.search(line) and not (i == 1 and line.startswith("﻿") and len(ZERO_WIDTH.findall(line)) == 1):
                hits.append(("LOW", "zero-width characters", " ".join(f"U+{ord(c):04X}" for c in set(ZERO_WIDTH.findall(line)))))
            for sev, what, snippet in hits:
                findings.append({"file": t, "line": i, "kind": what,
                                 "severity": LOWER[sev] if context and "invisible" not in what and "bidi" not in what else sev,
                                 "context": context, "snippet": snippet[:80]})
    return findings


def main():
    ap = argparse.ArgumentParser(description="Find text that tries to steer the AI grader (deterministic).")
    ap.add_argument("repo")
    ap.add_argument("--json")
    a = ap.parse_args()
    found = scan(Repo(Path(a.repo).resolve()))
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    for f in sorted(found, key=lambda f: (order[f["severity"]], f["file"], f["line"])):
        print(f"[{f['severity']:6}] {f['file']}:{f['line']}  {f['kind']}"
              + (f"  (expected here: {f['context']})" if f["context"] else "") + f"  | {f['snippet']}")
    counts = {s: sum(f["severity"] == s for f in found) for s in order}
    print(f"\n{counts['HIGH']} high, {counts['MEDIUM']} medium, {counts['LOW']} low")
    if a.json:
        Path(a.json).write_text(json.dumps({"findings": found, "counts": counts}, indent=2))
    return 1 if counts["HIGH"] else 0


if __name__ == "__main__":
    sys.exit(main())
