"""Parser for STEPBible's Translators Amalgamated Greek New Testament (TAGNT).

TAGNT is a UTF-8 tab-separated file (CC BY 4.0, github.com/STEPBible/STEPBible-Data)
that records every word from the major critical/traditional Greek NT editions
(NA27, NA28, SBL, Tyn, WH, Treg, TR, Byz) with the editions that contain it
plus optional per-edition spelling variants.

This parser extracts a single edition (passed as ``edition`` config) by
filtering rows whose ``editions`` column contains the target name. When a
spelling variant is recorded for the target edition, the variant form is
used instead of the default Greek field.

The parser scans every ``.txt`` file in the bible's source directory, so
catalog entries must declare ``extra_sources`` for any auxiliary files
(TAGNT ships split across two files because GitHub limits raw size).

Reference fields are book.chapter.verse with TAGNT's three-letter book
abbreviations (Mat, Mrk, Luk, Jhn, Act, Rom, 1Co, 2Co, Gal, Eph, Php, Col,
1Th, 2Th, 1Ti, 2Ti, Tit, Phm, Heb, Jas, 1Pe, 2Pe, 1Jn, 2Jn, 3Jn, Jud, Rev).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from ..normalize import ParsedVerse
from .base import BibleParser

TAGNT_TO_BOOK_ID: dict[str, str] = {
    "Mat": "mat", "Mrk": "mrk", "Luk": "luk", "Jhn": "jhn", "Act": "act",
    "Rom": "rom", "1Co": "1co", "2Co": "2co", "Gal": "gal", "Eph": "eph",
    "Php": "php", "Col": "col", "1Th": "1th", "2Th": "2th",
    "1Ti": "1ti", "2Ti": "2ti", "Tit": "tit", "Phm": "phm",
    "Heb": "heb", "Jas": "jas", "1Pe": "1pe", "2Pe": "2pe",
    "1Jn": "1jn", "2Jn": "2jn", "3Jn": "3jn", "Jud": "jud", "Rev": "rev",
}

KNOWN_EDITIONS = {"NA27", "NA28", "Tyn", "SBL", "WH", "Treg", "TR", "Byz"}


_RE_REF = re.compile(
    r"^(?P<book>[A-Za-z0-9]{3})\.(?P<chapter>\d+)\.(?P<verse>\d+)#(?P<word>\d+)(?:=(?P<status>\S+))?\s*$"
)
_RE_TRANSLIT = re.compile(r"\s*\([^)]*\)\s*$")


def _strip_translit(greek_field: str) -> str:
    return _RE_TRANSLIT.sub("", greek_field).strip()


def _editions_set(field: str) -> set[str]:
    return {e.strip().lstrip("+") for e in field.split("+") if e.strip()}


def _spelling_for(edition: str, variants_field: str) -> str | None:
    """Return the per-edition spelling variant for ``edition`` if one is
    recorded in ``variants_field``, else ``None``.

    ``variants_field`` looks like ``"Tyn+WH: Δαυεὶδ ; +TR: Δαβὶδ ;"``. Each
    semicolon-separated entry is ``EDITIONS: WORD``; the leading ``+`` on
    the editions list is decorative.
    """
    if not variants_field:
        return None
    for entry in variants_field.split(";"):
        entry = entry.strip()
        if not entry or ":" not in entry:
            continue
        eds, word = entry.split(":", 1)
        eds_set = _editions_set(eds)
        if edition in eds_set:
            return word.strip()
    return None


def _meaning_variant_for(edition: str, variants_field: str) -> str | None:
    """Return the per-edition meaning variant for ``edition`` if one is
    recorded in column 6 of TAGNT.

    Format: ``ἁγίων (O=hagiōn) saints. - G0040=A-GPM in: Tyn+WH+Treg+Byz``
    Multiple variants can be separated by ``;``.
    """
    if not variants_field or "in:" not in variants_field:
        return None
    for entry in variants_field.split(";"):
        entry = entry.strip()
        if " in:" not in entry:
            continue
        word_part, editions_part = entry.rsplit(" in:", 1)
        eds_set = _editions_set(editions_part.strip())
        if edition not in eds_set:
            continue
        # Greek word is the first whitespace-delimited token, sometimes with
        # trailing punctuation that we keep so the verse text reads correctly.
        first = word_part.split(" ", 1)[0].strip()
        if first:
            return first
    return None


def _parse_word_row(
    cols: list[str], edition: str
) -> tuple[tuple[str, int, int], str] | None:
    if len(cols) < 6:
        return None
    ref_field = cols[0].strip()
    m = _RE_REF.match(ref_field)
    if not m:
        return None
    book_abbr = m.group("book")
    book_id = TAGNT_TO_BOOK_ID.get(book_abbr)
    if book_id is None:
        return None
    chapter = int(m.group("chapter"))
    verse = int(m.group("verse"))

    editions_field = cols[5].strip() if len(cols) > 5 else ""
    spelling_variants = cols[7].strip() if len(cols) > 7 else ""
    meaning_variants = cols[6].strip() if len(cols) > 6 else ""

    if edition in _editions_set(editions_field):
        default_greek = _strip_translit(cols[1])
        word = _spelling_for(edition, spelling_variants) or default_greek
    else:
        # The word in col 1 belongs to other editions; check whether ``edition``
        # has its own reading recorded as a meaning variant (col 6).
        word = _meaning_variant_for(edition, meaning_variants)
        if word is None:
            return None
    if not word:
        return None
    return (book_id, chapter, verse), word


def _parse_file(
    path: Path, edition: str, allowed_book_ids: set[str]
) -> Iterable[tuple[tuple[str, int, int], str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            if not line or line.startswith("#") or line.startswith("\t"):
                continue
            if not line[0].isalnum():
                continue
            cols = line.split("\t")
            row = _parse_word_row(cols, edition)
            if row is None:
                continue
            (book_id, _, _), _ = row
            if book_id not in allowed_book_ids:
                continue
            yield row


class _StepbibleTagntParser(BibleParser):
    """Parser for STEPBible TAGNT split-file releases."""

    name = "stepbible_tagnt"

    def __init__(
        self,
        allowed_book_ids: set[str] | None = None,
        edition: str | None = None,
    ) -> None:
        if edition is None:
            raise ValueError("stepbible_tagnt parser requires `edition` config")
        if edition not in KNOWN_EDITIONS:
            raise ValueError(
                f"unknown edition {edition!r}; expected one of {sorted(KNOWN_EDITIONS)}"
            )
        if allowed_book_ids is None:
            allowed_book_ids = set(TAGNT_TO_BOOK_ID.values())
        self.edition = edition
        self.allowed_book_ids = allowed_book_ids

    def parse(self, source_path: Path) -> Iterable[ParsedVerse]:
        # ``source_path`` points at one of the TAGNT files; iterate every
        # ``.txt`` in its directory so we cover both Mat-Jhn and Act-Rev.
        directory = source_path.parent
        files = sorted(p for p in directory.glob("*.txt") if p.is_file())

        cur_key: tuple[str, int, int] | None = None
        cur_words: list[str] = []

        def flush() -> ParsedVerse | None:
            if cur_key is None or not cur_words:
                return None
            text = " ".join(w for w in cur_words if w).strip()
            if not text:
                return None
            book_id, chapter, verse = cur_key
            return ParsedVerse(book_id=book_id, chapter=chapter, verse=verse, text=text)

        for path in files:
            for key, word in _parse_file(path, self.edition, self.allowed_book_ids):
                if key != cur_key:
                    v = flush()
                    if v is not None:
                        yield v
                    cur_key = key
                    cur_words = [word]
                else:
                    cur_words.append(word)

        v = flush()
        if v is not None:
            yield v


PARSER = _StepbibleTagntParser
