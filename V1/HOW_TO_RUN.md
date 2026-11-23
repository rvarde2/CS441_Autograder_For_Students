# How to run the ScholarChain self-check

It checks **your own project repository** (your implementation of the ScholarChain assignment),
not the ScholarChain assignment repository.

A step-by-step guide. `README.md` is the reference (what every check means); this file gets you
from zero to a first result.

The self-check is **advisory**: it is not your grade. It reads your repository, never changes it,
and never runs your code.

---

## 1. Check what you need

| You need | Check with | Notes |
|---|---|---|
| A bash shell | `bash --version` | Linux and macOS: built in. **Windows: use WSL** (Windows Subsystem for Linux). Plain PowerShell or cmd won't work. |
| Python 3.8 or newer | `python3 --version` | Nothing to install with pip. |
| git | `git --version` | |

Optional: Claude Code (the `claude` command), only for the `--ai-ownership` step in section 7.

## 2. Put the self-check folder somewhere OUTSIDE your project

Clone the `CS441_Autograder_For_Students` repository your instructor shared, for example into your
home folder. Each version is a folder (`V1`, later `V2`, ...); use the newest one, or the one your
instructor names. `git pull` gets new versions.

**Keep it outside your ScholarChain repository.** Don't copy it into your project: it would end up
in your submission, and the checker would read its own files as yours.

```
~/CS441_Autograder_For_Students/V1/   <- the self-check (this file is here)
~/projects/my-scholarchain/     <- your repository (any name, anywhere)
```

## 3. Run it

From the self-check folder:

```bash
cd ~/CS441_Autograder_For_Students/V1
./selfcheck.sh --student <your NetID> ~/projects/my-scholarchain
```

- `--student`: your NetID (letters, digits, `.`, `_`, `-`). It labels your results file.
- The last argument is your repository's **root folder**: the one containing `.git` and `.claude/`.

If you see `Permission denied`, the download lost the file's "executable" setting. Either run it
through bash, or fix the setting once:

```bash
bash selfcheck.sh --student <your NetID> ~/projects/my-scholarchain
# or
chmod +x selfcheck.sh extract_ownership.sh
```

The output is long. To scroll through it: `./selfcheck.sh ... | less` (press `q` to quit).
Your results are saved either way.

## 4. Read the result

A run looks like this (a repository that has just finished Phase 0, so later work shows as FAIL):

```
ScholarChain self-check v1.0.5   repo: /home/you/projects/my-scholarchain
current phase: 0 (highest docs/agent-runs/phase-NN)

[ok  ] S01  No symlinks pointing outside the repo
[ok  ] F02  Every agent has name, description and an EXPLICIT tools field (least privilege)
[ok  ] P01  Phase evidence folders docs/agent-runs/phase-NN/
         - phases found: phase-00
...
[FAIL] R01  Required hooks: guard-dangerous, format-scala, verify-tests-ran, validate-agent-files
         - .claude/hooks/guard-dangerous.sh: missing
...
21 pass, 19 fail, 5 warn, 6 info

Saved: /home/you/CS441_Autograder_For_Students/V1/selfcheck-results/selfcheck-ab123.csv   <- the only file to share
       /home/you/CS441_Autograder_For_Students/V1/selfcheck-results/selfcheck-results.json   (keep on your computer; grader version 1.0.5)
ADVISORY ONLY: this is not your grade. See README.md for what it does and does not check.
```

| Label | What to do |
|---|---|
| `ok` | nothing |
| `FAIL` | fix it: the indented lines say what and where (file, line, phase) |
| `warn` | look at it; it may be fine (e.g. an overlap you documented), or worth fixing |
| `info` | nothing; recorded only (lines starting with `X` are observations about how students work) |

**Every check applies, whatever phase you have reached.** Early in the project you will see FAILs for
work you haven't done yet; that is expected. The `due_phase` column of the CSV (and the check table in
`README.md`) says which phase's work order each check belongs to, so you can tell "not done yet" from
"done but wrong". The final grading run gives the same result for the same commit.

Look up any check ID (F02, E03, ...) in `README.md` ("Every check") or `DESIGN.md` (how it decides).

## 5. Fix, commit, run again

1. Fix what a FAIL points to.
2. **`git add` new files.** The checker only reads files git tracks (what you'll submit), so a new
   file isn't seen until it's added.
3. **Commit.** Checks about history (phase commits, reports vs. commits, secrets in history) read
   your commits, not your working folder.
4. Run the self-check again.

Run it as often as you like: before each phase's human gate is a good habit.

## 6. Share your results (when your instructor asks)

Send **only `selfcheck-results/selfcheck-<NetID>.csv`**. Keep `selfcheck-results.json` on your
computer: it also lists where your project's files are, which nobody needs from you. It opens in Excel or Google Sheets, so you can
read every cell first. It contains check IDs, results, and the file names and lines where problems
were found: not your code, not your prompts.

If you think a result is wrong, add a short note saying which check and why. That feedback is used
to improve the checker.

## 7. Optional: `--ai-ownership`

```bash
./selfcheck.sh --ai-ownership --student <your NetID> ~/projects/my-scholarchain
```

Lets Claude Code read your ownership map (who may write which files) more accurately than the
built-in parser. **It uses your own Claude usage and sends repository content to Anthropic under
your account**, so it asks before it runs. It runs read-only: your `CLAUDE.md`, hooks, settings
and MCP servers are not loaded. You don't need it; without it, everything else still works.

## 8. If something goes wrong

| Message | Meaning and fix |
|---|---|
| `Permission denied` | the download lost the executable setting: use `bash selfcheck.sh ...` (section 3) |
| `selfcheck: python3 is required` / `python3 3.8 or newer is required` | install Python 3.8+ so that `python3 --version` works |
| `selfcheck: git is required` | install git |
| `selfcheck: not a folder: ...` | the path to your repository is wrong; check it with `ls` |
| `... is a subfolder of the git repository at ...` | you pointed at a folder inside your repo; use the path it prints |
| `... is not a git repository, but contains ...` | you pointed at a folder above your repo; use one of the paths it prints |
| `--out must be outside your repository` | choose a results folder that isn't inside your project |
| `--student: letters, digits, . _ - only` | use just your NetID |
| `--ai-ownership needs Claude Code` | install Claude Code, or run without `--ai-ownership` |
| `--ai-ownership needs --yes when not run interactively` | in a script, add `--yes` after reading section 7 |
| `--student needs a value` (or `--out` / `--model`) | the option is missing its value: `--student ab123`, not `--student` alone |
| `unknown option: ...` | a typo in an option name; options are `--student`, `--out`, `--ai-ownership`, `--model`, `--yes` |
| `cancelled` | you answered "no" to the `--ai-ownership` question; nothing was sent or saved |
| `AI ownership extraction failed (see .../ownership.jsonl)` | Claude Code didn't return a result (not logged in, usage limit, network); run without `--ai-ownership`, or try later |
| `reader: built-in reader` in the M01 details | fine: PyYAML isn't installed, so a built-in reader was used |
| E01 `warn`: "only N of 14 labels recognised" | your report uses a style the checker doesn't know; the assignment's field names (`FILES CREATED:` ...) always work. Headings (`## Files Created`), **bold** labels and tables are recognised too. |
| Lots of FAILs on a new repository | normal before your first `docs/agent-runs/phase-00/` exists (section 4) |

Exit codes, for scripts: `0` = no FAIL, `1` = at least one FAIL,
`2` = a setup problem (one of the messages above); nothing is saved on `2`.
