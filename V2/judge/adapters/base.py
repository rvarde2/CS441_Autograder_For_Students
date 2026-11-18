"""
adapters/base.py (V2): the contract every AI tool adapter fulfils. Only adapters know a tool's
command line and trace format; everything else (prompt, schema, verifier) is tool-independent.

Today: claude.py (safety: verified by experiments 1-4). Later: antigravity.py, chatgpt.py, each
only after its OWN control-run experiments (auto-loaded instruction files, read confinement,
MCP, hooks). The stack grader showed every tool needs its own threat review.
"""


class Adapter:
    name = "base"
    safety_status = "unverified"      # "verified" only after experiments 1-4 pass for this tool

    def version(self):
        """The tool's version string (recorded in every result)."""
        raise NotImplementedError

    def command(self, policy, system_prompt, schema, user_message):
        """The argv to run, ENFORCING the policy: only policy tools, every required flag,
        no forbidden tool. Raises if the policy can't be honoured."""
        raise NotImplementedError

    def answer(self, events):
        """The structured answer from the trace, or raise (never return a guess)."""
        raise NotImplementedError

    def files_opened(self, events, repo_root):
        """Repo-relative paths the model read successfully (from the trace, not its word)."""
        raise NotImplementedError

    def searches(self, events):
        """[(tool, pattern, path)] for every search the model made."""
        raise NotImplementedError

    def usage(self, events):
        """Token / cost figures if the tool reports them, else {}."""
        return {}
