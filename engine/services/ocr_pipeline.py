"""OCR pipeline service.

This module bridges the Django engine app to the translation package.
It accepts extractor-style OCR blocks and returns enriched TranslationBlock dicts.

Usage (from views.py or any Django code):
    from engine.services.ocr_pipeline import run_ocr_translation

    results = run_ocr_translation(blocks, back_lang="Gujarati")
"""

from typing import Any

from translation.pipeline import process_document


def run_ocr_translation(
    blocks: list[dict[str, Any]],
    back_lang: str | None = None,
) -> list[dict[str, Any]]:
    """Translate OCR blocks and optionally back-translate to target language.

    Args:
        blocks: List of OCR block dicts with keys: id, text, bbox (optional).
        back_lang: Target language name for back translation, e.g. "Gujarati".
                   Pass None to skip back translation.

    Returns:
        List of TranslationBlock dicts (see translation/models.py for schema).
    """
    return process_document(blocks, back_lang=back_lang)
