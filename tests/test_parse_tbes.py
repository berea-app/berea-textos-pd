"""Tests de ``pipeline/lexicon/parse_tbes.py``.

Dos niveles:

1. **Unit tests con fixtures sintéticas** (líneas TSV armadas con los mismos
   campos que produce STEPBible). Cubren casos límite del parser: sufijos
   minúscula (``H0122a``), filas decorativas (``$======``, ``- Named``),
   columnas vacías, HTML en la definición.

2. **Integration tests contra los archivos reales** descargados en P.1
   (``sources/stepbible_lexicon/TBESG.txt`` y ``TBESH.txt``). Validan:
   cobertura cuantitativa (~11k entries por archivo), spot-checks de palabras
   icónicas (``G25 ἀγαπάω``, ``H175 אַהֲרֹן``), y ausencia de regresiones
   silenciosas (ningún strong_base con formato inesperado).

Si los archivos fuente no están descargados, los tests de integración se
saltean con un mensaje claro — no fallan ruidosamente para no bloquear CI
en clones nuevos del repo.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

import pytest

from pipeline.lexicon.parse_tbes import (
    BriefLexiconEntry,
    parse_tbes_file,
)


def _nfc(s: str) -> str:
    """Normaliza a NFC para comparaciones robustas con griego politónico:
    STEPBible mezcla codepoints del bloque Greek Extended (U+1F00–U+1FFF)
    con sus equivalentes del bloque Greek Standard (U+0370–U+03FF). NFC
    los unifica a la forma estándar."""
    return unicodedata.normalize("NFC", s)

REPO_ROOT = Path(__file__).resolve().parent.parent
TBESG_PATH = REPO_ROOT / "sources" / "stepbible_lexicon" / "TBESG.txt"
TBESH_PATH = REPO_ROOT / "sources" / "stepbible_lexicon" / "TBESH.txt"


# ---------------------------------------------------------------------------
# Unit tests con fixtures sintéticas
# ---------------------------------------------------------------------------


def _write_fixture(tmp_path: Path, lines: list[str]) -> Path:
    """Escribe un archivo TSV de prueba. Las líneas no necesitan ``\\n``
    final; los unimos con ``\\n`` y agregamos ``\\n`` al final como hace el
    upstream real."""
    path = tmp_path / "fixture.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


class TestParseLineBasico:
    """Filas TSV bien formadas — caso feliz."""

    def test_parsea_entry_simple_griega(self, tmp_path):
        """``G0025 G0025 = G0025 ἀγαπάω agapaō G:V to love <def AS>``"""
        line = "\t".join([
            "G0025", "G0025 =", "G0025",
            "ἀγαπάω", "agapaō", "G:V", "to love",
            "<b>ἀγαπάω</b>, -ῶ, <BR /> [in LXX chiefly for אהב ;]",
        ])
        path = _write_fixture(tmp_path, [line])
        entries = list(parse_tbes_file(path, "grc"))
        assert len(entries) == 1
        e = entries[0]
        assert e.strong_base == "G25"
        assert e.strong_extended == "G25"
        assert e.lemma == "ἀγαπάω"
        assert e.transliteration == "agapaō"
        assert e.morph == "G:V"
        assert e.gloss_brief == "to love"
        assert e.definition_full is not None and "ἀγαπάω" in e.definition_full
        assert e.language == "grc"

    def test_parsea_entry_simple_hebrea(self, tmp_path):
        line = "\t".join([
            "H0175", "H0175 =", "H0175",
            "אַהֲרֹן", "a.ha.ron", "N:N-M-P", "Aaron",
            "A man of the tribe of Levi…",
        ])
        path = _write_fixture(tmp_path, [line])
        entries = list(parse_tbes_file(path, "hbo"))
        assert len(entries) == 1
        e = entries[0]
        assert e.strong_base == "H175"
        assert e.lemma == "אַהֲרֹן"
        assert e.language == "hbo"

    def test_sufijo_minuscula_en_estrong(self, tmp_path):
        """TBESH usa ``H0122a`` / ``H0176b`` para sub-acepciones de la
        misma raíz consonántica con vocalización distinta. Probamos que el
        parser detecta la línea (regex permisivo) y normaliza el extended."""
        line = "\t".join([
            "H0122a", "H0122A =", "H0122A",
            "אָדֹם", "a.dom", "H:A", "red",
            "red, ruddy",
        ])
        path = _write_fixture(tmp_path, [line])
        entries = list(parse_tbes_file(path, "hbo"))
        assert len(entries) == 1
        assert entries[0].strong_base == "H122"
        assert entries[0].strong_extended == "H122A"

    def test_sufijo_mayuscula_en_ustrong(self, tmp_path):
        """Personas/lugares en TBESG/TBESH usan sufijos mayúsculas en uStrong
        (``G2264G`` / ``G2264H``). Cada una es entry independiente con su
        propio extended."""
        lines = [
            "\t".join([
                "G2264", "G2264G =", "G2264G",
                "Ἡρώδης", "Hērōdēs", "N:N-M-P", "Herod",
                "Herod the Great",
            ]),
            "\t".join([
                "G2264", "G2264H = a Name of", "G2264H",
                "Ἡρώδης", "Hērōdēs", "N:N-M-P", "Herod",
                "Herod Antipas",
            ]),
        ]
        path = _write_fixture(tmp_path, lines)
        entries = list(parse_tbes_file(path, "grc"))
        assert len(entries) == 2
        assert entries[0].strong_base == entries[1].strong_base == "G2264"
        assert entries[0].strong_extended == "G2264G"
        assert entries[1].strong_extended == "G2264H"


class TestParseFiltrado:
    """Líneas que el parser DEBE descartar silenciosamente."""

    def test_descarta_header_inicial(self, tmp_path):
        lines = [
            "TBESG - Translators Brief lexicon - STEPBible.org CC BY",
            "See also:",
            "==========================================",
            "Fields:",
            "eStrong\tdStrong\tuStrong\tGreek\tTransliteration\tMorph\tGloss\tDef",
            "",
            # Después del header viene una fila real
            "\t".join([
                "G0025", "G0025 =", "G0025",
                "ἀγαπάω", "agapaō", "G:V", "to love", "definition…",
            ]),
        ]
        path = _write_fixture(tmp_path, lines)
        entries = list(parse_tbes_file(path, "grc"))
        assert len(entries) == 1
        assert entries[0].lemma == "ἀγαπάω"

    def test_descarta_secciones_decorativas(self, tmp_path):
        """Las filas ``$========== PERSON(s)`` y ``- Named``/``- Group`` no
        son entries léxicas. Descartar."""
        lines = [
            "$========== PERSON(s)",
            "Herod@Mat.2.1=G2264G\tKing Herod the Great…",
            "- Named\tHerod@Mat.2.1\tG2264G«G2264=Ἡρώδης\tHerod\thttps://...",
            "- Group\tHerod@Mat.14.1\tG2265«G2265=Ἡρωδιανοί\tHerodian\thttps://...",
            "\t".join([
                "G2266", "G2266 =", "G2266",
                "Ἡρωδιάς", "Hērōdias", "N:N-F-P", "Herodias", "Herodias…",
            ]),
        ]
        path = _write_fixture(tmp_path, lines)
        entries = list(parse_tbes_file(path, "grc"))
        assert len(entries) == 1
        assert entries[0].strong_extended == "G2266"

    def test_descarta_filas_con_columnas_insuficientes(self, tmp_path):
        """Si una fila empieza con ``G\\d+\\t`` pero tiene menos de 7 columnas
        (truncada por algún bug del upstream), la descartamos."""
        lines = [
            "G0025\tG0025 =\tG0025",  # solo 3 cols
            "\t".join([
                "G0026", "G0026 =", "G0026",
                "ἀγάπη", "agapē", "G:N-F", "love", "love…",
            ]),
        ]
        path = _write_fixture(tmp_path, lines)
        entries = list(parse_tbes_file(path, "grc"))
        assert len(entries) == 1
        assert entries[0].strong_extended == "G26"

    def test_descarta_filas_con_strong_invalido(self, tmp_path):
        """Si por algún motivo el código no parsea, descartamos sin lanzar.
        El parser corre sobre 22k líneas; una excepción acá pararía el build."""
        lines = [
            "G\tG =\tG\t\t\t\t\t",  # uStrong inválido
            "\t".join([
                "G0025", "G0025 =", "G0025",
                "ἀγαπάω", "agapaō", "G:V", "to love", "to love…",
            ]),
        ]
        path = _write_fixture(tmp_path, lines)
        entries = list(parse_tbes_file(path, "grc"))
        # La primera no matchea ``[GH]\d+`` así que es descartada por el
        # regex de la línea, no llega al parser de columnas.
        assert len(entries) == 1


class TestNormalizacionDeCampos:
    def test_columnas_vacias_se_convierten_a_none(self, tmp_path):
        """Si transliteración o morph vienen vacías, deben quedar como ``None``
        (no como string vacío, no como ``"   "``)."""
        line = "\t".join([
            "G0001", "G0001 =", "G0001",
            "α", "  ", "", "Alpha", "<b>α</b>",
        ])
        path = _write_fixture(tmp_path, [line])
        entries = list(parse_tbes_file(path, "grc"))
        assert len(entries) == 1
        assert entries[0].transliteration is None
        assert entries[0].morph is None

    def test_definition_full_puede_faltar(self, tmp_path):
        """STEPBible a veces emite filas con solo 7 columnas (sin
        definición). Eso es válido; debe producir entry con def=None."""
        line = "\t".join([
            "G0025", "G0025 =", "G0025",
            "ἀγαπάω", "agapaō", "G:V", "to love",
        ])
        path = _write_fixture(tmp_path, [line])
        entries = list(parse_tbes_file(path, "grc"))
        assert len(entries) == 1
        assert entries[0].definition_full is None

    def test_html_se_preserva_intacto(self, tmp_path):
        """La definición trae HTML inline (``<b>``, ``<BR>``, ``<ref=...>``).
        El parser NO lo limpia — eso es responsabilidad del empaquetador
        o del cliente. Test reasegura que no se nos escapó ningún strip."""
        html = "<b>ἀγαπάω</b>, -ῶ, <BR /> <ref='Jhn.3.16'>Jhn.3:16</ref>"
        line = "\t".join([
            "G0025", "G0025 =", "G0025",
            "ἀγαπάω", "agapaō", "G:V", "to love", html,
        ])
        path = _write_fixture(tmp_path, [line])
        e = next(iter(parse_tbes_file(path, "grc")))
        assert e.definition_full == html


# ---------------------------------------------------------------------------
# Integration tests contra los archivos reales descargados
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not TBESG_PATH.exists(), reason="TBESG.txt no descargado")
class TestTbesgReal:
    """Validación contra el TBESG real (descargado por download_stepbible.sh)."""

    @pytest.fixture(scope="class")
    def entries(self) -> list[BriefLexiconEntry]:
        return list(parse_tbes_file(TBESG_PATH, "grc"))

    def test_cantidad_de_entries_razonable(self, entries):
        """Esperamos ~11k entries. Si el upstream cambia y pasamos a 5k o
        a 20k, el test cae rojo y queremos investigar."""
        assert 10000 < len(entries) < 13000

    def test_todas_las_entries_son_griego(self, entries):
        """Todas las entries de TBESG deben tener strong_base con prefijo
        ``G``. Si aparece una ``H`` es bug del upstream o del filtrado."""
        for e in entries:
            assert e.strong_base.startswith("G"), e.strong_base

    def test_spot_check_agapao(self, entries):
        """G25 = ἀγαπάω = "to love". Palabra icónica, debe estar."""
        matches = [e for e in entries if e.strong_extended == "G25"]
        assert len(matches) == 1, f"esperaba 1 entry para G25, vi {len(matches)}"
        e = matches[0]
        assert _nfc(e.lemma) == _nfc("ἀγαπάω")
        assert e.transliteration == "agapaō"
        assert e.gloss_brief == "to love"
        assert e.morph == "G:V"
        assert e.language == "grc"

    def test_spot_check_logos(self, entries):
        """G3056 = λόγος = "word". Otra palabra alta-frecuencia."""
        matches = [e for e in entries if e.strong_extended == "G3056"]
        assert len(matches) >= 1
        assert _nfc(matches[0].lemma) == _nfc("λόγος")

    def test_spot_check_herodes_tres_personas(self, entries):
        """G2264 (Herodes) tiene tres sub-acepciones en TBESG (Herodes el
        Grande, Antipas, Agripa I). Las tres deben aparecer como entries
        independientes con el mismo strong_base."""
        herodes = [e for e in entries if e.strong_base == "G2264"]
        assert len(herodes) >= 3, f"esperaba ≥3 Herodes, vi {len(herodes)}"
        extendeds = {e.strong_extended for e in herodes}
        assert extendeds == {"G2264G", "G2264H", "G2264I"}


@pytest.mark.skipif(not TBESH_PATH.exists(), reason="TBESH.txt no descargado")
class TestTbeshReal:
    """Validación contra el TBESH real."""

    @pytest.fixture(scope="class")
    def entries(self) -> list[BriefLexiconEntry]:
        return list(parse_tbes_file(TBESH_PATH, "hbo"))

    def test_cantidad_de_entries_razonable(self, entries):
        assert 10000 < len(entries) < 13000

    def test_todas_las_entries_son_hebreo(self, entries):
        for e in entries:
            assert e.strong_base.startswith("H"), e.strong_base

    def test_spot_check_aharon(self, entries):
        """H175 = אַהֲרֹן = "Aaron". Persona icónica del AT."""
        matches = [e for e in entries if e.strong_extended == "H175"]
        assert len(matches) == 1
        e = matches[0]
        assert e.lemma == "אַהֲרֹן"
        assert "Aaron" in e.gloss_brief

    def test_spot_check_yhwh(self, entries):
        """H3068 = יְהוָה = el Tetragrámaton. Tiene varias sub-acepciones
        (G/H/...) por personajes homónimos vs el nombre divino. La forma
        canónica ``H3068`` (con o sin sufijo) debe estar."""
        yhwh = [e for e in entries if e.strong_base == "H3068"]
        assert len(yhwh) >= 1
        assert any("Yahweh" in (e.gloss_brief or "") or "LORD" in (e.gloss_brief or "")
                   or "יְהוָה" in e.lemma for e in yhwh)

    def test_sub_acepciones_con_sufijo_mayuscula(self, entries):
        """En TBESH, ~40% de las entries tienen sufijo de desambiguación
        (mayúscula en uStrong: ``H1G``, ``H22G``, ``H121H``). Si bajan
        muchísimo, es señal de que el parser perdió filas (regresión)."""
        with_suffix = [e for e in entries if e.strong_extended != e.strong_base]
        assert len(with_suffix) > 3000, (
            f"esperaba >3000 entries con sufijo de desambiguación, vi {len(with_suffix)}"
        )
