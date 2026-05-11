"""Empaqueta entries léxicas en archivos ``.bb`` deterministas (gzipped JSON).

Distinto de ``pipeline/pack.py`` (que empaqueta Biblias) en dos puntos clave:

- **Schema diferente**: payload ``{"type": "lexicon", "entries": [...]}`` con
  array de sources y atribuciones explícitas por fuente (TBESG vs Strong's vs
  LSJ vs BDB). La app distingue al renderizar el bottom sheet léxico.
- **Tamaño mayor**: las definiciones LSJ son enormes (median ~1.6 KB, p95
  ~13 KB), así que el .bb crudo puede llegar a 25 MB sin comprimir. Mantenemos
  gzip level 9 (mismo que Biblias) — comprime ~4×, pero el .bb resultante es
  igual la pieza más grande del corpus.

Reglas de determinismo (heredadas de ``pipeline/pack.py``):

- ``json.dumps(..., sort_keys=True, ensure_ascii=False, separators=(",", ":"))``.
- ``gzip.GzipFile(mtime=0, compresslevel=9)``.
- Entries ordenadas por ``(strong_base, strong_extended, source, lemma)`` —
  determinista y estable cross-build, sin depender del orden de inserción.
- Strings normalizados a **NFC** (griego politónico colapsa formas Greek
  Extended y Standard a una sola, simplificando lookup en la app).
"""

from __future__ import annotations

import gzip
import io
import json
import unicodedata
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from .parse_alignment_tagnt import WordAlignment
from .parse_tbes import BriefLexiconEntry

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "output"
BB_LEXICON_SCHEMA_VERSION = "1.0"
BB_ALIGNMENT_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class LexiconSource:
    """Una fuente que contribuye entries al lexicón empaquetado.

    Aparece en el header del .bb como elemento del array ``sources``. La app
    usa esta lista para construir la atribución del bottom sheet."""

    id: str                  # "stepbible" / "strongs" / "bdb" / "lsj"
    name: str                # legible en UI
    license: str             # "CC BY 4.0" / "public_domain" / "CC0"
    attribution: str         # texto exacto a mostrar
    source_url: str          # URL del repo upstream
    source_sha256: dict[str, str]  # {filename → sha256}


@dataclass(frozen=True)
class LexiconPackInput:
    """Conjunto de parámetros para empaquetar un .bb de lexicón."""

    data_id: str             # "lexicon_grc" / "lexicon_grc_lsj" / "lexicon_hbo"
    language: str            # "grc" / "hbo"
    display_name: str
    sources: list[LexiconSource]
    entries: list[BriefLexiconEntry]
    pipeline_commit: str     # SHA del repo berea-textos-pd al build
    built_at: str            # ISO 8601 con offset


def _nfc(s: str | None) -> str | None:
    if s is None:
        return None
    return unicodedata.normalize("NFC", s)


def _entry_to_dict(e: BriefLexiconEntry) -> dict:
    """Serializa una entry a dict normalizando Unicode. Omite campos ``None``
    para reducir el tamaño del JSON (la app reconstruye con defaults)."""
    out: dict[str, object] = {
        "strong_base": e.strong_base,
        "strong_extended": e.strong_extended,
        "lemma": _nfc(e.lemma),
        "gloss_brief": _nfc(e.gloss_brief),
        "language": e.language,
        "source": e.source,
    }
    if e.transliteration:
        out["transliteration"] = _nfc(e.transliteration)
    if e.morph:
        out["morph"] = e.morph
    if e.definition_full:
        out["definition_full"] = _nfc(e.definition_full)
    return out


def _entry_sort_key(e: BriefLexiconEntry) -> tuple:
    """Orden determinista. ``strong_base`` se ordena por (prefijo, número)
    para que ``G2`` < ``G10`` < ``G100`` (no alfabético)."""
    base = e.strong_base
    prefix = base[0]
    num = int(base[1:]) if base[1:].isdigit() else 0
    return (prefix, num, e.strong_extended, e.source, e.lemma)


def build_lexicon_payload(p: LexiconPackInput) -> dict:
    """Construye el dict del payload .bb (antes de JSON+gzip).

    Validación mínima: ``data_id`` no vacío, ``entries`` no vacío, todas las
    entries del mismo ``language``. Inconsistencias acá son bugs del build
    script, queremos fallar ruidoso."""
    if not p.data_id:
        raise ValueError("data_id requerido")
    if not p.entries:
        raise ValueError("entries no puede estar vacío")
    langs = {e.language for e in p.entries}
    if langs != {p.language}:
        raise ValueError(
            f"entries con language(s) {langs} no coinciden con "
            f"LexiconPackInput.language={p.language!r}"
        )

    sorted_entries = sorted(p.entries, key=_entry_sort_key)

    return {
        "build_info": {
            "built_at": p.built_at,
            "pipeline_commit": p.pipeline_commit,
        },
        "data_id": p.data_id,
        "display_name": p.display_name,
        "entries": [_entry_to_dict(e) for e in sorted_entries],
        "entry_count": len(sorted_entries),
        "language": p.language,
        "schema_version": BB_LEXICON_SCHEMA_VERSION,
        "sources": [asdict(s) for s in p.sources],
        "type": "lexicon",
    }


def pack_lexicon(p: LexiconPackInput, output_dir: Path | None = None) -> Path:
    """Empaqueta el lexicón a ``{output_dir}/{data_id}.bb`` (gzip JSON).

    Determinismo: dos builds con el mismo input producen archivos byte a
    byte idénticos. Si no, hay bug en sort_keys / mtime / sort_key."""
    out_dir = output_dir or OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{p.data_id}.bb"

    payload = build_lexicon_payload(p)
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


def read_lexicon_bb(path: Path) -> dict:
    """Lee un .bb de lexicón previamente empaquetado. Útil para tests
    round-trip y para herramientas de diagnóstico."""
    with gzip.open(path, "rb") as gz:
        return json.loads(gz.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Helpers de unión multi-fuente
# ---------------------------------------------------------------------------


def merge_entries(*streams: Iterable[BriefLexiconEntry]) -> list[BriefLexiconEntry]:
    """Junta múltiples streams de entries en una lista única.

    No deduplica — múltiples fuentes para el mismo Strong's son intencionales
    (la app las muestra como cards separadas en el bottom sheet con su
    atribución). El orden de salida no importa porque ``pack_lexicon`` lo
    re-ordena por ``_entry_sort_key`` antes de serializar."""
    out: list[BriefLexiconEntry] = []
    for stream in streams:
        out.extend(stream)
    return out


# ===========================================================================
# Empaquetado de archivos de ALINEAMIENTO (TAGNT / TAHOT por edición)
# ===========================================================================


@dataclass(frozen=True)
class AlignmentSource:
    """Fuente que contribuye al alineamiento. Típicamente una sola por .bb
    (a diferencia del lexicón que combina varias)."""

    id: str                          # "tagnt" / "tahot"
    name: str                        # legible en UI
    license: str
    attribution: str
    source_url: str
    source_sha256: dict[str, str]    # {filename → sha256}


@dataclass(frozen=True)
class AlignmentPackInput:
    """Parámetros para empaquetar un .bb de alineamiento por edición."""

    data_id: str                     # "alignment_grc_nt_wh", "alignment_hbo_ot", ...
    language: str                    # "grc" / "hbo"
    testament: str                   # "nt" / "ot"
    bible_id: str                    # bible_id Berea al que aplica
    display_name: str
    source: AlignmentSource
    alignments: list[WordAlignment]
    pipeline_commit: str
    built_at: str


def _alignment_to_dict(a: WordAlignment) -> dict:
    """Serializa una WordAlignment. Omite campos None para reducir tamaño."""
    out: dict[str, object] = {
        "book_id": a.book_id,
        "chapter": a.chapter,
        "verse": a.verse,
        "position": a.position,
        "word_original": _nfc(a.word_original),
    }
    if a.transliteration:
        out["transliteration"] = _nfc(a.transliteration)
    if a.lemma:
        out["lemma"] = _nfc(a.lemma)
    if a.strong_extended:
        out["strong"] = a.strong_extended
    if a.morph:
        out["morph"] = a.morph
    if a.gloss:
        out["gloss"] = _nfc(a.gloss)
    return out


# Orden canónico de libros del NT/AT por book_id Berea — duplicado del canon
# pero codificado para evitar leer el JSON en cada sort.
_BOOK_ORDER = {
    # AT
    "gen": 1, "exo": 2, "lev": 3, "num": 4, "deu": 5,
    "jos": 6, "jdg": 7, "rut": 8, "1sa": 9, "2sa": 10,
    "1ki": 11, "2ki": 12, "1ch": 13, "2ch": 14,
    "ezr": 15, "neh": 16, "est": 17,
    "job": 18, "psa": 19, "pro": 20, "ecc": 21, "sng": 22,
    "isa": 23, "jer": 24, "lam": 25, "ezk": 26, "dan": 27,
    "hos": 28, "jol": 29, "amo": 30, "oba": 31, "jon": 32,
    "mic": 33, "nam": 34, "hab": 35, "zep": 36,
    "hag": 37, "zec": 38, "mal": 39,
    # NT
    "mat": 40, "mrk": 41, "luk": 42, "jhn": 43, "act": 44,
    "rom": 45, "1co": 46, "2co": 47, "gal": 48, "eph": 49,
    "php": 50, "col": 51, "1th": 52, "2th": 53,
    "1ti": 54, "2ti": 55, "tit": 56, "phm": 57,
    "heb": 58, "jas": 59, "1pe": 60, "2pe": 61,
    "1jn": 62, "2jn": 63, "3jn": 64, "jud": 65, "rev": 66,
}


def _alignment_sort_key(a: WordAlignment) -> tuple:
    return (_BOOK_ORDER.get(a.book_id, 999), a.chapter, a.verse, a.position)


def build_alignment_payload(p: AlignmentPackInput) -> dict:
    if not p.data_id:
        raise ValueError("data_id requerido")
    if not p.alignments:
        raise ValueError("alignments no puede estar vacío")
    if p.testament not in ("nt", "ot"):
        raise ValueError(f"testament debe ser 'nt' o 'ot', no {p.testament!r}")

    sorted_aligns = sorted(p.alignments, key=_alignment_sort_key)

    return {
        "alignments": [_alignment_to_dict(a) for a in sorted_aligns],
        "bible_id": p.bible_id,
        "build_info": {
            "built_at": p.built_at,
            "pipeline_commit": p.pipeline_commit,
        },
        "data_id": p.data_id,
        "display_name": p.display_name,
        "entry_count": len(sorted_aligns),
        "language": p.language,
        "schema_version": BB_ALIGNMENT_SCHEMA_VERSION,
        "source": asdict(p.source),
        "testament": p.testament,
        "type": "alignment",
    }


def pack_alignment(p: AlignmentPackInput, output_dir: Path | None = None) -> Path:
    """Empaqueta el alineamiento a ``{output_dir}/{data_id}.bb`` (gzip JSON
    determinista). Mismo contrato que ``pack_lexicon``."""
    out_dir = output_dir or OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{p.data_id}.bb"

    payload = build_alignment_payload(p)
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


def read_alignment_bb(path: Path) -> dict:
    """Lee un .bb de alineamiento. Útil para tests round-trip."""
    with gzip.open(path, "rb") as gz:
        return json.loads(gz.read().decode("utf-8"))
