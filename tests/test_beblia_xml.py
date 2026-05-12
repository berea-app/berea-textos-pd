"""Parser-level tests for the Beblia/Holy-Bible-XML-Format parser.

Tests run against an inline fixture so they don't need the full archive.
"""

from __future__ import annotations

from pathlib import Path

from pipeline.parsers.beblia_xml import _BEBLIA_NUMBER_TO_USFM, BebliaXmlParser

FIXTURE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<bible translation="Spanish 1569" status="Public Domain">
  <testament name="Old">
    <book number="1">
      <chapter number="1">
        <verse number="1">En el principio creó Dios los cielos y la tierra.</verse>
        <verse number="2">Y la tierra estaba desordenada y vacía.</verse>
      </chapter>
      <chapter number="2">
        <verse number="4">Estos son los orígenes de los cielos y de la tierra.</verse>
      </chapter>
    </book>
    <book number="19">
      <chapter number="23">
        <verse number="1">El SEÑOR es mi pastor; nada me faltará.</verse>
      </chapter>
    </book>
  </testament>
  <testament name="New">
    <book number="43">
      <chapter number="3">
        <verse number="16">Porque de tal manera amó Dios al mundo.</verse>
      </chapter>
    </book>
    <book number="66">
      <chapter number="22">
        <verse number="21">La gracia de nuestro Señor Jesucristo sea con todos vosotros. Amén.</verse>
      </chapter>
    </book>
  </testament>
</bible>
"""


def _write_fixture(tmp_path: Path) -> Path:
    p = tmp_path / "fixture.xml"
    p.write_text(FIXTURE_XML, encoding="utf-8")
    return p


def test_beblia_number_map_covers_full_protestant_canon():
    assert len(_BEBLIA_NUMBER_TO_USFM) == 66
    assert _BEBLIA_NUMBER_TO_USFM[1] == "gen"
    assert _BEBLIA_NUMBER_TO_USFM[19] == "psa"
    assert _BEBLIA_NUMBER_TO_USFM[43] == "jhn"
    assert _BEBLIA_NUMBER_TO_USFM[66] == "rev"
    # No duplicate USFM ids.
    assert len(set(_BEBLIA_NUMBER_TO_USFM.values())) == 66


def test_parser_yields_all_verses_in_canonical_form(tmp_path: Path):
    parser = BebliaXmlParser()
    verses = list(parser.parse(_write_fixture(tmp_path)))
    assert len(verses) == 6

    gen_1_1 = verses[0]
    assert gen_1_1.book_id == "gen"
    assert gen_1_1.chapter == 1
    assert gen_1_1.verse == 1
    assert gen_1_1.text.startswith("En el principio creó Dios")

    # Psalm 23:1 is the Reina-Antigua hallmark — "el SEÑOR" instead of
    # "Jehová", which is what distinguishes this digitalization from RV1909.
    psa_23_1 = next(
        v for v in verses if v.book_id == "psa" and v.chapter == 23
    )
    assert "SEÑOR" in psa_23_1.text

    rev_last = next(
        v for v in verses
        if v.book_id == "rev" and v.chapter == 22 and v.verse == 21
    )
    assert rev_last.text.endswith("Amén.")


def test_parser_respects_allowed_book_ids(tmp_path: Path):
    parser = BebliaXmlParser(allowed_book_ids={"gen", "psa"})
    verses = list(parser.parse(_write_fixture(tmp_path)))
    book_ids = {v.book_id for v in verses}
    assert book_ids == {"gen", "psa"}


def test_parser_skips_empty_and_malformed_entries(tmp_path: Path):
    bad = tmp_path / "bad.xml"
    bad.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<bible>
  <testament name="Old">
    <book number="1">
      <chapter number="1">
        <verse number="1">   </verse>
        <verse number="not-a-number">texto</verse>
        <verse number="2">Texto válido.</verse>
      </chapter>
      <chapter number="abc">
        <verse number="1">Ignorar.</verse>
      </chapter>
    </book>
    <book number="999">
      <chapter number="1">
        <verse number="1">Libro fuera de rango, ignorar.</verse>
      </chapter>
    </book>
  </testament>
</bible>
""", encoding="utf-8")
    parser = BebliaXmlParser()
    verses = list(parser.parse(bad))
    assert len(verses) == 1
    assert verses[0].text == "Texto válido."
    assert verses[0].book_id == "gen"
    assert verses[0].chapter == 1
    assert verses[0].verse == 2


def test_full_source_round_trips_to_31102_verses():
    """Smoke test against the downloaded source if present.

    Skipped when sources/ses1569/ hasn't been populated yet (CI runs the
    pipeline end-to-end, so the file will exist there)."""
    import pytest

    source = (
        Path(__file__).resolve().parent.parent
        / "sources"
        / "ses1569"
        / "Spanish1569Bible.xml"
    )
    if not source.exists():
        pytest.skip("ses1569 source not yet downloaded")

    parser = BebliaXmlParser()
    verses = list(parser.parse(source))
    assert len(verses) == 31102

    book_ids = sorted({v.book_id for v in verses})
    assert len(book_ids) == 66

    # Gen 1:1, Jn 3:16, last verse of Rev.
    gen_1_1 = next(
        v for v in verses if v.book_id == "gen" and v.chapter == 1 and v.verse == 1
    )
    assert gen_1_1.text == "En el principio creó Dios los cielos y la tierra."

    jhn_3_16 = next(
        v for v in verses
        if v.book_id == "jhn" and v.chapter == 3 and v.verse == 16
    )
    assert "amó Dios al mundo" in jhn_3_16.text

    rev_last = next(
        v for v in verses
        if v.book_id == "rev" and v.chapter == 22 and v.verse == 21
    )
    assert rev_last.text.endswith(".")
