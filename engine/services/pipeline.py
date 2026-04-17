"""Orchestrator: OCR -> language detect -> translate -> rebuild.

Wires every service together and persists the results into the Django
models. Runs synchronously in the request cycle - fine for the mock, and
easy to later move behind Celery/Django-Q without changing the logic.
"""
from __future__ import annotations

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.db import transaction

from ..models import Block, Document, Page
from .fonts import ensure_fonts_available
from .language import detect_language
from .ocr_pipeline import BlockResult, MockOCRService, OCRService
from .preview import render_previews
from .rebuild import RebuildBlock, rebuild_pdf
from .translate import (
    MockTranslationService,
    OllamaTranslationService,
    TranslationService,
)

logger = logging.getLogger(__name__)


def process_document(
    document_id: uuid.UUID | str,
    *,
    ocr: OCRService | None = None,
    translator: TranslationService | None = None,
) -> Document:
    """Run the full pipeline for a single `Document`.

    Services default to the mocks; pass real implementations to swap in.
    Persists results to the DB and updates `document.status` along the way.
    """
    doc = Document.objects.get(pk=document_id)
    ocr = ocr or MockOCRService()
    if translator is None:
        translator = OllamaTranslationService()
        translator.ping()

    doc.status = Document.Status.PROCESSING
    doc.error_message = f"Using {translator.__class__.__name__}"
    doc.save(update_fields=["status", "error_message", "updated_at"])

    try:
        source_path = Path(doc.original_file.path)
        _enforce_page_cap(source_path)

        previews = _render_previews_for_doc(doc, source_path)
        ocr_pages = ocr.extract(source_path)
        _enforce_page_cap_from_ocr(ocr_pages)

        with transaction.atomic():
            # Clean slate in case of a retry.
            doc.pages.all().delete()
            _persist_pages_and_blocks(
                doc, ocr_pages, previews, translator=translator
            )

        _rebuild_and_attach(doc, source_path, ocr_pages)

        doc.status = Document.Status.DONE
        doc.error_message = ""
        doc.save(update_fields=["status", "error_message", "updated_at"])
    except Exception as exc:
        logger.exception("Pipeline failed for document %s", doc.pk)
        doc.status = Document.Status.FAILED
        doc.error_message = str(exc)[:2000]
        doc.save(update_fields=["status", "error_message", "updated_at"])
        raise

    return doc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _enforce_page_cap(source_path: Path) -> None:
    cap = int(getattr(settings, "MAX_PAGES_PER_UPLOAD", 10))
    suffix = source_path.suffix.lower()
    if suffix not in {".pdf"}:
        return  # Images are always 1 page, no check needed.
    import fitz

    with fitz.open(source_path) as doc:
        if doc.page_count > cap:
            raise ValueError(
                f"PDF has {doc.page_count} pages, max allowed is {cap}."
            )


def _enforce_page_cap_from_ocr(pages: list) -> None:
    cap = int(getattr(settings, "MAX_PAGES_PER_UPLOAD", 10))
    if len(pages) > cap:
        raise ValueError(f"OCR produced {len(pages)} pages, max allowed is {cap}.")


def _render_previews_for_doc(doc: Document, source_path: Path) -> dict[int, Path]:
    out_dir = Path(settings.MEDIA_ROOT) / "previews" / str(doc.id)
    png_paths = render_previews(source_path, out_dir)
    return {i: p for i, p in enumerate(png_paths)}


def _persist_pages_and_blocks(
    doc: Document,
    ocr_pages,
    previews: dict[int, Path],
    *,
    translator: TranslationService,
) -> None:
    for page_result in ocr_pages:
        page = Page.objects.create(
            document=doc,
            index=page_result.index,
            width_pt=page_result.width_pt,
            height_pt=page_result.height_pt,
        )
        preview_path = previews.get(page_result.index)
        if preview_path and preview_path.exists():
            with preview_path.open("rb") as fh:
                page.preview.save(
                    f"page_{page_result.index:03d}.png",
                    File(fh),
                    save=True,
                )
        _persist_blocks(
            page, page_result.blocks, target_lang=doc.target_lang, translator=translator
        )


def _persist_blocks(
    page: Page,
    blocks: list[BlockResult],
    *,
    target_lang: str,
    translator: TranslationService,
) -> None:
    if not blocks:
        return

    workers = max(1, int(getattr(settings, "TRANSLATION_CONCURRENCY", 4)))
    detected_langs = [detect_language(b.text) for b in blocks]

    def _translate_one(i: int) -> str:
        return translator.translate(
            blocks[i].text,
            src_lang=detected_langs[i],
            tgt_lang=target_lang,
        )

    with ThreadPoolExecutor(max_workers=workers) as ex:
        translations = list(ex.map(_translate_one, range(len(blocks))))

    rows = [
        Block(
            page=page,
            order=i,
            block_type=b.block_type or Block.Type.PARAGRAPH,
            x0=b.x0,
            y0=b.y0,
            x1=b.x1,
            y1=b.y1,
            original_text=b.text,
            translated_text=translations[i],
            detected_lang=detected_langs[i],
            confidence=b.confidence,
            font_size_pt=b.font_size_pt,
        )
        for i, b in enumerate(blocks)
    ]
    Block.objects.bulk_create(rows)


def _rebuild_and_attach(doc: Document, source_path: Path, ocr_pages) -> None:
    missing = ensure_fonts_available()
    if missing:
        raise RuntimeError(
            "Cannot rebuild PDF - missing fonts: "
            + ", ".join(str(p) for p in missing)
            + ". Run `python scripts/download_fonts.py`."
        )

    blocks_by_page: dict[int, list[RebuildBlock]] = {}
    page_sizes: dict[int, tuple[float, float]] = {}
    for page in doc.pages.all():
        page_sizes[page.index] = (page.width_pt, page.height_pt)
        blocks_by_page[page.index] = [
            RebuildBlock(
                x0=b.x0,
                y0=b.y0,
                x1=b.x1,
                y1=b.y1,
                translated_text=b.translated_text,
                font_size_pt=b.font_size_pt,
                block_type=b.block_type,
            )
            for b in page.blocks.all()
        ]

    out_dir = Path(settings.MEDIA_ROOT) / "translated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{doc.id}.pdf"
    rebuild_pdf(source_path, blocks_by_page, page_sizes, out_path)

    with out_path.open("rb") as fh:
        doc.translated_file.save(f"{doc.id}.pdf", File(fh), save=True)
