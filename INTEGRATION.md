# Extractor + PDF Builder Integration

Use this document for teammate handoff.

## Extractor Teammate: What to Send

Send a JSON array of OCR text blocks.

```json
[
  {
    "id": "blk_001",
    "bbox": [15, 20, 380, 72],
    "text": "Original OCR text here"
  },
  {
    "id": "blk_002",
    "bbox": null,
    "text": "Second OCR line/paragraph"
  }
]
```

### Required fields
- `id` (string)
- `text` (string)

### Optional fields
- `bbox` (array or null): `[x1, y1, x2, y2]`

`bbox` is forwarded to output for document reconstruction. If extractor has no layout data, set `bbox: null`.

## Translation Runner: How to Execute

### Option A — CLI (standalone, no Django needed)

From project root:

```powershell
py test\run_pipeline.py --input <extractor_json_path> --output <translated_json_path> --back-lang <target_language>
```

Example:

```powershell
py test\run_pipeline.py --input test\extractor_input_example.json --output test_results.json --back-lang Gujarati
```

### Option B — Django REST API (integrated, recommended for full-stack use)

Start the Django server:

```powershell
py manage.py runserver
```

Then `POST` to `http://127.0.0.1:8000/api/translate/`:

```json
{
  "blocks": [
    {"id": "blk_001", "bbox": [15, 20, 380, 72], "text": "Original OCR text here"},
    {"id": "blk_002", "bbox": null, "text": "Second OCR line"}
  ],
  "back_lang": "Gujarati"
}
```

Other endpoints:
- `GET /api/languages/` — list supported back-translation languages
- `GET /api/health/`    — health check

## PDF Builder Teammate: How to Consume Output

Translation output JSON contains one object per input block:
- `id`
- `bbox`
- `original_text`
- `detected_language`
- `language_code`
- `script`
- `confidence`
- `translation_en`
- `back_translation`
- `back_translation_lang`
- `error`

### Rendering rule
1. Use `back_translation` as preferred text for PDF output.
2. If `back_translation` is null/empty, fallback to `translation_en`.
3. Use `bbox` (if present) to place text at original coordinates.
4. Log blocks where `error` is not null.

> **⚠️ CRITICAL: Font Selection**
> Because output may contain non-Latin scripts (Arabic, Hindi, Gujarati, CJK etc.), the PDF Builder
> **must** use a Unicode-compliant font (e.g., *Noto Sans* or *Arial Unicode MS*).
> Standard PDF fonts (Helvetica, Times) will render these characters as "tofu" boxes (▯▯▯).

> **⚠️ CRITICAL: `bbox` Coordinate System**
> `bbox` values are **pixel coordinates** in `[x1, y1, x2, y2]` format (top-left to bottom-right).
> These are **not** normalized (0–1). PDF builder must map pixel coords to PDF point coords using
> the original image/page dimensions.

## .env / API Config for Translation Teammate

Create `.env` at project root:

```env
HF_CHAT_URL=https://router.huggingface.co/v1/chat/completions
HF_MODEL=Qwen/Qwen3-8B
HF_API_TOKEN=hf_xxxxxxxxxxxxxxxxx
```

Do not commit real tokens to GitHub.
