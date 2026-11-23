# How to run the ScholarChain V2 judge

A step-by-step guide from zero to a first result. `README.md` explains what V2 is and how to read the
results; `RUBRIC.md` lists exactly what is judged.

V2 is **advisory**: it is not your grade. It reads your repository, never changes it, and never runs
your code. It uses **your own Claude Code login and usage**.

Run V1 first (`../V1/HOW_TO_RUN.md`): it is free, checks structure, and catches problems (wrong folder,
missing phase reports) that would otherwise waste a V2 run.

---

## 1. Check what you need

| You need | Check with | Notes |
|---|---|---|
| A bash shell | `bash --version` | Linux and macOS: built in. **Windows: use WSL.** |
| Python 3.8 or newer | `python3 --version` | |
| jsonschema (Python package) | `python3 -c "import jsonschema"` | If missing: `python3 -m pip install --user jsonschema` |
| git | `git --version` | |
| Claude Code, logged in | `claude --version` | 2.1.326 or newer (`claude update`). Log in once by running `claude`. |
| *or* Antigravity CLI | `agy --version` | Optional: 1.5.11 or newer, logged in. |

## 2. Keep this folder OUTSIDE your project

Same rule as V1: the `CS441_Autograder_For_Students` clone must not be inside your ScholarChain
repository (it would end up in your submission, and V2 refuses to write results inside your repo).

```
~/CS441_Autograder_For_Students/V2/   <- the judge (this file is here)
~/projects/my-scholarchain/           <- your repository (any name, anywhere)
```

`git pull` in `CS441_Autograder_For_Students` gets new versions and categories.

## 3. Preview for free (no AI call)

```bash
cd ~/CS441_Autograder_For_Students/V2
./judge.sh --student <your NetID> ~/projects/my-scholarchain --dry-run
```

It shows your current phase (your highest `docs/agent-runs/phase-NN` folder) and the categories it will judge:
all of them, whatever your phase (use `--category` to choose). Nothing is sent and nothing is used.

If you see `Permission denied`: `bash judge.sh ...`, or once `chmod +x judge.sh`.

## 4. The real run

```bash
./judge.sh --student <your NetID> ~/projects/my-scholarchain
```

It first asks which AI tool to use (1 = Claude Code with Sonnet, the default; 2 = Antigravity), then prints the
categories it will judge, in project-phase order, and an **estimated cost**, then asks `continue? [y/N]`. Each category takes about 1-2 minutes.

| Category | From phase | Measured cost per run with Opus (API-equivalent; Sonnet, the default, is about 3x lower) |
|---|---:|---|
| `dataset_engineering` | 3 | about $0.30-0.55 |
| `hadoop_mapreduce` | 4 | about $0.45-0.75 |
| `spark_analytics` | 6 | about $0.15-0.35 |

On a Claude subscription this counts against your plan's usage instead of costing money.

Useful options:

| Option | What it does |
|---|---|
| `--category hadoop_mapreduce` | judge only that category (repeat the option for several) |
| `--adapter claude` / `--adapter antigravity` | choose the AI tool without being asked |
| `--yes` | do not ask before starting |

## 5. Read your results

Results are in `V2/results/<repo>-<time>/`:

- `<category>/result.md`: the verdict table. Start here.
- `<category>/result.json`: the judge's reason for every item (`items.<ID>.reason`) and its citations
  (file, lines, exact quote from your code).
- `v2-<NetID>-<time>.csv`: verdicts only. **Share only this file**, and only when your instructor asks.
  Keep everything else on your computer: it quotes your code.

What the words mean is in `README.md` (section 3) and `RUBRIC.md`. `needs_human = yes` in the CSV means
"look at this yourself": the code could not confirm that verdict (for example a citation did not
match your files, or nothing in your project seems to call the code the item is about).

## 6. Common problems

| Message | What to do |
|---|---|
| `is not the root folder of a git repository` | point it at the folder that contains `.git` |
| `needs the Python package jsonschema` | `python3 -m pip install --user jsonschema` |
| `Claude Code ... is older than 2.1.326` | `claude update` |
| `no valid run` in a category | the AI's answer could not be verified (see `<category>/result.md`); run that category again |
| usage limit reached | wait for your plan's usage to reset; `--category` lets you judge one category at a time |
