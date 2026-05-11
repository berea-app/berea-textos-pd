"""Tests del empaquetado .bb léxico (P.5).

Tres bloques:

1. **Unit**: ``build_lexicon_payload`` con fixtures pequeñas — verifica
   estructura del header, ordenamiento determinista, normalización NFC,
   serialización compacta.
2. **Round-trip**: ``pack_lexicon`` → ``read_lexicon_bb`` recupera todas las
   entries idénticas a las que entraron (con NFC aplicado). Verifica
   determinismo byte a byte de builds repetidos.
3. **Build real**: contra los archivos descargados — verifica que los 3
   ``.bb`` reales (``lexicon_grc.bb``, ``lexicon_grc_lsj.bb``,
   ``lexicon_hbo.bb``) se construyen sin error y tienen propiedades
   esperadas (entry_count, sources con atribución correcta, lemmas
   normalizados).
"""

from __future__ import annotations

import unicodedata

import pytest

from pipeline.lexicon.build import (
    LEXICON_TARGETS,
    SOURCES_DIR,
    build_lexicon,
)
from pipeline.lexicon.pack import (
    LexiconPackInput,
    LexiconSource,
    build_lexicon_payload,
    pack_lexicon,
    read_lexicon_bb,
)
from pipeline.lexicon.parse_tbes import BriefLexiconEntry


def _make_entry(
    base: str = "G25",
    extended: str | None = None,
    lemma: str = "ἀγαπάω",
    *,
    source: str = "stepbible",
    language: str = "grc",
) -> BriefLexiconEntry:
    return BriefLexiconEntry(
        strong_base=base,
        strong_extended=extended or base,
        lemma=lemma,
        transliteration="agapaō",
        morph="G:V",
        gloss_brief="to love",
        definition_full="to love",
        language=language,
        source=source,
    )


def _make_source(sid: str = "stepbible") -> LexiconSource:
    return LexiconSource(
        id=sid,
        name=f"Source {sid}",
        license="CC BY 4.0",
        attribution=f"Atribución {sid}",
        source_url=f"https://example.com/{sid}",
        source_sha256={"foo.txt": "0" * 64},
    )


# ===========================================================================
# Unit: build_lexicon_payload
# ===========================================================================


class TestBuildPayload:
    def test_estructura_basica(self):
        inp = LexiconPackInput(
            data_id="lexicon_grc",
            language="grc",
            display_name="Test",
            sources=[_make_source()],
            entries=[_make_entry()],
            pipeline_commit="abc123",
            built_at="2026-05-11T17:00:00-03:00",
        )
        payload = build_lexicon_payload(inp)
        assert payload["type"] == "lexicon"
        assert payload["schema_version"] == "1.0"
        assert payload["data_id"] == "lexicon_grc"
        assert payload["language"] == "grc"
        assert payload["entry_count"] == 1
        assert payload["build_info"]["pipeline_commit"] == "abc123"
        assert payload["build_info"]["built_at"] == "2026-05-11T17:00:00-03:00"

    def test_entries_ordenadas_deterministicamente(self):
        """Las entries deben salir ordenadas por (prefix, num, extended,
        source, lemma) — sin importar el orden de entrada."""
        entries = [
            _make_entry(base="G100", lemma="μ"),
            _make_entry(base="G2", lemma="α"),
            _make_entry(base="G10", lemma="β"),
            _make_entry(base="G2", lemma="α", source="strongs"),
        ]
        inp = LexiconPackInput(
            data_id="lexicon_grc", language="grc", display_name="T",
            sources=[_make_source()],
            entries=entries,
            pipeline_commit="x", built_at="2026-05-11T17:00:00-03:00",
        )
        payload = build_lexicon_payload(inp)
        bases = [e["strong_base"] for e in payload["entries"]]
        # G2 (numérico) < G10 < G100 — no orden alfabético (que daría G10, G100, G2).
        assert bases == ["G2", "G2", "G10", "G100"]
        # Mismo strong_base + lemma, distinta source → orden por source:
        sources_for_g2 = [e["source"] for e in payload["entries"] if e["strong_base"] == "G2"]
        assert sources_for_g2 == ["stepbible", "strongs"]

    def test_normaliza_nfc_en_lemma_y_translit(self):
        """Greek Extended U+1F71 colapsa a Greek Standard U+03AC tras NFC."""
        lemma_extended = "ἀγαπάω"   # con U+1F71
        lemma_standard = "ἀγαπάω"   # con U+03AC — debería ser equivalente NFC
        e = BriefLexiconEntry(
            strong_base="G25", strong_extended="G25",
            lemma=lemma_extended, transliteration="agapάō",
            morph="G:V", gloss_brief="to love",
            definition_full=None, language="grc", source="stepbible",
        )
        inp = LexiconPackInput(
            data_id="lexicon_grc", language="grc", display_name="T",
            sources=[_make_source()], entries=[e],
            pipeline_commit="x", built_at="2026-05-11T17:00:00-03:00",
        )
        payload = build_lexicon_payload(inp)
        assert payload["entries"][0]["lemma"] == unicodedata.normalize("NFC", lemma_extended)
        assert payload["entries"][0]["lemma"] == unicodedata.normalize("NFC", lemma_standard)

    def test_omite_campos_none_para_reducir_tamano(self):
        """Cuando transliteration/morph/definition_full son None, no aparecen
        en el JSON. La app reconstruye con defaults."""
        e = BriefLexiconEntry(
            strong_base="G25", strong_extended="G25", lemma="ἀγαπάω",
            transliteration=None, morph=None,
            gloss_brief="to love", definition_full=None,
            language="grc", source="stepbible",
        )
        inp = LexiconPackInput(
            data_id="lexicon_grc", language="grc", display_name="T",
            sources=[_make_source()], entries=[e],
            pipeline_commit="x", built_at="2026-05-11T17:00:00-03:00",
        )
        payload = build_lexicon_payload(inp)
        out_entry = payload["entries"][0]
        assert "transliteration" not in out_entry
        assert "morph" not in out_entry
        assert "definition_full" not in out_entry
        assert "lemma" in out_entry  # presente siempre

    def test_falla_si_entries_vacio(self):
        inp = LexiconPackInput(
            data_id="lexicon_grc", language="grc", display_name="T",
            sources=[_make_source()], entries=[],
            pipeline_commit="x", built_at="x",
        )
        with pytest.raises(ValueError, match="entries"):
            build_lexicon_payload(inp)

    def test_falla_si_languages_no_coinciden(self):
        """Mix de language=grc con language=hbo en la misma entry list es bug
        del build script — fallamos ruidoso."""
        entries = [_make_entry(language="grc"), _make_entry(language="hbo")]
        inp = LexiconPackInput(
            data_id="lexicon_grc", language="grc", display_name="T",
            sources=[_make_source()], entries=entries,
            pipeline_commit="x", built_at="x",
        )
        with pytest.raises(ValueError, match="language"):
            build_lexicon_payload(inp)


# ===========================================================================
# Round-trip: pack → read
# ===========================================================================


class TestRoundTrip:
    def test_pack_y_lectura_recupera_entries(self, tmp_path):
        entries = [
            _make_entry(base="G25", lemma="ἀγαπάω"),
            _make_entry(base="G3056", lemma="λόγος"),
        ]
        inp = LexiconPackInput(
            data_id="test_grc", language="grc", display_name="Test",
            sources=[_make_source()], entries=entries,
            pipeline_commit="abc", built_at="2026-05-11T17:00:00-03:00",
        )
        out_path = pack_lexicon(inp, output_dir=tmp_path)
        assert out_path.exists()
        assert out_path.name == "test_grc.bb"

        loaded = read_lexicon_bb(out_path)
        assert loaded["entry_count"] == 2
        lemmas = {e["lemma"] for e in loaded["entries"]}
        # NFC normaliza los lemmas, comparamos NFC:
        expected = {unicodedata.normalize("NFC", "ἀγαπάω"),
                    unicodedata.normalize("NFC", "λόγος")}
        assert lemmas == expected

    def test_determinismo_byte_a_byte(self, tmp_path):
        """Dos invocaciones con el mismo input producen archivos idénticos."""
        entries = [_make_entry(base=f"G{i}") for i in [25, 100, 5, 3056]]
        inp = LexiconPackInput(
            data_id="det_test", language="grc", display_name="T",
            sources=[_make_source()], entries=entries,
            pipeline_commit="abc", built_at="2026-05-11T17:00:00-03:00",
        )
        out_a = tmp_path / "a"
        out_b = tmp_path / "b"
        path_a = pack_lexicon(inp, output_dir=out_a)
        path_b = pack_lexicon(inp, output_dir=out_b)
        assert path_a.read_bytes() == path_b.read_bytes()


# ===========================================================================
# Build real contra archivos descargados
# ===========================================================================

_HAS_SOURCES = (SOURCES_DIR / "stepbible_lexicon" / "TBESG.txt").exists()


@pytest.mark.skipif(not _HAS_SOURCES, reason="fuentes upstream no descargadas")
class TestBuildReal:
    """Construye cada uno de los 3 .bb y valida propiedades del payload.

    Los builds toman ~2-5 s cada uno (LSJ es el más lento) — usamos
    ``scope="class"`` en las fixtures para no rebuildear cada test."""

    @pytest.fixture(scope="class")
    def lexicon_grc(self, tmp_path_factory):
        out = tmp_path_factory.mktemp("real_grc")
        path = build_lexicon("lexicon_grc", output_dir=out)
        return read_lexicon_bb(path), path

    @pytest.fixture(scope="class")
    def lexicon_hbo(self, tmp_path_factory):
        out = tmp_path_factory.mktemp("real_hbo")
        path = build_lexicon("lexicon_hbo", output_dir=out)
        return read_lexicon_bb(path), path

    @pytest.fixture(scope="class")
    def lexicon_grc_lsj(self, tmp_path_factory):
        out = tmp_path_factory.mktemp("real_lsj")
        path = build_lexicon("lexicon_grc_lsj", output_dir=out)
        return read_lexicon_bb(path), path

    def test_grc_default_tiene_dos_sources(self, lexicon_grc):
        payload, _ = lexicon_grc
        assert payload["type"] == "lexicon"
        assert payload["language"] == "grc"
        assert payload["data_id"] == "lexicon_grc"
        source_ids = {s["id"] for s in payload["sources"]}
        assert source_ids == {"stepbible", "strongs"}

    def test_grc_default_combina_tbes_y_strongs(self, lexicon_grc):
        """TBESG da ~11k entries y Strong's da ~5.5k. La unión es ~16k.
        ``G25 ἀγαπάω`` debe aparecer de ambas fuentes."""
        payload, _ = lexicon_grc
        assert payload["entry_count"] > 15000
        g25 = [e for e in payload["entries"] if e["strong_base"] == "G25"]
        sources_for_g25 = {e["source"] for e in g25}
        assert sources_for_g25 == {"stepbible", "strongs"}

    def test_grc_lsj_solo_lsj(self, lexicon_grc_lsj):
        payload, _ = lexicon_grc_lsj
        assert payload["data_id"] == "lexicon_grc_lsj"
        source_ids = {s["id"] for s in payload["sources"]}
        assert source_ids == {"lsj"}
        # ~11k entries (TFLSJ base + extra)
        assert 10000 < payload["entry_count"] < 13000

    def test_hbo_combina_tbesh_y_bdb(self, lexicon_hbo):
        payload, _ = lexicon_hbo
        assert payload["language"] == "hbo"
        source_ids = {s["id"] for s in payload["sources"]}
        assert source_ids == {"stepbible", "bdb"}
        # H175 (Aaron) viene de TBESH y BDB
        h175 = [e for e in payload["entries"] if e["strong_base"] == "H175"]
        sources_for_h175 = {e["source"] for e in h175}
        assert "stepbible" in sources_for_h175 and "bdb" in sources_for_h175

    def test_tamanos_dentro_del_target(self, lexicon_grc, lexicon_hbo, lexicon_grc_lsj):
        """Sanity check de tamaños vs lo estimado en P.5 (~2/8/1 MB).
        Si crece descontroladamente algo se rompió en el packer."""
        _, p_grc = lexicon_grc
        _, p_hbo = lexicon_hbo
        _, p_lsj = lexicon_grc_lsj
        # Margen amplio: ±50% del observado al diseñar P.5.
        assert 0.5e6 < p_grc.stat().st_size < 4e6
        assert 0.5e6 < p_hbo.stat().st_size < 4e6
        assert 4e6 < p_lsj.stat().st_size < 15e6

    def test_all_sources_tienen_atribucion_no_vacia(
        self, lexicon_grc, lexicon_hbo, lexicon_grc_lsj
    ):
        """Atribución es legal: cada source debe tener texto no vacío."""
        for payload, _ in (lexicon_grc, lexicon_hbo, lexicon_grc_lsj):
            for s in payload["sources"]:
                assert s["attribution"], f"source {s['id']} sin atribución"
                assert s["license"], f"source {s['id']} sin license"
                assert s["source_url"].startswith("http"), s["source_url"]

    def test_lemmas_son_nfc(self, lexicon_grc):
        """Sample de 50 lemmas — todos deben ser NFC."""
        payload, _ = lexicon_grc
        for e in payload["entries"][:50]:
            assert e["lemma"] == unicodedata.normalize("NFC", e["lemma"])


def test_lexicon_targets_son_los_tres_esperados():
    """Sanity check del catálogo: los 3 .bb planeados existen."""
    assert set(LEXICON_TARGETS) == {"lexicon_grc", "lexicon_grc_lsj", "lexicon_hbo"}
