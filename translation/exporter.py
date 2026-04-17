"""Export utilities for translation results."""

import json
from typing import Any


def export_json(results: list[Any], filepath: str) -> None:
    """Write translation results to UTF-8 JSON."""
    with open(filepath, "w", encoding="utf-8") as file_handle:
        json.dump(results, file_handle, ensure_ascii=False, indent=2)
