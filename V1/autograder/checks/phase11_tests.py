"""
Checks due by PHASE 11, "adversarial testing and full repository review": tests build up over
the earlier phases, and the full inventory is reviewed here.

  T01   at least 25 MEANINGFUL tests ("A test that asserts only that a method returns a non-null
        value is not meaningful coverage.")
  X05   observation (due from phase 0): the same counts, recorded to tune T01

Code can count tests and flag obviously weak ones. Whether the inventory covers what the README
lists (parser, Hadoop mapper/reducer, prompt-injection, claim-verification, ...) needs judgement.
"""
import re

from ..registry import check_group

# Start of a test case: munit/ScalaTest `test("...")`, `property("...")`, `it("...")`,
# ScalaTest `"x" should "y" in {` / `"x" in {`, and Python `def test_x(`.
TEST_START = re.compile(r'^\s*(?:test|property|it)\s*\(\s*"|^\s*"[^"]+"\s+(?:in|should|must)\s*\{|'
                        r'^\s*def\s+test_\w+\s*\(')
ASSERTION = re.compile(r"assert|expect|should|intercept|check\(|forAll|\bmust\b|fail\(")
TRIVIAL = re.compile(r"assert\s*\(\s*true\s*\)|!=\s*null|\bnotNull\b|isDefined\b|nonEmpty\b|"
                     r"assert\s*\(\s*\w+\s*\)\s*$")
TEST_FILE = re.compile(r"(^|/)(src/test|tests?)/|Test\w*\.(scala|java)$|_test\.py$|test_\w+\.py$")


@check_group(phase=11)
def tests(repo, out):
    total, weak, per_file = 0, [], {}
    for t in repo.tracked:
        if not (TEST_FILE.search(t) and t.endswith((".scala", ".java", ".py"))):
            continue
        lines = (repo.read(t) or "").splitlines()
        starts = [i for i, l in enumerate(lines) if TEST_START.search(l)]
        per_file[t] = len(starts)
        total += len(starts)
        # A test's body = the rest of its own line (one-line tests: `test("x") { assertEquals(a, b) }`)
        # plus the lines up to the next test. Weak = no assertion, or only trivial ones.
        # (An earlier version skipped the test's own line, so every one-line test looked empty.)
        for k, s in enumerate(starts):
            own = lines[s][TEST_START.search(lines[s]).end():]
            own = own.split('"', 1)[1] if own.count('"') else own        # drop the rest of the test name
            body = [own] + lines[s + 1:(starts[k + 1] if k + 1 < len(starts) else len(lines))]
            asserts = [l for l in body if ASSERTION.search(l)]
            if not asserts:
                weak.append(f"{t}:{s + 1}: no assertion found  {lines[s].strip()[:60]}")
            elif all(TRIVIAL.search(l) for l in asserts):
                weak.append(f"{t}:{s + 1}: only trivial assertions (non-null/true)  {lines[s].strip()[:60]}")
    meaningful = total - len(weak)
    # X05 (observation, due from phase 0): test counts over time, to tune the 25-test check.
    out.add("X05", "Observation: test counts (to tune T01)", "INFO",
            [f"{total} found, {len(weak)} trivial, {meaningful} counted"], due=0,
            data={"found": total, "trivial": len(weak), "counted": meaningful})
    out.add("T01", "At least 25 meaningful automated tests", "PASS" if meaningful >= 25 else "FAIL",
            [f"{total} tests found, {len(weak)} look trivial, {meaningful} counted (need 25)"]
            + [f"{f}: {n}" for f, n in sorted(per_file.items()) if n] + weak)
