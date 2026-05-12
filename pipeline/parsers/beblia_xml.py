"""Parser for the single-file XML format used by ``Beblia/Holy-Bible-XML-Format``.

The repository ships every Bible as one XML file with the structure::

    <bible translation="..." status="...">
      <testament name="Old|New">
        <book number="1..66">
          <chapter number="1..N">
            <verse number="1..M">texto del versículo</verse>
            ...
          </chapter>
          ...
        </book>
        ...
      </testament>
      ...
    </bible>

Book ``number`` is a global 1..66 index following the standard Protestant
order (Genesis=1 ... Revelation=66). Numbering is the Masoretic / TR scheme;
no deuterocanonicals appear in the editions Berea ingests through this parser.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterable
from pathlib import Path

from ..normalize import ParsedVerse
from .base import BibleParser

# Beblia uses a 1-based global book index (1=Genesis ... 66=Revelation) in
# canonical Protestant order. The map below converts that index to the USFM
# 3.0 lowercase IDs Berea uses across the repo.
_BEBLIA_NUMBER_TO_USFM: dict[int, str] = {
    1: "gen", 2: "exo", 3: "lev", 4: "num", 5: "deu",
    6: "jos", 7: "jdg", 8: "rut",
    9: "1sa", 10: "2sa", 11: "1ki", 12: "2ki",
    13: "1ch", 14: "2ch", 15: "ezr", 16: "neh", 17: "est",
    18: "job", 19: "psa", 20: "pro", 21: "ecc", 22: "sng",
    23: "isa", 24: "jer", 25: "lam", 26: "ezk", 27: "dan",
    28: "hos", 29: "jol", 30: "amo", 31: "oba", 32: "jon",
    33: "mic", 34: "nam", 35: "hab", 36: "zep", 37: "hag",
    38: "zec", 39: "mal",
    40: "mat", 41: "mrk", 42: "luk", 43: "jhn", 44: "act",
    45: "rom", 46: "1co", 47: "2co", 48: "gal", 49: "eph",
    50: "php", 51: "col", 52: "1th", 53: "2th", 54: "1ti",
    55: "2ti", 56: "tit", 57: "phm", 58: "heb", 59: "jas",
    60: "1pe", 61: "2pe", 62: "1jn", 63: "2jn", 64: "3jn",
    65: "jud", 66: "rev",
}


class BebliaXmlParser(BibleParser):
    """Parser for the Beblia/Holy-Bible-XML-Format single-file XML editions."""

    name = "beblia_xml"

    def __init__(
        self,
        allowed_book_ids: set[str] | None = None,
    ) -> None:
        self.allowed_book_ids = allowed_book_ids or set()

    def parse(self, source_path: Path) -> Iterable[ParsedVerse]:
        tree = ET.parse(source_path)
        root = tree.getroot()
        for testament in root.findall("testament"):
            for book in testament.findall("book"):
                num_attr = book.get("number")
                if num_attr is None:
                    continue
                try:
                    book_num = int(num_attr)
                except ValueError:
                    continue
                book_id = _BEBLIA_NUMBER_TO_USFM.get(book_num)
                if book_id is None:
                    continue
                if self.allowed_book_ids and book_id not in self.allowed_book_ids:
                    continue
                yield from self._parse_book(book, book_id)

    def _parse_book(
        self, book_elem: ET.Element, book_id: str
    ) -> Iterable[ParsedVerse]:
        for chapter in book_elem.findall("chapter"):
            ch_attr = chapter.get("number")
            if ch_attr is None:
                continue
            try:
                ch_num = int(ch_attr)
            except ValueError:
                continue
            if ch_num < 1:
                continue
            for verse in chapter.findall("verse"):
                v_attr = verse.get("number")
                if v_attr is None:
                    continue
                try:
                    verse_num = int(v_attr)
                except ValueError:
                    continue
                text = (verse.text or "").strip()
                if not text:
                    continue
                yield ParsedVerse(
                    book_id=book_id,
                    chapter=ch_num,
                    verse=verse_num,
                    text=text,
                )


PARSER = BebliaXmlParser
