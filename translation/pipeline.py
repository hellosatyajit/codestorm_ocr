"""Main OCR translation pipeline."""

from typing import Any

from .back_translator import back_translate
from .models import TranslationBlock
from .translator import translate_block


def process_document(blocks: list[dict[str, Any]], back_lang: str = None) -> list[TranslationBlock]:
    """Translate OCR blocks and optionally back-translate to selected language."""
    results: list[TranslationBlock] = []

    for block in blocks:
        block_id = str(block.get("id", ""))
        block_bbox = block.get("bbox")
        block_text = str(block.get("text", ""))

        try:
            translated = translate_block(block_text)
            result: TranslationBlock = {
                "id": block_id,
                "bbox": block_bbox,
                "original_text": block_text,
                "detected_language": str(translated.get("detected_language", "Unknown")),
                "language_code": str(translated.get("language_code", "unknown")),
                "script": str(translated.get("script", "Unknown")),
                "confidence": float(translated.get("confidence", 0.0)),
                "translation_en": str(translated.get("translation_en", "")),
                "back_translation": None,
                "back_translation_lang": None,
                "error": None,
            }

            if back_lang:
                result["back_translation"] = back_translate(result["translation_en"], back_lang)
                result["back_translation_lang"] = back_lang

            results.append(result)
        except Exception as exc:
            fallback: TranslationBlock = {
                "id": block_id,
                "bbox": block_bbox,
                "original_text": block_text,
                "detected_language": "Unknown",
                "language_code": "unknown",
                "script": "Unknown",
                "confidence": 0.0,
                "translation_en": "[Translation failed]",
                "back_translation": None,
                "back_translation_lang": back_lang if back_lang else None,
                "error": str(exc),
            }
            results.append(fallback)

    return results
