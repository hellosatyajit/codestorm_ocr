"""Smoke test: end-to-end pipeline using OllamaTranslationService.

Usage:
    cd codestorm_ocr
    python scripts/smoke_ollama.py [path/to/file.pdf] [target_lang]

Creates a fresh Document, runs process_document(), and prints timing plus a
sample of original/translated text. Exits non-zero on any failure.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import django

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "codestorm_ocr.settings")
django.setup()

from django.core.files import File  # noqa: E402

from engine.models import Document  # noqa: E402
from engine.services.pipeline import process_document  # noqa: E402
from engine.services.translate import OllamaTranslationService  # noqa: E402


def main() -> int:
    args = sys.argv[1:]
    src = Path(args[0]) if args else (
        BASE_DIR / "media" / "originals" / "CODESTORM_Hackathon_2K26_PS.pdf"
    )
    target_lang = args[1] if len(args) > 1 else "hi"

    if not src.exists():
        print(f"ERROR: source PDF not found: {src}", file=sys.stderr)
        return 2

    print(f"[smoke] source   : {src}")
    print(f"[smoke] target   : {target_lang}")

    svc = OllamaTranslationService()
    print(f"[smoke] backend  : {svc.__class__.__name__} (model={svc._model})")

    try:
        svc.ping()
        print("[smoke] ollama   : OK")
    except RuntimeError as exc:
        print(f"[smoke] ollama   : FAIL ({exc})", file=sys.stderr)
        return 3

    with src.open("rb") as fh:
        doc = Document.objects.create(target_lang=target_lang)
        doc.original_file.save(src.name, File(fh), save=True)

    print(f"[smoke] doc.id   : {doc.id}")

    t0 = time.perf_counter()
    try:
        process_document(doc.id, translator=svc)
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        doc.refresh_from_db()
        print(
            f"[smoke] FAILED in {elapsed:.1f}s status={doc.status} "
            f"msg={doc.error_message!r}",
            file=sys.stderr,
        )
        raise

    elapsed = time.perf_counter() - t0
    doc.refresh_from_db()

    print(f"[smoke] elapsed  : {elapsed:.1f}s")
    print(f"[smoke] status   : {doc.status}")
    print(f"[smoke] error    : {doc.error_message!r}")
    print(f"[smoke] pages    : {doc.pages.count()}")

    blocks = []
    for p in doc.pages.all().order_by("index"):
        blocks.extend(list(p.blocks.all().order_by("order")))
    print(f"[smoke] blocks   : {len(blocks)}")

    for b in blocks[:5]:
        print("---")
        print(f"  order={b.order} detected={b.detected_lang}")
        print(f"  orig : {b.original_text[:100]!r}")
        print(f"  tgt  : {b.translated_text[:100]!r}")

    if doc.translated_file:
        print(f"[smoke] out pdf  : {doc.translated_file.path}")

    ok = doc.status == Document.Status.DONE and doc.translated_file
    print("[smoke] result   :", "OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
