"""End-to-end build: download → parse → normalize → pack → verify → manifest."""

from __future__ import annotations

import importlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .canon import load_canon_66
from .catalog import CATALOG, CatalogEntry
from .download import fetch, sha256_of
from .normalize import normalize_books
from .pack import OUTPUT_DIR, PackInput, pack
from .parsers.base import BibleParser
from .verify import VerifyReport, verify

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "manifest" / "manifest.json"
MANIFEST_SCHEMA_VERSION = "1.1"
RELEASE_DOWNLOAD_BASE = (
    "https://github.com/berea-app/berea-textos-pd/releases/latest/download"
)


def _git_commit() -> str:
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return sha
    except Exception:
        return "uncommitted"


def _now_iso() -> str:
    if os.environ.get("BEREA_FAKE_NOW"):
        return os.environ["BEREA_FAKE_NOW"]
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()


def _load_parser(name: str, allowed_book_ids: set[str]) -> BibleParser:
    module = importlib.import_module(f"pipeline.parsers.{name}")
    cls = getattr(module, "PARSER", None)
    if cls is None:
        raise RuntimeError(f"parser module pipeline.parsers.{name} exposes no PARSER")
    return cls(allowed_book_ids=allowed_book_ids)


def build_one(bible_id: str) -> tuple[Path, VerifyReport]:
    if bible_id not in CATALOG:
        raise KeyError(f"unknown bible_id: {bible_id}")
    entry: CatalogEntry = CATALOG[bible_id]

    source_path = fetch(bible_id, entry.source_url, entry.source_filename)
    source_sha = sha256_of(source_path)

    parser = _load_parser(entry.parser, entry.effective_book_ids())
    verses = list(parser.parse(source_path))
    books = normalize_books(verses)

    out = pack(
        PackInput(
            bible_id=entry.bible_id,
            display_name=entry.display_name,
            language=entry.language,
            canon_family=entry.canon_family,
            license=entry.license,
            license_basis=entry.license_basis,
            source_url=entry.source_url,
            source_attribution=entry.source_attribution,
            attribution_required=entry.attribution_required,
            attribution_text=entry.attribution_text,
            parser=entry.parser,
            pipeline_commit=_git_commit(),
            source_sha256=source_sha,
            built_at=_now_iso(),
            books=books,
        )
    )
    report = verify(out, expected_canon_complete=entry.expected_canon_complete)
    return out, report


def regenerate_manifest() -> Path:
    """Rebuild manifest from CATALOG plus actual SHA-256/size of any built .bb."""
    bibles = []
    for bible_id, entry in CATALOG.items():
        bb_path = OUTPUT_DIR / f"{bible_id}.bb"
        if bb_path.exists():
            sha = sha256_of(bb_path)
            size = bb_path.stat().st_size
        else:
            sha, size = "TBD", 0
        bibles.append(
            {
                "attribution_required": entry.attribution_required,
                "attribution_text": entry.attribution_text,
                "bible_id": entry.bible_id,
                "bundled_in_apk": entry.bundled_in_apk,
                "canon_family": entry.canon_family,
                "category": entry.category,
                "display_name": entry.display_name,
                "download_url": f"{RELEASE_DOWNLOAD_BASE}/{entry.bible_id}.bb",
                "language": entry.language,
                "license": entry.license,
                "license_basis": entry.license_basis,
                "sha256": sha,
                "size_bytes": size,
                "source_attribution": entry.source_attribution,
                "source_url": entry.source_url,
            }
        )

    bibles.sort(key=lambda b: b["bible_id"])
    payload = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "updated_at": _now_iso(),
        "bibles": bibles,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return MANIFEST_PATH


def build_all() -> list[tuple[Path, VerifyReport]]:
    out = [build_one(b) for b in CATALOG]
    regenerate_manifest()
    # touch to ensure ordered canon list is reachable
    _ = load_canon_66()
    return out
