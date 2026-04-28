# Reproducibility

## The promise

Two clones of this repository at the same commit, on any machine with Python
3.11+, must produce byte-identical `.bb` files. SHA-256 checksums recorded in
`manifest/manifest.json` are part of the contract.

## How we keep it true

1. **Deterministic JSON.** `json.dumps(..., sort_keys=True, ensure_ascii=False, separators=(",", ":"))`.
2. **Deterministic gzip.** `gzip.GzipFile(mtime=0, compresslevel=9)`.
3. **Pinned source SHAs.** When a build runs, it records the SHA-256 of every
   input archive in `build_info.source_sha256`. The next build downloads the
   same archive and verifies the SHA matches. If upstream moves, the build
   aborts loudly — we do not silently rebuild against a moved target.
4. **Canonical ordering.** Books emit in the `order` field of `canon_66.json`;
   chapters and verses emit numerically.
5. **No build timestamps inside text.** `build_info.built_at` is informational;
   it is the *only* timestamp in the artifact and changes legitimately. Other
   timestamps (gzip mtime, file system mtimes) are zeroed or ignored.
6. **CI double-build.** `.github/workflows/ci.yml` runs the pipeline twice in
   the same job and compares SHA-256. If they differ, CI fails.

## Verifying reproducibility locally

```bash
./scripts/build_one.sh rv1909
sha256sum output/rv1909.bb
rm -rf output/rv1909.bb
./scripts/build_one.sh rv1909
sha256sum output/rv1909.bb
# The two checksums must match.
```

## Why this matters

The legitimacy of "this is the public-domain text of Reina-Valera 1909"
depends on a verifiable chain: source URL → declared SHA → parser → output
SHA. If any link in the chain is non-deterministic, the chain breaks. The
audit story collapses.

## What is **not** reproducible

- The wall-clock time recorded in `build_info.built_at`.
- The SHA of the resulting `.bb` between commits that change the parser, the
  canon, or the upstream source — these are legitimate version bumps.
- Embedding outputs (in v1.5+, when added). Embeddings depend on model
  weights and runtime; they will live under a separate folder with their
  own reproducibility story (probably "we publish weights + script, not
  byte-identical vectors").
