"""Page preview rasterization.

Produces one PNG per page used as the canvas background in the side-by-side
results view. For image uploads we just copy/convert the image so the
frontend has a single-page "preview" to display.
"""
from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def _pixmap_to_png(pix: "fitz.Pixmap", out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # PyMuPDF sometimes produces CMYK / alpha pixmaps; flatten to RGB for PNG.
    if pix.alpha or pix.n > 3:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    pix.save(str(out_path))


def render_previews(source_path: Path, out_dir: Path, *, dpi: int = 150) -> list[Path]:
    """Render ``source_path`` into one PNG per page, saved under ``out_dir``.

    Returns a list of PNG paths in page order.
    """
    source_path = Path(source_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    suffix = source_path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        # For image uploads we open them via PyMuPDF too - it handles
        # PNG/JPEG natively and gives us one "page".
        doc = fitz.open(source_path)
    else:
        doc = fitz.open(source_path)

    try:
        outputs: list[Path] = []
        for idx, page in enumerate(doc):
            pix = page.get_pixmap(dpi=dpi)
            out_path = out_dir / f"page_{idx:03d}.png"
            _pixmap_to_png(pix, out_path)
            outputs.append(out_path)
        return outputs
    finally:
        doc.close()
