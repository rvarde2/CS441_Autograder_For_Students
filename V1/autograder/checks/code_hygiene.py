"""
Code hygiene, due by PHASE 4 (when module code starts).

  V01   No hard-coded cloud locations or model IDs in production source code. Deduction:
        "Hardcoded buckets, endpoints, account IDs, thresholds, or model IDs without configuration
        rationale: up to 1 point lost."

Looked at: tracked .scala/.java/.py files, NOT tests, config files or docs (where such values
belong). Reported by KIND, file and line; the value itself is never printed. WARN: a value with a
documented rationale is allowed. Thresholds can't be recognised by pattern and aren't checked.
"""
import re

from ..registry import check_group
from ..sources import code_lines

KINDS = {
    # a LITERAL bucket name: "s3://my-bucket/..." counts; s"s3://$bucket", "s3://" + x and
    # startsWith("s3://") don't (1.0.1: 1.0.0 flagged every scheme literal)
    "S3 location": re.compile(r"[\"']s3a?://([a-z0-9][a-z0-9.\-]{2,})"),
    # a COMPLETE literal ARN (partition:service:region:account:resource). A prefix being built from
    # parts, "arn:aws:sqs:" + region + ..., is not hard-coded (1.0.4)
    "AWS ARN": re.compile(r"[\"']arn:aws[\w-]*:[^:\"'\s]*:[^:\"'\s]*:([^:\"'\s]*):[^\"'\s]+"),
    "AWS endpoint": re.compile(r"[\"'][\w.-]*\.amazonaws\.com"),
    "AWS account ID": re.compile(r"(?i)account[\w\s\"':=]*[\"'](\d{12})[\"']"),
    "model ID": re.compile(r"[\"'](?:anthropic\.|claude-|amazon\.titan|cohere\.|meta\.llama|gpt-\d|text-embedding-)"),
}
# (1.0.4) Not configuration, so never reported:
#   PUBLIC dataset buckets: their location is fixed by the dataset provider (OpenAlex snapshot, arXiv bulk data)
#   PLACEHOLDER account IDs: one repeated digit (000000000000) or AWS's documentation example 123456789012
PUBLIC_BUCKETS = {"openalex", "arxiv"}


def placeholder_account(acct):
    return bool(acct) and (len(set(acct)) == 1 or acct == "123456789012")


def reportable(kind, m):
    if kind == "S3 location":
        return m.group(1).split("/")[0] not in PUBLIC_BUCKETS
    if kind in ("AWS ARN", "AWS account ID"):
        return not placeholder_account(m.group(1))
    return True


@check_group(phase=4)
def hardcoded_values(repo, out):
    hits = [f"{t}:{i}: {kind}" for t, i, line in code_lines(repo, (".scala", ".java", ".py"), skip_tests=True)
            for kind, rx in KINDS.items() if (m := rx.search(line)) and reportable(kind, m)]
    out.record("hardcoded_values", value=hits)
    out.add("V01", "No hard-coded buckets, ARNs, endpoints, account IDs or model IDs in source code",
            "WARN" if hits else "PASS",
            hits[:20] + ([f"... and {len(hits) - 20} more"] if len(hits) > 20 else [])
            + (["move them to configuration, or document why they're fixed"] if hits else []))
