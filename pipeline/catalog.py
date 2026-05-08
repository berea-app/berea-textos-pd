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

# KJV 1769 + Apocrypha: 39 OT + 27 NT + Anglican apocryphal canon (Tobit,
# Judith, Esther additions as a separate book ESG, Wisdom, Sirach, Baruch with
# the Letter of Jeremiah, Song of the Three Children, Susanna, Bel and the
# Dragon, 1-2 Maccabees, 1-2 Esdras, Prayer of Manasseh).
_KJV_APOCRYPHA_BOOK_IDS: tuple[str, ...] = _OT_BOOK_IDS + _NT_BOOK_IDS + (
    "tob", "jdt", "esg", "wis", "sir", "bar", "lje",
    "s3y", "sus", "bel", "1ma", "2ma", "1es", "2es", "man",
)

# Catholic 73-book canon: 39 OT + 7 deuterocanonicals (Tobit, Judith, Wisdom,
# Sirach, Baruch [with Letter of Jeremiah inline as ch.6], 1-2 Maccabees) + 27
# NT. Esther additions and Daniel additions (Susanna, Bel, Song of the Three)
# are typically inlined in the Catholic edition rather than split as separate
# books, so they are not declared here.
_CATHOLIC_73_BOOK_IDS: tuple[str, ...] = _OT_BOOK_IDS + (
    "tob", "jdt", "wis", "sir", "bar", "1ma", "2ma",
) + _NT_BOOK_IDS

# danloi2/itercatholicum publishes Torres Amat as 73 per-book JSON files.
# We pin to a specific commit for reproducibility: re-zipping by GitHub does
# not affect raw.githubusercontent.com (it serves the file's bytes verbatim
# at a given ref).
_ITERCATHOLICUM_COMMIT = "ffe943aaf0ec25dcbc0188f24471f6f6683069cc"
_ITERCATHOLICUM_RAW_BASE = (
    f"https://raw.githubusercontent.com/danloi2/itercatholicum/"
    f"{_ITERCATHOLICUM_COMMIT}/src/shared/data/bibles"
)
# Per-book ID stems shared by every itercatholicum edition. The full
# filename is built as ``<NN>-<stem>-<edition_suffix>.json``.
_ITERCATHOLICUM_BOOK_STEMS: tuple[tuple[int, str], ...] = (
    (1, "gen"), (2, "ex"), (3, "lev"), (4, "num"), (5, "dt"),
    (6, "jos"), (7, "jue"), (8, "rut"),
    (9, "1sam"), (10, "2sam"), (11, "1re"), (12, "2re"),
    (13, "1cron"), (14, "2cron"), (15, "esd"), (16, "neh"), (17, "tob"),
    (18, "jdt"), (19, "est"), (20, "1mac"), (21, "2mac"),
    (22, "job"), (23, "sal"), (24, "prov"), (25, "ecl"), (26, "cant"),
    (27, "sab"), (28, "eclo"), (29, "is"), (30, "jer"), (31, "lam"),
    (32, "bar"), (33, "ez"), (34, "dan"),
    (35, "os"), (36, "jl"), (37, "am"), (38, "abd"), (39, "jon"),
    (40, "miq"), (41, "nah"), (42, "hab"), (43, "sof"), (44, "ag"),
    (45, "zac"), (46, "mal"),
    (47, "mt"), (48, "mc"), (49, "lc"), (50, "jn"), (51, "hch"),
    (52, "rom"), (53, "1cor"), (54, "2cor"), (55, "gal"), (56, "ef"),
    (57, "flp"), (58, "col"), (59, "1tes"), (60, "2tes"),
    (61, "1tim"), (62, "2tim"), (63, "tit"), (64, "flm"),
    (65, "heb"), (66, "sant"), (67, "1pe"), (68, "2pe"),
    (69, "1jn"), (70, "2jn"), (71, "3jn"), (72, "jds"), (73, "ap"),
)


def _itercatholicum_sources(edition_dir: str, suffix: str) -> tuple[
    str, str, tuple[tuple[str, str], ...]
]:
    """Return (primary_url, primary_filename, extra_sources) for an edition.

    ``edition_dir`` is the upstream subdirectory name under
    ``src/shared/data/bibles/`` (e.g., ``1823_torres_amat_es``).
    ``suffix`` is the per-edition tail of the filename without ``.json``
    (e.g., ``ta-es`` for Torres Amat, ``vc-la`` for Vulgata Clementina).
    """
    base = f"{_ITERCATHOLICUM_RAW_BASE}/{edition_dir}"
    filenames = tuple(
        f"{n:02d}-{stem}-{suffix}.json" for n, stem in _ITERCATHOLICUM_BOOK_STEMS
    )
    primary = filenames[0]
    extras = tuple(
        (f"{base}/{name}", name) for name in filenames[1:]
    )
    return f"{base}/{primary}", primary, extras


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


def _torres_amat_entry() -> CatalogEntry:
    primary_url, primary_filename, extras = _itercatholicum_sources(
        "1823_torres_amat_es", "ta-es",
    )
    return CatalogEntry(
        bible_id="torres_amat",
        display_name="Torres Amat (1823)",
        language="es",
        canon_family="catholic_73",
        category="recomendado",
        license="public_domain",
        license_basis=(
            "Sagrada Biblia traducida de la Vulgata Latina al español por "
            "Félix Torres Amat (1823). Torres Amat (m. 1847) cumple "
            "vida + 95 desde 1942. Texto distribuido como dominio público "
            "por la digitalización de danloi2/itercatholicum a partir de "
            "credobiblestudy."
        ),
        source_url=primary_url,
        source_attribution=(
            "danloi2/itercatholicum · Torres Amat 1823 (es-ES) · "
            "credobiblestudy"
        ),
        attribution_required=False,
        attribution_text="Torres Amat 1823 · dominio público.",
        parser="itercatholicum_json",
        source_filename=primary_filename,
        bundled_in_apk=False,
        book_ids=_CATHOLIC_73_BOOK_IDS,
        # Esther y Daniel pueden traer adiciones inline con numeración
        # propia; el canon protestante de 39+27 es referencia, no exigencia.
        expected_canon_complete=False,
        extra_sources=extras,
    )


def _vulgata_clementina_entry() -> CatalogEntry:
    primary_url, primary_filename, extras = _itercatholicum_sources(
        "1592_vulgata_clementina_la", "vc-la",
    )
    return CatalogEntry(
        bible_id="vulgata",
        display_name="Vulgata Clementina (1592)",
        language="la",
        canon_family="catholic_73",
        category="original",
        license="public_domain",
        license_basis=(
            "Sixto-Clementine Vulgate, edición autoritativa de la Iglesia "
            "Católica fijada en 1592. Texto base en dominio público por "
            "antigüedad. Distribución a partir de la transcripción de "
            "Wikisource (la.wikisource.org/wiki/Vulgata_Clementina), "
            "estructurada por danloi2/itercatholicum."
        ),
        source_url=primary_url,
        source_attribution=(
            "danloi2/itercatholicum · Vulgata Clementina 1592 (la) · "
            "Wikisource"
        ),
        attribution_required=False,
        attribution_text="Vulgata Clementina 1592 · dominio público.",
        parser="itercatholicum_json",
        source_filename=primary_filename,
        bundled_in_apk=False,
        book_ids=_CATHOLIC_73_BOOK_IDS,
        expected_canon_complete=False,
        extra_sources=extras,
    )


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
    "kjv": CatalogEntry(
        bible_id="kjv",
        display_name="King James Version + Apocrypha (1769)",
        language="en",
        canon_family="protestant_66_plus_apocrypha",
        category="recomendado",
        license="public_domain",
        license_basis=(
            "King James Version, texto estandarizado de 1769, con Apócrifa. "
            "Dominio público por antigüedad fuera del Reino Unido. Dentro "
            "del UK, las Letters Patent del Crown reservan la impresión a "
            "Cambridge / Oxford / Collins; la distribución digital global "
            "no se considera afectada en la práctica. Berea distribuye el "
            "texto sin modificar."
        ),
        source_url="https://ebible.org/Scriptures/eng-kjv_usfm.zip",
        source_attribution="ebible.org · King James Version 1769 + Apocrypha",
        attribution_required=False,
        attribution_text=(
            "King James Version 1769 + Apocrypha · dominio público "
            "(fuera del Reino Unido)."
        ),
        parser="ebible_usfm",
        source_filename="eng-kjv_usfm.zip",
        bundled_in_apk=False,
        book_ids=_KJV_APOCRYPHA_BOOK_IDS,
        # Apocrypha + KJV uses non-canonical chapter counts in some books
        # (e.g., Esther additions ESG, 2 Esdras 16 chapters). Suppress the
        # verifier's "missing chapters" check.
        expected_canon_complete=False,
    ),
    "asv": CatalogEntry(
        bible_id="asv",
        display_name="American Standard Version (1901)",
        language="en",
        canon_family="protestant_66",
        category="recomendado",
        license="public_domain",
        license_basis=(
            "American Standard Version, publicada en 1901 (pre-1929 en EEUU "
            "y vida + 95 cumplido para todos los miembros del comité "
            "traductor). Distribución por ebible.org como dominio público."
        ),
        source_url="https://ebible.org/Scriptures/eng-asv_usfm.zip",
        source_attribution="ebible.org · American Standard Version 1901",
        attribution_required=False,
        attribution_text="American Standard Version 1901 · dominio público.",
        parser="ebible_usfm",
        source_filename="eng-asv_usfm.zip",
        bundled_in_apk=False,
    ),
    "ylt": CatalogEntry(
        bible_id="ylt",
        display_name="Young's Literal Translation (1898)",
        language="en",
        canon_family="protestant_66",
        category="recomendado",
        license="public_domain",
        license_basis=(
            "Young's Literal Translation, edición revisada de 1898 publicada "
            "póstumamente. Robert Young (m. 1888) cumple vida + 95 desde 1983. "
            "Distribución por ebible.org como dominio público."
        ),
        source_url="https://ebible.org/Scriptures/engylt_usfm.zip",
        source_attribution="ebible.org · Young's Literal Translation",
        attribution_required=False,
        attribution_text="Young's Literal Translation · dominio público.",
        parser="ebible_usfm",
        source_filename="engylt_usfm.zip",
        bundled_in_apk=False,
    ),
    "darby": CatalogEntry(
        bible_id="darby",
        display_name="Darby Translation (1890)",
        language="en",
        canon_family="protestant_66",
        category="recomendado",
        license="public_domain",
        license_basis=(
            "Darby Bible (1890). John Nelson Darby (m. 1882) cumple "
            "vida + 95 desde 1977. Distribución por ebible.org como "
            "dominio público."
        ),
        source_url="https://ebible.org/Scriptures/engDBY_usfm.zip",
        source_attribution="ebible.org · Darby Translation",
        attribution_required=False,
        attribution_text="Darby Translation 1890 · dominio público.",
        parser="ebible_usfm",
        source_filename="engDBY_usfm.zip",
        bundled_in_apk=False,
    ),
    "drc": CatalogEntry(
        bible_id="drc",
        display_name="Douay-Rheims 1899 (Challoner)",
        language="en",
        canon_family="catholic_73",
        category="recomendado",
        license="public_domain",
        license_basis=(
            "Douay-Rheims American Edition 1899, basada en la revisión de "
            "Richard Challoner (m. 1781) sobre el original de 1582-1610. "
            "Cumple vida + 95 desde 1876. Distribución por ebible.org como "
            "dominio público."
        ),
        source_url="https://ebible.org/Scriptures/engDRA_usfm.zip",
        source_attribution="ebible.org · Douay-Rheims American Edition 1899",
        attribution_required=False,
        attribution_text="Douay-Rheims 1899 (Challoner) · dominio público.",
        parser="ebible_usfm",
        source_filename="engDRA_usfm.zip",
        bundled_in_apk=False,
        book_ids=_CATHOLIC_73_BOOK_IDS,
        # Esther y Daniel incluyen las adiciones deuterocanónicas inline en
        # el USFM (capítulos extra), distinto al esquema KJV que las
        # publica como libros separados. La numeración de capítulos puede
        # divergir del canon protestante; suprimimos el chequeo.
        expected_canon_complete=False,
    ),
    "torres_amat": _torres_amat_entry(),
    "vulgata": _vulgata_clementina_entry(),
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
