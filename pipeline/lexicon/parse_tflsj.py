"""Parser para TFLSJ — *Translators Formatted Full LSJ Bible Lexicon* (STEPBible).

TFLSJ es Liddell-Scott-Jones (1940) re-formateado por Tyndale House con
abreviaturas expandidas, fechas de autores, y referencias bíblicas
hipervinculadas. Es la fuente más extensa de las disponibles: definiciones
de hasta 70 KB por entry para palabras de alta frecuencia, con citas de
autores griegos clásicos, papiros, y comparaciones cross-language.

Comparte el formato 8-columnas TSV de TBESG/TBESH (mismo schema upstream
desde Tyndale), así que el parser **es simplemente una llamada a
``parse_tbes_file`` con ``source="lsj"``**. Lo expongo como módulo separado
con su propio nombre para que el build script y los tests dejen claro qué
está procesando.

Upstream split en dos archivos:

- ``TFLSJ_0-5624.txt``: códigos Strong ≤ G5624 (rango clásico del NT).
- ``TFLSJ_extra.txt``: códigos > G5999 (variantes, palabras LXX-only,
  griego del Antiguo Testamento).

El caller pasa los dos paths e itera ambos (la función no fusiona porque
mantener archivos separados facilita el testing y debugging de cada rango).

Tamaño post-parseo: ~20 MB de definiciones plain text en total. Para el .bb
final esto requiere decisión en P.5: incluir completo, truncar o servir como
descarga separada opcional.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from .parse_tbes import BriefLexiconEntry, parse_tbes_file


def parse_tflsj_file(path: Path) -> Iterator[BriefLexiconEntry]:
    """Itera las entradas del TFLSJ. Mismo schema que TBES, distinta
    ``source``."""
    yield from parse_tbes_file(path, "grc", source="lsj")
