"""Parser-level tests for the Nestle 1904 TSV parser."""

from __future__ import annotations

from pipeline.parsers.nestle1904_tsv import _parse_bcv


def test_parse_bcv_handles_known_book_names():
    assert _parse_bcv("Matt 1:1") == ("mat", 1, 1)
    assert _parse_bcv("John 3:16") == ("jhn", 3, 16)
    assert _parse_bcv("1Cor 13:13") == ("1co", 13, 13)
    assert _parse_bcv("Rev 22:21") == ("rev", 22, 21)


def test_parse_bcv_returns_none_for_unknown_book():
    assert _parse_bcv("Esther 1:1") is None
    assert _parse_bcv("nonsense") is None
