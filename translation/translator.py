"""Core translator that converts source text into English."""

import json
import re
from typing import Dict

import requests

from .config import HF_CHAT_URL, MODEL, REQUEST_HEADERS


def _extract_json_object(raw: str) -> dict:
    """Extract first JSON object from model output."""
    cleaned = raw.strip().strip("`")

    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return {}

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def translate_block(text: str) -> Dict[str, object]:
    """Detect language/script and translate text to English."""
    prompt = f"""You are a multilingual translation engine.

Given this extracted text: "{text}"

Return ONLY valid JSON with these exact fields:
{{
  "detected_language": "full language name e.g. Arabic",
  "language_code": "ISO 639-1 code e.g. ar",
  "script": "script name e.g. Arabic, Devanagari, CJK, Cyrillic",
  "confidence": 0.95,
  "translation_en": "English translation here"
}}

No markdown. No explanation. Pure JSON only."""

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a precise translator. Return only valid JSON.",
            },
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.0,
        "max_tokens": 1400,
    }

    response = requests.post(HF_CHAT_URL, json=payload, headers=REQUEST_HEADERS, timeout=90)
    response.raise_for_status()

    data = response.json()

    raw = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "{}")
        if isinstance(data, dict)
        else "{}"
    )

    parsed = _extract_json_object(raw)

    return {
        "detected_language": parsed.get("detected_language", "Unknown"),
        "language_code": parsed.get("language_code", "unknown"),
        "script": parsed.get("script", "Unknown"),
        "confidence": float(parsed.get("confidence", 0.0)),
        "translation_en": parsed.get("translation_en", ""),
    }
