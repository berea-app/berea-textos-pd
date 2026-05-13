"""Parser TAHOT con extracción palabra-a-palabra para alineamiento AT hebreo.

TAHOT es el equivalente AT del TAGNT — pero con diferencias estructurales
significativas porque el AT hebreo tiene una sola "edición principal"
(texto Leningrad) y los problemas textuales se anotan como variantes (Qere,
Ketiv, restored, LXX-suplido).

Diferencias clave vs TAGNT:

- **Una edición única**: no hay WH/Treg/TR. El texto es Leningrad + corrections
  Tyndale. Berea lo mapea a la única Biblia hebrea del catálogo: ``wlc``.
- **Tipo de texto por fila**: el sufijo ``=L``, ``=Q``, ``=R``, ``=X`` indica
  qué tradición textual representa esa palabra. WLC moderno usa **L y Q**
  (Leningrad + Qere) como texto principal. R (restored) y X (supplied from
  LXX) son palabras que el WLC NO contiene como texto principal, así que el
  parser los DESCARTA.
- **Segmentación morfológica con ``/``**: las palabras hebreas se separan en
  prefijos + raíz + sufijos. ``וְ/הָ/אָ֗רֶץ`` = conjunción + artículo + tierra.
  Para el word_original del alineamiento usamos la palabra continua (sin ``/``).
- **Strong por palabra**: usamos la columna ``Root dStrong+Instance`` (col 9)
  que ya tiene solo el Strong's del root, sin los prefijos. Strippeamos los
  Instance markers (``_A``, ``_B``) que son metadatos no léxicos.

Columnas TSV (1-indexed) del TAHOT:

  1. ``Eng (Heb) Ref & Type``: ``Gen.1.1#01=L``
  2. ``Hebrew``: ``בְּ/רֵאשִׁ֖ית`` (con / como separador morfológico)
  3. ``Transliteration``: ``be./re.Shit``
  4. ``Translation``: ``in/ beginning``
  5. ``dStrongs``: ``H9003/{H7225G}`` (Strong por elemento)
  6. ``Grammar`` (morph): ``HR/Ncfsa``
  7. ``Meaning Variants``
  8. ``Spelling Variants``
  9. ``Root dStrong+Instance``: ``H7225G`` (solo root, posible Instance ``_A``)
  10. ``Alternative Strongs+Instance``
  11. ``Conjoin word``
  12. ``Expanded Strong tags``: texto enriquecido con lema y glosas.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from pathlib import Path

from .common import normalize_strong, parse_tagnt_ref
from .parse_alignment_tagnt import WordAlignment

# Tipos de fila TAHOT que conservamos. WLC moderno usa L (Leningrad) y Q
# (Qere reading) como texto principal. Descartamos X (suplido de LXX) y R
# (restored desde paralelos) porque el WLC no los contiene como texto.
_KEEP_TYPE_RE = re.compile(r"^[LQ]")

# Línea de datos: ``Gen.1.1#01=<type>\t``. El type debe empezar con L o Q.
_DATA_LINE_RE = re.compile(
    r"^[A-Za-z0-9]{3}\.\d+\.\d+#\d+=[LQ]\S*\t"
)

# Strong's "extendido" con posibles Instance markers (``_A``, ``_b``). Solo
# queremos la parte base + sufijo de desambiguación, sin Instance.
_STRONG_HEAD_RE = re.compile(r"^([GH]\d+[a-zA-Z]?)")

# Lemma y glosa están dentro del "Expanded Strong tags" (col 12), formato
# ``{H7225G=רֵאשִׁית=: beginning»first:1_beginning}`` o
# ``H9003=ב=in/{H7225G=...}``. Extraemos el primer match del root (entre
# llaves) — es la palabra principal.
_ROOT_LEMMA_RE = re.compile(
    r"\{(?P<strong>[GH]\d+[a-zA-Z]?)=(?P<lemma>[^=}]+)=(?P<gloss>[^}]+)\}"
)


def _strip_morph_segments(value: str) -> str:
    """Strippea los separadores ``/`` y ``\\`` y los espacios excedentes.

    TAHOT usa ``/`` para separar morfemas (prefijos/raíz/sufijos) y ``\\``
    para separar puntuación. Para el word_original/gloss queremos la
    palabra continua, sin esos marcadores.

    Ejemplos:
        ``"בְּ/רֵאשִׁ֖ית"`` → ``"בְּרֵאשִׁ֖ית"``
        ``"in/ beginning"`` → ``"in beginning"`` (espacios respetados)
        ``"עַל\\־"``         → ``"עַל־"``
    """
    # Strippeamos separadores pero respetando los espacios que vienen tras
    # el ``/`` en glosas en inglés (``"in/ beginning"`` → ``"in beginning"``).
    cleaned = value.replace("/", "").replace("\\", "")
    # Colapsar runs de whitespace.
    return " ".join(cleaned.split())


def _extract_root_strong(col9: str) -> str | None:
    """``H7225G`` o ``H0853_A`` → ``H7225G`` / ``H853``. Strippea el Instance
    marker y normaliza el padding de ceros a la forma sin padding del léxico
    (``H0853`` → ``H853``)."""
    s = col9.strip()
    if not s:
        return None
    m = _STRONG_HEAD_RE.match(s)
    if m is None:
        return None
    # normalize_strong devuelve (base, extended). Queremos el extended
    # (preserva sufijos de desambiguación ``G``/``H`` / ``a``/``b``).
    _, extended = normalize_strong(m.group(1))
    return extended


def _extract_lemma_gloss(col12: str, root_strong: str | None) -> tuple[str | None, str | None]:
    """De ``Expanded Strong tags`` extrae el lema y glosa correspondientes
    al ``root_strong``.

    Si ``root_strong=H7225G`` y col12 contiene ``{H7225G=רֵאשִׁית=: beginning»first:1_beginning}``,
    retorna ``("רֵאשִׁית", "beginning")``.

    Si no se encuentra match exacto, busca el primer ``{...}`` del col12.
    Retorna ``(None, None)`` si col12 no tiene formato esperado."""
    if not col12:
        return None, None
    if root_strong:
        # Match exacto por strong
        pattern = re.compile(
            r"\{" + re.escape(root_strong) + r"=([^=}]+)=([^}]+)\}"
        )
        m = pattern.search(col12)
        if m:
            return _clean_lemma_gloss(m.group(1), m.group(2))
    # Fallback: primer root entre llaves
    m = _ROOT_LEMMA_RE.search(col12)
    if m:
        return _clean_lemma_gloss(m.group("lemma"), m.group("gloss"))
    return None, None


def _clean_lemma_gloss(lemma: str, gloss: str) -> tuple[str, str]:
    """Limpia las cadenas crudas de col 12. Glosas pueden venir con notación
    ``: beginning»first:1_beginning`` donde el primer segmento (``beginning``)
    es la glosa base y el resto son sub-meanings/ocurrencias. Tomamos solo
    la glosa base."""
    lemma = lemma.strip()
    gloss = gloss.strip()
    # Si arranca con ":", strippearlo (artefacto del formato).
    gloss = gloss.lstrip(":").strip()
    # Cortar en el primer "»" (sub-meaning separator) si existe.
    if "»" in gloss:
        gloss = gloss.split("»", 1)[0].strip()
    return lemma, gloss


def _parse_row(cols: list[str]) -> WordAlignment | None:
    if len(cols) < 6:
        return None

    coord = parse_tagnt_ref(cols[0])
    if coord is None:
        return None
    book_id, chapter, verse, position = coord

    word_original = _strip_morph_segments(cols[1].strip())
    if not word_original:
        return None

    transliteration = _strip_morph_segments(cols[2].strip()) or None
    gloss = _strip_morph_segments(cols[3].strip()) or None
    morph = cols[5].strip() or None

    root_col = cols[8].strip() if len(cols) > 8 else ""
    root_strong = _extract_root_strong(root_col)

    expanded_col = cols[11].strip() if len(cols) > 11 else ""
    lemma, lex_gloss = _extract_lemma_gloss(expanded_col, root_strong)

    # Si la glosa contextual (col 4) estaba vacía pero el expanded col tiene
    # una lexica, usamos esa como fallback.
    if gloss is None and lex_gloss:
        gloss = lex_gloss

    return WordAlignment(
        book_id=book_id,
        chapter=chapter,
        verse=verse,
        position=position,
        word_original=word_original,
        transliteration=transliteration,
        lemma=lemma,
        strong_extended=root_strong,
        morph=morph,
        gloss=gloss,
    )


def parse_tahot_alignment(paths: Iterable[Path]) -> Iterator[WordAlignment]:
    """Itera el alineamiento TAHOT (texto AT hebreo Leningrad + Qere).

    ``paths``: lista de archivos TAHOT (Gen-Deu, Jos-Est, Job-Sng, Isa-Mal).

    El parser preserva el orden de aparición upstream. Cada palabra emitida
    corresponde a una ocurrencia única en el WLC — sin duplicados por
    versículo. Variantes Ketiv/Restored/LXX-supplied se descartan
    silenciosamente (la app v1.5 muestra solo el texto principal del WLC)."""
    for path in paths:
        with path.open("r", encoding="utf-8-sig") as f:
            for raw in f:
                if not _DATA_LINE_RE.match(raw):
                    continue
                cols = raw.rstrip("\n").split("\t")
                alignment = _parse_row(cols)
                if alignment is not None:
                    yield alignment
