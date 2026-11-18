"""
Checks due by PHASE 13, "create reproducible build, deployment, and experiment automation".

  U01   Every script under scripts/ runs in bash strict mode. Phase 13 work order: "Bash strict
        mode or an equivalently strict scripting language configuration."

Strict mode = `set` with -e, -u and -o pipefail, in any order or combination: `set -Eeuo pipefail`,
three separate `set` lines, or the long names `set -o errexit -o nounset -o pipefail`. WARN, because the README allows an equivalent
configuration (e.g. a Python script).

Sourced libraries (1.0.1): a script that `source`s (or `.`s) a library which sets strict mode is
strict too; a library that other scripts source needn't set it itself (it runs in its caller's
settings). The whole file is scanned (1.0.0 looked at the first 40 lines only).
"""
import re

from ..registry import check_group

SET = re.compile(r"^\s*set\s+([-+][\w-]+(?:\s+[-+]?[\w-]+)*)")


def strict(text):
    flags = " ".join(m.group(1) for line in text.splitlines() if (m := SET.match(line)))
    short = "".join(re.findall(r"(?<![\w-])-([a-zA-Z]+)", flags))
    # short (-e -u) or long (-o errexit -o nounset) forms both count
    return (("e" in short or "errexit" in flags) and ("u" in short or "nounset" in flags)
            and "pipefail" in flags)


SOURCE = re.compile(r"^\s*(?:source|\.)\s+(.+)$")
SCRIPT_NAME = re.compile(r"([\w.\-]+\.(?:sh|bash))\b")


@check_group(phase=13)
def automation(repo, out):
    scripts = sorted(t for t in repo.tracked if t.startswith("scripts/") and t.endswith((".sh", ".bash")))
    by_name = {}
    for t in scripts:
        by_name.setdefault(t.rsplit("/", 1)[-1], []).append(t)
    text = {t: repo.read(t) or "" for t in scripts}
    sources = {t: {s for line in text[t].splitlines() if (m := SOURCE.match(line))
                   for name in SCRIPT_NAME.findall(m.group(1)) for s in by_name.get(name, []) if s != t}
               for t in scripts}
    libraries = {s for t in scripts for s in sources[t]}            # sourced by some other script
    is_strict = {t: strict(text[t]) for t in scripts}
    changed = True
    while changed:                                                  # inherit through source chains
        changed = False
        for t in scripts:
            if not is_strict[t] and any(is_strict[s] for s in sources[t]):
                is_strict[t] = changed = True
    lax = [t for t in scripts if not is_strict[t] and t not in libraries]
    out.record("scripts", value={"all": scripts, "libraries": sorted(libraries), "not_strict": lax})
    if not scripts:
        status, details = "WARN", ["no shell scripts under scripts/ (Phase 13 names scripts/check.sh, plan.sh, ...)"]
    else:
        status = "WARN" if lax else "PASS"
        details = [f"not in strict mode (set -euo pipefail), directly or via a sourced library: {s}" for s in lax] \
            + [f"{len(scripts)} script(s) checked; {len(libraries)} sourced librar(ies) not required to set it themselves"]
    out.add("U01", "Scripts under scripts/ use bash strict mode (set -euo pipefail)", status, details)
