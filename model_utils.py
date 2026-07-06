import re
import torch

from threading import Thread
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

from config import MODEL_ID, MAX_NEW_TOKENS


_tokenizer = None
_model = None


def get_model_and_tokenizer():
    global _tokenizer, _model

    if _tokenizer is not None and _model is not None:
        return _model, _tokenizer

    print(f"Loading {MODEL_ID}...")

    _tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

    if _tokenizer.pad_token is None:
        _tokenizer.pad_token = _tokenizer.eos_token

    _model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )

    print("Model ready.")

    return _model, _tokenizer


def strip_think(text: str) -> str:
    """
    Remove DeepSeek-style thinking blocks.

    Handles both:
    - complete <think>...</think>
    - incomplete streaming <think>... that has not closed yet
    """
    # Remove complete think blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

    # Remove incomplete think block during streaming
    text = re.sub(r"<think>.*", "", text, flags=re.DOTALL)

    return text.strip()


def llm_call_sync(messages: list, max_tokens: int = 150) -> str:
    """
    Blocking LLM call.
    Use for short internal tasks:
    - paper classification
    - purpose extraction
    - JSON generation
    """
    model, tokenizer = get_model_and_tokenizer()

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            do_sample=False,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )

    new_ids = output_ids[0][inputs["input_ids"].shape[1]:]
    decoded = tokenizer.decode(new_ids, skip_special_tokens=True)

    return strip_think(decoded).strip()

def llm_call_raw_sync(messages: list, max_tokens: int = 500) -> str:
    """
    Generate the model response internally.
    Does not clean the output.
    Does not stream to Gradio.
    """
    model, tokenizer = get_model_and_tokenizer()

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            do_sample=False,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )

    new_ids = output_ids[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(new_ids, skip_special_tokens=True).strip()

def clean_for_user(text: str) -> str:
    """
    Removes reasoning-style text before showing answer to user.
    """
    text = strip_think(text).strip()

    # If model follows FINAL: format, keep only final answer.
    markers = [
        "FINAL:",
        "Final:",
        "FINAL ANSWER:",
        "Final answer:",
        "Answer:",
    ]

    for marker in markers:
        if marker in text:
            return text.split(marker, 1)[1].strip()

    # Remove common reasoning openings if model did not follow marker format.
    reasoning_phrases = [
        "Okay, so",
        "Okay, I need",
        "I need to figure out",
        "Let's analyze",
        "Let me analyze",
        "We need to",
    ]

    for phrase in reasoning_phrases:
        if text.startswith(phrase):
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            if paragraphs:
                return paragraphs[-1]

    return text.strip()

def llm_call_clean_sync(messages: list, max_tokens: int = 500) -> str:
    """
    Generate internally, clean reasoning text, then return only user-facing answer.
    """
    raw = llm_call_raw_sync(messages, max_tokens=max_tokens)
    return clean_for_user(raw)

def llm_call_streaming(messages: list):
    """
    Streaming LLM call.
    Use for user-facing chatbot replies.
    Yields text chunks as the model generates them.
    """
    model, tokenizer = get_model_and_tokenizer()

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    streamer = TextIteratorStreamer(
        tokenizer,
        skip_prompt=True,
        skip_special_tokens=True,
    )

    thread = Thread(
        target=model.generate,
        kwargs=dict(
            **inputs,
            streamer=streamer,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        ),
    )

    thread.start()

    for tok in streamer:
        yield tok

    thread.join()