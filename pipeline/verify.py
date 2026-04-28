"""Validation of a packed .bb against the canon.

Checks:
- Every book in the .bb has a known canonical book_id.
- No empty verses.
- UTF-8 round-trips without replacement chars.
- Per-book chapter count is at least the canon's expected count when the
  source claims to be a complete edition (configurable, since an "originals"
  manuscript like Westcott-Hort only ships the NT).
"""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from pathlib import Path

from .canon import load_full_canon


@dataclass
class VerifyReport:
    bible_id: str
    book_count: int
    verse_count: int
    warnings: list[str]
    ok: bool


def verify(bb_path: Path, *, expected_canon_complete: bool = True) -> VerifyReport:
    canon = load_full_canon()
    with gzip.open(bb_path, "rb") as f:
        payload = json.loads(f.read().decode("utf-8"))

    bible_id = payload["bible_id"]
    warnings: list[str] = []
    verse_count = 0

    for book in payload["books"]:
        book_id = book["book_id"]
        if book_id not in canon:
            warnings.append(f"unknown book_id {book_id!r}")
            continue

        canon_book = canon[book_id]
        chapters_seen = {ch["chapter"] for ch in book["chapters"]}

        if expected_canon_complete and canon_book.chapters:
            missing = set(range(1, canon_book.chapters + 1)) - chapters_seen
            if missing:
                warnings.append(
                    f"{book_id}: missing chapters {sorted(missing)} "
                    f"(expected {canon_book.chapters})"
                )

        for chapter in book["chapters"]:
            for verse in chapter["verses"]:
                text = verse.get("text", "")
                verse_count += 1
                if not text.strip():
                    warnings.append(
                        f"{book_id} {chapter['chapter']}:{verse['verse']} is empty"
                    )
                if "�" in text:
                    warnings.append(
                        f"{book_id} {chapter['chapter']}:{verse['verse']} "
                        f"contains UTF-8 replacement char"
                    )

    return VerifyReport(
        bible_id=bible_id,
        book_count=len(payload["books"]),
        verse_count=verse_count,
        warnings=warnings,
        ok=not warnings,
    )
