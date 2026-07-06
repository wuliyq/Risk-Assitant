import gradio as gr

from config import DRAFT_FILE
from paper_loader import load_draft
from state import fresh_state
from chat_flow import RiskAssistantFlow


FULL_DRAFT, RISK_SECTION = load_draft(DRAFT_FILE)

if not FULL_DRAFT:
    print(f"WARNING: Could not load draft from {DRAFT_FILE}")

flow = RiskAssistantFlow(
    full_draft=FULL_DRAFT,
    risk_section=RISK_SECTION,
)


with gr.Blocks(theme=gr.themes.Soft(), title="Risk Assistant") as demo:

    state = gr.State(fresh_state())

    gr.Markdown(
        "# 🏛️ Socratic Project Risk Assistant\n"
        "Click **Start** to begin. The assistant will read the paper, classify it, "
        "ask you to confirm the classification, then guide you through the risk "
        "section one question at a time."
    )

    chatbot = gr.Chatbot(label="Session", height=600)

    hidden_start_input = gr.Textbox(value="", visible=False)

    with gr.Row():
        user_input = gr.Textbox(
            label="Your reply",
            placeholder="Type here and press Enter...",
            scale=5,
            lines=1,
        )

        send_btn = gr.Button("Send", scale=1, variant="primary")

    with gr.Row():
        start_btn = gr.Button("Start", variant="primary")
        reset_btn = gr.Button("Reset", variant="secondary")

    start_btn.click(
        fn=flow.chat,
        inputs=[hidden_start_input, chatbot, state],
        outputs=[chatbot, state],
    )

    send_btn.click(
        fn=flow.chat,
        inputs=[user_input, chatbot, state],
        outputs=[chatbot, state],
    ).then(
        fn=lambda: "",
        outputs=user_input,
    )

    user_input.submit(
        fn=flow.chat,
        inputs=[user_input, chatbot, state],
        outputs=[chatbot, state],
    ).then(
        fn=lambda: "",
        outputs=user_input,
    )

    reset_btn.click(
        fn=flow.reset_session,
        inputs=[],
        outputs=[chatbot, state, user_input],
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
    )