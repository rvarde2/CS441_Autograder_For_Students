"""
prompt.py (V2): build the TRUSTED system prompt and the matching schema for one rubric category.

    from prompt import load_rubric, system_prompt, schema_for
    rubric = load_rubric("spark_analytics")
    text   = system_prompt(rubric)       # prompts/judge_system.md with the category filled in
    schema = schema_for(rubric)          # judgement.schema.json with this category's ids

Layer 1 of the injection defence: the system prompt is built ONLY from text we control
(prompts/judge_system.md + rubric/<category>.json). Nothing derived from a student's repository
(file contents, file NAMES, V1 facts, AI summaries) ever goes into it; that belongs in the user
message, labelled as data (the runner's job).
Prompt and schema are built from the SAME rubric file, so they always list the same ids.
"""
import json
import re
from pathlib import Path

from judgement import category_schema

HERE = Path(__file__).resolve().parent
TEMPLATE = (HERE / "prompts" / "judge_system.md").read_text()
PROMPT_VERSION = "judge_system/4"   # /2: severity words; /3: one problem one place; /4: called_by_job is a flag, not a verdict (round 3 review)


def load_rubric(category_id):
    data = json.loads((HERE / "rubric" / f"{category_id}.json").read_text())
    if data["category_id"] != category_id:
        raise ValueError(f"rubric file {category_id}.json declares {data['category_id']}")
    return data


def _items(rubric):
    width = max(len(i["id"]) for i in rubric["items"])
    return "\n".join(f"  {i['id']:<{width}}  {i['text']}" for i in rubric["items"])


def _deductions(rubric):
    if not rubric["deductions"]:
        return "  (none for this category)"
    width = max(len(d["id"]) for d in rubric["deductions"])
    return "\n".join(f"  {d['id']:<{width}}  \"{d['quote']}\"" for d in rubric["deductions"])


def system_prompt(rubric):
    text = (TEMPLATE.replace("{{CATEGORY_NAME}}", rubric["category_name"])
                    .replace("{{CATEGORY_ID}}", rubric["category_id"])
                    .replace("{{README_FULL_CREDIT}}", rubric["readme_full_credit"])
                    .replace("{{ITEMS}}", _items(rubric))
                    .replace("{{DEDUCTIONS}}", _deductions(rubric)))
    if (left := re.findall(r"\{\{[A-Z_]+\}\}", text)):          # fail loudly, never send a half prompt
        raise ValueError(f"unfilled placeholders: {left}")
    return text


def schema_for(rubric):
    return category_schema(rubric["category_id"], [i["id"] for i in rubric["items"]],
                           [d["id"] for d in rubric["deductions"]])
