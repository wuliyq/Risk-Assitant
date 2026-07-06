import os
import json


def load_draft(path: str) -> tuple[str, str]:
    """
    Returns:
      full_text: all paper sections
      risk_section_text: only risk-related sections
    """
    if not os.path.exists(path):
        return "", ""

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    doc = data[0] if isinstance(data, list) else data

    risk_keywords = {
        "risk management",
        "risk analysis",
        "risk inputs",
    }

    all_parts = []
    risk_parts = []

    for sec in doc.get("sections", []):
        heading = sec.get("heading", "")
        raw_text = sec.get("raw_text", "").strip()

        if not raw_text:
            continue

        block = f"[{heading}]\n{raw_text}"
        all_parts.append(block)

        if any(kw in heading.lower() for kw in risk_keywords):
            risk_parts.append(block)

    return "\n\n".join(all_parts), "\n\n".join(risk_parts)