# `.bb` format specification

Schema version: **1.0**

A `.bb` file is a gzipped UTF-8 JSON document carrying one Bible's text plus
metadata sufficient for the Berea app to import it into SQLite without
querying any external service.

## File extension

`.bb` (e.g., `rv1909.bb`). The format is gzip; we do not use `.json.gz`
because the app treats `.bb` as the canonical Berea container and version-bumps
its `schema_version` independently from the JSON inside.

## Compression

- gzip with maximum compression (level 9).
- `mtime=0` in the gzip header (so the byte output is deterministic).
- No trailing newline. The compressed file is the entire output.

## JSON layout (uncompressed)

```jsonc
{
  "schema_version": "1.0",
  "bible_id": "rv1909",
  "display_name": "Reina-Valera 1909",
  "language": "es",
  "canon_family": "protestant_66",
  "license": "public_domain",
  "license_basis": "Edición de 1909, dominio público en jurisdicciones que aplican vida+95.",
  "source_url": "https://ebible.org/Scriptures/spaRV1909_usfm.zip",
  "source_attribution": "ebible.org / Reina-Valera 1909",
  "attribution_required": false,
  "attribution_text": "Reina-Valera 1909 · dominio público.",
  "build_info": {
    "built_at": "2026-04-28T00:00:00-03:00",
    "pipeline_commit": "<git sha at build time>",
    "parser": "ebible_usfm",
    "source_sha256": "<sha256 of the upstream archive at build time>"
  },
  "books": [
    {
      "book_id": "gen",
      "display_name": "Génesis",
      "abbreviation": "Gn",
      "position": 1,
      "chapters": [
        {
          "chapter": 1,
          "verses": [
            { "verse": 1, "text": "En el principio crió Dios los cielos y la tierra." },
            { "verse": 2, "text": "Y la tierra estaba desordenada y vacía…" }
          ]
        }
      ]
    }
  ]
}
```

## Determinism

Two builds at the same git commit must produce byte-identical `.bb` files.
The pipeline guarantees this by:

1. Sorting JSON keys alphabetically (`json.dumps(..., sort_keys=True)`).
2. Using `separators=(",", ":")` (no whitespace).
3. UTF-8 without BOM, `ensure_ascii=False`.
4. gzip with `mtime=0`.
5. Books emitted in canonical order (`canon_66.json` `order` field).
6. Chapters and verses emitted in numeric order.

CI runs the pipeline twice and compares SHA-256.

## Build info fields

- `pipeline_commit` — the git SHA of `berea-textos-pd` at build time. Pinpoints
  exactly which version of the parser produced this file.
- `source_sha256` — the SHA-256 of the upstream archive (e.g., the ebible.org
  ZIP) consumed by the parser. If upstream changes, this changes too, and the
  next build naturally produces a new `.bb`.
- `parser` — module name under `pipeline/parsers/` that produced this file.

## Optional fields

The schema allows a per-verse `heading` and per-verse `verse_alias`. Both are
optional and only emitted when relevant (e.g., section headings preserved in
the source, or LXX↔MT verse alias annotations).

## Versioning

If a future change is **backwards-compatible** (additive optional fields), bump
to `1.1`, `1.2`, … . The app must accept any `1.x` `.bb`.

If a change is **breaking**, bump to `2.0` and gate consumption in the app
behind a manifest schema bump too. The app refuses to consume a `.bb` whose
major version is greater than what it knows.
