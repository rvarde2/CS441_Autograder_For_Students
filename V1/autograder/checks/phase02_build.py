"""
Checks due by PHASE 2, "create the build and repository skeleton" (build-engineer).

  K04   a .gitignore exists ("Git logistics: Include a complete .gitignore")

Phase 0's work order says "create exactly one file", so a seed-only repo legitimately has no
.gitignore yet; that's why this isn't a phase-0 check (an earlier version wrongly failed it).

The Phase 2 build files themselves (build.sbt, project/build.properties, project/plugins.sbt) are
checked by B01, a row in the requirements table (requirements.py). Room to grow here: a
multi-project build.sbt, pinned versions, a `check` alias (D04), which need their own logic.
"""
from ..registry import check_group


@check_group(phase=2)
def build_skeleton(repo, out):
    present = repo.read(".gitignore") is not None
    out.add("K04", "A .gitignore is present (Git logistics: 'Include a complete .gitignore')",
            "PASS" if present else "FAIL", [] if present else ["no .gitignore"])
