"""
adapters/antigravity.py (V2): Antigravity CLI (`agy -p`). Safety verified for Antigravity CLI 1.5.11:
  --sandbox                 enforces terminal sandbox mode
  --disable-slash-commands  disables slash command expansion in prompts
  --settings                allowNonWorkspaceAccess=false confines file reads/searches to the repo root,
                            incl. symlinks and ../ (exp. 4); permissions.allow=["read_file(*)"] and
                            permissions.deny=["write_file(*)", "command(*)", "mcp(*)", "read_url(*)",
                            "execute_url(*)", "download_url(*)", "unsandboxed(*)"] block all shell,
                            file write, MCP, and network/URL tools in headless mode (exp. 1-3);
                            trustedWorkspaces=[] keeps the target repo untrusted so workspace hooks,
                            MCP configs, plugins, and rules are skipped by gateOnWorkspaceTrust
"""
import json
import os
import subprocess
from pathlib import Path

from .base import Adapter

MANDATORY_FLAGS = ("--sandbox", "--disable-slash-commands")
MANDATORY_DENY = {
    "write_file(*)",
    "command(*)",
    "mcp(*)",
    "read_url(*)",
    "execute_url(*)",
    "download_url(*)",
    "unsandboxed(*)",
}
READ_TOOLS = ("view_file", "read_file")
SEARCH_TOOLS = ("grep_search", "code_search", "find_by_name")


class AntigravityAdapter(Adapter):
    name = "antigravity"
    safety_status = "verified"

    def version(self):
        try:
            out = subprocess.run(["agy", "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
            return f"agy {out}" if out and not out.startswith("agy") else (out or "unknown")
        except (OSError, subprocess.TimeoutExpired):
            return "unknown"

    def command(self, policy, system_prompt, schema, user_message):
        cfg = policy.get("antigravity")
        if not isinstance(cfg, dict):
            raise ValueError("policy is missing the 'antigravity' configuration section")

        tools = list(cfg.get("tools") or [])
        if not tools:
            raise ValueError("policy.antigravity.tools must not be empty")
        forbidden = set(cfg.get("forbidden_tools") or [])
        bad = set(tools) & forbidden
        if bad:
            raise ValueError(f"policy allows forbidden tools: {sorted(bad)}")

        req_flags = list(cfg.get("required_flags") or [])
        for f in MANDATORY_FLAGS:
            if f not in req_flags:
                raise ValueError(f"policy.antigravity.required_flags is missing the mandatory flag {f}")

        settings = dict(cfg.get("settings") or {})
        if settings.get("allowNonWorkspaceAccess") is not False:
            raise ValueError("policy.antigravity.settings.allowNonWorkspaceAccess must be false")
        if settings.get("enableTerminalSandbox") is not True:
            raise ValueError("policy.antigravity.settings.enableTerminalSandbox must be true")
        if settings.get("disableSlashCommands") is not True:
            raise ValueError("policy.antigravity.settings.disableSlashCommands must be true")
        if settings.get("trustedWorkspaces") != []:
            raise ValueError("policy.antigravity.settings.trustedWorkspaces must be []")

        perms = settings.get("permissions")
        if not isinstance(perms, dict):
            raise ValueError("policy.antigravity.settings.permissions must be a dict")
        allow = set(perms.get("allow") or [])
        deny = set(perms.get("deny") or [])
        if allow != {"read_file(*)"}:
            raise ValueError(f"policy.antigravity.settings.permissions.allow must be ['read_file(*)'], got {sorted(allow)}")
        missing_deny = MANDATORY_DENY - deny
        if missing_deny:
            raise ValueError(f"policy.antigravity.settings.permissions.deny is missing: {sorted(missing_deny)}")

        model = os.environ.get("AGY_MODEL") or cfg.get("model") or policy["model"]
        full_prompt = f"{system_prompt}\n\n---\n\n{user_message}"
        return [
            "agy",
            "-p",
            full_prompt,
            "--model",
            model,
            *req_flags,
            "--settings",
            json.dumps(settings, sort_keys=True),
            "--json-schema",
            json.dumps(schema),
            "--output-format",
            "stream-json",
        ]

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
                obj = json.loads(line)
                if isinstance(obj, dict):
                    out.append(obj)
            except json.JSONDecodeError:
                continue
        return out

    @staticmethod
    def _tool_steps(events):
        """Yield completed, non-error tool_info dicts from stream-json step_update events, deduplicated by step_index."""
        seen = set()
        for e in events:
            if e.get("event") != "step_update":
                continue
            s = e.get("step_update")
            if not isinstance(s, dict) or s.get("state") != "SUCCESS":
                continue
            ti = s.get("tool_info")
            if not isinstance(ti, dict) or ti.get("error"):
                continue
            idx = s.get("step_index")
            if idx is not None:
                if idx in seen:
                    continue
                seen.add(idx)
            name = ti.get("name") or s.get("tool_name") or ""
            params = ti.get("parameters") if isinstance(ti.get("parameters"), dict) else {}
            yield name, params

    def answer(self, events):
        for e in events:
            if e.get("event") == "result":
                r = e.get("result")
                if not isinstance(r, dict):
                    continue
                so = r.get("structured_output")
                if so is None:
                    raise ValueError(
                        f"result event has no structured_output (status={r.get('status')!r}, "
                        f"error={r.get('error')!r}, keys={sorted(r)})"
                    )
                return so
        raise ValueError("no result event in the trace")

    def files_opened(self, events, repo_root):
        root = str(Path(repo_root).resolve()).rstrip("/") + "/"
        ok = set()
        for name, params in self._tool_steps(events):
            if name in READ_TOOLS:
                p = str(params.get("AbsolutePath") or params.get("Path") or params.get("file_path") or "")
                if p:
                    ok.add(p[len(root):] if p.startswith(root) else p)
        return sorted(ok)

    def searches(self, events):
        out = []
        for name, params in self._tool_steps(events):
            if name in SEARCH_TOOLS:
                pattern = str(
                    params.get("Query")
                    or params.get("Pattern")
                    or params.get("query")
                    or params.get("pattern")
                    or ""
                )
                path = str(
                    params.get("SearchPath")
                    or params.get("SearchDirectory")
                    or params.get("DirectoryPath")
                    or params.get("Path")
                    or params.get("path")
                    or ""
                )
                out.append((name, pattern, path))
        return out

    def usage(self, events):
        for e in events:
            if e.get("event") == "result":
                r = e.get("result")
                if not isinstance(r, dict):
                    continue
                out = {k: r.get(k) for k in ("duration_seconds", "num_turns", "usage") if k in r}
                if isinstance(r.get("duration_seconds"), (int, float)):
                    out["duration_ms"] = int(round(r["duration_seconds"] * 1000))
                return out
        return {}
