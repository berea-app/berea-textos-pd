"""Sanity checks for the catalogue."""

from __future__ import annotations

from pipeline.catalog import CATALOG


def test_catalog_contains_rv1909_and_originals():
    assert "rv1909" in CATALOG
    assert "tr" in CATALOG
    assert "brenton" in CATALOG
    assert "wlc" in CATALOG


def test_each_entry_declares_legal_status():
    for bible_id, entry in CATALOG.items():
        assert entry.license in {
            "public_domain",
            "cc_by_4_0",
            "cc_by_sa_4_0",
            "other",
        }, f"{bible_id} has unknown license {entry.license!r}"
        assert entry.license_basis, f"{bible_id} missing license_basis"


def test_attribution_required_implies_attribution_text_present():
    for bible_id, entry in CATALOG.items():
        if entry.attribution_required:
            assert entry.attribution_text, (
                f"{bible_id} declares attribution_required but no attribution_text"
            )


def test_book_ids_default_when_empty():
    rv = CATALOG["rv1909"]
    assert rv.book_ids == ()
    assert len(rv.effective_book_ids()) == 66


def test_tr_is_nt_only():
    tr = CATALOG["tr"]
    assert len(tr.book_ids) == 27
    assert "gen" not in tr.book_ids
    assert "rev" in tr.book_ids


def test_wlc_is_ot_only():
    wlc = CATALOG["wlc"]
    assert len(wlc.book_ids) == 39
    assert "gen" in wlc.book_ids
    assert "mat" not in wlc.book_ids
