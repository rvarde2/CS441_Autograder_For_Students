# CS441 ScholarChain self-check

An **advisory** checker you run on your own ScholarChain repository. It is not your grade.

| Folder | Version | Status |
|---|---|---|
| [`V1/`](V1/) | 1.x | current |

**Start here:** [`V1/HOW_TO_RUN.md`](V1/HOW_TO_RUN.md) (step by step), then [`V1/README.md`](V1/README.md)
(what every check means) and [`V1/DESIGN.md`](V1/DESIGN.md) (how each check decides).

```bash
git clone https://github.com/rvarde2/CS441_Autograder_For_Students.git
cd CS441_Autograder_For_Students/V1
./selfcheck.sh --student <your NetID> ~/path/to/your-scholarchain-repo
```

New versions are added as new folders (`V2/`, ...); `git pull` gets them. Older versions stay
unchanged, so earlier results can always be traced to the code that produced them.
