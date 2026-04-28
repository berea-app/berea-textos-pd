"""Determinism of pack(): same input → same bytes."""

from __future__ import annotations

import gzip
import json

from pipeline.normalize import NormalizedBook, NormalizedChapter, ParsedVerse
from pipeline.pack import PackInput, pack


def _fake_input() -> PackInput:
    return PackInput(
        bible_id="test1",
        display_name="Test Bible",
        language="es",
        canon_family="protestant_66",
        license="public_domain",
        license_basis="test",
        source_url="https://example.com/test.zip",
        source_attribution="example.com",
        attribution_required=False,
        attribution_text="Test.",
        parser="ebible_usfm",
        pipeline_commit="0000000",
        source_sha256="0" * 64,
        built_at="2026-04-28T00:00:00-03:00",
        books=[
            NormalizedBook(
                book_id="gen",
                display_name="Génesis",
                abbreviation="Gn",
                position=1,
                chapters=[
                    NormalizedChapter(
                        chapter=1,
                        verses=[
                            ParsedVerse("gen", 1, 1, "En el principio."),
                            ParsedVerse("gen", 1, 2, "Y la tierra estaba desordenada."),
                        ],
                    )
                ],
            )
        ],
    )


def test_pack_is_deterministic(tmp_path, monkeypatch):
    import pipeline.pack as pkg

    monkeypatch.setattr(pkg, "OUTPUT_DIR", tmp_path)
    out1 = pack(_fake_input())
    bytes1 = out1.read_bytes()
    out2 = pack(_fake_input())
    bytes2 = out2.read_bytes()
    assert bytes1 == bytes2


def test_pack_is_valid_gzip_json(tmp_path, monkeypatch):
    import pipeline.pack as pkg

    monkeypatch.setattr(pkg, "OUTPUT_DIR", tmp_path)
    out = pack(_fake_input())
    decoded = json.loads(gzip.open(out).read().decode("utf-8"))
    assert decoded["bible_id"] == "test1"
    assert decoded["schema_version"] == "1.0"
    assert decoded["books"][0]["book_id"] == "gen"
    assert decoded["books"][0]["chapters"][0]["verses"][0]["text"] == "En el principio."
