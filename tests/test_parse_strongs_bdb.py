"""Tests de los parsers de Strong's Greek (openscriptures/strongs) y BDB
(openscriptures/HebrewLexicon).

Dos parsers, dos formatos (JSON-en-JS, XML), mismo target (``BriefLexiconEntry``
con ``source="strongs"`` o ``source="bdb"``). Test estructurado en bloques
paralelos para cada parser: unit con fixtures sintéticas + integration con
los archivos reales descargados en P.1.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

import pytest

from pipeline.lexicon.parse_bdb import parse_bdb_files
from pipeline.lexicon.parse_strongs_greek import parse_strongs_greek_file

REPO_ROOT = Path(__file__).resolve().parent.parent
STRONGS_GREEK_PATH = REPO_ROOT / "sources" / "openscriptures_greek" / "strongs-greek-dictionary.js"
BDB_PATH = REPO_ROOT / "sources" / "openscriptures_hebrew" / "BrownDriverBriggs.xml"
LEX_IDX_PATH = REPO_ROOT / "sources" / "openscriptures_hebrew" / "LexicalIndex.xml"


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


# ===========================================================================
# Strong's Greek
# ===========================================================================


class TestStrongsGreekUnit:
    """Fixtures sintéticas — el archivo real es un único JS con todas las
    entries en JSON, así que las fixtures replican esa estructura mínima."""

    def _write(self, tmp_path: Path, body: str) -> Path:
        # Reconstruye el wrapper JS que produce openscriptures (apenas
        # asignación + module.exports).
        text = f"var strongsGreekDictionary = {body}; module.exports = strongsGreekDictionary;"
        path = tmp_path / "fixture.js"
        path.write_text(text, encoding="utf-8")
        return path

    def test_parsea_entry_minima(self, tmp_path):
        body = (
            '{"G25":{'
            '"lemma":"ἀγαπάω",'
            '"translit":"agapáō",'
            '"kjv_def":"(be-)love(-ed)",'
            '"strongs_def":" to love","derivation":"perhaps from ἄγαν"'
            "}}"
        )
        path = self._write(tmp_path, body)
        entries = list(parse_strongs_greek_file(path))
        assert len(entries) == 1
        e = entries[0]
        assert e.strong_base == "G25"
        assert e.strong_extended == "G25"
        assert _nfc(e.lemma) == _nfc("ἀγαπάω")
        assert e.transliteration == "agapáō"
        assert e.gloss_brief == "love"  # extracted from kjv_def, paréntesis quitados
        assert e.definition_full is not None and "to love" in e.definition_full
        assert "perhaps from" in e.definition_full  # derivation appended
        assert e.language == "grc"
        assert e.source == "strongs"
        assert e.morph is None  # Strong's no trae morfología

    def test_glosa_se_extrae_del_primer_kjv_def(self, tmp_path):
        """``kjv_def: "agree, assure, believe"`` → gloss_brief = "agree"."""
        body = (
            '{"G3982":{'
            '"lemma":"πείθω","translit":"peíthō",'
            '"kjv_def":"agree, assure, believe, have confidence",'
            '"strongs_def":" to convince","derivation":"primary"}}'
        )
        path = self._write(tmp_path, body)
        e = next(iter(parse_strongs_greek_file(path)))
        assert e.gloss_brief == "agree"

    def test_quita_parentesis_decorativos_de_glosa(self, tmp_path):
        body = (
            '{"G25":{'
            '"lemma":"ἀγαπάω","translit":"agapáō",'
            '"kjv_def":"(be-)love(-ed)",'
            '"strongs_def":" to love","derivation":""}}'
        )
        path = self._write(tmp_path, body)
        e = next(iter(parse_strongs_greek_file(path)))
        assert e.gloss_brief == "love"

    def test_descarta_entries_sin_lemma(self, tmp_path):
        body = (
            '{"G99999":{'
            '"lemma":"",'  # vacío
            '"kjv_def":"x","strongs_def":"y","derivation":"","translit":""},'
            '"G25":{"lemma":"ἀγαπάω","translit":"agapáō",'
            '"kjv_def":"love","strongs_def":" to love","derivation":""}}'
        )
        path = self._write(tmp_path, body)
        entries = list(parse_strongs_greek_file(path))
        assert len(entries) == 1
        assert entries[0].strong_base == "G25"

    def test_levanta_si_no_es_un_js_de_strongs_valido(self, tmp_path):
        """Archivo sin el wrapper esperado → ValueError. Esto es fail-loud
        intencional — si el upstream cambia el formato, queremos verlo
        en el build, no en producción."""
        path = tmp_path / "fixture.js"
        path.write_text("// archivo vacío", encoding="utf-8")
        with pytest.raises(ValueError, match="no se pudo extraer"):
            list(parse_strongs_greek_file(path))


@pytest.mark.skipif(
    not STRONGS_GREEK_PATH.exists(),
    reason="strongs-greek-dictionary.js no descargado",
)
class TestStrongsGreekReal:
    @pytest.fixture(scope="class")
    def entries(self):
        return list(parse_strongs_greek_file(STRONGS_GREEK_PATH))

    def test_cantidad_de_entries_razonable(self, entries):
        """Strong's Greek tiene ~5,624 entries originales. El upstream
        digitalizado puede tener menos por entries vacías filtradas."""
        assert 5000 < len(entries) < 5700

    def test_todas_son_griego_y_source_strongs(self, entries):
        for e in entries:
            assert e.language == "grc"
            assert e.source == "strongs"
            assert e.strong_base.startswith("G")

    def test_spot_check_agapao(self, entries):
        matches = [e for e in entries if e.strong_base == "G25"]
        assert len(matches) == 1
        e = matches[0]
        assert _nfc(e.lemma) == _nfc("ἀγαπάω")
        assert "love" in e.gloss_brief.lower()
        assert e.definition_full and "love" in e.definition_full.lower()

    def test_spot_check_logos(self, entries):
        matches = [e for e in entries if e.strong_base == "G3056"]
        assert len(matches) == 1
        assert _nfc(matches[0].lemma) == _nfc("λόγος")

    def test_spot_check_christos(self, entries):
        """G5547 = Χριστός. La definición de Strong reza "anointed, i.e. the
        Messiah, an epithet of Jesus" — no usa "Christ" literalmente. Verificamos
        contra la palabra que sí está, no contra la transliteración popular."""
        matches = [e for e in entries if e.strong_base == "G5547"]
        assert len(matches) == 1
        assert _nfc(matches[0].lemma) == _nfc("Χριστός")
        defn = (matches[0].definition_full or "").lower()
        assert "messiah" in defn or "anointed" in defn


# ===========================================================================
# BDB (Brown-Driver-Briggs)
# ===========================================================================


class TestBdbUnit:
    """Fixtures sintéticas XML con la estructura openscriptures."""

    def _write(self, tmp_path: Path, bdb_body: str, idx_body: str) -> tuple[Path, Path]:
        ns_attrs = (
            'xsi:schemaLocation="x" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xmlns="http://openscriptures.github.com/morphhb/namespace"'
        )
        bdb = tmp_path / "bdb.xml"
        bdb.write_text(
            f'<?xml version="1.0" encoding="UTF-8"?>\n<lexicon {ns_attrs}>{bdb_body}</lexicon>',
            encoding="utf-8",
        )
        idx = tmp_path / "idx.xml"
        idx.write_text(
            f'<?xml version="1.0" encoding="UTF-8"?>\n<index {ns_attrs}>{idx_body}</index>',
            encoding="utf-8",
        )
        return bdb, idx

    def test_entry_basica(self, tmp_path):
        """Entry simple: lemma + glosa + def prosa unidos por Strong's."""
        bdb_body = """
        <part id="a" title="א">
          <section id="a.bn">
            <entry id="a.bn.ab"><w>אַהֲרֹן</w> <pos>n.pr.m.</pos>
              <def>Aaron</def>, elder brother of Moses.
              <status p="1">done</status>
            </entry>
          </section>
        </part>
        """
        idx_body = """
        <part xml:lang="heb">
          <entry id="ahd">
            <w xlit="ʾahărōn">אַהֲרֹן</w> <pos>Np</pos> <def>Aaron</def>
            <xref bdb="a.bn.ab" strong="175"/>
          </entry>
        </part>
        """
        bdb, idx = self._write(tmp_path, bdb_body, idx_body)
        entries = list(parse_bdb_files(bdb, idx))
        assert len(entries) == 1
        e = entries[0]
        assert e.strong_base == "H175"
        assert _nfc(e.lemma) == _nfc("אַהֲרֹן")
        assert e.transliteration == "ʾahărōn"
        assert e.morph == "Np"
        assert e.gloss_brief == "Aaron"
        assert e.language == "hbo"
        assert e.source == "bdb"
        assert e.definition_full and "Aaron" in e.definition_full
        # `<status>` debe estar fuera del texto plano:
        assert "done" not in e.definition_full

    def test_descarta_entries_sin_strong(self, tmp_path):
        """LexicalIndex entries sin ``<xref strong=...>`` no se generan."""
        idx_body = """
        <part>
          <entry id="aaa">
            <w xlit="x">א</w>
            <xref bdb="a.aa.aa"/>
            <!-- xref sin strong -->
          </entry>
          <entry id="ahd">
            <w xlit="ʾahărōn">אַהֲרֹן</w> <def>Aaron</def>
            <xref bdb="a.bn.ab" strong="175"/>
          </entry>
        </part>
        """
        bdb_body = '<entry id="a.bn.ab"><w>אַהֲרֹן</w></entry>'
        bdb, idx = self._write(tmp_path, bdb_body, idx_body)
        entries = list(parse_bdb_files(bdb, idx))
        assert len(entries) == 1
        assert entries[0].strong_base == "H175"

    def test_descarta_strong_no_numerico(self, tmp_path):
        """En el archivo real ~8 xrefs tienen ``strong="b"`` / ``"i"`` / etc.
        (residuos editoriales). Los descartamos."""
        idx_body = """
        <part>
          <entry id="x"><w xlit="x">א</w><def>foo</def><xref bdb="a" strong="b"/></entry>
          <entry id="y"><w xlit="x">א</w><def>foo</def><xref bdb="a" strong="175"/></entry>
        </part>
        """
        bdb_body = '<entry id="a"><w>א</w></entry>'
        bdb, idx = self._write(tmp_path, bdb_body, idx_body)
        entries = list(parse_bdb_files(bdb, idx))
        assert len(entries) == 1
        assert entries[0].strong_base == "H175"

    def test_definicion_full_incluye_senses_con_numeracion(self, tmp_path):
        """Las ``<sense n="N">`` deben preservar su numeración en el texto
        plano para que la app pueda renderizar la jerarquía."""
        bdb_body = """
        <entry id="a.x">
          <w>אָבִיב</w> <pos>n.m.</pos>
          <sense n="1"><def>fresh, young ears</def> of barley.</sense>
          <sense n="2"><def>Abib</def>, month of Exodus.</sense>
        </entry>
        """
        idx_body = """
        <part>
          <entry id="x">
            <w xlit="ʾābîb">אָבִיב</w><def>Abib</def>
            <xref bdb="a.x" strong="24"/>
          </entry>
        </part>
        """
        bdb, idx = self._write(tmp_path, bdb_body, idx_body)
        e = next(iter(parse_bdb_files(bdb, idx)))
        assert e.definition_full and "1." in e.definition_full and "2." in e.definition_full


@pytest.mark.skipif(not BDB_PATH.exists() or not LEX_IDX_PATH.exists(),
                    reason="archivos BDB / LexicalIndex no descargados")
class TestBdbReal:
    @pytest.fixture(scope="class")
    def entries(self):
        return list(parse_bdb_files(BDB_PATH, LEX_IDX_PATH))

    def test_cantidad_de_entries_razonable(self, entries):
        """LexicalIndex tiene 9299 entries con Strong's. Filtramos ~8 no
        numéricos. Esperamos ~9290."""
        assert 9000 < len(entries) < 9400

    def test_todas_son_hebreo_y_source_bdb(self, entries):
        for e in entries:
            assert e.language == "hbo"
            assert e.source == "bdb"
            assert e.strong_base.startswith("H")

    def test_spot_check_aharon(self, entries):
        matches = [e for e in entries if e.strong_base == "H175"]
        assert len(matches) >= 1
        e = matches[0]
        assert "Aaron" in e.gloss_brief or "Aaron" in (e.definition_full or "")

    def test_spot_check_ab(self, entries):
        """H1 = אָב = "father". Palabra altísima frecuencia."""
        matches = [e for e in entries if e.strong_base == "H1"]
        assert len(matches) >= 1
        assert any("father" in (e.gloss_brief or "").lower() for e in matches)

    def test_spot_check_yhwh(self, entries):
        """H3068 = יְהוָה = el Tetragrámaton. Debe estar."""
        matches = [e for e in entries if e.strong_base == "H3068"]
        assert len(matches) >= 1
