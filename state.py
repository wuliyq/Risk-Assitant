def fresh_state() -> dict:
    return {
        "step": 0,

        "expenditure": None,
        "physical": None,
        "project_type": None,

        "pending_classification": None,

        "pending_purpose": None,
        "purpose": None,

        "risk_q_count": 0,
    }


def _history(history: list) -> list:
    return list(history or [])


def append_bot(history: list, msg: str) -> list:
    history = _history(history)
    history.append({
        "role": "assistant",
        "content": msg,
    })
    return history


def append_exchange(history: list, user: str, bot: str) -> list:
    history = _history(history)

    if user is not None and str(user).strip():
        history.append({
            "role": "user",
            "content": user,
        })

    history.append({
        "role": "assistant",
        "content": bot,
    })

    return history


def set_last_bot(history: list, msg: str) -> list:
    history = _history(history)

    if history and history[-1].get("role") == "assistant":
        history[-1]["content"] = msg
    else:
        history.append({
            "role": "assistant",
            "content": msg,
        })

    return history


def add_streaming_placeholder(history: list, user: str = None) -> list:
    history = _history(history)

    if user is not None and str(user).strip():
        history.append({
            "role": "user",
            "content": user,
        })

    history.append({
        "role": "assistant",
        "content": "",
    })

    return history