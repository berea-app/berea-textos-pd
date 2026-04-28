"""Registry of every Bible the pipeline knows how to build.

Each entry declares the source URL, parser, license metadata, and category.
``manifest/pd_texts_manifest.json`` is regenerated from this catalog plus the
SHA-256 / size of the latest build.
"""

from __future__ import annotations

from dataclasses import dataclass


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
}
