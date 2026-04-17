"""Script-aware font picking and RTL shaping helpers.

The PDF rebuild step needs to pick the right TTF file per block and,
for Arabic, reshape the string (join letter forms) and run the bidi
algorithm before handing it to PyMuPDF. Otherwise Arabic glyphs render
disconnected and left-to-right.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from django.conf import settings


@dataclass(frozen=True)
class FontChoice:
    logical_name: str  # what we pass to PyMuPDF's `fontname=`
    font_path: Path
    is_rtl: bool = False


_DEVANAGARI = re.compile(r"[\u0900-\u097F]")
_ARABIC = re.compile(r"[\u0600-\u06FF]")
_CJK = re.compile(r"[\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]")


def _fonts_dir() -> Path:
    return Path(getattr(settings, "FONTS_DIR", Path("fonts")))


# Cache the resolved FontChoice objects so we don't hit disk for every block.
_FONT_CACHE: dict[str, FontChoice] = {}


def _resolve(key: str, logical_name: str, filename: str, *, is_rtl: bool = False) -> FontChoice:
    cached = _FONT_CACHE.get(key)
    if cached is not None:
        return cached
    path = _fonts_dir() / filename
    choice = FontChoice(logical_name=logical_name, font_path=path, is_rtl=is_rtl)
    _FONT_CACHE[key] = choice
    return choice


def pick_font(text: str) -> FontChoice:
    """Return the best bundled Noto font for rendering ``text``."""
    if _ARABIC.search(text or ""):
        return _resolve("ar", "NotoArabic", "NotoSansArabic-Regular.ttf", is_rtl=True)
    if _DEVANAGARI.search(text or ""):
        return _resolve("dev", "NotoDevanagari", "NotoSansDevanagari-Regular.ttf")
    if _CJK.search(text or ""):
        return _resolve("cjk", "NotoCJK", "NotoSansSC-Regular.ttf")
    return _resolve("lat", "NotoSans", "NotoSans-Regular.ttf")


def shape_for_display(text: str, font: FontChoice) -> str:
    """Reshape Arabic letter forms and apply bidi reordering.

    No-op for LTR scripts. Returns text ready to hand to
    ``page.insert_textbox`` with ``align=fitz.TEXT_ALIGN_RIGHT``.
    """
    if not font.is_rtl:
        return text
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text


def ensure_fonts_available() -> list[Path]:
    """Return the list of missing Noto TTF files, empty if all present."""
    required = [
        "NotoSans-Regular.ttf",
        "NotoSansArabic-Regular.ttf",
        "NotoSansDevanagari-Regular.ttf",
        "NotoSansSC-Regular.ttf",
    ]
    base = _fonts_dir()
    return [base / name for name in required if not (base / name).exists()]
