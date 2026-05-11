"""Tests de ``pipeline/lexicon/common.py``.

Cubre los dos núcleos del módulo: mapeo book_id (cobertura completa de los
66 libros del canon Berea) y normalización de códigos Strong's (todos los
formatos que STEPBible emite en producción)."""

from __future__ import annotations

import pytest

from pipeline.canon import load_canon_66
from pipeline.lexicon.common import (
    STEPBIBLE_TO_BOOK_ID,
    normalize_strong,
    parse_lemma_gloss,
    parse_strong_morph,
    parse_tagnt_ref,
    stepbible_to_book_id,
    strip_translit,
    strong_base,
    strong_extended,
)

# ---------------------------------------------------------------------------
# Mapeo book_id
# ---------------------------------------------------------------------------


class TestBookIdMapping:
    def test_cubre_los_66_libros_del_canon(self):
        """El mapeo debe cubrir los 66 libros del canon protestante. Si
        faltara uno, los parsers TAGNT/TAHOT descartarían silenciosamente sus
        filas y el ``.bb`` resultante tendría agujeros. Test fuerte y barato.
        """
        canon_ids = {b.book_id for b in load_canon_66()}
        mapped_ids = set(STEPBIBLE_TO_BOOK_ID.values())
        faltantes = canon_ids - mapped_ids
        assert not faltantes, f"book_ids del canon sin mapeo STEPBible: {sorted(faltantes)}"

    def test_no_hay_book_ids_inventados(self):
        """Inversa: ningún valor del mapeo debería caer fuera del canon."""
        canon_ids = {b.book_id for b in load_canon_66()}
        mapped_ids = set(STEPBIBLE_TO_BOOK_ID.values())
        sobrantes = mapped_ids - canon_ids
        assert not sobrantes, f"mapeo apunta a book_ids fuera del canon: {sorted(sobrantes)}"

    def test_no_hay_book_ids_duplicados(self):
        """Dos abreviaturas STEPBible distintas no pueden mapear al mismo
        book_id (sería bug del mapping table)."""
        mapped = list(STEPBIBLE_TO_BOOK_ID.values())
        duplicados = {b for b in mapped if mapped.count(b) > 1}
        assert not duplicados, f"book_ids duplicados en el mapeo: {sorted(duplicados)}"

    @pytest.mark.parametrize(
        "abbr,book_id",
        [
            ("Gen", "gen"),     # AT primer libro
            ("Mal", "mal"),     # AT último libro
            ("Mat", "mat"),     # NT primer libro
            ("Rev", "rev"),     # NT último libro
            ("Sng", "sng"),     # Cantares (no "Sos")
            ("Ezk", "ezk"),     # Ezequiel (no "Eze")
            ("Jol", "jol"),     # Joel
            ("Jhn", "jhn"),     # Juan (no "Joh")
            ("Php", "php"),     # Filipenses (no "Phl")
            ("Mrk", "mrk"),     # Marcos (no "Mar")
            ("1Sa", "1sa"),     # numéricos OT
            ("2Ki", "2ki"),
            ("1Co", "1co"),     # numéricos NT
            ("3Jn", "3jn"),
        ],
    )
    def test_casos_críticos(self, abbr, book_id):
        assert stepbible_to_book_id(abbr) == book_id

    def test_devuelve_none_para_abreviatura_desconocida(self):
        """Deuterocanónicos o malformados no rompen el mapping; el caller
        decide qué hacer."""
        assert stepbible_to_book_id("Tob") is None    # Tobías (no en canon 66)
        assert stepbible_to_book_id("XXX") is None
        assert stepbible_to_book_id("") is None


# ---------------------------------------------------------------------------
# Normalización Strong's
# ---------------------------------------------------------------------------


class TestNormalizeStrong:
    @pytest.mark.parametrize(
        "code,expected_base,expected_extended",
        [
            # Forma básica
            ("G25", "G25", "G25"),
            ("H1234", "H1234", "H1234"),
            # Con sufijo de desambiguación (minúscula = eStrong style)
            ("G25a", "G25", "G25a"),
            ("H1234b", "H1234", "H1234b"),
            ("G3588c", "G3588", "G3588c"),
            # Con sufijo de desambiguación (mayúscula = dStrong/uStrong style)
            ("G2264G", "G2264", "G2264G"),
            ("H0001G", "H1", "H1G"),
            ("G0032H", "G32", "G32H"),
            # Padding de ceros (STEPBible lo usa mixto)
            ("G0025", "G25", "G25"),
            ("G0025a", "G25", "G25a"),
            ("H0001", "H1", "H1"),
            ("G0080", "G80", "G80"),
            # Códigos altos
            ("G5624", "G5624", "G5624"),
            ("H8674", "H8674", "H8674"),
        ],
    )
    def test_separa_base_y_extendido(self, code, expected_base, expected_extended):
        base, extended = normalize_strong(code)
        assert base == expected_base
        assert extended == expected_extended

    def test_quita_ceros_a_la_izquierda(self):
        """G0025 y G25 deben colapsar al mismo base. Si no lo hicieran, el
        lookup en la app fallaría dependiendo de qué columna del TSV vino
        el código."""
        assert normalize_strong("G0025") == normalize_strong("G25")
        assert normalize_strong("G0025a") == normalize_strong("G25a")

    @pytest.mark.parametrize("invalid", ["", "25", "G", "Ga25", "G25AB", "G-25", "X25", "g25"])
    def test_rechaza_codigos_invalidos(self, invalid):
        """Códigos malformados son bugs del parser. Mejor fallar ruidosamente
        que enmascarar."""
        with pytest.raises(ValueError):
            normalize_strong(invalid)

    def test_atajos_strong_base_extended(self):
        assert strong_base("G0025a") == "G25"
        assert strong_extended("G0025a") == "G25a"


# ---------------------------------------------------------------------------
# Helpers de parsing TAGNT
# ---------------------------------------------------------------------------


class TestParseTagntRef:
    @pytest.mark.parametrize(
        "ref,expected",
        [
            ("Mat.1.2#17", ("mat", 1, 2, 17)),
            ("Mat.1.2#17=NKO", ("mat", 1, 2, 17)),
            ("Gen.1.1#1", ("gen", 1, 1, 1)),
            ("Rev.22.21#5=NKO", ("rev", 22, 21, 5)),
            ("3Jn.1.14#3", ("3jn", 1, 14, 3)),
            ("Psa.150.6#10=NKO", ("psa", 150, 6, 10)),
        ],
    )
    def test_parsea_referencias_validas(self, ref, expected):
        assert parse_tagnt_ref(ref) == expected

    @pytest.mark.parametrize(
        "ref",
        [
            "Mat.1.2",          # sin #pos
            "Mat.1#17",         # sin verso
            "XXX.1.1#1",        # libro desconocido
            "Tob.1.1#1",        # deuterocanónico (fuera de canon 66)
            "",
            "garbage",
        ],
    )
    def test_devuelve_none_para_malformados(self, ref):
        assert parse_tagnt_ref(ref) is None


class TestParseStrongMorph:
    @pytest.mark.parametrize(
        "field,expected",
        [
            ("G0080=N-APM", ("G0080", "N-APM")),
            ("G3588=T-ASM", ("G3588", "T-ASM")),
            ("G25a=V-AAI-3S", ("G25a", "V-AAI-3S")),
            ("H1234=HVqp3ms", ("H1234", "HVqp3ms")),
        ],
    )
    def test_parsea(self, field, expected):
        assert parse_strong_morph(field) == expected

    def test_devuelve_none_sin_igual(self):
        assert parse_strong_morph("G0080") is None
        assert parse_strong_morph("") is None


class TestParseLemmaGloss:
    def test_parsea_griego(self):
        assert parse_lemma_gloss("ἀδελφός=brother") == ("ἀδελφός", "brother")

    def test_parsea_hebreo(self):
        # יָדַע = "to know"
        assert parse_lemma_gloss("יָדַע=to know") == ("יָדַע", "to know")

    def test_trim_de_espacios(self):
        assert parse_lemma_gloss("  ἀγαπάω  =  to love  ") == ("ἀγαπάω", "to love")

    def test_devuelve_none_sin_igual(self):
        assert parse_lemma_gloss("ἀγαπάω") is None


class TestStripTranslit:
    def test_extrae_translit_griega(self):
        assert strip_translit("ἀδελφοὺς (adelphous)") == ("ἀδελφοὺς", "adelphous")

    def test_sin_parentesis_devuelve_palabra_intacta(self):
        assert strip_translit("ἀδελφοὺς") == ("ἀδελφοὺς", None)

    def test_strip_de_puntuacion_residual_no_es_responsabilidad_aqui(self):
        """``strip_translit`` solo separa palabra de translit. Si la palabra
        viene con puntuación pegada (``"αὐτοῦ· (autou)"``), eso queda en la
        palabra — el caller decide si lo limpia."""
        word, translit = strip_translit("αὐτοῦ· (autou)")
        assert translit == "autou"
        assert word == "αὐτοῦ·"
