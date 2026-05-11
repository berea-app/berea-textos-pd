"""Utilidades compartidas por los parsers de léxico y alineamiento.

Dos responsabilidades:

1. **Mapeo de abreviaturas STEPBible → ``book_id`` Berea.** STEPBible usa
   abreviaturas Title-case de 3 caracteres (``Gen``, ``Sng``, ``1Sa``, ``Jhn``).
   Berea usa USFM 3.0 lowercase (``gen``, ``sng``, ``1sa``, ``jhn``). El mapeo
   es prácticamente ``str.title()`` reversible, pero lo hardcodeamos para
   detectar errores y proteger contra cambios silenciosos del upstream.

2. **Normalización de códigos Strong's "extendidos".** STEPBible usa el sistema
   de Tyndale House: ``G25`` (base) y ``G25a`` / ``G25b`` (sub-acepciones).
   La app necesita ambas formas: el código base para lookups de lexicón, el
   extendido para desambiguar variantes en un mismo versículo.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Book IDs
# ---------------------------------------------------------------------------

# STEPBible (TAGNT/TAHOT) → Berea book_id (USFM 3.0 lowercase).
# Cobertura: 66 libros del canon protestante (39 AT + 27 NT).
STEPBIBLE_TO_BOOK_ID: dict[str, str] = {
    # --- AT (Tanaj / OT) ---
    "Gen": "gen", "Exo": "exo", "Lev": "lev", "Num": "num", "Deu": "deu",
    "Jos": "jos", "Jdg": "jdg", "Rut": "rut", "1Sa": "1sa", "2Sa": "2sa",
    "1Ki": "1ki", "2Ki": "2ki", "1Ch": "1ch", "2Ch": "2ch",
    "Ezr": "ezr", "Neh": "neh", "Est": "est",
    "Job": "job", "Psa": "psa", "Pro": "pro", "Ecc": "ecc", "Sng": "sng",
    "Isa": "isa", "Jer": "jer", "Lam": "lam", "Ezk": "ezk", "Dan": "dan",
    "Hos": "hos", "Jol": "jol", "Amo": "amo", "Oba": "oba", "Jon": "jon",
    "Mic": "mic", "Nam": "nam", "Hab": "hab", "Zep": "zep",
    "Hag": "hag", "Zec": "zec", "Mal": "mal",
    # --- NT ---
    "Mat": "mat", "Mrk": "mrk", "Luk": "luk", "Jhn": "jhn", "Act": "act",
    "Rom": "rom", "1Co": "1co", "2Co": "2co", "Gal": "gal", "Eph": "eph",
    "Php": "php", "Col": "col", "1Th": "1th", "2Th": "2th",
    "1Ti": "1ti", "2Ti": "2ti", "Tit": "tit", "Phm": "phm",
    "Heb": "heb", "Jas": "jas", "1Pe": "1pe", "2Pe": "2pe",
    "1Jn": "1jn", "2Jn": "2jn", "3Jn": "3jn", "Jud": "jud", "Rev": "rev",
}


def stepbible_to_book_id(abbr: str) -> str | None:
    """Mapea una abreviatura STEPBible (e.g. ``"Jhn"``) al ``book_id`` Berea.

    Retorna ``None`` si la abreviatura no pertenece al canon de 66 libros
    (puede ser deuterocanónico o abreviatura desconocida). Los parsers deben
    filtrar silenciosamente las filas con resultado ``None`` para tolerar
    futuras expansiones del upstream sin romper el build.
    """
    return STEPBIBLE_TO_BOOK_ID.get(abbr)


# ---------------------------------------------------------------------------
# Strong's codes
# ---------------------------------------------------------------------------

# G/H seguido de uno o más dígitos, opcionalmente con una letra como sufijo
# de desambiguación. STEPBible emite sufijos en dos convenciones distintas:
#   - **minúscula** (``H0122a``, ``H0176b``): usada en eStrong para distinguir
#     homógrafos consonánticos con vocalización distinta (BDB-style).
#   - **mayúscula** (``G2264G``, ``H0001G``): usada en dStrong / uStrong para
#     distinguir personas/lugares/significados (Tyndale's Disambiguated).
# Ambas son válidas y representan desambiguaciones legítimas — el regex acepta
# las dos, el caller distingue por contexto (columna del TSV).
_STRONG_RE = re.compile(r"^([GH])(\d+)([a-zA-Z])?$")


def normalize_strong(code: str) -> tuple[str, str]:
    """Separa un código Strong's en ``(base, extended)``.

    Ejemplos:

    >>> normalize_strong("G25")
    ('G25', 'G25')
    >>> normalize_strong("G25a")
    ('G25', 'G25a')
    >>> normalize_strong("H1234b")
    ('H1234', 'H1234b')

    El código base normaliza ceros a la izquierda (STEPBible emite ``G0025``
    en algunas columnas y ``G25`` en otras; usamos siempre la forma sin
    padding porque es la convención del lookup en runtime).

    Acepta indistintamente las formas ``G25`` y ``G0025``. Rechaza el resto
    con ``ValueError``: códigos malformados son típicamente bugs del parser
    y queremos verlos rápido, no enmascararlos.
    """
    if not code:
        raise ValueError("código Strong's vacío")
    m = _STRONG_RE.match(code)
    if not m:
        raise ValueError(f"código Strong's inválido: {code!r}")
    prefix, digits, suffix = m.group(1), m.group(2), m.group(3) or ""
    # Quitar padding de ceros: G0025 → G25, pero G0 (= no aplica) se mantiene.
    digits_int = int(digits)
    base = f"{prefix}{digits_int}"
    extended = f"{base}{suffix}"
    return base, extended


def strong_base(code: str) -> str:
    """Atajo: devuelve solo la forma base de un Strong's code."""
    return normalize_strong(code)[0]


def strong_extended(code: str) -> str:
    """Atajo: devuelve la forma extendida (con sufijo si aplica)."""
    return normalize_strong(code)[1]


# ---------------------------------------------------------------------------
# Helpers de parsing TAGNT/TAHOT
# ---------------------------------------------------------------------------

# Referencia con posición de palabra: ``Mat.1.2#17=NKO`` o ``Gen.1.1#3``.
# Captura book, chapter, verse, word_position; ignora el sufijo ``=...``.
TAGNT_REF_RE = re.compile(
    r"^(?P<book>[A-Za-z0-9]{3})\.(?P<chapter>\d+)\.(?P<verse>\d+)"
    r"#(?P<word>\d+)(?:=\S+)?\s*$"
)


def parse_tagnt_ref(ref: str) -> tuple[str, int, int, int] | None:
    """Parsea una referencia TAGNT/TAHOT ``Book.Ch.V#Pos`` a tupla.

    Retorna ``(book_id, chapter, verse, position)`` o ``None`` si la
    referencia es malformada o el libro no pertenece al canon Berea.
    """
    m = TAGNT_REF_RE.match(ref.strip())
    if not m:
        return None
    book_id = stepbible_to_book_id(m.group("book"))
    if book_id is None:
        return None
    return book_id, int(m.group("chapter")), int(m.group("verse")), int(m.group("word"))


# Combinación ``G0080=N-APM`` (Strong's "extendido" + morfología).
STRONG_MORPH_RE = re.compile(r"^(?P<strong>[GH]\d+[a-z]?)=(?P<morph>.+)$")


def parse_strong_morph(field: str) -> tuple[str, str] | None:
    """Parsea ``"G0080=N-APM"`` en ``("G0080", "N-APM")``.

    El código retornado NO está normalizado todavía — pasarlo por
    ``normalize_strong()`` si el consumidor necesita la separación
    base/extendida.
    """
    m = STRONG_MORPH_RE.match(field.strip())
    if not m:
        return None
    return m.group("strong"), m.group("morph")


# Lema con glosa: ``ἀδελφός=brother``. STEPBible separa con ``=``.
LEMMA_GLOSS_RE = re.compile(r"^(?P<lemma>[^=]+)=(?P<gloss>.+)$")


def parse_lemma_gloss(field: str) -> tuple[str, str] | None:
    """Parsea ``"ἀδελφός=brother"`` en ``("ἀδελφός", "brother")``.

    Retorna ``None`` si el campo no tiene el separador ``=``. STEPBible a
    veces deja la columna vacía o solo con el lema; en esos casos el caller
    debe decidir si descarta la fila o usa fallback.
    """
    m = LEMMA_GLOSS_RE.match(field.strip())
    if not m:
        return None
    return m.group("lemma").strip(), m.group("gloss").strip()


# Transliteración entre paréntesis al final de la palabra griega/hebrea:
# ``"ἀδελφοὺς (adelphous)"`` → palabra=``ἀδελφοὺς``, translit=``adelphous``.
TRANSLIT_RE = re.compile(r"^(?P<word>\S+?)\s*\((?P<translit>[^)]+)\)\s*$")


def strip_translit(field: str) -> tuple[str, str | None]:
    """Separa palabra original de la transliteración que TAGNT/TAHOT pega
    al final.

    Si el campo no tiene paréntesis, retorna ``(field, None)``.
    """
    field = field.strip()
    m = TRANSLIT_RE.match(field)
    if not m:
        return field, None
    return m.group("word").strip(), m.group("translit").strip()
