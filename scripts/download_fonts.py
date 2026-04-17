"""Download the Noto TTFs used by the PDF rebuild step.

Run once from the project root:

    python scripts/download_fonts.py

Covers the scripts we care about for the hackathon SOP:
Latin + Cyrillic, Arabic (RTL), Devanagari, and CJK.
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = PROJECT_ROOT / "fonts"

FONTS: list[tuple[str, str]] = [
    (
        "NotoSans-Regular.ttf",
        "https://github.com/google/fonts/raw/main/ofl/notosans/NotoSans%5Bwdth%2Cwght%5D.ttf",
    ),
    (
        "NotoSansArabic-Regular.ttf",
        "https://github.com/google/fonts/raw/main/ofl/notosansarabic/NotoSansArabic%5Bwdth%2Cwght%5D.ttf",
    ),
    (
        "NotoSansDevanagari-Regular.ttf",
        "https://github.com/google/fonts/raw/main/ofl/notosansdevanagari/NotoSansDevanagari%5Bwdth%2Cwght%5D.ttf",
    ),
    (
        "NotoSansSC-Regular.ttf",
        "https://github.com/google/fonts/raw/main/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf",
    ),
]


def download(name: str, url: str, dest_dir: Path) -> Path:
    dest = dest_dir / name
    if dest.exists() and dest.stat().st_size > 0:
        print(f"[skip] {name} already present ({dest.stat().st_size // 1024} KB)")
        return dest
    print(f"[fetch] {name} <- {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "codestorm-ocr/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as fh:
        while chunk := resp.read(1 << 16):
            fh.write(chunk)
    print(f"[ok]    {name} ({dest.stat().st_size // 1024} KB)")
    return dest


def main() -> int:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    failed: list[str] = []
    for name, url in FONTS:
        try:
            download(name, url, FONTS_DIR)
        except Exception as exc:
            print(f"[fail]  {name}: {exc}")
            failed.append(name)
    if failed:
        print("\nSome fonts failed to download:")
        for name in failed:
            print(f"  - {name}")
        print(
            "You can manually place these files in "
            f"{FONTS_DIR} from fonts.google.com/noto"
        )
        return 1
    print(f"\nAll fonts ready in {FONTS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
