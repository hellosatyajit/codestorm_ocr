"""Django views for the OCR Translation engine.

Endpoints:
  POST /api/translate/      - Translate OCR blocks (JSON body)
  GET  /api/languages/      - List supported back-translation languages
  GET  /api/health/         - Health-check
"""

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from engine.services.ocr_pipeline import run_ocr_translation
from translation.config import SUPPORTED_BACK_LANGS


@csrf_exempt
@require_http_methods(["POST"])
def translate_blocks(request):
    """Translate a list of OCR blocks to English (and optionally back-translate).

    Request body (JSON):
    {
        "blocks": [
            {"id": "blk_001", "bbox": [15, 20, 380, 72], "text": "..."},
            {"id": "blk_002", "bbox": null, "text": "..."}
        ],
        "back_lang": "Gujarati"   // optional
    }

    Response: JSON array of TranslationBlock objects.
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError) as exc:
        return JsonResponse({"error": f"Invalid JSON body: {exc}"}, status=400)

    blocks = body.get("blocks")
    if not isinstance(blocks, list) or len(blocks) == 0:
        return JsonResponse(
            {"error": "'blocks' must be a non-empty JSON array."}, status=400
        )

    # Normalize blocks — ensure each has at least id + text.
    normalized = []
    for idx, block in enumerate(blocks):
        if not isinstance(block, dict):
            return JsonResponse(
                {"error": f"Block at index {idx} is not a JSON object."}, status=400
            )
        text = str(block.get("text", "")).strip()
        if not text:
            continue
        normalized.append(
            {
                "id": str(block.get("id", f"block_{idx + 1}")),
                "bbox": block.get("bbox"),
                "text": text,
            }
        )

    if not normalized:
        return JsonResponse(
            {"error": "No blocks contained non-empty text."}, status=400
        )

    back_lang = body.get("back_lang") or None
    if back_lang and back_lang not in SUPPORTED_BACK_LANGS:
        return JsonResponse(
            {
                "error": f"Unsupported back_lang '{back_lang}'. "
                f"Supported: {SUPPORTED_BACK_LANGS}"
            },
            status=400,
        )

    results = run_ocr_translation(normalized, back_lang=back_lang)
    return JsonResponse(results, safe=False, json_dumps_params={"ensure_ascii": False})


@require_http_methods(["GET"])
def list_languages(request):
    """Return the list of supported back-translation languages."""
    return JsonResponse({"supported_back_langs": SUPPORTED_BACK_LANGS})


@require_http_methods(["GET"])
def health_check(request):
    """Simple health-check endpoint."""
    return JsonResponse({"status": "ok", "module": "translation"})
