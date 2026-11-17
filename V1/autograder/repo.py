"""
repo.py: the ONLY module that touches the student's repository.

Every check gets a `Repo` object and asks it for files, git data, and parsed configuration.
No other module opens, lists, stats or runs anything in the student's repository; keeping all
access here means the safety rules are written once and apply to every check:

  1. READ ONLY. Nothing in the student's repository is ever executed or modified.
     (`bash_syntax_error` runs `bash -n`, which PARSES a script without running it.)
  2. NO ESCAPING THE REPO. A file whose real location (after following symlinks) is outside the
     repository is treated as missing. A student can't make us read ~/.ssh via a symlink.
  3. HARDENED GIT. A repository's own .git/config can make git RUN COMMANDS (core.fsmonitor,
     diff.external, textconv filters, a pager). Every git call here overrides those settings on
     the command line, which takes priority over the repo's config. Verified by a control
     experiment: plain `git status` ran a command planted in .git/config; these calls didn't.

Parsed data (agents, settings, phases, ...) is computed once, on first use, and cached.
"""
import json
import os
import re
import subprocess
from functools import cached_property
from pathlib import Path

# Tools that can write files. Bash can too, but it's judged separately (it's also needed to run tests).
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}

# A commit message IDENTIFIES a phase when it STARTS with it ("phase-06 spark-engineer: ..."),
# not when prose mentions one ("fixed description of phase 0" is not phase-00's commit).
PHASE_MSG = re.compile(r"^\s*phase[-_ ]?(\d+)\b", re.I)

_GIT_SAFE = ["-c", "core.fsmonitor=false",      # would run a command on every status/diff
             "-c", "core.hooksPath=/dev/null",   # no repo hooks
             "-c", "safe.directory=*",           # a grader may not own the student's folder
             "-c", "core.pager=cat",             # a pager is a command too
             "-c", "diff.external="]             # external diff program
# Also passed per call where relevant: --no-ext-diff --no-textconv (diff drivers from .gitattributes)


class Repo:
    def __init__(self, root, ownership_file=None):
        self.root = Path(root).resolve()
        self.ownership_file = ownership_file   # optional AI extraction (see ownership.py)

    # ------------------------------------------------------------------ safe file access
    def rel(self, p):
        """Path relative to the repo root, as a string (for messages)."""
        return str(Path(p).relative_to(self.root))

    def inside(self, p):
        """True if p, after resolving symlinks, is still inside the repository."""
        try:
            Path(p).resolve().relative_to(self.root)
            return True
        except ValueError:
            return False

    def _p(self, p):
        """A repo-relative path (or an absolute one inside the repo) as an absolute Path."""
        return Path(p) if Path(p).is_absolute() else self.root / p

    def is_file(self, p):
        """A regular file whose real location is inside the repo."""
        p = self._p(p)
        return p.is_file() and self.inside(p)

    def is_dir(self, p):
        p = self._p(p)
        return p.is_dir() and self.inside(p)

    def is_executable(self, p):
        return self.is_file(p) and os.access(self._p(p), os.X_OK)

    def size(self, p):
        """Size in bytes, or None if not a file inside the repo."""
        return self._p(p).stat().st_size if self.is_file(p) else None

    def read(self, p):
        """Text of a file in the repo, or None if missing, not a file, or outside the repo."""
        if not self.is_file(p):
            return None
        return self._p(p).read_text(errors="replace")

    def read_bytes(self, p, max_bytes=None):
        """Raw bytes, or None if missing, a symlink, outside the repo, or larger than max_bytes."""
        q = self._p(p)
        if q.is_symlink() or not self.is_file(q) or (max_bytes is not None and q.stat().st_size > max_bytes):
            return None
        return q.read_bytes()

    def glob(self, folder, pattern):
        """Paths matching `pattern` directly in a repo folder (inside the repo only)."""
        d = self._p(folder)
        return sorted(p for p in d.glob(pattern) if self.inside(p)) if self.is_dir(d) else []

    def escaping_symlinks(self):
        """Repo-relative names of symlinks that point outside the repository (.git ignored)."""
        return [self.rel(p) for p in self.root.rglob("*")
                if p.is_symlink() and ".git" not in p.parts and not self.inside(p)]

    def bash_syntax_error(self, p):
        """`bash -n`: PARSES the script (never runs it). Error text, or None if it parses."""
        r = subprocess.run(["bash", "-n", str(self._p(p))], capture_output=True, text=True)
        return r.stderr.strip() if r.returncode else None

    def load_json(self, p):
        """(data, None) or (None, reason). reason is 'missing' or a parse error with line number."""
        text = self.read(p)
        if text is None:
            return None, "missing"
        try:
            return json.loads(text), None
        except json.JSONDecodeError as e:
            return None, f"invalid JSON at line {e.lineno}: {e.msg}"

    # ------------------------------------------------------------------ hardened git
    def git(self, *args, timeout=120):
        """Run a read-only git command in the repo. Returns stdout, or None if git failed."""
        cmd = ["git", "--no-pager", "-C", str(self.root), *_GIT_SAFE, *args]
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1"}
        r = subprocess.run(cmd, capture_output=True, text=True, errors="replace", env=env, timeout=timeout)
        return r.stdout if r.returncode == 0 else None

    @cached_property
    def is_git(self):
        return (self.root / ".git").exists() and self.git("rev-parse", "--is-inside-work-tree") is not None

    @cached_property
    def tracked(self):
        """Files git tracks. Not a git repo: every file instead (so checks still have input)."""
        if self.is_git:
            return [t for t in (self.git("ls-files", "-z") or "").split("\0") if t]
        return [self.rel(p) for p in self.root.rglob("*") if p.is_file() and ".git" not in p.parts]

    @cached_property
    def subjects(self):
        """['<short hash> <subject>', ...] for every commit on every branch."""
        return (self.git("log", "--all", "--format=%h %s") or "").splitlines() if self.is_git else []

    def toplevel(self):
        """The git work tree this folder belongs to (may be a PARENT of root), or None."""
        out = self.git("rev-parse", "--show-toplevel")
        return Path(out.strip()).resolve() if out else None

    def repos_below(self):
        """Git repositories one or two folders below root (for 'point me at your repo')."""
        return sorted({p.parent for p in list(self.root.glob("*/.git")) + list(self.root.glob("*/*/.git"))})

    def resolve_commit(self, h):
        """Full hash if h names a commit in this repo, else None."""
        out = self.git("rev-parse", "--verify", "--quiet", f"{h}^{{commit}}")
        return out.strip() if out else None

    # ------------------------------------------------------------------ the agent control plane
    @cached_property
    def agent_files(self):
        return self.glob(".claude/agents", "*.md")

    @cached_property
    def hook_files(self):
        return self.glob(".claude/hooks", "*")

    @cached_property
    def command_files(self):
        return self.glob(".claude/commands", "*.md")

    @cached_property
    def _agents_parsed(self):
        """Parse each agent file's frontmatter (the block between the first two '---' lines).
        Only a small YAML subset is needed: 'key: value' plus indented continuation lines.
        Returns (agents, problems): agents = {name: {file, tools, description}}."""
        agents, problems = {}, []
        for f in self.agent_files:
            text = self.read(f) or ""
            m = re.match(r"^---\n(.*?)\n---", text, re.S)
            if not m:
                problems.append(f"{self.rel(f)}: no frontmatter")
                continue
            fm, key = {}, None
            for line in m.group(1).splitlines():
                km = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
                if km:
                    key = km.group(1)
                    fm[key] = km.group(2).strip()
                elif key and line.startswith((" ", "\t")):
                    fm[key] += " " + line.strip()
            for k in ("name", "description", "tools"):
                if not fm.get(k):
                    problems.append(f"{self.rel(f)}: no explicit '{k}:'")
            tools = [t.strip() for t in fm.get("tools", "").strip("[]").split(",") if t.strip()]
            agents[fm.get("name") or f.stem] = {"file": self.rel(f), "tools": tools,
                                                "description": fm.get("description", "")}
        return agents, problems

    @property
    def agents(self):
        return self._agents_parsed[0]

    @property
    def agent_problems(self):
        return self._agents_parsed[1]

    @cached_property
    def settings(self):
        data, _ = self.load_json(".claude/settings.json")
        return data or {}

    @property
    def hook_cfg(self):
        return self.settings.get("hooks", {}) or {}

    @property
    def permissions(self):
        return self.settings.get("permissions", {}) or {}

    @cached_property
    def mcp(self):
        data, _ = self.load_json(".mcp.json")
        return data or {}

    # ------------------------------------------------------------------ phases
    @cached_property
    def phases(self):
        """Phase evidence folders docs/agent-runs/phase-NN, sorted."""
        return [d for d in self.glob("docs/agent-runs", "phase-*") if self.is_dir(d)]

    @staticmethod
    def phase_number(d):
        m = re.match(r"phase-(\d+)$", Path(d).name)
        return int(m.group(1)) if m else None

    @cached_property
    def current_phase(self):
        """Highest phase-NN folder, or None if there are none (then nothing is relaxed)."""
        nums = [n for d in self.phases if (n := self.phase_number(d)) is not None and d.is_dir()]
        return max(nums) if nums else None

    @cached_property
    def ownership(self):
        """Ownership rows, from the AI extraction or the built-in parser (see ownership.py)."""
        from .ownership import build
        return build(self)
