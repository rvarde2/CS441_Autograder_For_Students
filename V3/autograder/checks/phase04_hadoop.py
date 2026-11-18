"""
Checks due by PHASE 4, "implement raw ingestion and Hadoop MapReduce".

  H01   Hadoop MapReduce really exists: classes extending Mapper / Reducer.
        Deduction: "Hadoop requirement replaced by a local loop, Spark operation, or managed
        import: up to 3 points lost."

Presence is not correctness: this shows MapReduce code exists, not that it parses DBLP right.
FAIL only when there is no Hadoop MapReduce code at all; WARN when Hadoop is used but no
Mapper/Reducer class is found (e.g. Hadoop Streaming scripts: a human or the AI step judges).
"""
import re

from ..registry import check_group
from ..sources import code_lines

SRC = (".scala", ".java", ".py")
MAPPER = re.compile(r"\b(?:extends|with|implements)\s+(?:[\w.]*\.)?(Mapper|Reducer)\b")
HADOOP = re.compile(r"org\.apache\.hadoop\.mapred(?:uce)?\b|hadoop-streaming|hadoop-mapreduce-client")


@check_group(phase=4)
def hadoop(repo, out):
    classes, mentions = {"Mapper": [], "Reducer": []}, set()
    for t, i, line in code_lines(repo, SRC + (".sbt",), skip_tests=True):
        if HADOOP.search(line):
            mentions.add(t)
        if t.endswith(SRC) and (m := MAPPER.search(line)):
            classes[m.group(1)].append(f"{t}:{i}")
    out.record("hadoop", value={"mappers": classes["Mapper"], "reducers": classes["Reducer"],
                                "hadoop_files": sorted(mentions)})
    if classes["Mapper"] and classes["Reducer"]:
        status, details = "PASS", [f"{k}: {', '.join(v[:4])}" + (f" (+{len(v) - 4})" if len(v) > 4 else "")
                                   for k, v in classes.items()]
    elif mentions:
        status, details = "WARN", [f"Hadoop is referenced ({', '.join(sorted(mentions)[:4])}) but no class extending "
                                   f"{' and '.join(k for k, v in classes.items() if not v)} was found"]
    else:
        status, details = "FAIL", ["no Hadoop MapReduce code: no Mapper/Reducer classes and no org.apache.hadoop.mapreduce use"]
    out.add("H01", "Hadoop MapReduce is used (classes extending Mapper and Reducer)", status, details)
