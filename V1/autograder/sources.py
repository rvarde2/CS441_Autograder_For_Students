"""
sources.py: the non-comment lines of the student's tracked source files, for code checks
(H01, A01, V01, U01). Commented-out code never counts: `// df.collect()` is not a collect.

All reading goes through repo.read (inside-the-repo, tracked files only).
"""
import re

COMMENT = {".scala": "//", ".java": "//", ".sbt": "//", ".py": "#", ".sh": "#", ".bash": "#"}
# Test files: excluded where a check is about production code (hard-coded values in a test are fine).
TEST_FILE = re.compile(r"(^|/)(src/test|tests?)/|Test\w*\.(scala|java)$|Suite\.scala$|_test\.py$|(^|/)test_\w+\.py$")


def code_lines(repo, exts, skip_tests=False, under=None):
    """Yield (path, line number, line) for non-comment lines of tracked files with these extensions.
    under: only paths starting with this folder. Block comments (/* ... */) are skipped too."""
    for t in repo.tracked:
        ext = "." + t.rsplit(".", 1)[-1] if "." in t else ""
        if ext not in exts or (skip_tests and TEST_FILE.search(t)) or (under and not t.startswith(under)):
            continue
        marker, in_block = COMMENT.get(ext, "#"), False
        for i, line in enumerate((repo.read(t) or "").splitlines(), 1):
            s = line.strip()
            if marker == "//":
                if in_block:
                    in_block = "*/" not in s
                    continue
                if s.startswith("/*"):
                    in_block = "*/" not in s
                    continue
                if s.startswith(("*", "//")):
                    continue
            elif s.startswith("#") and not s.startswith("#!"):
                continue
            yield t, i, line
