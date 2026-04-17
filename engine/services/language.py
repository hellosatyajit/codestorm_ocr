"""Thin wrapper around `langdetect` that never raises."""
from __future__ import annotations

import re

from langdetect import DetectorFactory, LangDetectException, detect

# Make langdetect reproducible - without this the library is non-deterministic
# on short inputs which trips up tests and demos.
DetectorFactory.seed = 0

_SCRIPT_SHORTCIRCUIT: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"[\u0600-\u06FF]"), "ar"),
    (re.compile(r"[\u0900-\u097F]"), "hi"),
    (re.compile(r"[\u3040-\u309F\u30A0-\u30FF]"), "ja"),
    (re.compile(r"[\uAC00-\uD7AF]"), "ko"),
    (re.compile(r"[\u4E00-\u9FFF]"), "zh"),
    (re.compile(r"[\u0400-\u04FF]"), "ru"),
]


def detect_language(text: str) -> str:
    """Return an ISO 639-1ish language code or ``"unknown"``.

    langdetect struggles on very short strings and mixed-script text, so we
    first run a cheap Unicode-range shortcircuit that handles the SOP's
    target scripts (Arabic, Devanagari, CJK, Cyrillic). If none match we
    fall through to langdetect for Latin-script languages.
    """
    clean = (text or "").strip()
    if len(clean) < 2:
        return "unknown"
    for pattern, code in _SCRIPT_SHORTCIRCUIT:
        if pattern.search(clean):
            return code
    try:
        return detect(clean)
    except LangDetectException:
        return "unknown"
