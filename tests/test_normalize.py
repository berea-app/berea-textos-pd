"""normalize_books groups verses by book and orders canonically."""

from __future__ import annotations

import pytest

from pipeline.normalize import ParsedVerse, normalize_books


def test_normalize_orders_books_by_canon_position():
    verses = [
        ParsedVerse("rev", 1, 1, "Apocalipsis."),
        ParsedVerse("gen", 1, 1, "En el principio."),
    ]
    books = normalize_books(verses)
    assert [b.book_id for b in books] == ["gen", "rev"]


def test_normalize_rejects_unknown_book_id():
    with pytest.raises(ValueError, match="unknown book_id"):
        normalize_books([ParsedVerse("xxx", 1, 1, "Texto")])


def test_normalize_rejects_duplicate_verse():
    with pytest.raises(ValueError, match="duplicate verse"):
        normalize_books(
            [
                ParsedVerse("gen", 1, 1, "Uno"),
                ParsedVerse("gen", 1, 1, "Dos"),
            ]
        )
