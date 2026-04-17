"""Real PyMuPDF-based PDF rebuild.

Given the original file and a list of translated blocks per page, produce
a new PDF that:

1. Preserves the original page visuals (images, figures, backgrounds) by
   copying the source page with ``show_pdf_page``.
2. Whites out every translated-block region so the original text doesn't
   bleed through underneath.
3. Writes the translated text into the same bounding box, picking a
   script-matched Noto font and applying RTL shaping for Arabic.
4. Uses a tiered fit algorithm (line-height shrink, then font-size
   shrink, then truncation) so long translations still land inside the
   box without disappearing.

For image uploads we synthesize a blank page matching the OCR page size
since there's no source PDF to copy from.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

from .fonts import FontChoice, ensure_fonts_available, pick_font, shape_for_display

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

# Font-size shrink percentages; tried in order after line-height shrinks fail.
_FONT_SHRINK_STEPS = (95, 90, 85, 80, 75, 70, 65, 60, 55, 50)
# Line-height values to try before shrinking the font.
_LINE_HEIGHT_STEPS = (1.2, 1.1, 1.0)
# Padding added to the white-out rect so antialiased descenders don't peek.
_WHITEOUT_PAD_RATIO = 0.15


@dataclass
class RebuildBlock:
    """Subset of the DB Block row that the rebuild step needs."""

    x0: float
    y0: float
    x1: float
    y1: float
    translated_text: str
    font_size_pt: float
    block_type: str = "paragraph"


def rebuild_pdf(
    source_path: Path,
    blocks_by_page: dict[int, list[RebuildBlock]],
    page_sizes: dict[int, tuple[float, float]],
    out_path: Path,
) -> Path:
    """Render the translated PDF to ``out_path`` and return the path.

    ``blocks_by_page`` maps page index -> list of blocks to paint.
    ``page_sizes`` maps page index -> (width_pt, height_pt); required for
    image uploads where we synthesize a page. For PDF inputs the original
    page rect wins.
    """
    source_path = Path(source_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    missing = ensure_fonts_available()
    if missing:
        raise RuntimeError(
            "Missing Noto font files: "
            + ", ".join(str(p) for p in missing)
            + ". Run `python scripts/download_fonts.py` first."
        )

    suffix = source_path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return _rebuild_from_image(source_path, blocks_by_page, page_sizes, out_path)
    return _rebuild_from_pdf(source_path, blocks_by_page, out_path)


def _rebuild_from_pdf(
    source_path: Path,
    blocks_by_page: dict[int, list[RebuildBlock]],
    out_path: Path,
) -> Path:
    src = fitz.open(source_path)
    out = fitz.open()
    try:
        for pno, src_page in enumerate(src):
            new_page = out.new_page(
                width=src_page.rect.width, height=src_page.rect.height
            )
            # Copy original page content (images, vectors, backgrounds).
            new_page.show_pdf_page(new_page.rect, src, pno)
            _paint_blocks(new_page, blocks_by_page.get(pno, []))
        out.save(str(out_path), deflate=True, garbage=3)
    finally:
        out.close()
        src.close()
    return out_path


def _rebuild_from_image(
    source_path: Path,
    blocks_by_page: dict[int, list[RebuildBlock]],
    page_sizes: dict[int, tuple[float, float]],
    out_path: Path,
) -> Path:
    out = fitz.open()
    try:
        # Single page sized either from the OCR result or a sensible default.
        width, height = page_sizes.get(0, (612.0, 792.0))
        new_page = out.new_page(width=width, height=height)
        # Place the original image as a background so the user still sees it.
        try:
            new_page.insert_image(new_page.rect, filename=str(source_path))
        except Exception:
            # If PyMuPDF can't read this image, leave the page blank - the
            # translated blocks will still be drawn below.
            pass
        _paint_blocks(new_page, blocks_by_page.get(0, []))
        out.save(str(out_path), deflate=True, garbage=3)
    finally:
        out.close()
    return out_path


def _paint_blocks(page: "fitz.Page", blocks: list[RebuildBlock]) -> None:
    for block in blocks:
        text = (block.translated_text or "").strip()
        if not text:
            continue
        rect = fitz.Rect(block.x0, block.y0, block.x1, block.y1)
        if rect.is_empty or rect.width <= 1 or rect.height <= 1:
            continue
        pad = rect.height * _WHITEOUT_PAD_RATIO
        whiteout = fitz.Rect(
            rect.x0 - pad, rect.y0 - pad, rect.x1 + pad, rect.y1 + pad
        )
        page.draw_rect(whiteout, color=None, fill=(1, 1, 1), overlay=True)
        _insert_text_fit(page, rect, text, block.font_size_pt)


def _insert_text_fit(
    page: "fitz.Page", rect: "fitz.Rect", text: str, base_size: float
) -> str:
    """Tiered fit: line-height shrink, then font shrink, then truncation.

    Returns a tag string describing which tier succeeded - useful for
    debugging, ignored in production.
    """
    font = pick_font(text)
    display_text = shape_for_display(text, font)
    align = fitz.TEXT_ALIGN_RIGHT if font.is_rtl else fitz.TEXT_ALIGN_LEFT

    base_size = max(float(base_size or 11.0), 6.0)

    # Tier 1: keep original font size, shrink line-height.
    for lh in _LINE_HEIGHT_STEPS:
        rv = page.insert_textbox(
            rect,
            display_text,
            fontname=font.logical_name,
            fontfile=str(font.font_path),
            fontsize=base_size,
            lineheight=lh,
            color=(0, 0, 0),
            align=align,
        )
        if rv >= 0:
            return "fit-original"

    # Tier 2: shrink the font size while keeping line-height tight.
    for pct in _FONT_SHRINK_STEPS:
        fs = max(6.0, base_size * pct / 100.0)
        rv = page.insert_textbox(
            rect,
            display_text,
            fontname=font.logical_name,
            fontfile=str(font.font_path),
            fontsize=fs,
            lineheight=1.0,
            color=(0, 0, 0),
            align=align,
        )
        if rv >= 0:
            return f"fit-shrunk-{pct}"

    # Tier 3: truncate with an ellipsis and write whatever fits.
    truncated = _truncate(text, max_chars=max(40, int(rect.width / 2)))
    truncated_display = shape_for_display(truncated, font)
    page.insert_textbox(
        rect,
        truncated_display,
        fontname=font.logical_name,
        fontfile=str(font.font_path),
        fontsize=max(6.0, base_size * 0.5),
        lineheight=1.0,
        color=(0, 0, 0),
        align=align,
    )
    return "fit-truncated"


def _truncate(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "\u2026"


__all__ = ["RebuildBlock", "rebuild_pdf", "FontChoice"]
