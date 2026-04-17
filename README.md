# Multilingual OCR Translation Module

This project translates OCR-extracted text blocks to English and optionally back-translates into a target language (Hindi, Gujarati, Chinese, Devanagari-family languages, and more).

It is designed for 3-team-member flow:
- Extractor teammate -> sends OCR JSON blocks
- Translation teammate (this module) -> enriches/translate blocks
- PDF builder teammate -> uses translated JSON to render output PDF

## Project Structure

**Translation module (your work):**
- `translation/config.py` - API endpoint/model/env config + supported target languages
- `translation/models.py` - shared typed output schema (`TranslationBlock`)
- `translation/translator.py` - source text -> English translation
- `translation/back_translator.py` - English -> selected target language
- `translation/pipeline.py` - orchestrates full per-block flow with error fallback
- `translation/exporter.py` - writes UTF-8 JSON safely
- `test/run_pipeline.py` - CLI runner that reads extractor JSON and outputs translated JSON
- `test/extractor_input_example.json` - sample input contract for extractor teammate

**Django integration (engine app):**
- `engine/services/ocr_pipeline.py` - service bridge calling `translation.pipeline`
- `engine/views.py` - Django REST views (`POST /api/translate/`, `GET /api/languages/`, `GET /api/health/`)
- `engine/urls.py` - URL routing for engine app
- `codestorm_ocr/urls.py` - root URL config including `api/` prefix

## Setup (Step by Step)

1. Install dependencies:
   ```bash
   py -m pip install requests python-dotenv
   ```
2. Create `.env` in project root with:
   ```env
   HF_CHAT_URL=https://router.huggingface.co/v1/chat/completions
   HF_MODEL=Qwen/Qwen3-8B
   HF_API_TOKEN=hf_xxxxxxxxxxxxxxxxx
   ```
3. Prepare extractor JSON input (same format as `test/extractor_input_example.json`)
4. **Option A — CLI only:**
   ```powershell
   py test\run_pipeline.py --input test\extractor_input_example.json --output test_results.json --back-lang Hindi
   ```
5. **Option B — Django REST API (full integration):**
   ```powershell
   py manage.py runserver
   # Then POST to http://127.0.0.1:8000/api/translate/
   ```
6. Share output JSON (or API response) with PDF builder teammate

## Supported Back Languages

Configured in `translation/config.py` (`SUPPORTED_BACK_LANGS`) including:
- Hindi, Marathi, Nepali, Bengali, Tamil, Telugu, Kannada, Malayalam, Punjabi, Urdu
- Gujarati, Arabic, Chinese, Japanese, Korean
- French, Spanish, German, Italian, Portuguese, Russian, Turkish, Vietnamese

## Notes

- `bbox` values are **pixel coordinates** `[x1, y1, x2, y2]` (top-left/bottom-right), not normalized.
- If translation fails, the block is still returned with `error` field set.
- `translation/__pycache__/` is auto-generated Python bytecode cache; safe to ignore.
- PDF builder must use a Unicode-compliant font (e.g. Noto Sans) for non-Latin scripts.
- Do **not** commit your real `HF_API_TOKEN` to Git; `.env` is already in `.gitignore`.
- `ensure_ascii=False` is set in `exporter.py` — Unicode characters are written correctly.
