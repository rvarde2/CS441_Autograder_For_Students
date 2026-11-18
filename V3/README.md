# ScholarChain V3 (experimental): AI judge for the agentic factory

V3 judges one rubric category, **Agentic factory and agent reproducibility** (3.0 points): your control model,
agent files, separation of duties, ownership map, hooks, MCP policy and commands, phase records, repairs and
ratification, agent catalog, and reproduction instructions. Every item is in [`RUBRIC.md`](RUBRIC.md).

It is **advisory and experimental**: not your grade. It reads your repository and never runs anything in it
(hooks are read, not executed). It was checked on synthetic test repositories only. V1 checks the structure of
your factory for free; V3 judges its content. Run V1 first.

## Run it

Same requirements and steps as V2 (see `../V2/HOW_TO_RUN.md`), from this folder:

```bash
cd ~/CS441_Autograder_For_Students/V3
./judge.sh --student <your NetID> ~/projects/my-scholarchain --dry-run   # free preview
./judge.sh --student <your NetID> ~/projects/my-scholarchain             # asks which AI tool, then the cost
```

It asks which AI tool to use (1 = Claude Code with Sonnet, the default; 2 = Antigravity). One run costs about
$0.30-0.40 API-equivalent with Sonnet (on a subscription: your plan's usage) and takes 1-2 minutes.

## Results

In `V3/results/<repo>-<time>/`: `factory_reproducibility/result.md` (verdict table), `result.json` (reasons and
citations: keep it), and `v3-<NetID>-<time>.csv` (verdicts only: **share only this file** when asked).
`needs_human = yes` marks a verdict the code could not confirm: look at it yourself.

## Limits

- Judged from your files only: whether hooks really block at run time, and actually replaying a phase, are
  checked by a human (and in your demo's guard probes).
- Requirements that live in git history (constitutional changes without ratification, a reviewer editing
  production code) come from V1's facts and a human, not from this judge.
