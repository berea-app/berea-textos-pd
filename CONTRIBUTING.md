# Contributing

Thanks for considering a contribution. This repository feeds the Berea Android
app, so changes have to be careful, traceable, and reproducible.

## Ground rules

1. **Public domain only.** Every text added must be unambiguously in the public
   domain in both Argentina (life + 70) and the United States (life + 95). When
   in doubt, open an issue tagged `decision-required` with the publication year,
   author death year, and source URL — do not commit code that downloads
   the text yet.
2. **Reproducible builds.** Pipelines must be deterministic: two runs from the
   same commit must produce byte-identical `.bb` files. Random ordering, file
   timestamps, or non-stable hash maps in output are bugs.
3. **Documented decisions.** Editorial choices (which edition, which spelling,
   how to handle additions to Daniel/Esther) go to `DECISIONS.md` with a short
   rationale.
4. **Tests.** Each parser ships with tests that lock down verse counts per book,
   UTF-8 integrity, and absence of empty verses.

## Adding a new public-domain text

See [`docs/adding_a_new_text.md`](docs/adding_a_new_text.md) for the full
checklist. Summary:

1. Verify legal status (life + 95).
2. Add the source URL to a new parser under `pipeline/parsers/`.
3. Confirm the canonical `book_id` set against `canon/canon_66.json` (or
   `canon/canon_extendido.json` for deuterocanonical books).
4. Run `./scripts/build_one.sh <bible_id>` and inspect the resulting `.bb`.
5. Add tests under `tests/`.
6. Update `manifest/manifest.json` (the build script regenerates
   SHA-256 and size automatically).
7. Submit a PR with the source URL, sample of Genesis 1, and notes on any
   editorial decisions you made.

## Pull-request workflow

- Branch from `main`.
- Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `test:`.
- CI must pass (`pytest`, `ruff check`, reproducibility check).
- Request review before merge. Decisions affecting the manifest schema or
  legal status of a text require explicit sign-off in the PR thread.

## Code style

- Python 3.11+, type-hinted where it adds clarity.
- `ruff` for linting and import ordering (config in `pyproject.toml`).
- Docstrings in English (this is a public, international-facing repo).
- Editorial documentation (`DECISIONS.md`, `docs/`) in Spanish — this captures
  the maintainer's reasoning.

## Sensitive issues

If you find a text in the catalogue whose public-domain status you doubt, open
an issue with label `legal` and stop using the affected `.bb` file. We err on
the side of removing it pending review.
