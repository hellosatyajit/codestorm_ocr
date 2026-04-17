"""Views for the translation engine.

Intentionally keeps everything synchronous - the mock pipeline finishes
in well under a second, and that lets us avoid Celery for the hackathon.
Swap the `process_document` call for a task enqueue later.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET, require_http_methods

from .forms import UploadForm
from .models import Block, Document, Page
from .services.pipeline import process_document

logger = logging.getLogger(__name__)


def _engine_url(name: str, doc_id, *, path_suffix: str) -> str:
    """Resolve engine:<name>; fall back to literal path if URLconf is stale."""
    try:
        return reverse(f"engine:{name}", args=[doc_id])
    except NoReverseMatch:
        return f"/doc/{doc_id}/{path_suffix}"


_ORIGINAL_INLINE_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


@require_http_methods(["GET", "POST"])
def upload_view(request):
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = Document.objects.create(
                original_file=form.cleaned_data["file"],
                target_lang=form.cleaned_data["target_lang"],
            )
            try:
                process_document(doc.id)
            except Exception as exc:  # pragma: no cover - surfaced to the user
                logger.exception("Upload processing failed: %s", exc)
            return redirect(reverse("engine:results", args=[doc.id]))
    else:
        form = UploadForm()
    return render(request, "engine/upload.html", {"form": form})


@require_GET
def results_view(request, doc_id):
    doc = get_object_or_404(Document, pk=doc_id)
    pages = list(doc.pages.all().prefetch_related("blocks"))
    orig_name = (doc.original_file.name or "").lower()
    doc_is_pdf = orig_name.endswith(".pdf")
    return render(
        request,
        "engine/results.html",
        {
            "doc": doc,
            "pages": pages,
            "doc_is_pdf": doc_is_pdf,
            "blocks_json_url": reverse("engine:blocks_json", args=[doc.id]),
            "download_json_url": reverse("engine:download_json", args=[doc.id]),
            "download_pdf_url": reverse("engine:download_pdf", args=[doc.id]),
            "view_original_url": _engine_url(
                "view_original", doc.id, path_suffix="original"
            ),
            "view_translated_pdf_url": _engine_url(
                "view_translated_pdf", doc.id, path_suffix="translated.pdf"
            ),
        },
    )


def _serialize_doc(doc: Document) -> dict:
    pages_out: list[dict] = []
    for page in doc.pages.all().prefetch_related("blocks"):
        blocks_out: list[dict] = []
        for block in page.blocks.all():
            blocks_out.append(
                {
                    "block_id": block.pk,
                    "order": block.order,
                    "type": block.block_type,
                    "bounding_box": [block.x0, block.y0, block.x1, block.y1],
                    "original_text": block.original_text,
                    "translated_text": block.translated_text,
                    "detected_language": block.detected_lang,
                    "confidence": round(block.confidence, 4),
                    "font_size_pt": round(block.font_size_pt, 2),
                }
            )
        pages_out.append(
            {
                "page_index": page.index,
                "width_pt": page.width_pt,
                "height_pt": page.height_pt,
                "preview_url": page.preview.url if page.preview else None,
                "blocks": blocks_out,
            }
        )
    return {
        "document_id": str(doc.id),
        "status": doc.status,
        "source_language": doc.source_lang,
        "target_language": doc.target_lang,
        "created_at": doc.created_at.isoformat(),
        "pages": pages_out,
        "error_message": doc.error_message or None,
    }


@require_GET
def blocks_json(request, doc_id):
    """Canvas-facing JSON feed used by the side-by-side frontend."""
    doc = get_object_or_404(Document, pk=doc_id)
    return JsonResponse(_serialize_doc(doc))


@require_GET
def download_json(request, doc_id):
    """Structured export the user downloads for SOP scenario #4."""
    doc = get_object_or_404(Document, pk=doc_id)
    payload = json.dumps(_serialize_doc(doc), ensure_ascii=False, indent=2)
    response = HttpResponse(payload, content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="{doc.id}.json"'
    )
    return response


@require_GET
def download_pdf(request, doc_id):
    """Translated PDF download (SOP scenario #5)."""
    doc = get_object_or_404(Document, pk=doc_id)
    if not doc.translated_file:
        raise Http404("Translated PDF not ready yet.")
    path = Path(doc.translated_file.path)
    if not path.exists():
        raise Http404("Translated PDF missing on disk.")
    return FileResponse(
        path.open("rb"),
        as_attachment=True,
        filename=f"{doc.id}-translated.pdf",
        content_type="application/pdf",
    )


@require_GET
@xframe_options_sameorigin
def view_original(request, doc_id):
    """Serve the uploaded original (PDF or image) for inline viewing."""
    doc = get_object_or_404(Document, pk=doc_id)
    path = Path(doc.original_file.path)
    if not path.exists():
        raise Http404("Original file missing on disk.")
    suffix = path.suffix.lower()
    content_type = _ORIGINAL_INLINE_TYPES.get(suffix, "application/octet-stream")
    resp = FileResponse(
        path.open("rb"),
        as_attachment=False,
        filename=path.name,
        content_type=content_type,
    )
    resp["Content-Disposition"] = f'inline; filename="{path.name}"'
    return resp


@require_GET
@xframe_options_sameorigin
def view_translated_pdf(request, doc_id):
    """Serve translated PDF for inline viewing (e.g. results page iframe)."""
    doc = get_object_or_404(Document, pk=doc_id)
    if not doc.translated_file:
        raise Http404("Translated PDF not ready yet.")
    path = Path(doc.translated_file.path)
    if not path.exists():
        raise Http404("Translated PDF missing on disk.")
    resp = FileResponse(
        path.open("rb"),
        as_attachment=False,
        filename=f"{doc.id}-translated.pdf",
        content_type="application/pdf",
    )
    resp["Content-Disposition"] = (
        f'inline; filename="{doc.id}-translated.pdf"'
    )
    return resp
