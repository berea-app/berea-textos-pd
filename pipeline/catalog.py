"""Registry of every Bible the pipeline knows how to build.

Each entry declares the source URL, parser, license metadata, and category.
``manifest/manifest.json`` is regenerated from this catalogue plus the
SHA-256 / size of the latest build.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .canon import load_canon_66

# 27 NT books (USFM lowercase).
_NT_BOOK_IDS: tuple[str, ...] = (
    "mat", "mrk", "luk", "jhn", "act",
    "rom", "1co", "2co", "gal", "eph", "php", "col",
    "1th", "2th", "1ti", "2ti", "tit", "phm",
    "heb", "jas", "1pe", "2pe", "1jn", "2jn", "3jn", "jud", "rev",
)

# 39 OT books (USFM lowercase).
_OT_BOOK_IDS: tuple[str, ...] = (
    "gen", "exo", "lev", "num", "deu",
    "jos", "jdg", "rut", "1sa", "2sa", "1ki", "2ki",
    "1ch", "2ch", "ezr", "neh", "est",
    "job", "psa", "pro", "ecc", "sng",
    "isa", "jer", "lam", "ezk", "dan",
    "hos", "jol", "amo", "oba", "jon",
    "mic", "nam", "hab", "zep", "hag", "zec", "mal",
)

# Brenton LXX (1851) covers the OT plus deuterocanonical books, but uses
# ``DAG`` (Daniel Greek with additions inline) instead of ``DAN``. ``DAG`` is
# mapped to ``dan`` by the parser, so the catalogue entry only needs to declare
# ``dan`` once.
_BRENTON_BOOK_IDS: tuple[str, ...] = _OT_BOOK_IDS + (
    "tob", "jdt", "esg", "wis", "sir", "bar", "lje",
    "sus", "bel", "1ma", "2ma", "1es", "man", "3ma", "4ma",
)


@dataclass(frozen=True)
class CatalogEntry:
    bible_id: str
    display_name: str
    language: str
    canon_family: str
    category: str
    license: str
    license_basis: str
    source_url: str
    source_attribution: str
    attribution_required: bool
    attribution_text: str
    parser: str
    source_filename: str
    bundled_in_apk: bool
    # Optional. When empty, defaults to the protestant 66.
    book_ids: tuple[str, ...] = field(default_factory=tuple)
    # Setting this to False suppresses the verifier's "missing chapters"
    # warning. Useful for editions that follow MT versification (Joel 4
    # vs RV's Joel 3, Malachi 3 vs RV's Malachi 4) or that ship the LXX
    # additions inline.
    expected_canon_complete: bool = True
    # Additional files that must be downloaded alongside ``source_url``
    # before the parser runs. Parsers that consume directories (e.g.,
    # STEPBible TAGNT split into two files) read every entry from the
    # bible's sources directory.
    extra_sources: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    # Parser-specific configuration. Forwarded to the parser ``__init__``
    # via the ``parser_config`` keyword.
    parser_config: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def effective_book_ids(self) -> set[str]:
        if self.book_ids:
            return set(self.book_ids)
        return {b.book_id for b in load_canon_66()}


CATALOG: dict[str, CatalogEntry] = {
    "rv1909": CatalogEntry(
        bible_id="rv1909",
        display_name="Reina-Valera 1909",
        language="es",
        canon_family="protestant_66",
        category="recomendado",
        license="public_domain",
        license_basis=(
            "Edición de 1909, dominio público en jurisdicciones que aplican "
            "vida + 95. Cipriano de Valera (m. 1602) y Casiodoro de Reina "
            "(m. 1594) están en PD por edad."
        ),
        source_url="https://ebible.org/Scriptures/spaRV1909_usfm.zip",
        source_attribution="ebible.org · Reina-Valera 1909",
        attribution_required=False,
        attribution_text="Reina-Valera 1909 · dominio público.",
        parser="ebible_usfm",
        source_filename="spaRV1909_usfm.zip",
        bundled_in_apk=True,
    ),
    "tr": CatalogEntry(
        bible_id="tr",
        display_name="Textus Receptus (NT)",
        language="grc",
        canon_family="ms_only",
        category="original",
        license="public_domain",
        license_basis=(
            "Textus Receptus griego, dominio público por antigüedad. "
            "Anotaciones de manuscritos por Adam Boyd, dedicadas a PD."
        ),
        source_url="https://ebible.org/Scriptures/grctr_usfm.zip",
        source_attribution="ebible.org · Textus Receptus (Adam Boyd)",
        attribution_required=False,
        attribution_text="Textus Receptus · dominio público.",
        parser="ebible_usfm",
        source_filename="grctr_usfm.zip",
        bundled_in_apk=False,
        book_ids=_NT_BOOK_IDS,
    ),
    "brenton": CatalogEntry(
        bible_id="brenton",
        display_name="Brenton Septuagint (English, 1851)",
        language="en",
        canon_family="septuagint_only",
        category="original",
        license="public_domain",
        license_basis=(
            "Sir Lancelot C. L. Brenton, traducción inglesa de la "
            "Septuaginta publicada en 1851. Brenton (m. 1862) cumple "
            "vida + 95 desde 1957."
        ),
        source_url="https://ebible.org/Scriptures/eng-Brenton_usfm.zip",
        source_attribution="ebible.org · Brenton 1851",
        attribution_required=False,
        attribution_text="Brenton Septuagint, 1851 · dominio público.",
        parser="ebible_usfm",
        source_filename="eng-Brenton_usfm.zip",
        bundled_in_apk=False,
        book_ids=_BRENTON_BOOK_IDS,
        expected_canon_complete=False,
    ),
    "nestle1904": CatalogEntry(
        bible_id="nestle1904",
        display_name="Nestle 1904 (NT)",
        language="grc",
        canon_family="ms_only",
        category="original",
        license="public_domain",
        license_basis=(
            "Eberhard Nestle (m. 1913) — la edición de 1904 cumple "
            "vida + 95 desde 2008. La curaduría morfológica de "
            "biblicalhumanities/Nestle1904 está bajo licencia abierta; "
            "Berea sólo distribuye el texto griego desnudo."
        ),
        source_url=(
            "https://raw.githubusercontent.com/biblicalhumanities/"
            "Nestle1904/master/morph/Nestle1904.csv"
        ),
        source_attribution="biblicalhumanities · Nestle 1904",
        attribution_required=False,
        attribution_text="Nestle 1904 · dominio público.",
        parser="nestle1904_tsv",
        source_filename="Nestle1904.csv",
        bundled_in_apk=False,
        book_ids=_NT_BOOK_IDS,
    ),
    "wh": CatalogEntry(
        bible_id="wh",
        display_name="Westcott-Hort 1881 (NT)",
        language="grc",
        canon_family="ms_only",
        category="original",
        license="cc_by_4_0",
        license_basis=(
            "Texto base: Westcott + Hort 1881 (vida + 95 desde 1996). "
            "Distribuido por STEPBible/Tyndale House con licencia "
            "Creative Commons Attribution 4.0; la atribución a STEPBible "
            "es obligatoria."
        ),
        source_url=(
            "https://raw.githubusercontent.com/STEPBible/STEPBible-Data/master/"
            "Translators%20Amalgamated%20OT%2BNT/"
            "TAGNT%20Mat-Jhn%20-%20Translators%20Amalgamated%20Greek%20NT%20-%20"
            "STEPBible.org%20CC-BY.txt"
        ),
        source_attribution=(
            "STEPBible.org / Tyndale House Cambridge — TAGNT (CC BY 4.0)"
        ),
        attribution_required=True,
        attribution_text=(
            "Westcott-Hort 1881 (NT) extraído del corpus TAGNT de "
            "STEPBible.org / Tyndale House Cambridge, distribuido bajo "
            "Creative Commons Attribution 4.0. github.com/STEPBible"
        ),
        parser="stepbible_tagnt",
        source_filename="TAGNT_Mat-Jhn.txt",
        bundled_in_apk=False,
        book_ids=_NT_BOOK_IDS,
        extra_sources=(
            (
                "https://raw.githubusercontent.com/STEPBible/STEPBible-Data/master/"
                "Translators%20Amalgamated%20OT%2BNT/"
                "TAGNT%20Act-Rev%20-%20Translators%20Amalgamated%20Greek%20NT%20-%20"
                "STEPBible.org%20CC-BY.txt",
                "TAGNT_Act-Rev.txt",
            ),
        ),
        parser_config=(("edition", "WH"),),
    ),
    "tregelles": CatalogEntry(
        bible_id="tregelles",
        display_name="Tregelles 1879 (NT, ed. Jongkind)",
        language="grc",
        canon_family="ms_only",
        category="original",
        license="cc_by_4_0",
        license_basis=(
            "Texto base: Tregelles 1879 (vida + 95 desde 1970), edición "
            "completada por Jongkind 2009. Distribución vía STEPBible/"
            "Tyndale House bajo CC BY 4.0; atribución obligatoria."
        ),
        source_url=(
            "https://raw.githubusercontent.com/STEPBible/STEPBible-Data/master/"
            "Translators%20Amalgamated%20OT%2BNT/"
            "TAGNT%20Mat-Jhn%20-%20Translators%20Amalgamated%20Greek%20NT%20-%20"
            "STEPBible.org%20CC-BY.txt"
        ),
        source_attribution=(
            "STEPBible.org / Tyndale House Cambridge — TAGNT (CC BY 4.0)"
        ),
        attribution_required=True,
        attribution_text=(
            "Tregelles 1879 (NT, ed. Jongkind 2009) extraído del corpus "
            "TAGNT de STEPBible.org / Tyndale House Cambridge, distribuido "
            "bajo Creative Commons Attribution 4.0. github.com/STEPBible"
        ),
        parser="stepbible_tagnt",
        source_filename="TAGNT_Mat-Jhn.txt",
        bundled_in_apk=False,
        book_ids=_NT_BOOK_IDS,
        extra_sources=(
            (
                "https://raw.githubusercontent.com/STEPBible/STEPBible-Data/master/"
                "Translators%20Amalgamated%20OT%2BNT/"
                "TAGNT%20Act-Rev%20-%20Translators%20Amalgamated%20Greek%20NT%20-%20"
                "STEPBible.org%20CC-BY.txt",
                "TAGNT_Act-Rev.txt",
            ),
        ),
        parser_config=(("edition", "Treg"),),
    ),
    "wlc": CatalogEntry(
        bible_id="wlc",
        display_name="Westminster Leningrad Codex (OSHB)",
        language="hbo",
        canon_family="protestant_66",
        category="original",
        license="cc_by_4_0",
        license_basis=(
            "Texto del WLC en dominio público; morfología y datos OSHB "
            "bajo Creative Commons Attribution 4.0 (CC BY 4.0). La "
            "atribución se refleja en el manifest y en la pantalla "
            "Sobre Berea de la app."
        ),
        source_url=(
            "https://github.com/openscriptures/morphhb/releases/download/"
            "v.2.2/OSHB-v.2.2.zip"
        ),
        source_attribution="Open Scriptures Hebrew Bible v2.2 (CC BY 4.0)",
        attribution_required=True,
        attribution_text=(
            "Open Scriptures Hebrew Bible · Westminster Leningrad Codex · "
            "Creative Commons Attribution 4.0. github.com/openscriptures/morphhb"
        ),
        parser="oshb_osis",
        source_filename="OSHB-v.2.2.zip",
        bundled_in_apk=False,
        book_ids=_OT_BOOK_IDS,
        # WLC follows MT numbering (Joel 4 chapters, Malachi 3 chapters);
        # we ship those as-is. Cross-translation alignment via verse_alias.
        expected_canon_complete=False,
    ),
}
