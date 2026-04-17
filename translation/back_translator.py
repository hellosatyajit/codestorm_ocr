"""Back translation utility (English -> target language)."""

import re

import requests

from .config import HF_CHAT_URL, MODEL, REQUEST_HEADERS


def _clean_translation_text(text: str) -> str:
    """Remove chain-of-thought markers and extra wrapping."""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    cleaned = cleaned.strip('"').strip("'").strip()
    return cleaned


def back_translate(english_text: str, target_lang: str) -> str:
    """Translate English text into the requested target language."""
    prompt = f"""Translate this English text to {target_lang}.
Return ONLY the translated text, nothing else.
Do not include reasoning, tags, or notes.
Keep all details; do not summarize or shorten.
Preserve paragraph structure and line breaks from input.
Use natural, fluent {target_lang} grammar and sentence flow.
Do NOT do literal word-by-word translation.
Prioritize contextual meaning over direct lexical mapping.
Make the output sound like a native speaker wrote it.
If a direct translation sounds awkward, rewrite it idiomatically while preserving meaning.
Keep names/technical terms intact unless a standard native equivalent is better.

Text: "{english_text}" """

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a translation engine. Never include explanations or thinking.",
            },
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.0,
        # "max_tokens": 2200,
    }

    response = requests.post(HF_CHAT_URL, json=payload, headers=REQUEST_HEADERS, timeout=90)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        return ""
    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    return _clean_translation_text(content)
