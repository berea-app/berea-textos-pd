"""Normalization helpers for parsed verses.

Parsers emit a flat list of ParsedVerse; ``normalize_books`` groups them into
the canonical ``books -> chapters -> verses`` structure consumed by ``pack.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .canon import CanonBook, load_full_canon


@dataclass(frozen=True)
class ParsedVerse:
    book_id: str
    chapter: int
    verse: int
    text: str
    heading: str | None = None
    verse_alias: str | None = None


@dataclass(frozen=True)
class NormalizedBook:
    book_id: str
    display_name: str
    abbreviation: str
    position: int
    chapters: list["NormalizedChapter"]


@dataclass(frozen=True)
class NormalizedChapter:
    chapter: int
    verses: list[ParsedVerse]


def normalize_books(verses: Iterable[ParsedVerse]) -> list[NormalizedBook]:
    """Group ``verses`` by book and chapter in canonical order.

    Verifies every book_id is known and that no duplicate (book, chapter, verse)
    triplet appears. Books emit in the ``order`` field of canon_66/extendido,
    chapters and verses in numeric order.
    """
    canon = load_full_canon()
    by_book: dict[str, list[ParsedVerse]] = {}
    seen: set[tuple[str, int, int]] = set()

    for v in verses:
        if v.book_id not in canon:
            raise ValueError(f"unknown book_id: {v.book_id!r}")
        key = (v.book_id, v.chapter, v.verse)
        if key in seen:
            raise ValueError(f"duplicate verse: {v.book_id} {v.chapter}:{v.verse}")
        seen.add(key)
        by_book.setdefault(v.book_id, []).append(v)

    out: list[NormalizedBook] = []
    for book_id, vs in by_book.items():
        book: CanonBook = canon[book_id]
        vs.sort(key=lambda x: (x.chapter, x.verse))
        chapters: dict[int, list[ParsedVerse]] = {}
        for v in vs:
            chapters.setdefault(v.chapter, []).append(v)

        ordered_chapters = [
            NormalizedChapter(chapter=ch, verses=chapters[ch])
            for ch in sorted(chapters.keys())
        ]
        out.append(
            NormalizedBook(
                book_id=book_id,
                display_name=book.name_es,
                abbreviation=book.abbr_es,
                position=book.order or 0,
                chapters=ordered_chapters,
            )
        )

    out.sort(key=lambda b: b.position)
    return out
