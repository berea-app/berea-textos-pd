"""Parser TAGNT con extracción completa de alineamiento palabra-a-palabra.

A diferencia de ``pipeline/parsers/stepbible_tagnt.py`` (que solo extrae texto
griego para construir el ``.bb`` de la Biblia), este parser retiene por cada
palabra todos los campos que la app v1.5 necesita para el modo interlineal,
el lookup léxico y la comparación por lema:

- ``book_id``, ``chapter``, ``verse``, ``position`` — coordenada canónica.
- ``word_original`` — palabra en griego en su forma exacta para la edición.
- ``transliteration`` — para mostrar abajo en el interlineal.
- ``lemma`` — para lookup en el lexicón.
- ``strong_extended`` — para lookup en lexicón y para la concordancia léxica.
- ``morph`` — análisis morfológico (V-AAI-3S, etc.).
- ``gloss`` — traducción contextual al inglés (la app puede mostrar esto o
  preferir la glosa del lexicón).

Filtra por edición (WH/Treg/TR/etc.): solo emite palabras presentes en la
edición target, usando la spelling variant correcta si está registrada.

Columnas TSV (1-indexed) del TAGNT actual:

  1. Word & Type: ``Mat.1.1#01=NKO``
  2. Greek + translit: ``Βίβλος (Biblos)``
  3. English contextual: ``[The] book``
  4. dStrong + morph: ``G0976=N-NSF``
  5. Lema + glosa léxica: ``βίβλος=book``
  6. Editions: ``NA28+NA27+Tyn+SBL+WH+Treg+TR+Byz``
  7. Meaning variants (palabras solo en algunas ediciones)
  8. Spelling variants (palabras con grafía distinta por edición)
  9+. Spanish, sub-meaning, etc. — ignoramos en v1.5.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from .common import (
    parse_lemma_gloss,
    parse_strong_morph,
    parse_tagnt_ref,
    strip_translit,
)

# Ediciones que TAGNT registra y que Berea v1.5 soporta para alignment.
KNOWN_EDITIONS = {"NA27", "NA28", "Tyn", "SBL", "WH", "Treg", "TR", "Byz"}


@dataclass(frozen=True)
class WordAlignment:
    """Una palabra alineada en una coordenada canónica.

    Frozen para que sea hashable + reproducible. El packer normaliza a NFC
    al serializar; en memoria mantenemos lo que dio el parser para diferenciar
    bugs en el parser vs bugs en NFC."""

    book_id: str
    chapter: int
    verse: int
    position: int
    word_original: str
    transliteration: str | None
    lemma: str | None
    strong_extended: str | None   # dStrong "extended" (con sufijo G/H si aplica)
    morph: str | None
    gloss: str | None             # traducción contextual al inglés


def _editions_set(field: str) -> set[str]:
    """Parsea ``"NA28+NA27+Tyn+SBL+WH+Treg+TR+Byz"`` en un set de strings.

    También maneja líneas raras como ``"+TR: Δαβὶδ"`` donde el prefijo ``+``
    es decorativo en notaciones del upstream."""
    return {e.strip().lstrip("+") for e in field.split("+") if e.strip()}


def _spelling_variant_for(edition: str, variants_field: str) -> str | None:
    """``"Tyn+WH: Δαυεὶδ ; +TR: Δαβὶδ ;"`` → si ``edition="TR"``, retorna
    ``"Δαβὶδ"``. Si no hay variante para esa edición, retorna ``None`` (y
    el caller usa la forma default de col 2)."""
    if not variants_field:
        return None
    for entry in variants_field.split(";"):
        entry = entry.strip()
        if not entry or ":" not in entry:
            continue
        eds, word = entry.split(":", 1)
        if edition in _editions_set(eds):
            return word.strip()
    return None


def _meaning_variant_for(edition: str, variants_field: str) -> dict | None:
    """``"ἁγίων (O=hagiōn) saints. - G0040=A-GPM in: Tyn+WH+Treg+Byz"``.

    Significa: la palabra completa con todos sus campos aparece solo en las
    ediciones listadas tras ``in:``. Si ``edition`` está, devolvemos un dict
    con ``word_original``, ``transliteration``, ``gloss`` ``strong_morph``.
    Si no, ``None``.

    Múltiples variantes pueden venir separadas por ``;``."""
    if not variants_field or "in:" not in variants_field:
        return None
    for entry in variants_field.split(";"):
        entry = entry.strip()
        if " in:" not in entry:
            continue
        word_part, editions_part = entry.rsplit(" in:", 1)
        if edition not in _editions_set(editions_part.strip()):
            continue
        # word_part formato: ``ἁγίων (hagiōn) saints. - G0040=A-GPM``
        # Lo separamos en (greek+translit)  (gloss)  ``- G...``
        match = re.match(
            r"^(?P<word_translit>\S+(?:\s*\([^)]+\))?)\s+(?P<gloss>.+?)\s+-\s+"
            r"(?P<strong_morph>[GH]\d+[a-zA-Z]?=\S+)\s*$",
            word_part,
        )
        if not match:
            continue
        word_translit = match.group("word_translit")
        word, translit = strip_translit(word_translit)
        return {
            "word_original": word,
            "transliteration": translit,
            "gloss": match.group("gloss").strip().rstrip("."),
            "strong_morph": match.group("strong_morph"),
        }
    return None


def _parse_row(cols: list[str], edition: str) -> WordAlignment | None:
    """Parsea una fila TAGNT en una ``WordAlignment`` para ``edition``.

    Retorna ``None`` si la palabra no aparece en esa edición. El caller
    no debe contar los ``None`` como errores — es el filtrado normal."""
    if len(cols) < 6:
        return None

    coord = parse_tagnt_ref(cols[0])
    if coord is None:
        return None
    book_id, chapter, verse, position = coord

    editions_field = cols[5].strip()
    spelling_variants = cols[7].strip() if len(cols) > 7 else ""
    meaning_variants = cols[6].strip() if len(cols) > 6 else ""

    in_edition = edition in _editions_set(editions_field)

    if in_edition:
        # La palabra está en la edición: usar la forma default (col 2) o la
        # variante de spelling si aplica para esta edición.
        default_word, default_translit = strip_translit(cols[1])
        variant = _spelling_variant_for(edition, spelling_variants)
        if variant:
            word_original, transliteration = strip_translit(variant)
            # Si la variante no traía paréntesis, conservamos la translit
            # default (mejor algo que nada).
            if transliteration is None:
                transliteration = default_translit
        else:
            word_original = default_word
            transliteration = default_translit
        gloss = (cols[2] or "").strip() or None
        strong_morph_field = cols[3].strip() if len(cols) > 3 else ""
        lemma_gloss_field = cols[4].strip() if len(cols) > 4 else ""
    else:
        # No está en la edición default: ver si una meaning variant la trae.
        mv = _meaning_variant_for(edition, meaning_variants)
        if mv is None:
            return None
        word_original = mv["word_original"]
        transliteration = mv["transliteration"]
        gloss = mv["gloss"] or None
        strong_morph_field = mv["strong_morph"]
        # Meaning variants no traen lemma — heredamos del default (col 5)
        # como mejor aproximación.
        lemma_gloss_field = cols[4].strip() if len(cols) > 4 else ""

    if not word_original:
        return None

    # Strong + morph
    strong_extended: str | None = None
    morph: str | None = None
    sm = parse_strong_morph(strong_morph_field) if strong_morph_field else None
    if sm is not None:
        strong_extended, morph = sm

    # Lemma (col 5: ``ἀγαπάω=to love``)
    lemma: str | None = None
    lg = parse_lemma_gloss(lemma_gloss_field) if lemma_gloss_field else None
    if lg is not None:
        lemma = lg[0]

    return WordAlignment(
        book_id=book_id,
        chapter=chapter,
        verse=verse,
        position=position,
        word_original=word_original,
        transliteration=transliteration,
        lemma=lemma,
        strong_extended=strong_extended,
        morph=morph,
        gloss=gloss,
    )


# Línea de datos: comienza con ``[A-Za-z0-9]{3}.<digits>.<digits>#<digits>``.
# Filtra header, secciones decorativas y notas (``#_...``, ``# Mat...``,
# ``Word & Type``).
_DATA_LINE_RE = re.compile(
    r"^[A-Za-z0-9]{3}\.\d+\.\d+#\d+(?:=\S+)?\t"
)


def parse_tagnt_alignment(
    paths: Iterable[Path], edition: str
) -> Iterator[WordAlignment]:
    """Itera el alineamiento TAGNT para una edición concreta.

    ``paths``: lista de archivos TAGNT (típicamente Mat-Jhn y Act-Rev split).
    ``edition``: una de ``KNOWN_EDITIONS``.

    El parser preserva el orden de aparición upstream — las palabras de un
    mismo versículo ya vienen ordenadas por posición. El packer reordena
    al serializar para garantizar determinismo cross-build."""
    if edition not in KNOWN_EDITIONS:
        raise ValueError(
            f"edition {edition!r} desconocida; opciones: {sorted(KNOWN_EDITIONS)}"
        )

    for path in paths:
        with path.open("r", encoding="utf-8-sig") as f:
            for raw in f:
                if not _DATA_LINE_RE.match(raw):
                    continue
                cols = raw.rstrip("\n").split("\t")
                alignment = _parse_row(cols, edition)
                if alignment is not None:
                    yield alignment
