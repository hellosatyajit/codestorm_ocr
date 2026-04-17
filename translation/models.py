"""Typed data models for OCR translation pipeline."""

from typing import Any, TypedDict


class TranslationBlock(TypedDict):
    id: str
    bbox: Any
    original_text: str
    detected_language: str
    language_code: str
    script: str
    confidence: float
    translation_en: str
    back_translation: str | None
    back_translation_lang: str | None
    error: str | None
