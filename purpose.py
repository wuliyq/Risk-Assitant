from model_utils import llm_call_clean_sync


def infer_purpose(full_draft: str) -> str:
    messages = [{
        "role": "user",
        "content": (
            "Read the OBJECTIVE and BACKGROUND sections of this paper.\n\n"
            "Do not show reasoning.\n"
            "Return only the final answer after the marker FINAL:.\n\n"
            "Write ONE sentence, max 40 words, stating:\n"
            "1. What is being built or done.\n"
            "2. Why it is needed, meaning the business or operational driver.\n\n"
            "Format exactly:\n"
            "FINAL: <one sentence>\n\n"
            f"PAPER:\n{full_draft[:4000]}"
        ),
    }]

    return llm_call_clean_sync(messages, max_tokens=350)

def purpose_confirm_msg(inferred: str) -> str:
    return (
        "Based on the Objective and Background sections, here is my understanding "
        "of the project purpose:\n\n"
        f"> {inferred}\n\n"
        "**Is this correct?**\n\n"
        "- Reply **Yes** to confirm and move on.\n"
        "- Or describe the correct purpose in your own words and I'll update it."
    )