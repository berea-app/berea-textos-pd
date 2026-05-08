"""Parser-level tests for the ebible USFM parser.

These run against a small inline fixture so they don't need the full archive.
"""

from __future__ import annotations

from pipeline.parsers.ebible_usfm import _clean_text, _parse_book

_GEN_V1 = (
    '\\v 1  \\w EN el principio|strong="H7225"\\w*'
    ' \\w crió|strong="H1254"\\w* \\w Dios|strong="H0430"\\w*.'
)
GEN_FIXTURE = (
    "\\id GEN  Genesis\n"
    "\\h Génesis\n"
    "\\toc1 Génesis\n"
    "\\mt1 Génesis\n"
    "\\c 1\n"
    "\\p\n"
    f"{_GEN_V1}\n"
    "\\v 2  Texto con \\add adición\\add* y \\nd nombre divino\\nd*.\n"
    "\\v 3  Después \\f + nota \\f* del versículo.\n"
    "\\c 2\n"
    "\\v 1  Capítulo dos versículo uno.\n"
)


def test_clean_text_strips_morphology_tags():
    raw = '\\w EN el principio|strong="H7225"\\w* \\w crió|strong="H1254"\\w*.'
    assert _clean_text(raw) == "EN el principio crió."


def test_clean_text_drops_footnotes_and_xrefs():
    raw = "Hola \\f + esto es nota \\f* mundo \\x + xref \\x*."
    assert _clean_text(raw) == "Hola mundo ."


def test_parse_book_yields_clean_verses():
    verses = list(_parse_book(GEN_FIXTURE, allowed_book_ids={"gen"}))
    assert len(verses) == 4
    assert verses[0].book_id == "gen"
    assert verses[0].chapter == 1
    assert verses[0].verse == 1
    assert verses[0].text == "EN el principio crió Dios."
    assert verses[1].text == "Texto con adición y nombre divino."
    assert verses[2].text == "Después del versículo."
    assert verses[3].chapter == 2
    assert verses[3].verse == 1


def test_parse_book_filters_disallowed():
    verses = list(_parse_book(GEN_FIXTURE, allowed_book_ids={"exo"}))
    assert verses == []
