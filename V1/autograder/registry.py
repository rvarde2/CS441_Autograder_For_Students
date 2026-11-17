"""
registry.py: how checks are declared, collected and labelled.

A CHECK GROUP is one function that runs a few related checks. It declares the phase by which
its checks are due:

    @check_group(phase=1)
    def control_plane(repo, out):
        out.add("F01", "Control-plane files present", "FAIL", ["missing: CLAUDE.md"])

Every check has a FIXED ID (F01, E03, ...) so results can be compared across students, runs and
versions. Never reuse or renumber an ID; retire it and add a new one.

Statuses:
  PASS   the fact holds
  FAIL   the fact doesn't hold; details say what and where
  WARN   something a human (or the later AI grader) must judge, e.g. a documented overlap
  INFO   recorded, not judged
  LATER  set by main.py: the check is due in a later phase than the student's current one
"""

GROUPS = []   # (phase, function), in the order the modules registered them


def check_group(phase):
    def register(fn):
        GROUPS.append((phase, fn))
        return fn
    return register


class Results:
    """Collects results. `due` is set by the runner to the phase of the group being run."""

    def __init__(self):
        self.items = []
        self.due = 0

    def add(self, cid, title, status, details=(), due=None, data=None):
        """due: override the group's phase (the requirements table has a phase per row).
        data: structured observation for INFO rows (names/counts only, never file contents);
        it goes into the JSON and the CSV's `observed` column (aggregated across students by the
        course staff's merge tool)."""
        assert status in ("PASS", "FAIL", "WARN", "INFO"), status
        item = {"id": cid, "title": title, "status": status, "details": list(details),
                "due_phase": self.due if due is None else due}
        if data is not None:
            item["data"] = data
        self.items.append(item)


def run_all(repo):
    """Run every registered group, in phase order (stable within a phase)."""
    out = Results()
    for phase, fn in sorted(GROUPS, key=lambda g: g[0]):
        out.due = phase
        fn(repo, out)
    return out.items
