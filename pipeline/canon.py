"""Canonical book identifiers loaded from canon/*.json.

These are shared with the Berea Android app. Both repositories ship the same
JSON files; the duplication is intentional and enforced by CI.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

CANON_DIR = Path(__file__).resolve().parent.parent / "canon"


@dataclass(frozen=True)
class CanonBook:
    book_id: str
    order: int | None
    testament: str | None
    section: str | None
    name_es: str
    name_en: str
    abbr_es: str
    chapters: int
    aliases: tuple[str, ...] = field(default_factory=tuple)
    parent_book_id: str | None = None
    canon_families: tuple[str, ...] = field(default_factory=tuple)
    numbering_note: str | None = None


def _from_json(entry: dict, *, extended: bool) -> CanonBook:
    return CanonBook(
        book_id=entry["book_id"],
        order=entry.get("order"),
        testament=entry.get("testament"),
        section=entry.get("section"),
        name_es=entry["name_es"],
        name_en=entry["name_en"],
        abbr_es=entry.get("abbr_es", ""),
        chapters=int(entry.get("chapters", 0)),
        aliases=tuple(entry.get("aliases", [])),
        parent_book_id=entry.get("parent_book_id"),
        canon_families=tuple(entry.get("canon_families", [])),
        numbering_note=entry.get("numbering_note"),
    )


def load_canon_66() -> list[CanonBook]:
    data = json.loads((CANON_DIR / "canon_66.json").read_text(encoding="utf-8"))
    books = data["books"] if isinstance(data, dict) and "books" in data else data
    out = [_from_json(b, extended=False) for b in books]
    if len(out) != 66:
        raise ValueError(f"canon_66.json must contain 66 books, got {len(out)}")
    return sorted(out, key=lambda b: b.order or 0)


def load_canon_extendido() -> list[CanonBook]:
    path = CANON_DIR / "canon_extendido.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    books = data["books"] if isinstance(data, dict) and "books" in data else data
    return [_from_json(b, extended=True) for b in books]


def load_full_canon() -> dict[str, CanonBook]:
    """Return {book_id: CanonBook} merging canon 66 and extended."""
    out: dict[str, CanonBook] = {}
    for b in load_canon_66() + load_canon_extendido():
        if b.book_id in out:
            raise ValueError(f"duplicate book_id across canon files: {b.book_id}")
        out[b.book_id] = b
    return out


def aliases_to_book_id() -> dict[str, str]:
    """Lookup map from any known alias (uppercase USFM, OSIS, name, abbr) to
    canonical lowercase USFM book_id."""
    full = load_full_canon()
    table: dict[str, str] = {}
    for book_id, book in full.items():
        keys: Iterable[str] = (
            book_id,
            book_id.upper(),
            book.name_es,
            book.name_es.lower(),
            book.name_en,
            book.name_en.lower(),
            book.abbr_es,
            *book.aliases,
        )
        for k in keys:
            if not k:
                continue
            table[k] = book_id
            table[k.upper()] = book_id
            table[k.lower()] = book_id
    return table
