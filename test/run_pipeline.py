"""Run translation pipeline from CLI.

Team integration contract:
1) Extractor member outputs a JSON file (list of blocks):
   [
     {"id": "block_1", "bbox": [x1, y1, x2, y2], "text": "..."},
     {"id": "block_2", "bbox": null, "text": "..."}
   ]
2) This runner reads that file and creates translated output JSON.
3) PDF builder member consumes the translated output JSON.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from translation.config import SUPPORTED_BACK_LANGS
from translation.exporter import export_json
from translation.pipeline import process_document


def _load_extractor_blocks(input_path: Path) -> list[dict[str, Any]]:
    """Load and normalize extractor output into required block format."""
    with input_path.open("r", encoding="utf-8") as file_handle:
        data = json.load(file_handle)

    if not isinstance(data, list):
        raise ValueError("Extractor input must be a JSON list of block objects.")

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Block at index {index} is not a JSON object.")
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        normalized.append(
            {
                "id": str(item.get("id", f"block_{index + 1}")),
                "bbox": item.get("bbox"),
                "text": text,
            }
        )

    return normalized


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OCR translation pipeline.")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to extractor JSON file containing OCR blocks.",
    )
    parser.add_argument(
        "--output",
        default="test_results.json",
        help="Output JSON path for translator results.",
    )
    parser.add_argument(
        "--back-lang",
        default="Hindi",
        help=f"Target language for back translation. Supported: {', '.join(SUPPORTED_BACK_LANGS)}",
    )
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    blocks = _load_extractor_blocks(input_path)
    if not blocks:
        raise ValueError("No valid text blocks found in extractor input.")

    results = process_document(blocks, back_lang=args.back_lang)
    export_json(results, str(output_path))

    print(f"Processed {len(results)} blocks")
    print(f"Input file: {input_path}")
    print(f"Output file: {output_path}")
    print("Share output JSON with the PDF builder teammate.")


if __name__ == "__main__":
    main()
