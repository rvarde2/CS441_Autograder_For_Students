# ScholarChain V4: your score

V4 turns your V1, V2 and V3 results into **points gained**, **points deducted** and a **score** (gained minus
deducted), per phase and overall, with a reason on every row. It uses exactly the weights and deductions used in
grading: see [`../RUBRIC.md`](../RUBRIC.md).

It does not read your repository and does not use AI: it only combines the results your own V1/V2/V3 runs saved.

## Run it

1. Run V1, V2 and V3 on your repository first (see `../V1/HOW_TO_RUN.md` and `../V2/HOW_TO_RUN.md`).
   Commit your work before running them: only committed files are checked.
2. Then, from this folder:

```bash
cd ~/CS441_Autograder_For_Students/V4
./score.sh --student <your NetID>
```

If you see `Permission denied`: `bash score.sh --student <your NetID>`.

It uses your **latest** run of each: V1 (`../V1/selfcheck-results/`), each V2 category and V3 (`../V2/results/`,
`../V3/results/`). If they were run on different commits, the sheet says so: re-run them on the same commit.

## What you get

Printed: points gained (of 9.0), points deducted, score, and a table per phase. Saved in `V4/results/<time>/`:

| File | What |
|---|---|
| `<NetID>.md` | your score sheet: every item and deduction with its points, status and reason (the judge's reason and the cited file and line) |
| `<NetID>.csv` | the same rows as a spreadsheet |
| `phases.csv` | gained, deducted and score per phase |

Row statuses: `auto` scored; `CHECK` scored but flagged by the verifier (the instructor looks at it); `PENDING` not
scored automatically (the judge could not decide, or the instructor decides); `CONFIRM` a proposed deduction (e.g.
a possible secret) that counts only if the instructor confirms it.

## Limits

- This covers the 9.0 points the autograder scores and the deductions in `RUBRIC.md`. The other 11.0 points are
  graded by the instructor.
- Your score here can differ from the graded one: the AI judge can vary between runs, and grading is run on your
  submitted tag.
- Nothing needs to be sent to anyone.
