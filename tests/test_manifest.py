"""Validate the generated manifest against schema.json."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_manifest_validates_against_schema():
    schema = json.loads((REPO_ROOT / "manifest" / "schema.json").read_text("utf-8"))
    manifest_path = REPO_ROOT / "manifest" / "manifest.json"
    if not manifest_path.exists():
        # CI generates it before running tests; if absent, fall back to a
        # synthetic minimal manifest to keep this test useful in local dev.
        manifest = {
            "schema_version": "1.1",
            "updated_at": "2026-04-28T00:00:00-03:00",
            "bibles": [],
        }
    else:
        manifest = json.loads(manifest_path.read_text("utf-8"))
    jsonschema.validate(manifest, schema)


def test_manifest_bible_entries_have_consistent_canon_family():
    manifest_path = REPO_ROOT / "manifest" / "manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text("utf-8"))
    for b in manifest["bibles"]:
        assert b["canon_family"] in {
            "protestant_66",
            "catholic_73",
            "orthodox",
            "septuagint_only",
            "ms_only",
        }
