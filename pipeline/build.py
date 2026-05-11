"""End-to-end build: download → parse → normalize → pack → verify → manifest."""

from __future__ import annotations

import importlib
import json
import os
import subprocess
from datetime import UTC, datetime
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
MANIFEST_SCHEMA_VERSION = "1.3"
RELEASE_DOWNLOAD_BASE = (
    "https://github.com/berea-app/berea-textos-pd/releases/latest/download"
)
NUMBERING_ALIAS_PATH = REPO_ROOT / "canon" / "numbering_alias.json"


# ---------------------------------------------------------------------------
# Metadatos por target léxico / alineamiento (v1.5)
#
# La descripción legal (license_basis), categoría, attribution_required y
# license agregada del .bb viven acá — el .bb mismo solo lleva las atribuciones
# por fuente. El manifest los compone para la pantalla "Datos de léxico".
# ---------------------------------------------------------------------------


_LEXICON_MANIFEST_META: dict[str, dict] = {
    "lexicon_grc": {
        "category": "recomendado",
        "license": "mixed",
        "license_basis": (
            "Combina STEPBible Brief Lexicon for Greek (TBESG) bajo "
            "Creative Commons Attribution 4.0 con el Strong's Greek "
            "Dictionary (1890) en dominio público / CC0 vía OpenScriptures. "
            "La atribución a STEPBible / Tyndale House Cambridge es "
            "obligatoria."
        ),
        "attribution_required": True,
        "attribution_text": (
            "Léxico griego: STEPBible.org / Tyndale House Cambridge (CC BY 4.0) "
            "+ Strong's Greek Dictionary (1890, PD/CC0 vía OpenScriptures)."
        ),
        "bundled_in_apk": False,
    },
    "lexicon_grc_lsj": {
        "category": "avanzado",
        "license": "cc_by_4_0",
        "license_basis": (
            "Liddell-Scott-Jones Greek-English Lexicon en dominio público "
            "por antigüedad; el formateo del TFLSJ por Tyndale House / "
            "STEPBible.org se distribuye bajo Creative Commons Attribution "
            "4.0, con atribución obligatoria. Descarga opcional por su "
            "tamaño (~7.6 MB comprimido)."
        ),
        "attribution_required": True,
        "attribution_text": (
            "Léxico LSJ completo: Liddell-Scott-Jones (PD) formateado por "
            "STEPBible.org / Tyndale House Cambridge (CC BY 4.0)."
        ),
        "bundled_in_apk": False,
    },
    "lexicon_hbo": {
        "category": "recomendado",
        "license": "cc_by_4_0",
        "license_basis": (
            "Combina STEPBible Brief Lexicon for Hebrew (TBESH) y el "
            "Brown-Driver-Briggs Hebrew Lexicon (1906, dominio público) "
            "digitalizado por Open Scriptures Hebrew Bible. Ambas fuentes "
            "se distribuyen bajo Creative Commons Attribution 4.0; "
            "atribución obligatoria."
        ),
        "attribution_required": True,
        "attribution_text": (
            "Léxico hebreo: STEPBible.org / Tyndale House Cambridge "
            "(TBESH, CC BY 4.0) + Brown-Driver-Briggs (1906, PD; "
            "digitalización CC BY 4.0 por Open Scriptures Hebrew Bible)."
        ),
        "bundled_in_apk": False,
    },
}


_ALIGNMENT_MANIFEST_META: dict[str, dict] = {
    "alignment_grc_nt_wh": {
        "category": "original",
        "license": "cc_by_4_0",
        "license_basis": (
            "Alineamiento palabra-a-palabra del NT Westcott-Hort (1881, PD) "
            "extraído del corpus TAGNT de STEPBible.org / Tyndale House "
            "Cambridge. Distribuido bajo Creative Commons Attribution 4.0; "
            "atribución obligatoria."
        ),
        "attribution_required": True,
        "attribution_text": (
            "Alineamiento NT WH: STEPBible.org / Tyndale House Cambridge — "
            "TAGNT (CC BY 4.0)."
        ),
        "bundled_in_apk": False,
    },
    "alignment_grc_nt_tregelles": {
        "category": "original",
        "license": "cc_by_4_0",
        "license_basis": (
            "Alineamiento palabra-a-palabra del NT Tregelles (1879, ed. "
            "Jongkind 2009) extraído del corpus TAGNT de STEPBible.org / "
            "Tyndale House Cambridge. CC BY 4.0; atribución obligatoria."
        ),
        "attribution_required": True,
        "attribution_text": (
            "Alineamiento NT Tregelles: STEPBible.org / Tyndale House "
            "Cambridge — TAGNT (CC BY 4.0)."
        ),
        "bundled_in_apk": False,
    },
    "alignment_grc_nt_tr": {
        "category": "original",
        "license": "cc_by_4_0",
        "license_basis": (
            "Alineamiento palabra-a-palabra del NT Textus Receptus "
            "(Scrivener 1894, PD) extraído del corpus TAGNT de "
            "STEPBible.org / Tyndale House Cambridge. CC BY 4.0; "
            "atribución obligatoria."
        ),
        "attribution_required": True,
        "attribution_text": (
            "Alineamiento NT TR: STEPBible.org / Tyndale House Cambridge — "
            "TAGNT (CC BY 4.0)."
        ),
        "bundled_in_apk": False,
    },
    "alignment_hbo_ot_wlc": {
        "category": "original",
        "license": "cc_by_4_0",
        "license_basis": (
            "Alineamiento palabra-a-palabra del AT hebreo "
            "Leningrad + Qere (WLC moderno) extraído del corpus TAHOT de "
            "STEPBible.org / Tyndale House Cambridge. CC BY 4.0; "
            "atribución obligatoria."
        ),
        "attribution_required": True,
        "attribution_text": (
            "Alineamiento AT WLC: STEPBible.org / Tyndale House Cambridge — "
            "TAHOT (CC BY 4.0)."
        ),
        "bundled_in_apk": False,
    },
}


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
    return datetime.now(UTC).astimezone().replace(microsecond=0).isoformat()


def _load_parser(
    name: str,
    allowed_book_ids: set[str],
    parser_config: dict[str, str],
) -> BibleParser:
    module = importlib.import_module(f"pipeline.parsers.{name}")
    cls = getattr(module, "PARSER", None)
    if cls is None:
        raise RuntimeError(f"parser module pipeline.parsers.{name} exposes no PARSER")
    try:
        return cls(allowed_book_ids=allowed_book_ids, **parser_config)
    except TypeError:
        # Parsers that don't accept extra kwargs.
        return cls(allowed_book_ids=allowed_book_ids)


def build_one(bible_id: str) -> tuple[Path, VerifyReport]:
    if bible_id not in CATALOG:
        raise KeyError(f"unknown bible_id: {bible_id}")
    entry: CatalogEntry = CATALOG[bible_id]

    source_path = fetch(bible_id, entry.source_url, entry.source_filename)
    for extra_url, extra_filename in entry.extra_sources:
        fetch(bible_id, extra_url, extra_filename)
    source_sha = sha256_of(source_path)

    parser_config = dict(entry.parser_config)
    parser = _load_parser(entry.parser, entry.effective_book_ids(), parser_config)
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


def _source_for_manifest(source: dict) -> dict:
    """Reduce el dict ``LexiconSource``/``AlignmentSource`` del .bb a los
    campos que el manifest expone. Descarta ``source_sha256`` (detalle de
    trazabilidad interno; no es útil en la UI de la app)."""
    return {
        "id": source["id"],
        "name": source["name"],
        "license": source["license"],
        "attribution": source["attribution"],
        "source_url": source["source_url"],
    }


def _build_lexicons_array() -> list[dict]:
    """Genera el array ``lexicons[]`` del manifest leyendo los .bb existentes
    en ``output/``. Si un target no fue construido todavía, su sha/size son
    ``"TBD"`` / ``0`` (mismo patrón que ``bibles[]``)."""
    from .lexicon.build import LEXICON_TARGETS
    from .lexicon.pack import OUTPUT_DIR as LEX_OUTPUT_DIR
    from .lexicon.pack import read_lexicon_bb

    out: list[dict] = []
    for data_id, target in LEXICON_TARGETS.items():
        meta = _LEXICON_MANIFEST_META.get(data_id)
        if meta is None:
            raise RuntimeError(
                f"_LEXICON_MANIFEST_META falta entrada para {data_id!r}"
            )
        bb_path = LEX_OUTPUT_DIR / f"{data_id}.bb"
        if bb_path.exists():
            sha = sha256_of(bb_path)
            size = bb_path.stat().st_size
            payload = read_lexicon_bb(bb_path)
            sources = [_source_for_manifest(s) for s in payload["sources"]]
        else:
            sha, size = "TBD", 0
            # Sin .bb no podemos enumerar las fuentes reales — dejamos una
            # entry mínima derivada del attribution_text del meta para que
            # la app no rompa si valida estrictamente.
            sources = [
                {
                    "id": "pending",
                    "name": "(pendiente de build)",
                    "license": "unknown",
                    "attribution": meta["attribution_text"],
                    "source_url": "https://github.com/berea-app/berea-textos-pd",
                }
            ]
        out.append(
            {
                "attribution_required": meta["attribution_required"],
                "attribution_text": meta["attribution_text"],
                "bundled_in_apk": meta["bundled_in_apk"],
                "category": meta["category"],
                "data_id": data_id,
                "display_name": target.display_name,
                "download_url": f"{RELEASE_DOWNLOAD_BASE}/{data_id}.bb",
                "language": target.language,
                "license": meta["license"],
                "license_basis": meta["license_basis"],
                "sha256": sha,
                "size_bytes": size,
                "sources": sources,
            }
        )
    out.sort(key=lambda e: e["data_id"])
    return out


def _build_alignments_array() -> list[dict]:
    """Genera el array ``alignments[]`` del manifest leyendo los .bb existentes."""
    from .lexicon.build import ALIGNMENT_TARGETS
    from .lexicon.pack import OUTPUT_DIR as LEX_OUTPUT_DIR
    from .lexicon.pack import read_alignment_bb

    out: list[dict] = []
    for data_id, target in ALIGNMENT_TARGETS.items():
        meta = _ALIGNMENT_MANIFEST_META.get(data_id)
        if meta is None:
            raise RuntimeError(
                f"_ALIGNMENT_MANIFEST_META falta entrada para {data_id!r}"
            )
        bb_path = LEX_OUTPUT_DIR / f"{data_id}.bb"
        if bb_path.exists():
            sha = sha256_of(bb_path)
            size = bb_path.stat().st_size
            payload = read_alignment_bb(bb_path)
            source = _source_for_manifest(payload["source"])
        else:
            sha, size = "TBD", 0
            source = {
                "id": "pending",
                "name": "(pendiente de build)",
                "license": "unknown",
                "attribution": meta["attribution_text"],
                "source_url": "https://github.com/berea-app/berea-textos-pd",
            }
        out.append(
            {
                "attribution_required": meta["attribution_required"],
                "attribution_text": meta["attribution_text"],
                "bible_id": target.bible_id,
                "bundled_in_apk": meta["bundled_in_apk"],
                "category": meta["category"],
                "data_id": data_id,
                "display_name": target.display_name,
                "download_url": f"{RELEASE_DOWNLOAD_BASE}/{data_id}.bb",
                "language": target.language,
                "license": meta["license"],
                "license_basis": meta["license_basis"],
                "sha256": sha,
                "size_bytes": size,
                "source": source,
                "testament": target.testament,
            }
        )
    out.sort(key=lambda e: e["data_id"])
    return out


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
        bible_entry = {
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
        if entry.numbering_scheme is not None:
            bible_entry["numbering_scheme"] = entry.numbering_scheme
        bibles.append(bible_entry)

    bibles.sort(key=lambda b: b["bible_id"])

    # Numbering alias dataset is published alongside the manifest as a
    # separate release asset. The manifest carries its sha256/size so the
    # app can verify the integrity of the file it downloads.
    numbering_alias_meta: dict | None = None
    if NUMBERING_ALIAS_PATH.exists():
        alias_bytes = NUMBERING_ALIAS_PATH.read_bytes()
        numbering_alias_meta = {
            "download_url": (
                f"{RELEASE_DOWNLOAD_BASE}/{NUMBERING_ALIAS_PATH.name}"
            ),
            "sha256": sha256_of(NUMBERING_ALIAS_PATH),
            "size_bytes": len(alias_bytes),
        }

    payload: dict = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "updated_at": _now_iso(),
        "bibles": bibles,
        "lexicons": _build_lexicons_array(),
        "alignments": _build_alignments_array(),
    }
    if numbering_alias_meta is not None:
        payload["numbering_alias"] = numbering_alias_meta
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
