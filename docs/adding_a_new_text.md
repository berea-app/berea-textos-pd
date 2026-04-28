# Adding a new public-domain text

Checklist for contributors. Skipping any step is grounds for rejection of the PR.

## 1. Legal due diligence

- Identify the **author** and the **year of death**. Verify the author died at
  least **95 years before today** (vida+95 — the rule of thumb in `DECISIONS.md`,
  D-006). This protects the catalogue in jurisdictions like the United States,
  not only in Argentina (vida+70).
- Identify the **edition** and the **publication year**. Verify the edition
  itself is in the public domain (some editions are derivative works with
  their own copyright by the editor; e.g., Rahlfs-Hanhart 2006 is **not** PD
  even though Rahlfs 1935 is).
- If anything is ambiguous, open a GitHub issue tagged `decision-required`
  and stop. Do not commit code that downloads the text yet.

## 2. Source URL

- Pick the most **canonical** upstream URL (the publisher's own site, not a
  random mirror). Document it in the parser docstring and in `DECISIONS.md`.
- Verify the source is reachable and the response is stable (an HTTP HEAD
  request returns a `Content-Length`, ideally an `ETag` or `Last-Modified`).
- Record the SHA-256 of the upstream archive. The pipeline will pin this and
  abort if it changes.

## 3. Canon mapping

- Open `canon/canon_66.json` (and `canon_extendido.json` if needed) and verify
  every book in the source maps to a known `book_id`.
- If the source uses non-standard names (e.g., "1 Reigns" for "1 Samuel" in
  LXX), document the alias mapping inside the parser, not in the canon JSON.

## 4. Parser

- Drop a new module under `pipeline/parsers/<name>.py` implementing the
  `BibleParser` interface from `pipeline/parsers/base.py`.
- One parser per source family (USFM, OSHB XML, plain XML, …), not one per
  Bible. If two Bibles ship in the same format, share the parser and pass
  configuration via the constructor.

## 5. Build the `.bb`

```bash
./scripts/build_one.sh <bible_id>
```

This downloads, parses, normalizes, packs, and verifies. Output lands in
`output/<bible_id>.bb`. Manifest is regenerated automatically.

## 6. Sample inspection (mandatory)

- Decompress the `.bb` and visually inspect at least:
  - The first chapter of the first book.
  - The last chapter of the last book.
  - One chapter per testament.
- Look for: encoding glitches (`â€œ` instead of `"`), missing verses, off-by-one
  numbering, OCR garbage in PD scans.

```bash
gunzip -c output/<bible_id>.bb | python -m json.tool | less
```

## 7. Tests

- Add a test under `tests/test_<bible_id>.py` that asserts:
  - Total verse count per book matches the canon's expected count.
  - No empty verses.
  - UTF-8 round-trips (no `�` replacement chars).
  - Specific spot-checks (Gen 1:1, John 3:16, the last verse of the source).

## 8. Manifest entry

- Run `./scripts/build_one.sh <bible_id>` and confirm
  `manifest/pd_texts_manifest.json` was updated with the new SHA-256 and size.
- Manually edit the human-readable fields: `display_name`, `category`,
  `license_basis`, `attribution_text`.

## 9. PR

- Title: `feat: add <bible_id> (<display_name>)`.
- Body: source URL, brief legal rationale, link to any open
  `decision-required` issues, sample of one chapter copied as plain text.
- CI must pass.
