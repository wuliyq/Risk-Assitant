import re
import json

from model_utils import llm_call_sync, strip_think
from parsers import (
    parse_capex_opex,
    parse_physical,
    parse_project_type,
)


def extract_json_object(raw: str) -> dict:
    cleaned = strip_think(raw).strip()
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)

    if not match:
        raise ValueError("No JSON object found.")

    return json.loads(match.group(0))


def normalize_label(value, allowed, default="Unclear"):
    if not isinstance(value, str):
        return default

    v = value.strip().lower()

    for label in allowed:
        if v == label.lower():
            return label

    return default


def normalize_confidence(value) -> float:
    try:
        if isinstance(value, str):
            value = value.strip().replace("%", "")
            value = float(value)

            if value > 1:
                value = value / 100.0
        else:
            value = float(value)
    except Exception:
        value = 0.0

    return max(0.0, min(1.0, value))


def clean_classification(raw_dict: dict) -> dict:
    expenditure = normalize_label(
        raw_dict.get("expenditure"),
        ["CAPEX", "OPEX", "Unclear"],
    )

    physical = normalize_label(
        raw_dict.get("physical"),
        ["Physical", "Non-Physical", "Unclear"],
    )

    project_type = normalize_label(
        raw_dict.get("project_type"),
        ["Estate", "Building", "Infrastructure", "Unclear"],
    )

    confidence = normalize_confidence(raw_dict.get("confidence", 0.0))

    reason = raw_dict.get("reason", "")
    if not isinstance(reason, str):
        reason = ""

    evidence = raw_dict.get("evidence", [])
    if isinstance(evidence, str):
        evidence = [evidence]

    if not isinstance(evidence, list):
        evidence = []

    evidence = [str(e).strip() for e in evidence if str(e).strip()]

    return {
        "expenditure": expenditure,
        "physical": physical,
        "project_type": project_type,
        "confidence": confidence,
        "reason": reason.strip(),
        "evidence": evidence[:3],
    }


def classify_paper(full_draft: str) -> dict:
    if not full_draft:
        return {
            "expenditure": "Unclear",
            "physical": "Unclear",
            "project_type": "Unclear",
            "confidence": 0.0,
            "reason": "No paper text was loaded.",
            "evidence": [],
        }

    messages = [{
        "role": "user",
        "content": f"""
You are classifying a project approval paper.

Read the paper and classify it using ONLY the allowed labels.

Return valid JSON only. Do not include markdown. Do not include explanation outside JSON.

JSON schema:
{{
  "expenditure": "CAPEX" | "OPEX" | "Unclear",
  "physical": "Physical" | "Non-Physical" | "Unclear",
  "project_type": "Estate" | "Building" | "Infrastructure" | "Unclear",
  "confidence": 0.0,
  "reason": "brief explanation",
  "evidence": ["short quote or paraphrase from the paper"]
}}

Definitions:
- CAPEX: new assets, construction, significant upgrades, or consultancy services for a development project.
- OPEX: recurring running costs, maintenance, or operational services.
- Physical: construction, civil works, site preparation, buildings, roads, drains, pipes, utilities, or other tangible infrastructure.
- Non-Physical: IT systems, software, studies, or intangible assets only.
- Estate: land preparation, master planning, or developing an entire district or estate.
- Building: constructing a building from scratch to meet identified customer needs.
- Infrastructure: enabling works serving multiple developments, such as roads, drains, sewers, utilities, substations, service corridors, or platform levelling.

Important:
- Consultancy services for a physical development project should still be treated as CAPEX if the consultancy supports development or construction.
- If the paper is only about recurring operations, routine maintenance, or running services, classify it as OPEX.
- If there is insufficient information, use "Unclear".

PAPER:
{full_draft[:8000]}
"""
    }]

    raw = llm_call_sync(messages, max_tokens=400)

    try:
        parsed = extract_json_object(raw)
        return clean_classification(parsed)
    except Exception:
        return {
            "expenditure": "Unclear",
            "physical": "Unclear",
            "project_type": "Unclear",
            "confidence": 0.0,
            "reason": "The model did not return a valid JSON classification.",
            "evidence": [],
        }


def classification_confirm_msg(c: dict) -> str:
    evidence = c.get("evidence", [])

    if evidence:
        evidence_text = "\n".join(f"- {e}" for e in evidence[:3])
    else:
        evidence_text = "- No clear evidence extracted."

    return (
        "I've read the paper and classified it as:\n\n"
        f"- **Expenditure**: {c.get('expenditure', 'Unclear')}\n"
        f"- **Physicality**: {c.get('physical', 'Unclear')}\n"
        f"- **Project type**: {c.get('project_type', 'Unclear')}\n"
        f"- **Confidence**: {c.get('confidence', 0.0):.2f}\n\n"
        f"**Reason:**\n{c.get('reason', '') or 'No reason provided.'}\n\n"
        f"**Evidence from the paper:**\n{evidence_text}\n\n"
        "**Please confirm if this classification is correct.**\n\n"
        "- Reply **Yes** to confirm and continue.\n"
        "- Or correct it, for example: **CAPEX, Physical, Infrastructure**."
    )


def merge_user_classification_correction(user_text: str, pending: dict) -> dict:
    merged = dict(pending or {})

    corrected_expenditure = parse_capex_opex(user_text)
    corrected_physical = parse_physical(user_text)
    corrected_project_type = parse_project_type(user_text)

    if corrected_expenditure:
        merged["expenditure"] = corrected_expenditure

    if corrected_physical:
        merged["physical"] = corrected_physical

    if corrected_project_type:
        merged["project_type"] = corrected_project_type

    return clean_classification(merged)


def classification_has_any_user_correction(user_text: str) -> bool:
    return any([
        parse_capex_opex(user_text),
        parse_physical(user_text),
        parse_project_type(user_text),
    ])


def classification_needs_more_info(c: dict) -> str:
    expenditure = c.get("expenditure")
    physical = c.get("physical")
    project_type = c.get("project_type")

    if expenditure not in ["CAPEX", "OPEX"]:
        return (
            "I still cannot clearly determine whether this is **CAPEX** or **OPEX**.\n\n"
            "Please reply with the correct classification, for example:\n\n"
            "**CAPEX, Physical, Infrastructure**"
        )

    if expenditure == "CAPEX" and physical not in ["Physical", "Non-Physical"]:
        return (
            "I still cannot clearly determine whether this is **Physical** or **Non-Physical CAPEX**.\n\n"
            "Please reply with the correct classification, for example:\n\n"
            "**CAPEX, Physical, Infrastructure**"
        )

    if expenditure == "CAPEX" and physical == "Physical":
        if project_type not in ["Estate", "Building", "Infrastructure"]:
            return (
                "I still cannot clearly determine whether this is an **Estate**, "
                "**Building**, or **Infrastructure** project.\n\n"
                "Please reply with the correct classification, for example:\n\n"
                "**CAPEX, Physical, Infrastructure**"
            )

    return ""