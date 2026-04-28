"""Parser-level tests for the OSHB OSIS XML parser.

Tests run against an inline fixture so they don't need the full archive.
"""

from __future__ import annotations

from pipeline.parsers.oshb_osis import _parse_book_file, _verse_text
from xml.etree import ElementTree as ET

OSIS_NS = "http://www.bibletechnologies.net/2003/OSIS/namespace"


GEN_FIXTURE = f"""<?xml version="1.0" encoding="UTF-8"?>
<osis xmlns="{OSIS_NS}">
  <osisText xml:lang="he" osisIDWork="OSHB">
    <header><work osisWork="OSHB"><title>OSHB</title></work></header>
    <div type="book" osisID="Gen">
      <chapter osisID="Gen.1">
        <verse osisID="Gen.1.1">
          <w>בְּרֵאשִׁית</w>
          <w>בָּרָא</w>
          <w>אֱלֹהִים</w>
          <w>אֵת</w>
          <w>הַ/שָּׁמַיִם</w>
          <w>וְ/אֵת</w>
          <w>הָ/אָרֶץ</w>
          <seg type="x-sof-pasuq">׃</seg>
        </verse>
        <verse osisID="Gen.1.2">
          <w>עַל</w>
          <seg type="x-maqqef">־</seg>
          <w>פְּנֵי</w>
          <w>תְהוֹם</w>
        </verse>
      </chapter>
    </div>
  </osisText>
</osis>
"""


def test_parse_book_file_emits_clean_hebrew():
    verses = list(_parse_book_file(GEN_FIXTURE, allowed_book_ids={"gen"}))
    assert len(verses) == 2

    v1 = verses[0]
    assert v1.book_id == "gen"
    assert v1.chapter == 1
    assert v1.verse == 1
    # Morpheme slashes stripped, words space-separated, sof-pasuq attached.
    assert v1.text == "בְּרֵאשִׁית בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם וְאֵת הָאָרֶץ׃"


def test_maqqef_attaches_with_no_spaces():
    verses = list(_parse_book_file(GEN_FIXTURE, allowed_book_ids={"gen"}))
    v2 = verses[1]
    assert v2.text == "עַל־פְּנֵי תְהוֹם"


def test_filters_disallowed_books():
    verses = list(_parse_book_file(GEN_FIXTURE, allowed_book_ids={"exo"}))
    assert verses == []


def test_verse_text_strips_morpheme_slashes_in_word():
    fragment = f'<verse xmlns="{OSIS_NS}" osisID="Gen.1.1"><w>וַ/יְהִי</w></verse>'
    elem = ET.fromstring(fragment)
    assert _verse_text(elem) == "וַיְהִי"
