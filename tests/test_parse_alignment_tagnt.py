"""Tests del parser de alineamiento TAGNT y de su packer.

Cubre:

1. Unit del parser: fixture TSV sintética, filtrado por edición, manejo de
   spelling variants y meaning variants.
2. Integration contra los archivos reales TAGNT descargados.
3. Round-trip del packer: pack_alignment → read_alignment_bb recupera los
   mismos datos (con NFC) y respeta determinismo byte a byte.
4. Spot checks de Jhn 3:16 en las 3 ediciones soportadas (WH, Treg, TR).
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

import pytest

from pipeline.lexicon.build import build_alignment
from pipeline.lexicon.pack import (
    AlignmentPackInput,
    AlignmentSource,
    build_alignment_payload,
    pack_alignment,
    read_alignment_bb,
)
from pipeline.lexicon.parse_alignment_tagnt import (
    WordAlignment,
    parse_tagnt_alignment,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
TAGNT_PATHS = [
    REPO_ROOT / "sources" / "stepbible_tagnt" / "TAGNT_Mat-Jhn.txt",
    REPO_ROOT / "sources" / "stepbible_tagnt" / "TAGNT_Act-Rev.txt",
]
_HAS_TAGNT = all(p.exists() for p in TAGNT_PATHS)


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


# ===========================================================================
# Unit: parser con fixtures sintéticas
# ===========================================================================


def _row(ref: str, *cols: str) -> str:
    """Arma una fila TSV con la primera columna ref y el resto en orden."""
    return "\t".join([ref, *cols]) + "\n"


def _write_fixture(tmp_path: Path, rows: list[str]) -> list[Path]:
    p = tmp_path / "fixture.txt"
    p.write_text("".join(rows), encoding="utf-8")
    return [p]


class TestParserBasico:
    def test_palabra_en_edicion_default(self, tmp_path):
        row = _row(
            "Jhn.3.16#03=NKO",
            "ἠγάπησεν (ēgapēsen)",
            "loved",
            "G0025=V-AAI-3S",
            "ἀγαπάω=to love",
            "NA28+NA27+Tyn+SBL+WH+Treg+TR+Byz",
            "", "", "", "", "", "", "",
        )
        paths = _write_fixture(tmp_path, [row])
        out = list(parse_tagnt_alignment(paths, "WH"))
        assert len(out) == 1
        w = out[0]
        assert w.book_id == "jhn"
        assert w.chapter == 3
        assert w.verse == 16
        assert w.position == 3
        assert _nfc(w.word_original) == _nfc("ἠγάπησεν")
        assert w.transliteration == "ēgapēsen"
        assert w.lemma == "ἀγαπάω"
        # strong_extended sin padding (forma canónica del léxico). El TSV
        # de STEPBible trae ``G0025``, el parser lo normaliza a ``G25``.
        assert w.strong_extended == "G25"
        assert w.morph == "V-AAI-3S"
        assert w.gloss == "loved"

    def test_filtra_palabra_no_presente_en_edicion(self, tmp_path):
        """Si una palabra solo aparece en TR (no en WH/Treg), el parser de
        WH no la emite."""
        row = _row(
            "Mat.1.1#99=K",
            "extra (extra)", "extra word", "G9999=X-NSM", "extra=word",
            "TR",  # solo TR
            "", "", "", "", "", "", "",
        )
        paths = _write_fixture(tmp_path, [row])
        wh = list(parse_tagnt_alignment(paths, "WH"))
        tr = list(parse_tagnt_alignment(paths, "TR"))
        assert wh == []
        assert len(tr) == 1

    def test_spelling_variant_se_aplica_a_edicion_target(self, tmp_path):
        """Δαυίδ → en TR es Δαβίδ. El parser debe emitir la forma de TR
        cuando se pide ``edition="TR"``."""
        row = _row(
            "Mat.1.1#06=NKO",
            "Δαυὶδ (Dauid)", "of David", "G1138=N-GSM-P",
            "Δαυίδ=David",
            "NA28+NA27+Tyn+SBL+WH+Treg+TR+Byz",
            "",
            "Tyn+WH: Δαυεὶδ ; +TR: Δαβὶδ ;",
            "", "", "", "", "",
        )
        paths = _write_fixture(tmp_path, [row])
        wh = next(iter(parse_tagnt_alignment(paths, "WH")))
        tr = next(iter(parse_tagnt_alignment(paths, "TR")))
        treg = next(iter(parse_tagnt_alignment(paths, "Treg")))
        assert _nfc(wh.word_original) == _nfc("Δαυεὶδ")
        assert _nfc(tr.word_original) == _nfc("Δαβὶδ")
        # Treg no tiene variant explícita → cae al default de col 2.
        assert _nfc(treg.word_original) == _nfc("Δαυὶδ")

    def test_meaning_variant_palabra_solo_en_otras_ediciones(self, tmp_path):
        """Cuando una palabra está en una edición pero NO en el default
        (col 2), se captura via 'meaning variants' (col 7).

        Formato col 7: ``ἁγίων (hagiōn) saints. - G0040=A-GPM in: Tyn+WH``.
        Si pedimos WH, la palabra ``ἁγίων`` debe emitirse para WH; para TR
        (no listado en ``in:``) no debe emitirse."""
        row = _row(
            "Rom.16.27#01=NKO",
            "δόξα (doxa)",  # palabra default
            "glory",
            "G1391=N-NSF",
            "δόξα=glory",
            "NA28+NA27+SBL+TR+Byz",   # nota: WH+Treg NO están en ediciones default
            "ἁγίων (hagiōn) saints. - G0040=A-GPM in: WH+Treg",  # meaning variant
            "", "", "", "", "", "",
        )
        paths = _write_fixture(tmp_path, [row])
        wh = list(parse_tagnt_alignment(paths, "WH"))
        tr = list(parse_tagnt_alignment(paths, "TR"))
        assert len(wh) == 1
        assert _nfc(wh[0].word_original) == _nfc("ἁγίων")
        assert wh[0].transliteration == "hagiōn"
        assert wh[0].strong_extended == "G40"
        assert wh[0].morph == "A-GPM"
        # TR usa la palabra default
        assert len(tr) == 1
        assert _nfc(tr[0].word_original) == _nfc("δόξα")

    def test_edicion_desconocida_levanta(self, tmp_path):
        paths = _write_fixture(tmp_path, [_row("Mat.1.1#01=NKO", "x", "x", "G1=X", "x=x", "WH")])
        with pytest.raises(ValueError, match="edition"):
            list(parse_tagnt_alignment(paths, "FAKE"))

    def test_filas_invalidas_se_descartan(self, tmp_path):
        """Líneas que no matchean el regex de inicio (header, comentarios,
        filas truncadas) no se emiten."""
        rows = [
            "# Mat.1.1\tcabecera\textra\n",
            "#_Translation\tfoo\tbar\n",
            "\n",  # vacía
            "Word & Type\tGreek\tEnglish\n",
            _row(
                "Mat.1.1#01=NKO", "Βίβλος (Biblos)", "book",
                "G0976=N-NSF", "βίβλος=book",
                "WH+Treg",
                "", "", "", "", "", "", "",
            ),
        ]
        paths = _write_fixture(tmp_path, rows)
        out = list(parse_tagnt_alignment(paths, "WH"))
        assert len(out) == 1
        assert (
            out[0].word_original.startswith("Βίβλος")
            or _nfc(out[0].word_original) == _nfc("Βίβλος")
        )


# ===========================================================================
# Round-trip del packer
# ===========================================================================


def _make_source() -> AlignmentSource:
    return AlignmentSource(
        id="tagnt",
        name="Test TAGNT",
        license="CC BY 4.0",
        attribution="STEPBible",
        source_url="https://example.com",
        source_sha256={"foo.txt": "0" * 64},
    )


def _make_alignment(**kw) -> WordAlignment:
    defaults = dict(
        book_id="jhn", chapter=3, verse=16, position=3,
        word_original="ἠγάπησεν",
        transliteration="ēgapēsen",
        lemma="ἀγαπάω",
        strong_extended="G25",
        morph="V-AAI-3S",
        gloss="loved",
    )
    defaults.update(kw)
    return WordAlignment(**defaults)


class TestPackerRoundTrip:
    def test_pack_y_lectura_recupera_alignment(self, tmp_path):
        alignments = [_make_alignment()]
        inp = AlignmentPackInput(
            data_id="test_grc_nt",
            language="grc", testament="nt", bible_id="wh",
            display_name="Test",
            source=_make_source(),
            alignments=alignments,
            pipeline_commit="abc",
            built_at="2026-05-11T19:00:00-03:00",
        )
        path = pack_alignment(inp, output_dir=tmp_path)
        loaded = read_alignment_bb(path)
        assert loaded["type"] == "alignment"
        assert loaded["schema_version"] == "1.0"
        assert loaded["entry_count"] == 1
        a = loaded["alignments"][0]
        assert a["book_id"] == "jhn"
        assert a["position"] == 3
        assert _nfc(a["word_original"]) == _nfc("ἠγάπησεν")
        assert a["strong"] == "G25"

    def test_determinismo_byte_a_byte(self, tmp_path):
        alignments = [
            _make_alignment(verse=2, position=1),
            _make_alignment(verse=1, position=5),
            _make_alignment(book_id="mat", chapter=1, verse=1, position=1),
        ]
        inp = AlignmentPackInput(
            data_id="det_test",
            language="grc", testament="nt", bible_id="wh",
            display_name="T",
            source=_make_source(),
            alignments=alignments,
            pipeline_commit="abc",
            built_at="2026-05-11T19:00:00-03:00",
        )
        out_a = pack_alignment(inp, output_dir=tmp_path / "a")
        out_b = pack_alignment(inp, output_dir=tmp_path / "b")
        assert out_a.read_bytes() == out_b.read_bytes()

    def test_orden_canonico_por_libro_capitulo_verso_posicion(self, tmp_path):
        """Salida ordenada por (book_order, chapter, verse, position) — Mat
        antes que Jhn, capitulo 1 antes que 3, etc."""
        alignments = [
            _make_alignment(book_id="jhn", chapter=3, verse=16, position=2),
            _make_alignment(book_id="mat", chapter=1, verse=1, position=1),
            _make_alignment(book_id="jhn", chapter=3, verse=16, position=1),
            _make_alignment(book_id="jhn", chapter=1, verse=1, position=1),
        ]
        inp = AlignmentPackInput(
            data_id="order_test",
            language="grc", testament="nt", bible_id="wh",
            display_name="T",
            source=_make_source(),
            alignments=alignments,
            pipeline_commit="x",
            built_at="2026-05-11T19:00:00-03:00",
        )
        payload = build_alignment_payload(inp)
        seq = [
            (a["book_id"], a["chapter"], a["verse"], a["position"])
            for a in payload["alignments"]
        ]
        assert seq == [
            ("mat", 1, 1, 1),
            ("jhn", 1, 1, 1),
            ("jhn", 3, 16, 1),
            ("jhn", 3, 16, 2),
        ]

    def test_falla_si_testament_invalido(self, tmp_path):
        inp = AlignmentPackInput(
            data_id="x", language="grc", testament="xt", bible_id="wh",
            display_name="T", source=_make_source(),
            alignments=[_make_alignment()],
            pipeline_commit="x", built_at="x",
        )
        with pytest.raises(ValueError, match="testament"):
            build_alignment_payload(inp)

    def test_falla_si_alignments_vacio(self, tmp_path):
        inp = AlignmentPackInput(
            data_id="x", language="grc", testament="nt", bible_id="wh",
            display_name="T", source=_make_source(),
            alignments=[],
            pipeline_commit="x", built_at="x",
        )
        with pytest.raises(ValueError, match="alignments"):
            build_alignment_payload(inp)


# ===========================================================================
# Integration: archivos reales TAGNT
# ===========================================================================


@pytest.mark.skipif(not _HAS_TAGNT, reason="TAGNT no descargado")
class TestParserReal:
    """Spot checks contra Jhn 3:16 en las 3 ediciones soportadas."""

    @pytest.fixture(scope="class")
    def aligns(self):
        return {
            ed: list(parse_tagnt_alignment(TAGNT_PATHS, ed))
            for ed in ["WH", "Treg", "TR"]
        }

    def test_cantidad_de_palabras_por_edicion(self, aligns):
        """NT griego ~137-139k palabras según edición. Variaciones reales:
        TR (Byz texto receptus) tiene más que WH (texto crítico)."""
        for ed in ["WH", "Treg", "TR"]:
            assert 130000 < len(aligns[ed]) < 145000, (
                f"{ed}: vi {len(aligns[ed])} palabras"
            )
        assert len(aligns["TR"]) > len(aligns["WH"])  # TR es más extenso

    def test_jhn_3_16_palabra_3_es_egapesen(self, aligns):
        """ἠγάπησεν en Jhn 3:16 posición 3 — verso icónico."""
        for ed in ["WH", "Treg", "TR"]:
            w3 = next(
                w for w in aligns[ed]
                if w.book_id == "jhn" and w.chapter == 3 and w.verse == 16 and w.position == 3
            )
            assert _nfc(w3.word_original) == _nfc("ἠγάπησεν"), f"{ed}: {w3.word_original!r}"
            assert _nfc(w3.lemma) == _nfc("ἀγαπάω")
            assert w3.strong_extended == "G25"
            assert w3.morph == "V-AAI-3S"
            assert w3.gloss == "loved"

    def test_todos_book_ids_pertenecen_al_nt(self, aligns):
        nt_books = {
            "mat", "mrk", "luk", "jhn", "act",
            "rom", "1co", "2co", "gal", "eph",
            "php", "col", "1th", "2th",
            "1ti", "2ti", "tit", "phm",
            "heb", "jas", "1pe", "2pe",
            "1jn", "2jn", "3jn", "jud", "rev",
        }
        for w in aligns["WH"]:
            assert w.book_id in nt_books


@pytest.mark.skipif(not _HAS_TAGNT, reason="TAGNT no descargado")
class TestBuildReal:
    """End-to-end: build_alignment produce los .bb esperados."""

    @pytest.fixture(scope="class")
    def grc_wh(self, tmp_path_factory):
        out = tmp_path_factory.mktemp("align_wh")
        path = build_alignment("alignment_grc_nt_wh", output_dir=out)
        return read_alignment_bb(path), path

    def test_estructura_basica(self, grc_wh):
        payload, _ = grc_wh
        assert payload["type"] == "alignment"
        assert payload["schema_version"] == "1.0"
        assert payload["language"] == "grc"
        assert payload["testament"] == "nt"
        assert payload["bible_id"] == "wh"
        assert payload["data_id"] == "alignment_grc_nt_wh"
        assert payload["source"]["id"] == "tagnt"
        assert payload["entry_count"] > 100000

    def test_source_tiene_atribucion(self, grc_wh):
        payload, _ = grc_wh
        s = payload["source"]
        assert s["attribution"]
        assert s["license"]
        assert s["source_url"].startswith("http")
        assert s["source_sha256"]  # dict no vacío

    def test_tamano_dentro_del_rango(self, grc_wh):
        """~3 MB esperado tras gzip-9."""
        _, p = grc_wh
        assert 1.5e6 < p.stat().st_size < 5e6
