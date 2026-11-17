"""
Checks due by PHASE 13, "create reproducible build, deployment, and experiment automation".

  U01   Every script under scripts/ runs in bash strict mode. Phase 13 work order: "Bash strict
        mode or an equivalently strict scripting language configuration."

Strict mode = `set` with -e, -u and -o pipefail, in any order or combination: `set -Eeuo pipefail`,
three separate `set` lines, or the long names `set -o errexit -o nounset -o pipefail`. WARN, because the README allows an equivalent
configuration (e.g. a Python script).
"""
import re

from ..registry import check_group

SET = re.compile(r"^\s*set\s+([-+][\w-]+(?:\s+[-+]?[\w-]+)*)")


def strict(text):
    flags = " ".join(m.group(1) for line in text.splitlines()[:40] if (m := SET.match(line)))
    short = "".join(re.findall(r"(?<![\w-])-([a-zA-Z]+)", flags))
    # short (-e -u) or long (-o errexit -o nounset) forms both count
    return (("e" in short or "errexit" in flags) and ("u" in short or "nounset" in flags)
            and "pipefail" in flags)


@check_group(phase=13)
def automation(repo, out):
    scripts = sorted(t for t in repo.tracked if t.startswith("scripts/") and t.endswith((".sh", ".bash")))
    lax = [s for s in scripts if not strict(repo.read(s) or "")]
    if not scripts:
        status, details = "WARN", ["no shell scripts under scripts/ (Phase 13 names scripts/check.sh, plan.sh, ...)"]
    else:
        status = "WARN" if lax else "PASS"
        details = [f"not in strict mode (set -euo pipefail): {s}" for s in lax] + [f"{len(scripts)} script(s) checked"]
    out.add("U01", "Scripts under scripts/ use bash strict mode (set -euo pipefail)", status, details)
