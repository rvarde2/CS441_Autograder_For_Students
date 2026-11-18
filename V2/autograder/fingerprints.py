"""
fingerprints.py: line normalization for copy detection, shared by the checker and by the
instructor's make_fingerprints.py (which must normalize EXACTLY the same way).

A file's fingerprint is the set of hashes of its normalized lines. Normalization makes a renamed
fork still match the tutorial:
  - lowercase, whitespace collapsed, blank lines dropped
  - project names (taskforge / scholarchain / "task forge" / "scholar chain") -> "<project>"
  - lines shorter than MIN_LEN characters are ignored ("fi", "}", "---"): they're in every file
    and would inflate similarity
Only hashes are stored and shipped, never the tutorial's text.
"""
import hashlib
import re

MIN_LEN = 12
PROJECT = re.compile(r"task\s*forge|scholar\s*chain", re.I)


def norm_lines(text):
    out = []
    for line in text.splitlines():
        s = PROJECT.sub("<project>", " ".join(line.lower().split()))
        if len(s) >= MIN_LEN:
            out.append(s)
    return out


def line_hash(s):
    return hashlib.sha1(s.encode()).hexdigest()[:12]


def fingerprint(text):
    return {line_hash(s) for s in norm_lines(text)}
