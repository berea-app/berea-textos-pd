"""Parser para los lexicones breves de STEPBible: TBESG (griego) y TBESH (hebreo).

Ambos archivos comparten la misma estructura — 8 columnas TSV con header largo
explicativo — así que un solo parser parametrizado por ``language`` sirve para
los dos. La diferencia operativa entre TBESG y TBESH es:

- prefijo del código Strong's (``G…`` vs ``H…``);
- prefijo morfológico (``G:N-LI`` vs ``H:N-M``, con casos mixtos en TBESH);
- en TBESG existen secciones decorativas ``$========== PERSON(s)`` con filas
  ``- Named`` / ``- Group`` que no son entries léxicas y se descartan.

Columnas del TSV (1-indexed):

  1. eStrong#: código base con sufijo opcional minúscula (``H0122a``).
  2. dStrong:  Disambiguated Strong's con texto explicativo
               (``G0001G =``, ``G2264G = the Greek of``).
  3. uStrong:  Unified Strong's (el código canónico que usa Berea para lookup).
  4. Greek/Hebrew: lema en script original (puede traer variantes con coma).
  5. Transliteration.
  6. Morph: código morfológico abreviado.
  7. Gloss: glosa breve en una o pocas palabras.
  8. Definition: definición completa (Abbott-Smith para griego; BDB resumido
     para hebreo). Trae HTML inline (``<b>``, ``<br>``, ``<ref=...>``).

El parser preserva los 4 últimos campos sin tocarlos — limpiar el HTML es
responsabilidad del empaquetador (P.5) o de la app, según convenga.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from .common import normalize_strong

# Captura el primer código Strong's al inicio de un string. STEPBible emite a
# veces uStrong "compuesto" como ``H0022G (H0001I+H1391)`` para nombres de
# múltiples palabras o ``H2438H,`` con coma residual. Tomamos solo el primer
# código bien formado (``H0022G`` / ``H2438H``) y descartamos el resto.
_STRONG_HEAD_RE = re.compile(r"^([GH]\d+[a-zA-Z]?)")


@dataclass(frozen=True)
class BriefLexiconEntry:
    """Entrada de lexicón breve (TBESG / TBESH).

    Una fila del TSV produce una sola ``BriefLexiconEntry``. Si el mismo
    ``strong_base`` tiene varias sub-acepciones (``G2264G``, ``G2264H``,
    ``G2264I`` para los tres Herodes), cada una es una entry independiente
    con el MISMO ``strong_base`` y DISTINTO ``strong_extended``.

    Convención de columnas STEPBible mapeadas a los campos:

    - ``strong_base``    ← eStrong (col 1, código histórico). Es la clave que
      usa el TAGNT/TAHOT en su columna ``Word=Grammar``; por tanto la app
      busca aquí cuando renderiza una palabra desde el alineamiento.
    - ``strong_extended`` ← uStrong (col 3, código unificado). Distingue
      sub-acepciones. Para palabras griegas que son préstamos del hebreo
      (``Ἀαρών`` G0002 → uStrong H0175), el extended puede tener prefijo
      distinto del base; eso es intencional — preserva el cross-ref.
    """

    strong_base: str          # "G25" / "G2264" (siempre eStrong normalizado)
    strong_extended: str      # "G25" / "G2264G" / "H175" — uStrong normalizado
    lemma: str                # "ἀγαπάω" / "אַהֲרֹן"
    transliteration: str | None
    morph: str | None
    gloss_brief: str          # glosa corta, ya en inglés
    definition_full: str | None  # def. extendida con HTML del upstream
    language: str             # "grc" / "hbo"
    source: str = "stepbible"  # constante para este parser — útil al unificar


# Línea de datos: empieza con prefijo (G|H), dígitos, sufijo minúscula opcional
# y tab. Esto descarta tanto las líneas de header como las decorativas.
_DATA_LINE_RE = re.compile(r"^[GH]\d+[a-z]?\t")


def _clean_or_none(value: str | None) -> str | None:
    """Strip + colapsa a ``None`` si quedó vacío. STEPBible deja columnas
    con ``""`` o solo espacios en casos sin info; queremos representar esa
    ausencia explícitamente."""
    if value is None:
        return None
    s = value.strip()
    return s or None


def _parse_line(line: str, language: str, source: str) -> BriefLexiconEntry | None:
    """Parsea una fila de datos TSV. Retorna ``None`` si la fila está
    malformada — preferimos un skip silencioso que romper el batch entero,
    pero el caller debe contar los skips para detectar regresiones."""
    cols = line.rstrip("\n").split("\t")
    if len(cols) < 7:
        return None

    # **eStrong (col 1)** es el código histórico de Strong's; lo usamos como
    # ``strong_base`` porque es lo que el TAGNT/TAHOT emite en su columna
    # ``Word=Grammar`` (e.g. ``G0080=N-APM``). El lookup desde el alineamiento
    # entra por esta clave.
    e_strong_raw = cols[0].strip()
    # **uStrong (col 3)** es Tyndale's Unified Strong's: distingue
    # sub-acepciones (personas homónimas, polisemias) con sufijos
    # mayúscula/minúscula. Lo usamos como ``strong_extended`` — permite a la
    # app desambiguar cuando el TAGNT trae el sufijo, y agrupar cuando no.
    u_strong_raw = cols[2].strip()
    if not e_strong_raw or not u_strong_raw:
        return None

    # uStrong a veces viene "compuesto" para nombres multi-palabra o con
    # coma residual del upstream — extraer solo el primer código bien formado.
    m = _STRONG_HEAD_RE.match(u_strong_raw)
    if m is None:
        return None
    u_strong_clean = m.group(1)

    try:
        base, _ = normalize_strong(e_strong_raw)
        _, extended = normalize_strong(u_strong_clean)
    except ValueError:
        return None

    lemma = cols[3].strip()
    if not lemma:
        return None

    transliteration = _clean_or_none(cols[4])
    morph = _clean_or_none(cols[5])
    gloss_brief = cols[6].strip()
    if not gloss_brief:
        # Sin glosa la entry no aporta valor mostrable. STEPBible rara vez
        # deja esta columna vacía, pero ocurre en algunos nombres propios.
        return None

    # def_full es opcional — TBESG la trae para ~95% de las entries, TBESH
    # para casi todas pero algunas vienen vacías cuando la fuente Abbott-Smith
    # / BDB resumido no la cubre.
    definition_full = _clean_or_none(cols[7]) if len(cols) > 7 else None

    return BriefLexiconEntry(
        strong_base=base,
        strong_extended=extended,
        lemma=lemma,
        transliteration=transliteration,
        morph=morph,
        gloss_brief=gloss_brief,
        definition_full=definition_full,
        language=language,
        source=source,
    )


def parse_tbes_file(
    path: Path, language: str, *, source: str = "stepbible"
) -> Iterator[BriefLexiconEntry]:
    """Itera las entradas léxicas de un archivo TBESG o TBESH.

    ``language``: ``"grc"`` para TBESG, ``"hbo"`` para TBESH. El parser no
    valida que el prefijo de los códigos (``G``/``H``) coincida con el
    ``language``: cargar TBESH como ``"grc"`` produce entries con códigos H
    pero la app va a fallar el lookup. El caller (build script) es quien
    elige el ``language`` correcto.

    ``source``: etiqueta que se inyecta en cada entry para distinguir fuentes
    al unificar en el ``.bb`` final. Default ``"stepbible"`` para TBESG/TBESH.
    Los archivos TFLSJ (LSJ formateado) usan el mismo formato y se parsean
    con esta misma función pasando ``source="lsj"``.

    Filtros silenciosos:

    - Header inicial (líneas hasta la primera fila de datos).
    - Secciones decorativas ``$========== ...`` (3 ocurrencias en TBESG).
    - Filas auxiliares ``- Named`` / ``- Group`` (4 en TBESG, sub-entradas
      de personas que repiten data ya capturada en la línea principal).
    - Líneas vacías.
    """
    with path.open("r", encoding="utf-8-sig") as f:
        for raw in f:
            if not _DATA_LINE_RE.match(raw):
                continue
            entry = _parse_line(raw, language, source)
            if entry is not None:
                yield entry
