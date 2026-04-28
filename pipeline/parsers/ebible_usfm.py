"""Parser for ebible.org USFM ZIP archives.

Used for any text packaged by ebible.org as ``<lang><id>_usfm.zip`` where the
archive contains one ``\\id <USFM3>`` per book file. RV 1909 is the pilot.

The parser strips USFM markup down to plain UTF-8 verse text:
- ``\\f ... \\f*`` footnotes — dropped.
- ``\\x ... \\x*`` cross-references — dropped.
- ``\\w word|strong="..."\\w*`` morphology-tagged words — replaced by ``word``.
- All other ``\\tag`` and ``\\tag*`` markers — stripped, keeping any contained text.
- ``\\h``, ``\\toc[123]``, ``\\mt[123]``, ``\\is[12]``, ``\\imt[12]``, ``\\cl``,
  ``\\cd``, ``\\cp``, ``\\ide``, ``\\rem``, ``\\sts``, ``\\usfm``, ``\\b``,
  ``\\r``, ``\\mr``, ``\\ms[12]``, ``\\sr``, ``\\d`` lines — dropped.
- ``\\s[1-4]`` section headings — captured and attached to the next verse as
  ``heading``.
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from typing import Iterable

from ..normalize import ParsedVerse
from .base import BibleParser

# USFM 3-letter book IDs to canonical (USFM lowercase) book_ids.
USFM_TO_BOOK_ID: dict[str, str] = {
    "GEN": "gen", "EXO": "exo", "LEV": "lev", "NUM": "num", "DEU": "deu",
    "JOS": "jos", "JDG": "jdg", "RUT": "rut",
    "1SA": "1sa", "2SA": "2sa", "1KI": "1ki", "2KI": "2ki",
    "1CH": "1ch", "2CH": "2ch", "EZR": "ezr", "NEH": "neh", "EST": "est",
    "JOB": "job", "PSA": "psa", "PRO": "pro", "ECC": "ecc", "SNG": "sng",
    "ISA": "isa", "JER": "jer", "LAM": "lam", "EZK": "ezk", "DAN": "dan",
    "HOS": "hos", "JOL": "jol", "AMO": "amo", "OBA": "oba", "JON": "jon",
    "MIC": "mic", "NAM": "nam", "HAB": "hab", "ZEP": "zep", "HAG": "hag",
    "ZEC": "zec", "MAL": "mal",
    "MAT": "mat", "MRK": "mrk", "LUK": "luk", "JHN": "jhn", "ACT": "act",
    "ROM": "rom", "1CO": "1co", "2CO": "2co", "GAL": "gal", "EPH": "eph",
    "PHP": "php", "COL": "col", "1TH": "1th", "2TH": "2th", "1TI": "1ti",
    "2TI": "2ti", "TIT": "tit", "PHM": "phm", "HEB": "heb", "JAS": "jas",
    "1PE": "1pe", "2PE": "2pe", "1JN": "1jn", "2JN": "2jn", "3JN": "3jn",
    "JUD": "jud", "REV": "rev",
    # Deuterocanonical / LXX-only mappings (kept here for parsers that consume
    # archives carrying those books even when this Bible doesn't).
    "TOB": "tob", "JDT": "jdt", "ESG": "esg", "WIS": "wis", "SIR": "sir",
    "BAR": "bar", "LJE": "lje", "S3Y": "s3y", "SUS": "sus", "BEL": "bel",
    "1MA": "1ma", "2MA": "2ma", "3MA": "3ma", "4MA": "4ma", "MAN": "man",
    "1ES": "1es", "2ES": "2es", "PS2": "ps2", "ODA": "oda", "PSS": "pss",
    # Brenton's LXX uses ``DAG`` ("Daniel Greek") for the LXX edition of
    # Daniel that interleaves Susanna, Bel and the Dragon, and the Song of
    # the Three Young Men. We map it to ``dan``; chapters 13-14 carry the
    # additions inline (the verifier accepts extra chapters beyond the
    # canon's expected count).
    "DAG": "dan",
}

# Files we always skip (front matter, glossary, peripheral material).
SKIPPED_USFM_IDS = {"FRT", "BAK", "GLO", "INT", "CNC", "TDX", "NDX", "OTH", "XXA", "XXB", "XXC", "XXD"}

_RE_FOOTNOTE = re.compile(r"\\f\s.*?\\f\*", re.DOTALL)
_RE_XREF = re.compile(r"\\x\s.*?\\x\*", re.DOTALL)
_RE_WORD = re.compile(r"\\w\s+([^|\\]+?)(?:\|[^\\]*)?\\w\*")
_RE_CLOSE_TAG = re.compile(r"\\\+?\w+\*")
_RE_OPEN_TAG = re.compile(r"\\\+?\w+\d?\s?")
_RE_VERSE = re.compile(r"^\\v\s+(\S+)\s*(.*)$")
_RE_CHAPTER = re.compile(r"^\\c\s+(\d+)")
_RE_HEADING = re.compile(r"^\\s\d?\s*(.*)$")
_RE_ID = re.compile(r"^\\id\s+(\S+)")

# Lines whose entire content is metadata or formatting, no verse text.
_RE_META_LINE = re.compile(
    r"^\\(?:h|toc[1-3]?|mt[1-9]?|ms[1-4]?|imt[1-9]?|is[1-4]?|cl|cd|cp|ide|rem|sts|usfm|"
    r"r|mr|sr|d|b|nb|pi[1-9]?|sp|ph[1-9]?|li[1-9]?|periph)\b"
)


def _clean_text(s: str) -> str:
    """Strip USFM markup from ``s`` and return cleaned UTF-8 text."""
    s = _RE_FOOTNOTE.sub("", s)
    s = _RE_XREF.sub("", s)
    s = _RE_WORD.sub(r"\1", s)
    s = _RE_CLOSE_TAG.sub("", s)
    s = _RE_OPEN_TAG.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _verse_number(token: str) -> tuple[int, str | None]:
    """Parse a USFM verse token. Returns ``(start, alias)`` where alias is the
    raw token when it's a range or list (``"1-2"``, ``"1,3"``), else ``None``.

    USFM 3.0 allows letter suffixes (``2a``, ``5b``); we drop them for the
    integer key but keep them in the alias so the reader can display the
    original label.
    """
    m = re.match(r"^(\d+)", token)
    if not m:
        raise ValueError(f"unparseable verse token: {token!r}")
    start = int(m.group(1))
    if token == m.group(1):
        return start, None
    return start, token


def _parse_book(usfm_text: str, allowed_book_ids: set[str]) -> Iterable[ParsedVerse]:
    """Yield ParsedVerse from a single USFM book file.

    ``allowed_book_ids`` filters out books outside the catalogue's canon family
    (e.g., a future LXX archive shipping deuterocanonical books that this
    Bible's manifest entry does not advertise).
    """
    book_id: str | None = None
    chapter: int | None = None
    pending_heading: str | None = None
    cur_verse_num: int | None = None
    cur_verse_alias: str | None = None
    cur_verse_heading: str | None = None
    cur_text: list[str] = []

    def flush() -> ParsedVerse | None:
        if cur_verse_num is None or chapter is None or book_id is None:
            return None
        text = _clean_text(" ".join(cur_text))
        if not text:
            return None
        return ParsedVerse(
            book_id=book_id,
            chapter=chapter,
            verse=cur_verse_num,
            text=text,
            heading=cur_verse_heading,
            verse_alias=cur_verse_alias,
        )

    for raw_line in usfm_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("\\id"):
            m = _RE_ID.match(line)
            if not m:
                continue
            usfm_id = m.group(1).upper()
            if usfm_id in SKIPPED_USFM_IDS:
                return
            book_id = USFM_TO_BOOK_ID.get(usfm_id)
            if book_id is None:
                # Unknown book — skip silently. The manifest controls which
                # books we ship; raising here would break parsers that read
                # archives shipping more books than we want.
                return
            if book_id not in allowed_book_ids:
                return
            continue

        if (m := _RE_CHAPTER.match(line)):
            v = flush()
            if v is not None:
                yield v
            chapter = int(m.group(1))
            cur_verse_num = None
            cur_verse_alias = None
            cur_verse_heading = None
            cur_text = []
            pending_heading = None
            continue

        if (m := _RE_VERSE.match(line)):
            token, body = m.group(1), m.group(2)
            new_verse_num, new_alias = _verse_number(token)
            # USFM lets editions split a verse into fragments (``\\v 50``
            # then ``\\v 50a``). When the integer matches the open verse,
            # we merge the fragment into the current text instead of
            # creating a duplicate; the alias records the fragmented form.
            if cur_verse_num is not None and new_verse_num == cur_verse_num:
                cur_text.append(body)
                if new_alias and not cur_verse_alias:
                    cur_verse_alias = new_alias
                continue
            v = flush()
            if v is not None:
                yield v
            cur_verse_num = new_verse_num
            cur_verse_alias = new_alias
            cur_verse_heading = pending_heading
            pending_heading = None
            cur_text = [body]
            continue

        if (m := _RE_HEADING.match(line)):
            heading = _clean_text(m.group(1))
            if heading:
                pending_heading = heading
            continue

        if _RE_META_LINE.match(line):
            continue

        # Anything else is continuation of the current verse (including lines
        # that start with paragraph markers like ``\p`` followed by text).
        if cur_verse_num is not None:
            cur_text.append(line)

    v = flush()
    if v is not None:
        yield v


class _EbibleUsfmParser(BibleParser):
    """Parser that reads ebible.org-style USFM ZIP archives."""

    name = "ebible_usfm"

    def __init__(self, allowed_book_ids: set[str] | None = None) -> None:
        # Default: protestant 66 + extended (deuterocanonical). Per-Bible
        # filtering is done in ``catalog.py`` via ``CatalogEntry.book_ids``.
        if allowed_book_ids is None:
            from ..canon import load_full_canon

            allowed_book_ids = set(load_full_canon().keys())
        self.allowed_book_ids = allowed_book_ids

    def parse(self, source_path: Path) -> Iterable[ParsedVerse]:
        with zipfile.ZipFile(source_path, "r") as z:
            names = sorted(n for n in z.namelist() if n.lower().endswith(".usfm"))
            for name in names:
                with z.open(name) as f:
                    raw = f.read().decode("utf-8")
                buf = io.StringIO(raw)
                yield from _parse_book(buf.getvalue(), self.allowed_book_ids)


PARSER = _EbibleUsfmParser
