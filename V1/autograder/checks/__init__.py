"""
Check modules. Importing a module registers its groups (see registry.check_group).

  always.py            due from phase 0: S01 F02 P01 G01-03 K01-03 E01-07 C01-03 (+ X04)
  phase01_factory.py   phase 1: F01 F03-07 O01-06 R01-08
  phase02_build.py     phase 2: K04
  phase04_hadoop.py    phase 4: H01 (Hadoop MapReduce exists)
  code_hygiene.py      phase 4: V01 (hard-coded buckets/ARNs/endpoints/model IDs)
  phase06_spark.py     phase 6: A01 (no collect to one machine)
  phase11_tests.py     phase 11: T01 (+ X05)
  phase13_automation.py phase 13: U01 (scripts in bash strict mode)
  requirements.py      the TABLE module: B01 M01-M04 W01 W02, one row each in data/phase_requirements.json
  observations.py      X01-X03, X06: record, never judge

To add a check:
  - a simple requirement (a path, a folder, named definitions, a heading): add a ROW to
    data/phase_requirements.json; no code
  - anything with its own logic: a function decorated @check_group(phase=N) in the module for that
    phase (or a new checks/phaseNN_<topic>.py, added to the import line below)
  - always: a NEW ID (never reuse one), the quoted README rule, all repo access through `repo`,
    and a test repo that passes it plus one that fails it, then the regression run
"""
from . import (always, phase01_factory, phase02_build, phase04_hadoop, code_hygiene,  # noqa: F401
               phase06_spark, phase11_tests, phase13_automation, requirements, observations)
