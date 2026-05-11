"""Orquestador del build de archivos ``.bb`` léxicos para v1.5.

Produce tres archivos:

- ``lexicon_grc.bb``: griego default (TBESG + Strong's Greek). ~5-6 MB.
- ``lexicon_grc_lsj.bb``: griego avanzado (TFLSJ). ~20 MB. Descarga opcional.
- ``lexicon_hbo.bb``: hebreo (TBESH + BDB). ~6-8 MB.

La decisión de tener LSJ como descarga separada se discutió post-P.4 y se
documentó en PROGRESO.md.

Cada build invoca los parsers correspondientes, los unifica con
``merge_entries``, y emite el ``.bb`` determinista. Los SHAs de los archivos
fuente quedan registrados en el header del .bb para trazabilidad.

Convención de invocación: ``python -m pipeline.lexicon.build [data_id]``
(sin argumento, construye los tres).
"""

from __future__ import annotations

import argparse
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ..download import sha256_of
from .pack import (
    OUTPUT_DIR,
    AlignmentPackInput,
    AlignmentSource,
    LexiconPackInput,
    LexiconSource,
    merge_entries,
    pack_alignment,
    pack_lexicon,
)
from .parse_alignment_tagnt import parse_tagnt_alignment
from .parse_alignment_tahot import parse_tahot_alignment
from .parse_bdb import parse_bdb_files
from .parse_strongs_greek import parse_strongs_greek_file
from .parse_tbes import parse_tbes_file
from .parse_tflsj import parse_tflsj_file

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCES_DIR = REPO_ROOT / "sources"


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return "uncommitted"


def _now_iso() -> str:
    if os.environ.get("BEREA_FAKE_NOW"):
        return os.environ["BEREA_FAKE_NOW"]
    return datetime.now(UTC).astimezone().replace(microsecond=0).isoformat()


# ---------------------------------------------------------------------------
# Atribuciones canónicas de las fuentes
# ---------------------------------------------------------------------------

# Estas constantes son las atribuciones EXACTAS que la app va a mostrar en
# el bottom sheet léxico (footer "Fuentes: ..."). Si una upstream cambia su
# nombre o licencia, ajustamos acá y rebuildeamos.

_STEPBIBLE_SOURCE_URL = "https://github.com/STEPBible/STEPBible-Data"
_STEPBIBLE_LICENSE = "CC BY 4.0"
_STEPBIBLE_ATTRIBUTION = (
    "STEPBible.org / Tyndale House Cambridge — usado bajo CC BY 4.0"
)

_OPENSCRIPTURES_GREEK_URL = "https://github.com/openscriptures/strongs"
_OPENSCRIPTURES_HEBREW_URL = "https://github.com/openscriptures/HebrewLexicon"
_STRONGS_LICENSE = "CC0 (public_domain)"
_STRONGS_ATTRIBUTION = (
    "Strong's Greek Dictionary (1890) — dominio público; "
    "digitalización CC0 por OpenScriptures.org"
)
_BDB_LICENSE = "CC BY 4.0"
_BDB_ATTRIBUTION = (
    "Brown-Driver-Briggs Hebrew Lexicon (1906) — dominio público; "
    "digitalización CC BY 4.0 por Open Scriptures Hebrew Bible Project"
)


def _sha_of_sources(*paths: Path) -> dict[str, str]:
    """SHA-256 de los archivos fuente que el build consume. Si un archivo
    falta, lanza FileNotFoundError — fallar ruidoso es lo correcto acá."""
    return {p.name: sha256_of(p) for p in paths}


# ---------------------------------------------------------------------------
# Configuración por target
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LexiconTarget:
    data_id: str
    language: str
    display_name: str
    # Función que recibe SOURCES_DIR y retorna (entries, sources).
    build_fn: Callable[[Path], tuple[list, list[LexiconSource]]]


def _build_grc_default(sources_dir: Path) -> tuple[list, list[LexiconSource]]:
    """``lexicon_grc.bb``: TBESG + Strong's Greek."""
    tbesg = sources_dir / "stepbible_lexicon" / "TBESG.txt"
    strongs = sources_dir / "openscriptures_greek" / "strongs-greek-dictionary.js"

    entries = merge_entries(
        parse_tbes_file(tbesg, "grc", source="stepbible"),
        parse_strongs_greek_file(strongs),
    )
    sources = [
        LexiconSource(
            id="stepbible",
            name="STEPBible Brief Lexicon for Greek (TBESG)",
            license=_STEPBIBLE_LICENSE,
            attribution=_STEPBIBLE_ATTRIBUTION,
            source_url=_STEPBIBLE_SOURCE_URL,
            source_sha256=_sha_of_sources(tbesg),
        ),
        LexiconSource(
            id="strongs",
            name="Strong's Greek Dictionary (1890, PD)",
            license=_STRONGS_LICENSE,
            attribution=_STRONGS_ATTRIBUTION,
            source_url=_OPENSCRIPTURES_GREEK_URL,
            source_sha256=_sha_of_sources(strongs),
        ),
    ]
    return entries, sources


def _build_grc_lsj(sources_dir: Path) -> tuple[list, list[LexiconSource]]:
    """``lexicon_grc_lsj.bb``: TFLSJ completo (base + extra)."""
    base = sources_dir / "stepbible_lexicon" / "TFLSJ_0-5624.txt"
    extra = sources_dir / "stepbible_lexicon" / "TFLSJ_extra.txt"

    entries = merge_entries(parse_tflsj_file(base), parse_tflsj_file(extra))
    sources = [
        LexiconSource(
            id="lsj",
            name="Liddell-Scott-Jones Full Bible Lexicon (TFLSJ)",
            license=_STEPBIBLE_LICENSE,
            attribution=(
                "Liddell-Scott-Jones Greek-English Lexicon — dominio público; "
                "formateado por Tyndale House / STEPBible.org bajo CC BY 4.0"
            ),
            source_url=_STEPBIBLE_SOURCE_URL,
            source_sha256=_sha_of_sources(base, extra),
        ),
    ]
    return entries, sources


def _build_hbo(sources_dir: Path) -> tuple[list, list[LexiconSource]]:
    """``lexicon_hbo.bb``: TBESH + BDB."""
    tbesh = sources_dir / "stepbible_lexicon" / "TBESH.txt"
    bdb = sources_dir / "openscriptures_hebrew" / "BrownDriverBriggs.xml"
    lex_idx = sources_dir / "openscriptures_hebrew" / "LexicalIndex.xml"

    entries = merge_entries(
        parse_tbes_file(tbesh, "hbo", source="stepbible"),
        parse_bdb_files(bdb, lex_idx),
    )
    sources = [
        LexiconSource(
            id="stepbible",
            name="STEPBible Brief Lexicon for Hebrew (TBESH)",
            license=_STEPBIBLE_LICENSE,
            attribution=_STEPBIBLE_ATTRIBUTION,
            source_url=_STEPBIBLE_SOURCE_URL,
            source_sha256=_sha_of_sources(tbesh),
        ),
        LexiconSource(
            id="bdb",
            name="Brown-Driver-Briggs Hebrew Lexicon (1906, PD)",
            license=_BDB_LICENSE,
            attribution=_BDB_ATTRIBUTION,
            source_url=_OPENSCRIPTURES_HEBREW_URL,
            source_sha256=_sha_of_sources(bdb, lex_idx),
        ),
    ]
    return entries, sources


# ---------------------------------------------------------------------------
# Targets de alineamiento (P.6+)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AlignmentTarget:
    data_id: str
    language: str
    testament: str
    bible_id: str
    display_name: str
    # edition de TAGNT/TAHOT: "WH", "Treg", "TR", etc.
    edition: str


# Las 3 ediciones del NT griego que tienen Biblia en el catálogo Berea:
#   - WH       → bible_id "wh"        (Westcott-Hort 1881)
#   - Treg     → bible_id "tregelles" (Tregelles 1879)
#   - TR       → bible_id "tr"        (Scrivener 1894 / Textus Receptus)
# Nestle 1904 NO está en TAGNT, así que su Biblia no recibe alineamiento en
# v1.5. Si el usuario quiere interlineal/léxico, debe activar una de las 3
# ediciones soportadas como Biblia primaria.
_TAGNT_PATHS = [
    SOURCES_DIR / "stepbible_tagnt" / "TAGNT_Mat-Jhn.txt",
    SOURCES_DIR / "stepbible_tagnt" / "TAGNT_Act-Rev.txt",
]

_TAHOT_PATHS = [
    SOURCES_DIR / "stepbible_tahot" / "TAHOT_Gen-Deu.txt",
    SOURCES_DIR / "stepbible_tahot" / "TAHOT_Jos-Est.txt",
    SOURCES_DIR / "stepbible_tahot" / "TAHOT_Job-Sng.txt",
    SOURCES_DIR / "stepbible_tahot" / "TAHOT_Isa-Mal.txt",
]


def _build_alignment_grc_nt(target: AlignmentTarget) -> tuple[list, AlignmentSource]:
    """Construye un alineamiento NT griego para una edición específica."""
    alignments = list(parse_tagnt_alignment(_TAGNT_PATHS, target.edition))
    source = AlignmentSource(
        id="tagnt",
        name=f"TAGNT — Translators Amalgamated Greek NT ({target.edition})",
        license=_STEPBIBLE_LICENSE,
        attribution=_STEPBIBLE_ATTRIBUTION,
        source_url=_STEPBIBLE_SOURCE_URL,
        source_sha256=_sha_of_sources(*_TAGNT_PATHS),
    )
    return alignments, source


def _build_alignment_hbo_ot(target: AlignmentTarget) -> tuple[list, AlignmentSource]:
    """Construye el alineamiento AT hebreo (Leningrad + Qere).

    A diferencia del NT (3 ediciones), TAHOT emite una sola "edición" que
    se mapea al WLC del catálogo Berea. El parámetro ``edition`` del target
    se ignora — está acá solo por simetría con el grc."""
    alignments = list(parse_tahot_alignment(_TAHOT_PATHS))
    source = AlignmentSource(
        id="tahot",
        name="TAHOT — Translators Amalgamated Hebrew OT (Leningrad + Qere)",
        license=_STEPBIBLE_LICENSE,
        attribution=_STEPBIBLE_ATTRIBUTION,
        source_url=_STEPBIBLE_SOURCE_URL,
        source_sha256=_sha_of_sources(*_TAHOT_PATHS),
    )
    return alignments, source


ALIGNMENT_TARGETS: dict[str, AlignmentTarget] = {
    "alignment_grc_nt_wh": AlignmentTarget(
        data_id="alignment_grc_nt_wh",
        language="grc",
        testament="nt",
        bible_id="wh",
        display_name="Alineamiento NT griego — Westcott-Hort (1881)",
        edition="WH",
    ),
    "alignment_grc_nt_tregelles": AlignmentTarget(
        data_id="alignment_grc_nt_tregelles",
        language="grc",
        testament="nt",
        bible_id="tregelles",
        display_name="Alineamiento NT griego — Tregelles (1879)",
        edition="Treg",
    ),
    "alignment_grc_nt_tr": AlignmentTarget(
        data_id="alignment_grc_nt_tr",
        language="grc",
        testament="nt",
        bible_id="tr",
        display_name="Alineamiento NT griego — Textus Receptus (Scrivener 1894)",
        edition="TR",
    ),
    "alignment_hbo_ot_wlc": AlignmentTarget(
        data_id="alignment_hbo_ot_wlc",
        language="hbo",
        testament="ot",
        bible_id="wlc",
        display_name="Alineamiento AT hebreo — Westminster Leningrad Codex",
        # TAHOT no distingue ediciones; este campo queda como marcador
        # ("WLC" no es un identificador de TAGNT, no se pasa al parser).
        edition="WLC",
    ),
}


LEXICON_TARGETS: dict[str, LexiconTarget] = {
    "lexicon_grc": LexiconTarget(
        data_id="lexicon_grc",
        language="grc",
        display_name="Léxico griego (TBESG + Strong's)",
        build_fn=_build_grc_default,
    ),
    "lexicon_grc_lsj": LexiconTarget(
        data_id="lexicon_grc_lsj",
        language="grc",
        display_name="Léxico griego LSJ completo (avanzado)",
        build_fn=_build_grc_lsj,
    ),
    "lexicon_hbo": LexiconTarget(
        data_id="lexicon_hbo",
        language="hbo",
        display_name="Léxico hebreo (TBESH + BDB)",
        build_fn=_build_hbo,
    ),
}


# ---------------------------------------------------------------------------
# Entrypoints
# ---------------------------------------------------------------------------


def build_lexicon(data_id: str, output_dir: Path | None = None) -> Path:
    """Construye un .bb de lexicón. ``data_id`` debe estar en
    ``LEXICON_TARGETS``."""
    if data_id not in LEXICON_TARGETS:
        raise ValueError(
            f"data_id {data_id!r} desconocido; opciones: {list(LEXICON_TARGETS)}"
        )
    target = LEXICON_TARGETS[data_id]
    entries, sources = target.build_fn(SOURCES_DIR)
    pack_input = LexiconPackInput(
        data_id=target.data_id,
        language=target.language,
        display_name=target.display_name,
        sources=sources,
        entries=entries,
        pipeline_commit=_git_commit(),
        built_at=_now_iso(),
    )
    return pack_lexicon(pack_input, output_dir=output_dir)


def build_alignment(data_id: str, output_dir: Path | None = None) -> Path:
    """Construye un .bb de alineamiento. ``data_id`` debe estar en
    ``ALIGNMENT_TARGETS``."""
    if data_id not in ALIGNMENT_TARGETS:
        raise ValueError(
            f"data_id {data_id!r} desconocido; opciones: {list(ALIGNMENT_TARGETS)}"
        )
    target = ALIGNMENT_TARGETS[data_id]
    # Enrutar por testamento: NT usa TAGNT (parametrizado por edición), AT
    # usa TAHOT (una sola edición Leningrad).
    if target.testament == "nt":
        alignments, source = _build_alignment_grc_nt(target)
    else:
        alignments, source = _build_alignment_hbo_ot(target)
    pack_input = AlignmentPackInput(
        data_id=target.data_id,
        language=target.language,
        testament=target.testament,
        bible_id=target.bible_id,
        display_name=target.display_name,
        source=source,
        alignments=alignments,
        pipeline_commit=_git_commit(),
        built_at=_now_iso(),
    )
    return pack_alignment(pack_input, output_dir=output_dir)


def build_all_lexicons(output_dir: Path | None = None) -> list[Path]:
    """Construye los .bb de lexicón."""
    return [build_lexicon(did, output_dir=output_dir) for did in LEXICON_TARGETS]


def build_all_alignments(output_dir: Path | None = None) -> list[Path]:
    """Construye los .bb de alineamiento."""
    return [build_alignment(did, output_dir=output_dir) for did in ALIGNMENT_TARGETS]


def build_all(output_dir: Path | None = None) -> list[Path]:
    """Construye todos los .bb del módulo v1.5 (lexicones + alineamientos).
    Determinista — dos invocaciones con el mismo HEAD producen archivos
    idénticos byte a byte."""
    return build_all_lexicons(output_dir) + build_all_alignments(output_dir)


def main(argv: list[str] | None = None) -> int:
    all_targets = list(LEXICON_TARGETS) + list(ALIGNMENT_TARGETS)
    parser = argparse.ArgumentParser(
        description="Build .bb files for the v1.5 lexicon + alignment module"
    )
    parser.add_argument(
        "data_id",
        nargs="?",
        choices=all_targets + ["all", "lexicons", "alignments"],
        default="all",
        help=(
            "Qué .bb construir: nombre específico, 'lexicons' (los del léxico), "
            "'alignments' (los de alineamiento), o 'all' (default)."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=f"Directorio destino (default: {OUTPUT_DIR})",
    )
    args = parser.parse_args(argv)

    if args.data_id == "all":
        paths = build_all(output_dir=args.output_dir)
    elif args.data_id == "lexicons":
        paths = build_all_lexicons(output_dir=args.output_dir)
    elif args.data_id == "alignments":
        paths = build_all_alignments(output_dir=args.output_dir)
    elif args.data_id in LEXICON_TARGETS:
        paths = [build_lexicon(args.data_id, output_dir=args.output_dir)]
    else:
        paths = [build_alignment(args.data_id, output_dir=args.output_dir)]

    for p in paths:
        size_mb = p.stat().st_size / 1e6
        print(f"  ✓ {p.name}  {size_mb:.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
