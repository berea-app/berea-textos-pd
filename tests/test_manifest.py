"""Validate the generated manifest against schema.json."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "manifest" / "schema.json"
MANIFEST_PATH = REPO_ROOT / "manifest" / "manifest.json"


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text("utf-8"))


def _load_manifest_or_minimal() -> dict:
    if not MANIFEST_PATH.exists():
        # CI generates it before running tests; fall back to a synthetic
        # minimal manifest to keep this test useful in local dev.
        return {
            "schema_version": "1.3",
            "updated_at": "2026-05-11T21:00:00-03:00",
            "bibles": [],
        }
    return json.loads(MANIFEST_PATH.read_text("utf-8"))


def test_manifest_validates_against_schema():
    schema = _load_schema()
    manifest = _load_manifest_or_minimal()
    jsonschema.validate(manifest, schema)


def test_manifest_bible_entries_have_consistent_canon_family():
    if not MANIFEST_PATH.exists():
        return
    manifest = json.loads(MANIFEST_PATH.read_text("utf-8"))
    for b in manifest["bibles"]:
        assert b["canon_family"] in {
            "protestant_66",
            "protestant_66_plus_apocrypha",
            "catholic_73",
            "orthodox",
            "septuagint_only",
            "ms_only",
        }


# ===========================================================================
# Schema 1.3 — lexicons[] y alignments[]
# ===========================================================================


class TestSchema13:
    """Verifica la estructura del schema 1.3 (v1.5)."""

    def test_schema_version_es_13(self):
        schema = _load_schema()
        assert schema["$id"].endswith("manifest-1.3.json")

    def test_lexicon_y_alignment_definidos(self):
        schema = _load_schema()
        assert "Lexicon" in schema["$defs"]
        assert "Alignment" in schema["$defs"]
        assert "LexicalSource" in schema["$defs"]

    def test_lexicons_y_alignments_son_optional(self):
        """Schema 1.3 NO requiere lexicons[] / alignments[] — un manifest
        sólo con bibles[] sigue siendo válido (compat con v1.0-v1.4)."""
        schema = _load_schema()
        assert "lexicons" not in schema["required"]
        assert "alignments" not in schema["required"]

    def test_lexicon_data_id_pattern(self):
        schema = _load_schema()
        pattern = schema["$defs"]["Lexicon"]["properties"]["data_id"]["pattern"]
        assert pattern == r"^lexicon_[a-z0-9_]+$"

    def test_alignment_data_id_pattern(self):
        schema = _load_schema()
        pattern = schema["$defs"]["Alignment"]["properties"]["data_id"]["pattern"]
        assert pattern == r"^alignment_[a-z0-9_]+$"

    def test_alignment_testament_enum(self):
        schema = _load_schema()
        enum = schema["$defs"]["Alignment"]["properties"]["testament"]["enum"]
        assert set(enum) == {"nt", "ot"}

    def test_lexicon_category_enum_incluye_avanzado(self):
        """LSJ es 'avanzado' (no estaba en el enum de bibles[].category)."""
        schema = _load_schema()
        enum = schema["$defs"]["Lexicon"]["properties"]["category"]["enum"]
        assert set(enum) == {"recomendado", "avanzado"}


# ===========================================================================
# Manifest real — lexicons[] y alignments[]
# ===========================================================================


@pytest.mark.skipif(not MANIFEST_PATH.exists(), reason="manifest.json no generado")
class TestManifestReal:
    @pytest.fixture(scope="class")
    def manifest(self) -> dict:
        return json.loads(MANIFEST_PATH.read_text("utf-8"))

    def test_schema_version_13(self, manifest):
        assert manifest["schema_version"] == "1.3"

    def test_lexicons_presente(self, manifest):
        assert "lexicons" in manifest
        ids = {x["data_id"] for x in manifest["lexicons"]}
        assert ids == {"lexicon_grc", "lexicon_grc_lsj", "lexicon_hbo"}

    def test_alignments_presente(self, manifest):
        assert "alignments" in manifest
        ids = {x["data_id"] for x in manifest["alignments"]}
        assert ids == {
            "alignment_grc_nt_wh",
            "alignment_grc_nt_tregelles",
            "alignment_grc_nt_tr",
            "alignment_hbo_ot_wlc",
        }

    def test_lexicons_estan_ordenados_por_data_id(self, manifest):
        ids = [x["data_id"] for x in manifest["lexicons"]]
        assert ids == sorted(ids)

    def test_alignments_estan_ordenados_por_data_id(self, manifest):
        ids = [x["data_id"] for x in manifest["alignments"]]
        assert ids == sorted(ids)

    def test_lexicons_todos_requieren_atribucion(self, manifest):
        """Todas las fuentes léxicas de Berea v1.5 incluyen al menos una
        fuente bajo CC BY 4.0 → attribution_required=True en todos los .bb."""
        for x in manifest["lexicons"]:
            assert x["attribution_required"] is True, x["data_id"]

    def test_alignments_todos_requieren_atribucion(self, manifest):
        for x in manifest["alignments"]:
            assert x["attribution_required"] is True, x["data_id"]

    def test_alignment_bible_id_es_valido(self, manifest):
        """Cada alignment debe apuntar a un bible_id presente en bibles[]."""
        bible_ids = {b["bible_id"] for b in manifest["bibles"]}
        for a in manifest["alignments"]:
            assert a["bible_id"] in bible_ids, (
                f"alignment {a['data_id']} apunta a bible_id "
                f"{a['bible_id']!r} que no existe en bibles[]"
            )

    def test_download_url_de_lexicon_termina_en_bb(self, manifest):
        for x in manifest["lexicons"]:
            assert x["download_url"].endswith(f"/{x['data_id']}.bb")

    def test_download_url_de_alignment_termina_en_bb(self, manifest):
        for x in manifest["alignments"]:
            assert x["download_url"].endswith(f"/{x['data_id']}.bb")

    def test_lexicon_lsj_es_categoria_avanzado(self, manifest):
        lsj = next(x for x in manifest["lexicons"] if x["data_id"] == "lexicon_grc_lsj")
        assert lsj["category"] == "avanzado"

    def test_lexicons_brief_son_recomendado(self, manifest):
        for did in ("lexicon_grc", "lexicon_hbo"):
            entry = next(x for x in manifest["lexicons"] if x["data_id"] == did)
            assert entry["category"] == "recomendado", did

    def test_alignments_son_categoria_original(self, manifest):
        for x in manifest["alignments"]:
            assert x["category"] == "original", x["data_id"]

    def test_alignment_hbo_apunta_a_wlc(self, manifest):
        wlc = next(
            x for x in manifest["alignments"]
            if x["data_id"] == "alignment_hbo_ot_wlc"
        )
        assert wlc["bible_id"] == "wlc"
        assert wlc["testament"] == "ot"
        assert wlc["language"] == "hbo"

    def test_alignments_nt_apuntan_a_biblia_correcta(self, manifest):
        mapping = {
            "alignment_grc_nt_wh": "wh",
            "alignment_grc_nt_tregelles": "tregelles",
            "alignment_grc_nt_tr": "tr",
        }
        for data_id, bible_id in mapping.items():
            entry = next(
                x for x in manifest["alignments"] if x["data_id"] == data_id
            )
            assert entry["bible_id"] == bible_id
            assert entry["testament"] == "nt"
            assert entry["language"] == "grc"

    def test_sources_de_lexicon_grc_combina_stepbible_y_strongs(self, manifest):
        grc = next(x for x in manifest["lexicons"] if x["data_id"] == "lexicon_grc")
        ids = {s["id"] for s in grc["sources"]}
        assert ids == {"stepbible", "strongs"}

    def test_sources_de_lexicon_hbo_combina_stepbible_y_bdb(self, manifest):
        hbo = next(x for x in manifest["lexicons"] if x["data_id"] == "lexicon_hbo")
        ids = {s["id"] for s in hbo["sources"]}
        assert ids == {"stepbible", "bdb"}

    def test_source_de_alignment_nt_es_tagnt(self, manifest):
        for did in (
            "alignment_grc_nt_wh",
            "alignment_grc_nt_tregelles",
            "alignment_grc_nt_tr",
        ):
            entry = next(x for x in manifest["alignments"] if x["data_id"] == did)
            assert entry["source"]["id"] == "tagnt"

    def test_source_de_alignment_at_es_tahot(self, manifest):
        entry = next(
            x for x in manifest["alignments"]
            if x["data_id"] == "alignment_hbo_ot_wlc"
        )
        assert entry["source"]["id"] == "tahot"

    def test_sha256_y_size_estan_set(self, manifest):
        """Si los .bb existen, sha256 debe ser hex de 64 chars y size > 0."""
        out = REPO_ROOT / "output"
        for x in manifest["lexicons"] + manifest["alignments"]:
            bb = out / f"{x['data_id']}.bb"
            if not bb.exists():
                continue
            assert x["sha256"] != "TBD", x["data_id"]
            assert len(x["sha256"]) == 64
            assert x["size_bytes"] > 0


# ===========================================================================
# Compat: manifest sin lexicons[] / alignments[] sigue validando
# ===========================================================================


def test_manifest_legacy_sin_lexicons_sigue_valido():
    schema = _load_schema()
    legacy = {
        "schema_version": "1.2",
        "updated_at": "2026-04-28T00:00:00-03:00",
        "bibles": [],
    }
    jsonschema.validate(legacy, schema)
