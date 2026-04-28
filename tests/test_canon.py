"""Sanity checks for the canonical book identifiers."""

from __future__ import annotations

from pipeline.canon import load_canon_66, load_canon_extendido, load_full_canon


def test_canon_66_has_66_books():
    books = load_canon_66()
    assert len(books) == 66


def test_canon_66_book_ids_unique():
    ids = [b.book_id for b in load_canon_66()]
    assert len(ids) == len(set(ids))


def test_canon_66_orders_are_unique_and_consecutive():
    orders = sorted([b.order for b in load_canon_66()])
    assert orders == list(range(1, 67))


def test_canon_66_ot_nt_split_is_39_27():
    books = load_canon_66()
    ot = [b for b in books if b.testament == "OT"]
    nt = [b for b in books if b.testament == "NT"]
    assert len(ot) == 39
    assert len(nt) == 27


def test_full_canon_has_no_duplicate_book_ids_across_files():
    full = load_full_canon()
    extended = load_canon_extendido()
    for ext in extended:
        assert ext.book_id in full
        assert full[ext.book_id].parent_book_id == ext.parent_book_id


def test_known_books_have_expected_chapter_counts():
    counts = {b.book_id: b.chapters for b in load_canon_66()}
    assert counts["gen"] == 50
    assert counts["psa"] == 150
    assert counts["isa"] == 66
    assert counts["mat"] == 28
    assert counts["rev"] == 22
