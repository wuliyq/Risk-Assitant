from state import (
    fresh_state,
    append_exchange,
    set_last_bot,
    add_streaming_placeholder,
)

from parsers import is_agreement, is_rejection_only

from classification import (
    classify_paper,
    classification_confirm_msg,
    classification_has_any_user_correction,
    merge_user_classification_correction,
    clean_classification,
    classification_needs_more_info,
)

from purpose import infer_purpose, purpose_confirm_msg
from prompts import build_system_prompt
from model_utils import llm_call_streaming, strip_think


class RiskAssistantFlow:
    def __init__(self, full_draft: str, risk_section: str):
        self.full_draft = full_draft
        self.risk_section = risk_section

    def chat(self, user_message: str, history: list, state: dict):
        user_text = (user_message or "").strip()
        state = state or fresh_state()
        step = state["step"]

        # STEP 0: LLM classifies paper, then always asks user to confirm.
        if step == 0:
            history = add_streaming_placeholder(history, None)

            msg = (
                "Hello! I'm here to help you review the risk management section "
                "of your paper through guided questions.\n\n"
                "First, I'll read the paper and classify the project type."
            )

            history = set_last_bot(history, msg)
            yield history, state

            classification = classify_paper(self.full_draft)
            state["pending_classification"] = classification

            confirm_msg = classification_confirm_msg(classification)

            acc = ""
            for ch in confirm_msg:
                acc += ch
                yield set_last_bot(history, acc), state

            history = set_last_bot(history, confirm_msg)
            state["step"] = 10
            yield history, state
            return

        # STEP 10: User confirms or corrects classification.
        if step == 10:
            pending = state.get("pending_classification") or {}

            user_supplied_correction = classification_has_any_user_correction(user_text)

            if is_agreement(user_text) and not user_supplied_correction:
                confirmed = clean_classification(pending)

            elif is_rejection_only(user_text) and not user_supplied_correction:
                msg = (
                    "No problem — please provide the correct classification.\n\n"
                    "For example:\n\n"
                    "**CAPEX, Physical, Infrastructure**\n\n"
                    "or\n\n"
                    "**CAPEX, Physical, Building**"
                )

                history = append_exchange(history, user_text, msg)
                yield history, state
                return

            else:
                confirmed = merge_user_classification_correction(user_text, pending)

            state["expenditure"] = confirmed.get("expenditure")
            state["physical"] = confirmed.get("physical")
            state["project_type"] = confirmed.get("project_type")
            state["pending_classification"] = confirmed

            history = append_exchange(history, user_text, "")

            missing_msg = classification_needs_more_info(confirmed)

            if missing_msg:
                history = set_last_bot(history, missing_msg)
                yield history, state
                return

            if state["expenditure"] != "CAPEX":
                msg = (
                    "Confirmed — this does not appear to be a **CAPEX** paper.\n\n"
                    "This tool currently reviews Capital Expenditure papers only, "
                    "so I will stop here."
                )

                history = set_last_bot(history, msg)
                state["step"] = 99
                yield history, state
                return

            if state["physical"] != "Physical":
                msg = (
                    "Confirmed — this appears to be **Non-Physical CAPEX**.\n\n"
                    "This tool is currently optimised for Physical CAPEX projects, "
                    "so I will stop here."
                )

                history = set_last_bot(history, msg)
                state["step"] = 99
                yield history, state
                return

            ack = (
                f"Confirmed — this is a **{state['expenditure']}**, "
                f"**{state['physical']}**, **{state['project_type']}** project. ✓\n\n"
                "Now I'll read the paper to extract the project purpose."
            )

            history = set_last_bot(history, ack)
            yield history, state

            inferred = infer_purpose(self.full_draft)
            state["pending_purpose"] = inferred

            confirm = purpose_confirm_msg(inferred)

            history = add_streaming_placeholder(history, None)

            acc = ""
            for ch in confirm:
                acc += ch
                yield set_last_bot(history, acc), state

            history = set_last_bot(history, confirm)
            state["step"] = 4
            yield history, state
            return

        # STEP 4: User confirms or corrects purpose.
        if step == 4:
            if is_agreement(user_text):
                state["purpose"] = state.get("pending_purpose", "")
                ack = (
                    f"Purpose confirmed. ✓\n\n"
                    f"> {state['purpose']}\n\n"
                    "**Before we start, please note:**\n\n"
                    "If a risk is already in your division's risk register, then it is generally "
                    "**not considered a key risk** for this paper.\n\n"
                    "A **key risk** is a risk that falls into one or more of the following categories:\n\n"
                    "1. Risks requiring a management decision or escalation.\n"
                    "2. Risks with regulatory or compliance implications.\n"
                    "3. Strategic or reputational risks that JTC must own.\n"
                    "4. Risks that JTC is prepared to accept without mitigation, meaning deliberate risk-taking.\n\n"
                    "Now let me start reviewing your risk section."
                )
            else:
                state["purpose"] = user_text
                ack = (
                    f"Got it — I've updated the purpose to:\n\n"
                    f"> {state['purpose']}\n\n"
                    "**Before we start, please note:**\n\n"
                    "If a risk is already in your division's risk register, then it is generally "
                    "**not considered a key risk** for this paper.\n\n"
                    "A **key risk** is a risk that falls into one or more of the following categories:\n\n"
                    "1. Risks requiring a decision or escalation.\n"
                    "2. Risks with regulatory or compliance implications.\n"
                    "3. Strategic or reputational risks that JTC must own.\n"
                    "4. Risks that JTC is prepared to accept without mitigation, meaning deliberate risk-taking.\n\n"
                    "Now let me start reviewing your risk section."
                )

            history = append_exchange(history, user_text, ack)
            yield history, state

            system_prompt = build_system_prompt(
                state,
                self.full_draft,
                self.risk_section,
            )

            model_msgs = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Begin your Socratic review. In one sentence, acknowledge the "
                        "project type and purpose. Then ask your first and only question "
                        "about the most important gap you see in the risk section. "
                        "One question only."
                    ),
                },
            ]

            history = add_streaming_placeholder(history, None)

            raw = ""
            for tok in llm_call_streaming(model_msgs):
                raw += tok
                yield set_last_bot(history, strip_think(raw)), state

            history = set_last_bot(history, strip_think(raw))
            state["step"] = 5
            state["risk_q_count"] = 1
            yield history, state
            return

        # STEP 5+: Ongoing Socratic risk review.
        if step >= 5:
            system_prompt = build_system_prompt(
                state,
                self.full_draft,
                self.risk_section,
            )

            model_msgs = [
                {"role": "system", "content": system_prompt},
            ]

            in_review = False

            for msg in history:
                role = msg.get("role")
                content = msg.get("content", "")

                if (
                    role == "assistant"
                    and content
                    and "start reviewing your risk section" in content
                ):
                    in_review = True
                    continue

                if not in_review:
                    continue

                if role in ["user", "assistant"] and content and content.strip():
                    model_msgs.append({
                        "role": role,
                        "content": content,
                    })

            model_msgs.append({
                "role": "user",
                "content": user_text,
            })

            history = append_exchange(history, user_text, "")

            raw = ""
            for tok in llm_call_streaming(model_msgs):
                raw += tok
                yield set_last_bot(history, strip_think(raw)), state

            history = set_last_bot(history, strip_think(raw))
            state["risk_q_count"] += 1
            yield history, state
            return

        # STEP 99: Session stopped.
        if step == 99:
            msg = (
                "This session has ended because the paper is outside the current "
                "scope of the tool. Please reset the session to review another paper."
            )

            history = append_exchange(history, user_text, msg)
            yield history, state
            return

    def reset_session(self):
        return [], fresh_state(), ""