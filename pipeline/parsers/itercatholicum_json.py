"""Parser for the per-book JSON files published by ``danloi2/itercatholicum``.

The repository ships each Bible as a directory of one JSON file per book under
``src/shared/data/bibles/<edition>/<NN>-<bookid>-<vid>-<lang>.json``. Each file
follows the schema:

    {
        "id": "01",
        "nomen_es": "Génesis",
        "acronymum_es": "Gen",
        "lingua": "es-ES",
        "versio": "Torres Amat (1823)",
        "fons": "...",
        "licentia": "Dominio Público",
        "ctd_capitula": 50,
        "ctd_versus": 1532,
        "capitula": [
            {"numerus": 1, "ctd_versus": 31, "versus": {"1": "...", "2": "..."}},
            ...
        ],
    }

The parser is given the path of one of those files (the primary entry of the
catalogue), and walks ``parent_dir/*.json`` to read every book file in the
edition. Book IDs in the source use Spanish-ish abbreviations (``ex``, ``dt``,
``mt``, ``mc``); we map them to the canonical USFM lowercase IDs Berea uses.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

from ..normalize import ParsedVerse
from .base import BibleParser

# Map the Spanish/abbreviated book IDs used in the source filenames to the
# USFM 3.0 lowercase IDs adopted across the repo (canon_66/canon_extendido).
_SOURCE_BOOK_ID_TO_USFM: dict[str, str] = {
    "gen": "gen", "ex": "exo", "lev": "lev", "num": "num", "dt": "deu",
    "jos": "jos", "jue": "jdg", "rut": "rut",
    "1sam": "1sa", "2sam": "2sa", "1re": "1ki", "2re": "2ki",
    "1cron": "1ch", "2cron": "2ch", "esd": "ezr", "neh": "neh", "est": "est",
    "1mac": "1ma", "2mac": "2ma",
    "job": "job", "sal": "psa", "prov": "pro", "ecl": "ecc", "cant": "sng",
    "sab": "wis", "eclo": "sir",
    "is": "isa", "jer": "jer", "lam": "lam", "bar": "bar", "ez": "ezk",
    "dan": "dan",
    "os": "hos", "jl": "jol", "am": "amo", "abd": "oba", "jon": "jon",
    "miq": "mic", "nah": "nam", "hab": "hab", "sof": "zep", "ag": "hag",
    "zac": "zec", "mal": "mal",
    "tob": "tob", "jdt": "jdt",
    "mt": "mat", "mc": "mrk", "lc": "luk", "jn": "jhn", "hch": "act",
    "rom": "rom", "1cor": "1co", "2cor": "2co", "gal": "gal", "ef": "eph",
    "flp": "php", "col": "col", "1tes": "1th", "2tes": "2th",
    "1tim": "1ti", "2tim": "2ti", "tit": "tit", "flm": "phm",
    "heb": "heb", "sant": "jas",
    "1pe": "1pe", "2pe": "2pe", "1jn": "1jn", "2jn": "2jn", "3jn": "3jn",
    "jds": "jud", "ap": "rev",
}

# File names look like ``01-gen-ta-es.json``; the second component is the
# source's own book ID. We use a regex to pull it out independent of edition
# (``ta`` for Torres Amat, future editions may use other tokens).
_RE_FILENAME = re.compile(r"^\d+-([a-z0-9]+)-[a-z]+-[a-z]+\.json$")


class IterCatholicumJsonParser(BibleParser):
    """Parser for the per-book JSON files of danloi2/itercatholicum."""

    name = "itercatholicum_json"

    def __init__(
        self,
        allowed_book_ids: set[str] | None = None,
    ) -> None:
        self.allowed_book_ids = allowed_book_ids or set()

    def parse(self, source_path: Path) -> Iterable[ParsedVerse]:
        # source_path is the catalogue's primary file. Walk its directory so
        # every book of the edition is parsed regardless of which one was
        # declared as primary.
        directory = source_path.parent
        for entry in sorted(directory.iterdir()):
            if not entry.is_file():
                continue
            m = _RE_FILENAME.match(entry.name)
            if not m:
                continue
            source_book_id = m.group(1).lower()
            book_id = _SOURCE_BOOK_ID_TO_USFM.get(source_book_id)
            if book_id is None:
                # An edition shipping a book Berea doesn't catalog yet
                # should be ignored quietly rather than aborting the build.
                continue
            if self.allowed_book_ids and book_id not in self.allowed_book_ids:
                continue
            yield from self._parse_book_file(entry, book_id)

    def _parse_book_file(
        self, path: Path, book_id: str
    ) -> Iterable[ParsedVerse]:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        capitula = data.get("capitula") or []
        for chapter in capitula:
            ch_num = chapter.get("numerus")
            if not isinstance(ch_num, int) or ch_num < 1:
                continue
            versus = chapter.get("versus") or {}
            for verse_key, text in versus.items():
                if not isinstance(text, str) or not text.strip():
                    continue
                try:
                    verse_num = int(verse_key)
                except (TypeError, ValueError):
                    # Unusual key (e.g., "1a"). Strip suffix and keep it as alias.
                    m = re.match(r"^(\d+)", str(verse_key))
                    if not m:
                        continue
                    verse_num = int(m.group(1))
                    yield ParsedVerse(
                        book_id=book_id,
                        chapter=ch_num,
                        verse=verse_num,
                        text=text.strip(),
                        verse_alias=str(verse_key),
                    )
                else:
                    yield ParsedVerse(
                        book_id=book_id,
                        chapter=ch_num,
                        verse=verse_num,
                        text=text.strip(),
                    )


PARSER = IterCatholicumJsonParser
