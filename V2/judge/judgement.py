"""
judgement.py (V2): turn the schema TEMPLATE into the schema for one rubric category.

    from judgement import category_schema
    schema = category_schema("spark_analytics", ["SPARK-01", ...], ["SPARK-COLLECT", ...])

Filled in per category, so the AI can't invent, skip or rename anything:
  - category: the id, as a const
  - items: exactly len(item_ids) entries; item_id from that list only
  - deductions: exactly len(deduction_ids) entries; deduction_id from that list only
(JSON Schema can't say "each id exactly once" for objects in a list; verify.py checks that.)
"""
import copy
import json
from pathlib import Path

TEMPLATE = json.loads((Path(__file__).resolve().parent / "judgement.schema.json").read_text())


def category_schema(category, item_ids, deduction_ids):
    if not item_ids:
        raise ValueError("a category needs at least one rubric item")
    if len(set(item_ids)) != len(item_ids) or len(set(deduction_ids)) != len(deduction_ids):
        raise ValueError("duplicate ids")
    s = copy.deepcopy(TEMPLATE)
    s.pop("$comment", None)
    p = s["properties"]
    p["category"]["const"] = category
    p["items"]["minItems"] = p["items"]["maxItems"] = len(item_ids)
    p["items"]["items"]["properties"]["item_id"]["enum"] = list(item_ids)
    p["deductions"]["minItems"] = p["deductions"]["maxItems"] = len(deduction_ids)
    if deduction_ids:
        p["deductions"]["items"]["properties"]["deduction_id"]["enum"] = list(deduction_ids)
    else:                                   # a category with no related deductions: empty list only
        p["deductions"]["items"]["properties"]["deduction_id"].pop("enum")
    return s
