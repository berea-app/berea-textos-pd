"""Parser for the Open Scriptures Hebrew Bible (OSHB) OSIS XML release.

OSHB ships one XML file per book inside ``OSHB-v.X.Y.zip``. Each file is OSIS
markup with ``<div type="book" osisID="...">`` containing ``<chapter>`` and
``<verse osisID="Gen.1.1">...</verse>`` containers; the verse text is the
concatenation of the ``<w>`` elements (with diacritics) joined by spaces.

OSHB uses ``/`` inside ``<w>`` content to mark morpheme boundaries; we strip
those slashes when emitting the verse text so the .bb carries the displayable
Hebrew form.

Reference: https://github.com/openscriptures/morphhb
"""

from __future__ import annotations

import zipfile
from collections.abc import Iterable
from pathlib import Path
from xml.etree import ElementTree as ET

from ..normalize import ParsedVerse
from .base import BibleParser

OSIS_NS = "http://www.bibletechnologies.net/2003/OSIS/namespace"
_NS = {"osis": OSIS_NS}

# OSIS book id → USFM 3.0 lowercase canonical book_id.
OSIS_TO_BOOK_ID: dict[str, str] = {
    "Gen": "gen", "Exod": "exo", "Lev": "lev", "Num": "num", "Deut": "deu",
    "Josh": "jos", "Judg": "jdg", "Ruth": "rut",
    "1Sam": "1sa", "2Sam": "2sa", "1Kgs": "1ki", "2Kgs": "2ki",
    "1Chr": "1ch", "2Chr": "2ch", "Ezra": "ezr", "Neh": "neh", "Esth": "est",
    "Job": "job", "Ps": "psa", "Prov": "pro", "Eccl": "ecc", "Song": "sng",
    "Isa": "isa", "Jer": "jer", "Lam": "lam", "Ezek": "ezk", "Dan": "dan",
    "Hos": "hos", "Joel": "jol", "Amos": "amo", "Obad": "oba", "Jonah": "jon",
    "Mic": "mic", "Nah": "nam", "Hab": "hab", "Zeph": "zep", "Hag": "hag",
    "Zech": "zec", "Mal": "mal",
}


def _word_text(elem: ET.Element) -> str:
    """Concatenate all text descendants of ``elem`` and strip morpheme slashes."""
    parts: list[str] = []
    if elem.text:
        parts.append(elem.text)
    for child in elem:
        if child.text:
            parts.append(child.text)
        if child.tail:
            parts.append(child.tail)
    return "".join(parts).replace("/", "")


def _verse_text(verse_elem: ET.Element) -> str:
    """Build the readable Hebrew text for one ``<verse>`` element.

    Words are space-separated by default. Hebrew maqaf (``־``) is a binder
    that attaches the next word with no spaces (``לֵב־אָבוֹת``). The sof-pasuq
    (``׃``) and paseq (``׀``) are punctuation that attach to the preceding
    word.
    """
    out: list[str] = []
    last_was_joiner = False
    for elem in verse_elem.iter():
        tag = elem.tag.split("}", 1)[-1]
        if tag == "w":
            text = _word_text(elem)
            if not text:
                continue
            if out and not last_was_joiner:
                out.append(" ")
            out.append(text)
            last_was_joiner = False
        elif tag == "seg":
            seg_type = elem.attrib.get("type", "")
            text = (elem.text or "").strip()
            if not text:
                continue
            if seg_type == "x-maqqef":
                # Joiner: no surrounding spaces; the next <w> attaches directly.
                out.append(text)
                last_was_joiner = True
            elif seg_type in ("x-sof-pasuq", "x-paseq"):
                # Punctuation: attach to previous token, then a space.
                out.append(text)
                last_was_joiner = False
            else:
                if out and not last_was_joiner:
                    out.append(" ")
                out.append(text)
                last_was_joiner = False
    return "".join(out).strip()


def _parse_book_file(xml_text: str, allowed_book_ids: set[str]) -> Iterable[ParsedVerse]:
    root = ET.fromstring(xml_text)
    for book in root.iter(f"{{{OSIS_NS}}}div"):
        if book.attrib.get("type") != "book":
            continue
        osis_id = book.attrib.get("osisID", "")
        book_id = OSIS_TO_BOOK_ID.get(osis_id)
        if not book_id or book_id not in allowed_book_ids:
            continue

        for verse in book.iter(f"{{{OSIS_NS}}}verse"):
            ref = verse.attrib.get("osisID")
            if not ref:
                continue
            # osisID = "Gen.1.1"
            try:
                _, ch_str, v_str = ref.split(".")
                chapter = int(ch_str)
                verse_num = int(v_str)
            except ValueError:
                continue
            text = _verse_text(verse)
            if not text:
                continue
            yield ParsedVerse(
                book_id=book_id,
                chapter=chapter,
                verse=verse_num,
                text=text,
            )


class _OshbOsisParser(BibleParser):
    """Parser that reads the OSHB v2.2 zip release of the Westminster Leningrad Codex."""

    name = "oshb_osis"

    def __init__(self, allowed_book_ids: set[str] | None = None) -> None:
        if allowed_book_ids is None:
            allowed_book_ids = set(OSIS_TO_BOOK_ID.values())
        self.allowed_book_ids = allowed_book_ids

    def parse(self, source_path: Path) -> Iterable[ParsedVerse]:
        with zipfile.ZipFile(source_path, "r") as z:
            names = sorted(
                n for n in z.namelist()
                if n.lower().endswith(".xml") and "__macosx" not in n.lower()
            )
            for name in names:
                with z.open(name) as f:
                    raw = f.read().decode("utf-8")
                yield from _parse_book_file(raw, self.allowed_book_ids)


PARSER = _OshbOsisParser
