"""Validate canon/numbering_alias.json against its schema and check
coherence (no duplicate aliases, split/merge sets disjoint from 1:1
chapter aliases, sanity probes against actual built Bibles)."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ALIAS_PATH = REPO_ROOT / "canon" / "numbering_alias.json"
ALIAS_SCHEMA_PATH = REPO_ROOT / "canon" / "numbering_alias.schema.json"
OUTPUT_DIR = REPO_ROOT / "output"


def _load_alias() -> dict:
    return json.loads(ALIAS_PATH.read_text("utf-8"))


def _load_bible(bible_id: str) -> dict | None:
    """Load a built ``.bb`` if present, else return None (so the test
    can skip rather than fail in dev environments where the build hasn't
    been run yet)."""
    bb_path = OUTPUT_DIR / f"{bible_id}.bb"
    if not bb_path.exists():
        return None
    with gzip.open(bb_path, "rt", encoding="utf-8") as f:
        return json.load(f)


def _psalm_first_verse(bb: dict, ch: int) -> str | None:
    book = next((b for b in bb["books"] if b["book_id"] == "psa"), None)
    if book is None:
        return None
    chap = next((c for c in book["chapters"] if c["chapter"] == ch), None)
    if chap is None or not chap["verses"]:
        return None
    return chap["verses"][0]["text"]


# --- Validation against schema ----------------------------------------


def test_alias_validates_against_schema():
    schema = json.loads(ALIAS_SCHEMA_PATH.read_text("utf-8"))
    payload = _load_alias()
    jsonschema.validate(payload, schema)


# --- Internal coherence -----------------------------------------------


def test_chapter_aliases_have_unique_mt_keys_per_book():
    payload = _load_alias()
    seen: set[tuple[str, int]] = set()
    for entry in payload["chapter_aliases"]:
        key = (entry["book"], entry["mt"])
        assert key not in seen, f"duplicate (book, mt) in chapter_aliases: {key}"
        seen.add(key)


def test_chapter_aliases_have_unique_vulgata_keys_per_book():
    payload = _load_alias()
    seen: set[tuple[str, int]] = set()
    for entry in payload["chapter_aliases"]:
        key = (entry["book"], entry["vulgata"])
        assert key not in seen, (
            f"duplicate (book, vulgata) in chapter_aliases: {key}"
        )
        seen.add(key)


def test_chapter_aliases_disjoint_from_split_or_merge():
    payload = _load_alias()
    chapter_alias_pairs: set[tuple[str, int, int]] = {
        (e["book"], e["mt"], e["vulgata"]) for e in payload["chapter_aliases"]
    }
    for sm in payload["split_or_merge"]:
        for mt_ch in sm["mt_chapters"]:
            for vulg_ch in sm["vulgata_chapters"]:
                assert (sm["book"], mt_ch, vulg_ch) not in chapter_alias_pairs, (
                    f"split_or_merge entry overlaps chapter_aliases: "
                    f"{sm['book']} mt={mt_ch} vulgata={vulg_ch}"
                )


def test_split_or_merge_chapters_unique_per_book():
    """A given (book, mt_chapter) should appear at most once across
    split_or_merge — no chapter participates in two structural rules."""
    payload = _load_alias()
    seen_mt: set[tuple[str, int]] = set()
    seen_vulg: set[tuple[str, int]] = set()
    for sm in payload["split_or_merge"]:
        for ch in sm["mt_chapters"]:
            key = (sm["book"], ch)
            assert key not in seen_mt, f"mt chapter listed twice: {key}"
            seen_mt.add(key)
        for ch in sm["vulgata_chapters"]:
            key = (sm["book"], ch)
            assert key not in seen_vulg, f"vulgata chapter listed twice: {key}"
            seen_vulg.add(key)


def test_psalter_coverage_is_complete():
    """For chapters 1..150, every (mt, vulgata) chapter must be accounted
    for either as a 1:1 alias, a split_or_merge entry, or an implicit
    identity (chapters that match without aliasing). The sets MT and
    Vulgata mentioned in the spec must reach the same total of 150."""
    payload = _load_alias()
    aliased_mt = {e["mt"] for e in payload["chapter_aliases"] if e["book"] == "psa"}
    aliased_vulg = {
        e["vulgata"] for e in payload["chapter_aliases"] if e["book"] == "psa"
    }
    sm_mt = {
        ch
        for sm in payload["split_or_merge"]
        if sm["book"] == "psa"
        for ch in sm["mt_chapters"]
    }
    sm_vulg = {
        ch
        for sm in payload["split_or_merge"]
        if sm["book"] == "psa"
        for ch in sm["vulgata_chapters"]
    }
    # Implicit identity: 1..8 and 148..150 are identical in both schemes
    # and not listed.
    implicit_identity = set(range(1, 9)) | set(range(148, 151))
    covered_mt = aliased_mt | sm_mt | implicit_identity
    covered_vulg = aliased_vulg | sm_vulg | implicit_identity
    assert covered_mt == set(range(1, 151)), (
        f"MT chapters not covered: {set(range(1, 151)) - covered_mt}"
    )
    assert covered_vulg == set(range(1, 151)), (
        f"Vulgata chapters not covered: {set(range(1, 151)) - covered_vulg}"
    )


# --- Sanity probes against actual built .bb files ---------------------


@pytest.mark.parametrize(
    "mt_ch,vulg_ch",
    [
        (11, 10),  # first chapter where the offset kicks in
        (23, 22),  # "El Señor es mi pastor" / "Dominus regit me"
        (51, 50),  # Miserere
        (113, 112),  # last chapter before the 114/115 merge
        (117, 116),  # first chapter after the 116 split
        (146, 145),  # last chapter before the 147 split
    ],
)
def test_psalm_chapter_alias_has_matching_text(mt_ch, vulg_ch):
    """For a sample of aliased chapters, verify that an MT-numbered
    edition (RV 1909) and a Vulgate-numbered edition (Vulgata Clementina)
    have *some* first verse on the corresponding chapter — proves the
    chapter exists on both sides. Full content equivalence is too strict
    (different translations) but the chapters must be present."""
    rv = _load_bible("rv1909")
    vc = _load_bible("vulgata")
    if rv is None or vc is None:
        pytest.skip("output/.bb files not built yet")
    assert _psalm_first_verse(rv, mt_ch) is not None, (
        f"RV 1909 missing Psalm {mt_ch}"
    )
    assert _psalm_first_verse(vc, vulg_ch) is not None, (
        f"Vulgata Clementina missing Psalm {vulg_ch}"
    )
