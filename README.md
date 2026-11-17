# CS441 ScholarChain self-check

An **advisory** checker you run on **your own project repository** (your implementation of the
ScholarChain assignment, not the assignment repository). It is not your grade.

| Folder | Version | Status |
|---|---|---|
| [`V1/`](V1/) | 1.0.1 | current (what's new: [`V1/README.md`](V1/README.md#whats-new-in-101)) |

**Start here:** [`V1/HOW_TO_RUN.md`](V1/HOW_TO_RUN.md) (step by step), then [`V1/README.md`](V1/README.md)
(what every check means) and [`V1/DESIGN.md`](V1/DESIGN.md) (how each check decides).

```bash
git clone https://github.com/rvarde2/CS441_Autograder_For_Students.git
cd CS441_Autograder_For_Students/V1
./selfcheck.sh --student <your NetID> ~/path/to/your-scholarchain-repo
```

Results are saved in `V1/selfcheck-results/`. **Share only the `.csv` file** when your instructor
asks; keep the `.json` on your computer.

New versions are added as new folders (`V2/`, ...); `git pull` gets them. Older versions stay
unchanged, so earlier results can always be traced to the code that produced them.
