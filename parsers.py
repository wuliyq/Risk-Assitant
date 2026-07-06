import re


def has_negation_near(text: str, keyword: str) -> bool:
    t = text.lower()

    patterns = [
        rf"\bnot\s+(a\s+|an\s+|the\s+)?{keyword}\b",
        rf"\bno\s+{keyword}\b",
        rf"\bnon[-\s]?{keyword}\b",
    ]

    return any(re.search(p, t) for p in patterns)


def parse_capex_opex(text: str):
    t = text.lower()

    capex_positive = (
        ("capex" in t or "capital expenditure" in t or "capital" in t)
        and not has_negation_near(t, "capex")
        and "not capital" not in t
    )

    opex_positive = (
        (
            "opex" in t
            or "operating expenditure" in t
            or "operating" in t
            or "operational" in t
        )
        and not has_negation_near(t, "opex")
        and "not operating" not in t
    )

    if capex_positive:
        return "CAPEX"

    if opex_positive:
        return "OPEX"

    if has_negation_near(t, "capex") or "not capital" in t:
        return "OPEX"

    return "Other"


def parse_physical(text: str):
    t = text.lower()

    if (
        "non-physical" in t
        or "non physical" in t
        or "not physical" in t
        or "intangible" in t
        or "software" in t
        or "it system" in t
    ):
        return "Non-Physical"

    if (
        "physical" in t
        or "construction" in t
        or "civil works" in t
        or "site works" in t
        or "road" in t
        or "drain" in t
        or "sewer" in t
        or "utility" in t
        or "utilities" in t
        or "building" in t
        or "infrastructure" in t
    ):
        return "Physical"

    return "Other"


def parse_project_type(text: str):
    t = text.lower()

    if (
        "building" in t
        or "build" in t
        or "facility" in t
        or "factory" in t
        or "muf" in t
        or "warehouse" in t
        or "dormitory" in t
    ):
        return "Building"

    if (
        "estate" in t
        or "land preparation" in t
        or "master planning" in t
        or "district" in t
    ):
        return "Estate"

    if (
        "infrastructure" in t
        or "infra" in t
        or "road" in t
        or "drain" in t
        or "sewer" in t
        or "utilities" in t
        or "utility" in t
        or "platform levelling" in t
        or "platform leveling" in t
    ):
        return "Infrastructure"

    return "Other"


def is_agreement(text: str) -> bool:
    t = text.lower().strip(" .,!?\n\t")

    agree_exact = {
        "yes",
        "y",
        "correct",
        "right",
        "yep",
        "yup",
        "ok",
        "okay",
        "sure",
        "confirmed",
        "agree",
        "yes correct",
        "yes it is correct",
        "classification is correct",
        "this is correct",
    }

    return t in agree_exact


def is_rejection_only(text: str) -> bool:
    t = text.lower().strip(" .,!?\n\t")

    reject_exact = {
        "no",
        "n",
        "wrong",
        "incorrect",
        "not correct",
        "classification is wrong",
        "this is wrong",
    }

    return t in reject_exact