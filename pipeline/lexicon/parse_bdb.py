"""Parser para Brown-Driver-Briggs Hebrew Lexicon (openscriptures/HebrewLexicon).

Dos archivos XML colaboran:

- ``BrownDriverBriggs.xml``: las entradas en sí — palabra hebrea + pos +
  definiciones + senses + referencias bíblicas. Cada ``<entry>`` tiene un id
  jerárquico (``a.aa.aa``, ``a.bn.ab``, ...) pero **no** tiene Strong's number
  directo.
- ``LexicalIndex.xml``: el puente. Cada ``<entry>`` lista lemma + transliteración
  + pos + glosa corta + ``<xref bdb="..." strong="..." twot="..."/>`` que une
  el lemma con la entry BDB y con el código Strong's.

La estrategia es:

1. Indexar BDB entries por id en un dict ``{id: <element>}``.
2. Iterar LexicalIndex entries que tengan ``<xref strong="...">``; por cada
   una extraer los metadatos (lemma, xlit, pos, def) y la entry BDB
   referenciada (definición prosa completa).
3. Yield una ``BriefLexiconEntry`` por cada LexicalIndex entry con strong.

Esto da N entries por Strong's cuando el upstream lista sub-acepciones (Strong
1 — "father" — tiene ~3 entries en LexicalIndex: el sustantivo principal, el
verbo cognado, etc.). Las preservamos todas; la app las agrupa por
``strong_base`` al mostrar.

**Limitación conocida:** Strong's con sufijos extendidos (``H1G``, ``H0001G``)
NO se generan acá — BDB usa solo Strong's "original" sin desambiguación
mayúscula tipo Tyndale. La desambiguación viene de TBESH (parser ``parse_tbes``).
En la app, los lookups por ``strong_base`` traen ambas fuentes y el bottom
sheet las muestra como cards separadas.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from lxml import etree

from .common import normalize_strong
from .parse_tbes import BriefLexiconEntry

_NS = {"b": "http://openscriptures.github.com/morphhb/namespace"}


def _entry_text(entry: etree._Element) -> str:
    """Extrae el texto plano de una entry BDB.

    XML structure: el texto está distribuido entre los nodos hijos (``<w>``,
    ``<def>``, ``<pos>``, ``<ref>``, ``<sense>``, ``<foreign>``, etc.) más
    el ``.text`` y ``.tail`` de la propia entry. Concatenamos todo, pero
    omitimos los elementos ``<status>`` (editorial: "done", "ref") y los
    ``<foreign>`` con texto no-hebreo dificultoso de renderizar.

    Para ``<sense n="N">``, prefijamos ``N. `` al texto del sense para que
    la enumeración se preserve en la salida plana.
    """
    parts: list[str] = []

    def walk(elem: etree._Element) -> None:
        tag = etree.QName(elem.tag).localname
        if tag == "status":
            # Tail del status sí lo conservamos (texto que sigue a la etiqueta).
            if elem.tail:
                parts.append(elem.tail)
            return
        if tag == "foreign":
            # El contenido textual del foreign no aporta a una glosa
            # hebrea; lo omitimos pero preservamos el tail.
            if elem.tail:
                parts.append(elem.tail)
            return
        if tag == "sense":
            n = elem.get("n")
            if n:
                parts.append(f" {n}. ")
        # Texto inmediato del elemento (antes de cualquier hijo).
        if elem.text:
            parts.append(elem.text)
        for child in elem:
            walk(child)
        # Tail: texto que viene DESPUÉS del cierre del elemento, todavía
        # dentro del padre.
        if elem.tail:
            parts.append(elem.tail)

    # No queremos prefijo "N. " para la propia entry (no es sense).
    if entry.text:
        parts.append(entry.text)
    for child in entry:
        walk(child)
    if entry.tail:
        # Tail de la entry pertenece al hermano siguiente; no incluir.
        pass

    text = "".join(parts)
    # Colapsar runs de whitespace (XML pretty-printing deja indents).
    return " ".join(text.split())


def _xref_strong_to_base(strong_attr: str) -> str | None:
    """Convierte el ``strong="175"`` del xref a la forma ``"H175"``.

    El upstream emite el número desnudo (sin prefijo H). Hay ~8 casos no
    numéricos en el archivo real (``b``, ``i``, ``d``…) que son partículas
    o residuos editoriales; los descartamos."""
    if not strong_attr or not strong_attr.isdigit():
        return None
    return f"H{int(strong_attr)}"


def _li_entry_field(entry: etree._Element, local_name: str) -> str | None:
    """Extrae el texto de un hijo directo por nombre local. Si no existe,
    devuelve ``None``."""
    child = entry.find(f"b:{local_name}", _NS)
    if child is None or child.text is None:
        return None
    s = child.text.strip()
    return s or None


def parse_bdb_files(
    bdb_path: Path, lexical_index_path: Path
) -> Iterator[BriefLexiconEntry]:
    """Itera las entradas léxicas BDB unidas con su Strong's vía LexicalIndex.

    Yield una ``BriefLexiconEntry`` por cada ``<entry>`` del LexicalIndex que
    tenga ``<xref strong="...">``. Cuando varias entries LexicalIndex comparten
    el mismo Strong's (sub-acepciones), todas se yieldean — el caller decide
    cómo agruparlas.
    """
    # Index BDB por id (consume la mayoría del trabajo: 11k entries).
    bdb_tree = etree.parse(str(bdb_path))
    bdb_by_id: dict[str, etree._Element] = {}
    for entry in bdb_tree.iter(f"{{{_NS['b']}}}entry"):
        eid = entry.get("id")
        if eid:
            bdb_by_id[eid] = entry

    # Iterar LexicalIndex y combinar.
    li_tree = etree.parse(str(lexical_index_path))
    for li_entry in li_tree.iter(f"{{{_NS['b']}}}entry"):
        xref = li_entry.find("b:xref", _NS)
        if xref is None:
            continue
        strong_base = _xref_strong_to_base(xref.get("strong") or "")
        if strong_base is None:
            continue

        try:
            base, _ = normalize_strong(strong_base)
        except ValueError:
            continue

        # lemma + transliteración vienen del <w xlit="..."> dentro del
        # LexicalIndex entry.
        w = li_entry.find("b:w", _NS)
        if w is None or w.text is None or not w.text.strip():
            continue
        lemma = w.text.strip()
        translit = w.get("xlit") or None

        pos = _li_entry_field(li_entry, "pos")    # "N" / "V" / "Np" / "A"
        gloss = _li_entry_field(li_entry, "def")  # "father" / "perish" / "Aaron"
        if not gloss:
            continue

        # Definición full: texto plano de la entry BDB referenciada.
        bdb_id = xref.get("bdb")
        definition_full: str | None = None
        if bdb_id:
            bdb_entry = bdb_by_id.get(bdb_id)
            if bdb_entry is not None:
                definition_full = _entry_text(bdb_entry) or None

        yield BriefLexiconEntry(
            strong_base=base,
            strong_extended=base,
            lemma=lemma,
            transliteration=translit,
            morph=pos,
            gloss_brief=gloss,
            definition_full=definition_full,
            language="hbo",
            source="bdb",
        )
