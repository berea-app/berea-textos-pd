"""Parser for the biblicalhumanities/Nestle1904 TSV release.

The upstream file is named ``Nestle1904.csv`` but is actually tab-separated
UTF-8 with a BOM. Each row is one Greek word with the columns: ``BCV``,
``text``, ``func_morph``, ``form_morph``, ``strongs``, ``lemma``,
``normalized``. The ``BCV`` column carries the reference in the form
``Matt 1:1`` using a fixed set of English short book names.

We concatenate consecutive rows that share the same BCV with single spaces
and emit one ParsedVerse per verse. The morphology and Strong's columns
are dropped (they belong in v1.5+ tables, not in the .bb).

Reference: https://github.com/biblicalhumanities/Nestle1904
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from ..normalize import ParsedVerse
from .base import BibleParser

# Nestle 1904 short book names → USFM 3.0 lowercase.
NESTLE_TO_BOOK_ID: dict[str, str] = {
    "Matt": "mat", "Mark": "mrk", "Luke": "luk", "John": "jhn", "Acts": "act",
    "Rom": "rom", "1Cor": "1co", "2Cor": "2co", "Gal": "gal", "Eph": "eph",
    "Phil": "php", "Col": "col", "1Thess": "1th", "2Thess": "2th",
    "1Tim": "1ti", "2Tim": "2ti", "Titus": "tit", "Phlm": "phm",
    "Heb": "heb", "Jas": "jas", "1Pet": "1pe", "2Pet": "2pe",
    "1John": "1jn", "2John": "2jn", "3John": "3jn", "Jude": "jud", "Rev": "rev",
}


def _parse_bcv(bcv: str) -> tuple[str, int, int] | None:
    """Parse ``"Matt 1:1"`` → ``("mat", 1, 1)``."""
    try:
        book_part, verse_part = bcv.rsplit(" ", 1)
        chapter_str, verse_str = verse_part.split(":", 1)
        book_id = NESTLE_TO_BOOK_ID.get(book_part.strip())
        if not book_id:
            return None
        return book_id, int(chapter_str), int(verse_str)
    except (ValueError, KeyError):
        return None


def _iter_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        header = f.readline()
        # Sanity check: first column must be 'BCV'.
        if not header.startswith("BCV"):
            raise ValueError(f"unexpected Nestle1904 header: {header!r}")
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            if not line:
                continue
            yield line.split("\t")


def _parse_file(path: Path, allowed_book_ids: set[str]) -> Iterable[ParsedVerse]:
    cur_key: tuple[str, int, int] | None = None
    cur_words: list[str] = []

    def flush() -> ParsedVerse | None:
        if cur_key is None or not cur_words:
            return None
        text = " ".join(w for w in cur_words if w).strip()
        if not text:
            return None
        book_id, chapter, verse = cur_key
        return ParsedVerse(book_id=book_id, chapter=chapter, verse=verse, text=text)

    for row in _iter_rows(path):
        if len(row) < 2:
            continue
        bcv = row[0].strip()
        word = row[1].strip()
        parsed = _parse_bcv(bcv)
        if parsed is None:
            continue
        if parsed[0] not in allowed_book_ids:
            continue
        if parsed != cur_key:
            v = flush()
            if v is not None:
                yield v
            cur_key = parsed
            cur_words = [word]
        else:
            cur_words.append(word)

    v = flush()
    if v is not None:
        yield v


class _Nestle1904TsvParser(BibleParser):
    """Parser for biblicalhumanities Nestle 1904 morphology TSV."""

    name = "nestle1904_tsv"

    def __init__(self, allowed_book_ids: set[str] | None = None) -> None:
        if allowed_book_ids is None:
            allowed_book_ids = set(NESTLE_TO_BOOK_ID.values())
        self.allowed_book_ids = allowed_book_ids

    def parse(self, source_path: Path) -> Iterable[ParsedVerse]:
        yield from _parse_file(source_path, self.allowed_book_ids)


PARSER = _Nestle1904TsvParser
