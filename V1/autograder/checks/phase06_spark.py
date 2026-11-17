"""
Checks due by PHASE 6, "build the temporal coauthorship graph and run Spark analytics".

  A01   Spark code doesn't pull data to one machine. Deduction: "Spark coauthorship analytics
        absent or performed by collecting the graph to one process: up to 3 points lost."

Collecting a small summary (top-10 researchers) is legitimate, so every hit is a WARN with file
and line, for a human or the AI step to judge. Only Spark code is looked at: files under a path
containing "spark", or files that import org.apache.spark / pyspark.
"""
import re

from ..registry import check_group
from ..sources import code_lines

SRC = (".scala", ".java", ".py")
COLLECT = re.compile(r"\.(collect|collectAsList|collectAsMap|toLocalIterator|toPandas)\s*\(?")
SPARK = re.compile(r"org\.apache\.spark|pyspark")


@check_group(phase=6)
def spark(repo, out):
    spark_files = {t for t, _, line in code_lines(repo, SRC, skip_tests=True) if SPARK.search(line)}
    spark_files |= {t for t in repo.tracked if "spark" in t.lower() and t.endswith(SRC)}
    hits = [f"{t}:{i}: .{m.group(1)}" for t, i, line in code_lines(repo, SRC, skip_tests=True)
            if t in spark_files and (m := COLLECT.search(line))]
    out.record("spark", value={"files": sorted(spark_files), "collect_calls": [h.rsplit(": .", 1)[0] for h in hits]})
    if not spark_files:
        status, details = "WARN", ["no Spark code found (no path containing 'spark', no org.apache.spark / pyspark import)"]
    else:
        status = "WARN" if hits else "PASS"
        details = hits[:20] + ([f"... and {len(hits) - 20} more"] if len(hits) > 20 else []) \
            + [f"{len(spark_files)} Spark source file(s) checked"]
    out.add("A01", "Spark code doesn't collect data to one machine (.collect, .toLocalIterator, ...)", status, details)
