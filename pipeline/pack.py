"""Pack normalized books into a deterministic ``.bb`` (gzipped JSON).

Determinism rules (see docs/format_bb.md):
- ``json.dumps(..., sort_keys=True, ensure_ascii=False, separators=(",", ":"))``
- ``gzip.GzipFile(mtime=0, compresslevel=9)``
- UTF-8, no BOM, no trailing newline.
"""

from __future__ import annotations

import gzip
import io
import json
from dataclasses import dataclass
from pathlib import Path

from .normalize import NormalizedBook

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
BB_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class PackInput:
    bible_id: str
    display_name: str
    language: str
    canon_family: str
    license: str
    license_basis: str
    source_url: str
    source_attribution: str
    attribution_required: bool
    attribution_text: str
    parser: str
    pipeline_commit: str
    source_sha256: str
    built_at: str
    books: list[NormalizedBook]


def _book_to_dict(b: NormalizedBook) -> dict:
    return {
        "abbreviation": b.abbreviation,
        "book_id": b.book_id,
        "chapters": [
            {
                "chapter": ch.chapter,
                "verses": [
                    _verse_to_dict(v) for v in ch.verses
                ],
            }
            for ch in b.chapters
        ],
        "display_name": b.display_name,
        "position": b.position,
    }


def _verse_to_dict(v) -> dict:
    out = {"text": v.text, "verse": v.verse}
    if v.heading:
        out["heading"] = v.heading
    if v.verse_alias:
        out["verse_alias"] = v.verse_alias
    return out


def build_bb_payload(p: PackInput) -> dict:
    return {
        "attribution_required": p.attribution_required,
        "attribution_text": p.attribution_text,
        "bible_id": p.bible_id,
        "books": [_book_to_dict(b) for b in p.books],
        "build_info": {
            "built_at": p.built_at,
            "parser": p.parser,
            "pipeline_commit": p.pipeline_commit,
            "source_sha256": p.source_sha256,
        },
        "canon_family": p.canon_family,
        "display_name": p.display_name,
        "language": p.language,
        "license": p.license,
        "license_basis": p.license_basis,
        "schema_version": BB_SCHEMA_VERSION,
        "source_attribution": p.source_attribution,
        "source_url": p.source_url,
    }


def pack(p: PackInput) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{p.bible_id}.bb"
    payload = build_bb_payload(p)
    raw = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0, compresslevel=9) as gz:
        gz.write(raw)
    out_path.write_bytes(buf.getvalue())
    return out_path
