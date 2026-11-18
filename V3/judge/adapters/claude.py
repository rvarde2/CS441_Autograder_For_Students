"""
adapters/claude.py (V2): Claude Code (`claude -p`). Safety verified for Claude Code 2.1.326:
  --restricted         student CLAUDE.md / hooks / settings not loaded (exp. 1); Read/Glob/Grep
                       confined to the working directory, incl. symlinks and ../ (exp. 4)
  --strict-mcp-config  no MCP servers start (exp. 2)
  --tools              only the policy's read-only tools
"""
import json
import subprocess
from pathlib import Path

from .base import Adapter


class ClaudeAdapter(Adapter):
    name = "claude"
    safety_status = "verified"

    def version(self):
        try:
            return subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            return "unknown"

    def command(self, policy, system_prompt, schema, user_message):
        tools = list(policy["tools"])
        bad = set(tools) & set(policy["forbidden_tools"])
        if bad:
            raise ValueError(f"policy allows forbidden tools: {sorted(bad)}")
        for f in ("--restricted", "--strict-mcp-config"):
            if f not in policy["required_flags"]:
                raise ValueError(f"policy is missing the mandatory flag {f}")
        return ["claude", "-p", user_message, "--model", policy["model"], "--tools", *tools,
                *policy["required_flags"], "--append-system-prompt", system_prompt,
                "--json-schema", json.dumps(schema), "--output-format", "stream-json", "--verbose"]

    def run(self, argv, cwd, trace_path, timeout=900):
        """Run in the repo (cwd) with stdin closed; the raw trace goes to trace_path (outside the repo)."""
        with open(trace_path, "w") as out:
            r = subprocess.run(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.PIPE,
                               text=True, timeout=timeout)
        return r.returncode, r.stderr[-2000:]

    # ------------------------------------------------------------------ trace parsing
    @staticmethod
    def events(trace_path):
        out = []
        for line in Path(trace_path).read_text(errors="replace").splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    @staticmethod
    def _blocks(events):
        for e in events:
            msg = e.get("message")
            if isinstance(msg, dict):
                for b in msg.get("content", []) or []:
                    if isinstance(b, dict):
                        yield b

    def answer(self, events):
        for e in events:
            if e.get("type") == "result":
                so = e.get("structured_output")
                if so is None:
                    raise ValueError(f"result event has no structured_output (keys: {sorted(e)})")
                return so
        raise ValueError("no result event in the trace")

    def files_opened(self, events, repo_root):
        root = str(Path(repo_root).resolve()).rstrip("/") + "/"
        asked, ok = {}, set()
        for b in self._blocks(events):
            if b.get("type") == "tool_use" and b.get("name") == "Read":
                asked[b.get("id")] = str((b.get("input") or {}).get("file_path", ""))
            elif b.get("type") == "tool_result" and not b.get("is_error") and b.get("tool_use_id") in asked:
                p = asked[b["tool_use_id"]]
                ok.add(p[len(root):] if p.startswith(root) else p)
        return sorted(ok)

    def searches(self, events):
        out = []
        for b in self._blocks(events):
            if b.get("type") == "tool_use" and b.get("name") in ("Grep", "Glob"):
                i = b.get("input") or {}
                out.append((b["name"], str(i.get("pattern", "")), str(i.get("path", ""))))
        return out

    def usage(self, events):
        for e in events:
            if e.get("type") == "result":
                return {k: e.get(k) for k in ("total_cost_usd", "duration_ms", "num_turns", "usage") if k in e}
        return {}
