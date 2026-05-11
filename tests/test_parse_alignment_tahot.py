"""Tests del parser de alineamiento TAHOT (hebreo AT).

Estructura paralela al test de TAGNT pero con diferencias específicas del
formato hebreo:

- Una sola "edición" (sin parámetro de filtrado por edition).
- Tipos de fila L/Q (incluir), R/X (descartar).
- Segmentación morfológica con ``/`` que se strippea para el word_original.
- Strong's root extraído de col 9 con Instance markers (``_A``).
- Lema y glosa léxica vienen de col 12 (``Expanded Strong tags``).
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

import pytest

from pipeline.lexicon.build import build_alignment
from pipeline.lexicon.pack import read_alignment_bb
from pipeline.lexicon.parse_alignment_tahot import parse_tahot_alignment

REPO_ROOT = Path(__file__).resolve().parent.parent
TAHOT_PATHS = sorted((REPO_ROOT / "sources" / "stepbible_tahot").glob("*.txt"))
_HAS_TAHOT = len(TAHOT_PATHS) >= 4


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _row(ref: str, *cols: str) -> str:
    """Arma una fila TSV con 12 columnas (rellenando con vacíos)."""
    extended = list(cols) + [""] * (12 - len(cols))
    return "\t".join([ref, *extended[:12]]) + "\n"


def _write_fixture(tmp_path: Path, rows: list[str]) -> list[Path]:
    p = tmp_path / "fixture.txt"
    p.write_text("".join(rows), encoding="utf-8")
    return [p]


# ===========================================================================
# Unit: parser con fixtures sintéticas
# ===========================================================================


class TestParserBasico:
    def test_palabra_leningrad_basica(self, tmp_path):
        """Gen 1:1 בָּרָ֣א (created)."""
        row = _row(
            "Gen.1.1#02=L",
            "בָּרָ֣א",              # col 2: Hebrew
            "ba.Ra'",               # col 3: Translit
            "he created",           # col 4: Translation
            "{H1254A}",             # col 5: dStrongs
            "HVqp3ms",              # col 6: Grammar
            "",                     # col 7: Meaning Variants
            "",                     # col 8: Spelling Variants
            "H1254A",               # col 9: Root dStrong+Instance
            "",                     # col 10
            "",                     # col 11
            "{H1254A=בָּרָא=to create}",  # col 12: Expanded
        )
        paths = _write_fixture(tmp_path, [row])
        out = list(parse_tahot_alignment(paths))
        assert len(out) == 1
        w = out[0]
        assert w.book_id == "gen"
        assert w.chapter == 1
        assert w.verse == 1
        assert w.position == 2
        assert _nfc(w.word_original) == _nfc("בָּרָ֣א")
        assert w.transliteration == "ba.Ra'"
        assert w.gloss == "he created"
        assert w.strong_extended == "H1254A"
        assert w.morph == "HVqp3ms"
        assert _nfc(w.lemma) == _nfc("בָּרָא")

    def test_strippa_separadores_morfologicos(self, tmp_path):
        """``בְּ/רֵאשִׁ֖ית`` debe quedar como ``בְּרֵאשִׁ֖ית`` (sin ``/``)."""
        row = _row(
            "Gen.1.1#01=L",
            "בְּ/רֵאשִׁ֖ית", "be./re.Shit", "in/ beginning",
            "H9003/{H7225G}", "HR/Ncfsa", "", "",
            "H7225G", "", "",
            "H9003=ב=in/{H7225G=רֵאשִׁית=: beginning»first:1_beginning}",
        )
        paths = _write_fixture(tmp_path, [row])
        w = next(iter(parse_tahot_alignment(paths)))
        assert "/" not in w.word_original
        assert _nfc(w.word_original) == _nfc("בְּרֵאשִׁ֖ית")
        # Glosa contextual: "in/ beginning" → "in beginning"
        assert w.gloss == "in beginning"
        # Lema del expanded tag (después del separador "»" y prefijo ":")
        assert _nfc(w.lemma) == _nfc("רֵאשִׁית")

    def test_instance_marker_se_strippea_del_strong(self, tmp_path):
        """``H0853_A`` (instance marker) → ``H0853``."""
        row = _row(
            "Gen.1.1#04=L",
            "אֵ֥ת", "'et", "<obj.>", "{H0853}", "HTo", "", "",
            "H0853_A",  # col 9 con Instance marker
            "", "", "{H0853=אֵת=[Obj.]}",
        )
        paths = _write_fixture(tmp_path, [row])
        w = next(iter(parse_tahot_alignment(paths)))
        assert w.strong_extended == "H0853"

    def test_lemma_glosa_se_extraen_del_expanded_tag(self, tmp_path):
        """Cuando expanded tag tiene formato ``{Hxxx=lemma=: glosa»sub:n_glosa}``,
        extrae lemma y la primera glosa (antes del ``»``)."""
        row = _row(
            "Gen.1.2#01=L",
            "וְ/הָ/אָ֗רֶץ", "ve./ha./'A.retz", "and/ the/ earth",
            "H9002/H9009/{H0776G}", "HC/Td/Ncfsa", "", "",
            "H0776G", "", "",
            "H9002=ו=and/H9009=ה=the/{H0776G=אֶ֫רֶץ=: country;_planet»land:2_country;_planet}",
        )
        paths = _write_fixture(tmp_path, [row])
        w = next(iter(parse_tahot_alignment(paths)))
        assert _nfc(w.lemma) == _nfc("אֶ֫רֶץ")
        # Gloss contextual viene de col 4, no del expanded → "and the earth"
        assert w.gloss == "and the earth"

    def test_descarta_tipo_X_supplied_from_lxx(self, tmp_path):
        """Filas con ``=X`` (texto restaurado desde LXX) NO deben emitirse —
        WLC moderno no las contiene."""
        rows = [
            _row("Gen.4.8#0501=X", "נֵלְכָה", "ne.le.Khah", "let us go",
                 "{H1980G}", "HVqi1cp", "", "",
                 "H1980G", "H3212", "", "{H1980G=הָלַךְ=to go}"),
            _row("Gen.1.1#01=L", "בְּרֵאשִׁית", "be.re.shit", "in beginning",
                 "{H7225G}", "HNcfsa", "", "", "H7225G", "", "",
                 "{H7225G=רֵאשִׁית=beginning}"),
        ]
        paths = _write_fixture(tmp_path, rows)
        out = list(parse_tahot_alignment(paths))
        assert len(out) == 1
        assert out[0].book_id == "gen" and out[0].chapter == 1

    def test_descarta_tipo_R_restored(self, tmp_path):
        """``=R`` (Jos 21.36-37, Neh 7.67b) restaurado desde paralelos. NO
        está en Leningrad → descartar."""
        rows = [
            _row("Jos.21.36#01=R", "וּמִ/מַּטֵּה", "u.mi.ma.Teh", "and from tribe",
                 "...", "...", "", "", "H4294", "", "", "{H4294=מַטֶּה=tribe}"),
            _row("Gen.1.1#01=L", "בְּרֵאשִׁית", "be.re.shit", "in beginning",
                 "{H7225G}", "HNcfsa", "", "", "H7225G", "", "",
                 "{H7225G=רֵאשִׁית=beginning}"),
        ]
        paths = _write_fixture(tmp_path, rows)
        out = list(parse_tahot_alignment(paths))
        assert len(out) == 1
        assert out[0].book_id == "gen"

    def test_incluye_tipo_Q_qere(self, tmp_path):
        """``=Q(k)`` (Qere principal con Ketiv variante) SÍ se incluye — es
        el texto principal del WLC moderno."""
        row = _row(
            "Gen.8.17#14=Q(k)",
            "הַיְצֵ֣א", "hay.tze'", "bring out", "{H3318H}", "HVhv2ms", "", "",
            "H3318H", "", "", "{H3318H=יָצָא=to come out}",
        )
        paths = _write_fixture(tmp_path, [row])
        out = list(parse_tahot_alignment(paths))
        assert len(out) == 1
        assert out[0].book_id == "gen" and out[0].chapter == 8

    def test_filas_invalidas_se_descartan(self, tmp_path):
        """Headers y comentarios del TAHOT no deben emitirse."""
        rows = [
            "# Comentario\n",
            "Eng (Heb) Ref & Type\tHebrew\tTransliteration\n",
            "\n",
            _row("Gen.1.1#01=L", "בְּרֵאשִׁית", "be.re.shit", "in beginning",
                 "{H7225G}", "HNcfsa", "", "", "H7225G", "", "",
                 "{H7225G=רֵאשִׁית=beginning}"),
        ]
        paths = _write_fixture(tmp_path, rows)
        out = list(parse_tahot_alignment(paths))
        assert len(out) == 1


# ===========================================================================
# Integration: archivo real TAHOT
# ===========================================================================


@pytest.mark.skipif(not _HAS_TAHOT, reason="TAHOT no descargado")
class TestParserReal:
    @pytest.fixture(scope="class")
    def aligns(self):
        return list(parse_tahot_alignment(TAHOT_PATHS))

    def test_cantidad_de_palabras_razonable(self, aligns):
        """AT hebreo ~283k palabras según TAHOT (L + Q, descartando R + X)."""
        assert 280000 < len(aligns) < 290000

    def test_todos_los_39_libros_at_cubiertos(self, aligns):
        from collections import Counter
        books = Counter(a.book_id for a in aligns)
        ot_books = {
            "gen", "exo", "lev", "num", "deu",
            "jos", "jdg", "rut", "1sa", "2sa",
            "1ki", "2ki", "1ch", "2ch",
            "ezr", "neh", "est",
            "job", "psa", "pro", "ecc", "sng",
            "isa", "jer", "lam", "ezk", "dan",
            "hos", "jol", "amo", "oba", "jon",
            "mic", "nam", "hab", "zep",
            "hag", "zec", "mal",
        }
        cubiertos = set(books.keys())
        faltantes = ot_books - cubiertos
        assert not faltantes, f"libros AT sin palabras: {sorted(faltantes)}"

    def test_gen_1_1_palabra_2_es_bara(self, aligns):
        """בָּרָא = "he created" en Gen 1:1 posición 2."""
        w = next(
            a for a in aligns
            if a.book_id == "gen" and a.chapter == 1 and a.verse == 1 and a.position == 2
        )
        assert _nfc(w.word_original) == _nfc("בָּרָ֣א")
        assert _nfc(w.lemma) == _nfc("בָּרָא")
        assert w.strong_extended == "H1254A"
        assert w.morph == "HVqp3ms"
        # Glosa puede ser "he created" o "<he> created" según mejora del upstream
        assert "created" in (w.gloss or "")

    def test_no_book_id_fuera_de_canon_at(self, aligns):
        nt_books = {"mat", "mrk", "luk", "jhn", "act", "rom"}  # sampler
        for a in aligns:
            assert a.book_id not in nt_books, f"NT book en TAHOT: {a.book_id}"


# ===========================================================================
# Build real
# ===========================================================================


@pytest.mark.skipif(not _HAS_TAHOT, reason="TAHOT no descargado")
class TestBuildReal:
    @pytest.fixture(scope="class")
    def hbo_wlc(self, tmp_path_factory):
        out = tmp_path_factory.mktemp("align_hbo")
        path = build_alignment("alignment_hbo_ot_wlc", output_dir=out)
        return read_alignment_bb(path), path

    def test_estructura(self, hbo_wlc):
        payload, _ = hbo_wlc
        assert payload["type"] == "alignment"
        assert payload["language"] == "hbo"
        assert payload["testament"] == "ot"
        assert payload["bible_id"] == "wlc"
        assert payload["source"]["id"] == "tahot"
        assert payload["entry_count"] > 280000

    def test_tamano_aproximado(self, hbo_wlc):
        """~7-8 MB esperado tras gzip-9 (3× el NT por más palabras)."""
        _, p = hbo_wlc
        assert 5e6 < p.stat().st_size < 12e6

    def test_atribucion_correcta(self, hbo_wlc):
        payload, _ = hbo_wlc
        assert "STEPBible" in payload["source"]["attribution"]
        assert payload["source"]["license"] == "CC BY 4.0"
