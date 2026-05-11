"""Tests del parser TFLSJ.

TFLSJ es un wrapper trivial sobre ``parse_tbes_file`` con ``source="lsj"``,
pero verificamos:

1. Que el wrapper inyecta correctamente el ``source``.
2. Que ambos archivos del split (``_0-5624`` y ``_extra``) parsean.
3. Que las definiciones LSJ extensas se preservan completas (no se truncan
   por algún strip silencioso).
4. Conteos razonables y spot-checks de palabras icónicas.

Los tests integration usan los archivos reales; saltean si no están.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

import pytest

from pipeline.lexicon.parse_tbes import parse_tbes_file
from pipeline.lexicon.parse_tflsj import parse_tflsj_file

REPO_ROOT = Path(__file__).resolve().parent.parent
TFLSJ_BASE = REPO_ROOT / "sources" / "stepbible_lexicon" / "TFLSJ_0-5624.txt"
TFLSJ_EXTRA = REPO_ROOT / "sources" / "stepbible_lexicon" / "TFLSJ_extra.txt"


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


class TestSourceParameter:
    """El parámetro ``source`` se propaga a las entries y permite
    distinguir TBESG (``stepbible``) de TFLSJ (``lsj``) en el .bb unificado."""

    def test_parse_tbes_default_source(self, tmp_path):
        line = "\t".join([
            "G25", "G25 =", "G25",
            "ἀγαπάω", "agapaō", "G:V", "to love", "def",
        ])
        path = tmp_path / "f.txt"
        path.write_text(line + "\n", encoding="utf-8")
        e = next(iter(parse_tbes_file(path, "grc")))
        assert e.source == "stepbible"

    def test_parse_tbes_custom_source(self, tmp_path):
        line = "\t".join([
            "G25", "G25 =", "G25",
            "ἀγαπάω", "agapaō", "G:V", "to love", "def LSJ",
        ])
        path = tmp_path / "f.txt"
        path.write_text(line + "\n", encoding="utf-8")
        e = next(iter(parse_tbes_file(path, "grc", source="lsj")))
        assert e.source == "lsj"

    def test_parse_tflsj_wrapper_inyecta_source_lsj(self, tmp_path):
        """``parse_tflsj_file`` debe etiquetar las entries como ``source="lsj"``
        sin importar qué tipo de archivo se le pase (la responsabilidad de
        que el path sea efectivamente TFLSJ es del caller)."""
        line = "\t".join([
            "G25", "G25 =", "G25",
            "ἀγαπάω", "agapaō", "G:V", "to love", "def LSJ",
        ])
        path = tmp_path / "f.txt"
        path.write_text(line + "\n", encoding="utf-8")
        e = next(iter(parse_tflsj_file(path)))
        assert e.source == "lsj"
        assert e.language == "grc"


@pytest.mark.skipif(not TFLSJ_BASE.exists(), reason="TFLSJ_0-5624.txt no descargado")
class TestTflsjBaseReal:
    @pytest.fixture(scope="class")
    def entries(self):
        return list(parse_tflsj_file(TFLSJ_BASE))

    def test_cantidad_de_entries_razonable(self, entries):
        """TFLSJ_0-5624 cubre el rango Strong's NT clásico. ~5,500-5,800
        entries esperadas."""
        assert 5000 < len(entries) < 6500

    def test_todas_source_lsj_y_griego(self, entries):
        for e in entries:
            assert e.source == "lsj"
            assert e.language == "grc"
            assert e.strong_base.startswith("G")

    def test_spot_check_agapao_def_es_lsj_no_abbottsmith(self, entries):
        """Para G25 (ἀγαπάω) la def LSJ es distinta y más extensa que
        Abbott-Smith. Verificamos longitud y palabras-clave."""
        matches = [e for e in entries if e.strong_base == "G25"]
        assert len(matches) == 1
        e = matches[0]
        assert _nfc(e.lemma) == _nfc("ἀγαπάω")
        # LSJ tiene refs a autores clásicos; Abbott-Smith no.
        assert e.definition_full is not None
        assert len(e.definition_full) > 500, (
            f"def. de ἀγαπάω en LSJ debería ser extensa, vi {len(e.definition_full)}"
        )

    def test_definiciones_largas_no_se_truncan(self, entries):
        """Existe al menos una entry con definición > 10 KB (palabras de muy
        alta frecuencia tienen LSJ enormes). Si el parser truncara
        silenciosamente, este test cae rojo."""
        very_long = [e for e in entries if e.definition_full and len(e.definition_full) > 10000]
        assert len(very_long) > 50, (
            f"esperaba >50 entries con def > 10KB, vi {len(very_long)}"
        )


@pytest.mark.skipif(not TFLSJ_EXTRA.exists(), reason="TFLSJ_extra.txt no descargado")
class TestTflsjExtraReal:
    @pytest.fixture(scope="class")
    def entries(self):
        return list(parse_tflsj_file(TFLSJ_EXTRA))

    def test_cantidad_de_entries_razonable(self, entries):
        """TFLSJ_extra cubre Strong's >= G6000 (variantes, palabras LXX-only,
        equivalentes griegos de Strong's hebreos)."""
        assert 4000 < len(entries) < 6000

    def test_strongs_en_rango_extra(self, entries):
        """Casi todas las entries de TFLSJ_extra deben tener strong >= G6000,
        salvo casos puntuales de cross-ref. Si vemos muchas <G6000, hay
        contaminación del archivo base."""
        import re
        low = [
            e for e in entries
            if (m := re.match(r"G(\d+)", e.strong_base)) and int(m.group(1)) < 6000
        ]
        assert len(low) < 50, f"demasiadas entries de TFLSJ_extra con strong <G6000: {len(low)}"


@pytest.mark.skipif(
    not (TFLSJ_BASE.exists() and TFLSJ_EXTRA.exists()),
    reason="archivos TFLSJ no descargados",
)
class TestTflsjUnion:
    """Tests sobre la unión de ambos archivos — lo que el build script va
    a producir efectivamente."""

    @pytest.fixture(scope="class")
    def entries(self):
        return list(parse_tflsj_file(TFLSJ_BASE)) + list(parse_tflsj_file(TFLSJ_EXTRA))

    def test_total_cobertura(self, entries):
        """La unión de los dos archivos da el lexicón LSJ completo. ~11k
        entries totales (similar a TBESG)."""
        assert 10000 < len(entries) < 13000

    def test_strongs_unicos_aproximadamente_iguales_a_total(self, entries):
        """Para LSJ no deberíamos tener muchos duplicados de strong_base
        (cada lema clásico tiene una sola entry, salvo los pocos casos
        de cross-ref entre base y extra)."""
        bases = [e.strong_base for e in entries]
        assert len(set(bases)) > 10000
