"""Parser para ``strongs-greek-dictionary.js`` de openscriptures/strongs.

Este es el *Dictionary of Greek Words* de James Strong (1890), digitalizado por
Open Scriptures bajo CC-BY-SA. Contiene las glosas y definiciones que Strong
compiló a partir del *Greek-English Lexicon* de Thayer (1889) entre otras
fuentes — por eso lo usamos como sustituto Thayer-style en v1.5. La fuente se
etiqueta como ``"strongs"`` en la entry resultante (no ``"thayer"``) porque la
digitalización proviene del Strong's original, no del Thayer's full.

Formato upstream: el ``.js`` envuelve un objeto JavaScript que es JSON puro
salvo por dos líneas: un ``var ... = `` al inicio y un ``; module.exports = ...;``
al final. Strippeamos esos wrappers y parseamos como JSON.

Cada entrada tiene la forma:

    "G25": {
        "lemma": "ἀγαπάω",
        "translit": "agapáō",
        "kjv_def": "(be-)love(-ed)",
        "strongs_def": " to love (in a social or moral sense)",
        "derivation": "perhaps from ἄγαν (much)..."
    }

El mapeo a ``BriefLexiconEntry``:

- ``strong_base`` ← clave del dict (``G25``), normalizada.
- ``strong_extended`` ← idem (Strong's original no desambigua entre acepciones,
  así que base == extended siempre).
- ``lemma`` / ``transliteration`` ← directos.
- ``gloss_brief`` ← **siempre None**. Strong's upstream lista las traducciones
  KJV ordenadas alfabéticamente, no por frecuencia, así que el primer ítem
  suele ser engañoso (``G3056 λόγος`` → ``"account"`` en vez de ``"word"``;
  ``G2316 Θεός`` → ``"X exceeding"``; ``G2962 κύριος`` → ``"God"``). La
  glosa breve la provee STEPBible/BDB (cards a la par); la card de Strong's
  aporta valor con la definición larga y la etimología, no con la glosa.
- ``definition_full`` ← ``strongs_def`` completo (la definición tipo Thayer).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path

from .common import normalize_strong
from .parse_tbes import BriefLexiconEntry

# El JS abre con ``var <nombre> = {`` y cierra con ``}; module.exports = ...;``.
# Captura el objeto JSON entre los dos extremos.
_JS_WRAPPER_RE = re.compile(
    r"var\s+\w+\s*=\s*(?P<body>\{.*\})\s*;\s*module\.exports",
    re.DOTALL,
)


def parse_strongs_greek_file(path: Path) -> Iterator[BriefLexiconEntry]:
    """Itera las entradas del Strong's Greek Dictionary digitalizado.

    Filtros silenciosos: entradas sin ``lemma`` o sin Strong's parseable
    (no debería ocurrir en el archivo real, pero protege contra ediciones
    upstream corruptas). Entradas sin ``strongs_def`` (definición larga)
    tampoco se emiten — sin ese campo la card no aporta nada que
    STEPBible/BDB no cubran ya.
    """
    raw = path.read_text(encoding="utf-8")
    m = _JS_WRAPPER_RE.search(raw)
    if m is None:
        raise ValueError(f"no se pudo extraer el cuerpo JSON de {path}")
    data: dict[str, dict[str, str]] = json.loads(m.group("body"))

    for strong_code, fields in data.items():
        try:
            base, _ = normalize_strong(strong_code)
        except ValueError:
            continue

        lemma = (fields.get("lemma") or "").strip()
        if not lemma:
            continue

        strongs_def = (fields.get("strongs_def") or "").strip()
        if not strongs_def:
            # Sin definición larga la card de Strong's queda sin contenido
            # útil (no llevamos gloss_brief desde Strong's — ver módulo
            # docstring). Skip silencioso.
            continue
        derivation = (fields.get("derivation") or "").strip()
        translit = (fields.get("translit") or "").strip() or None

        # ``definition_full`` agrega derivation entre paréntesis al strongs_def,
        # porque la etimología enriquece el análisis bereano sin ocupar campo
        # separado en SQLite.
        if derivation:
            definition_full = f"{strongs_def} ({derivation})".strip()
        else:
            definition_full = strongs_def

        yield BriefLexiconEntry(
            strong_base=base,
            strong_extended=base,
            lemma=lemma,
            transliteration=translit,
            morph=None,  # Strong's original no incluye morfología
            gloss_brief=None,
            definition_full=definition_full,
            language="grc",
            source="strongs",
        )
