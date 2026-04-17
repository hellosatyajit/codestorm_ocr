"""Configuration for translation services."""

import os
from pathlib import Path


def _load_dotenv() -> None:
    """Load simple KEY=VALUE pairs from project .env file."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()

# Hugging Face chat-completions endpoint (OpenAI-compatible).
HF_CHAT_URL = os.getenv(
    "HF_CHAT_URL",
    "https://router.huggingface.co/v1/chat/completions",
)

# Model id passed to HF chat-completions API.
# Default is Qwen 3 family.
MODEL = os.getenv("HF_MODEL", "Qwen/Qwen3-8B")

# Hugging Face token. You can keep this in env var or hardcode temporarily.
# Recommended env var:
#   HF_API_TOKEN=hf_xxxxxxxxx
API_KEY = os.getenv("HF_API_TOKEN") or os.getenv("TRANSLATION_API_KEY")
REQUEST_HEADERS = (
    {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    if API_KEY
    else {"Content-Type": "application/json"}
)

# Supported back-translation language choices for UI/API consumers.
SUPPORTED_BACK_LANGS = [
    "Hindi",
    "Marathi",
    "Nepali",
    "Bengali",
    "Tamil",
    "Telugu",
    "Kannada",
    "Malayalam",
    "Punjabi",
    "Urdu",
    "French",
    "Spanish",
    "German",
    "Italian",
    "Russian",
    "Arabic",
    "Chinese",
    "Japanese",
    "Gujarati",
    "Portuguese",
    "Korean",
    "Turkish",
    "Vietnamese",
]

# Helpful script mapping for UI and teammates.
LANGUAGE_SCRIPT_HINTS = {
    "Hindi": "Devanagari",
    "Marathi": "Devanagari",
    "Nepali": "Devanagari",
    "Bengali": "Bengali",
    "Tamil": "Tamil",
    "Telugu": "Telugu",
    "Kannada": "Kannada",
    "Malayalam": "Malayalam",
    "Punjabi": "Gurmukhi",
    "Urdu": "Arabic",
    "French": "Latin",
    "Spanish": "Latin",
    "German": "Latin",
    "Italian": "Latin",
    "Russian": "Cyrillic",
    "Arabic": "Arabic",
    "Chinese": "CJK",
    "Japanese": "CJK",
    "Gujarati": "Gujarati",
    "Portuguese": "Latin",
    "Korean": "Hangul",
    "Turkish": "Latin",
    "Vietnamese": "Latin",
}

# ---------------------------------------------------------------------------
# Hugging Face mode note:
# If you do not have a local model, keep using remote API calls with your
# HF token. translator.py / back_translator.py are configured for
# chat-completions payloads.
# ---------------------------------------------------------------------------
