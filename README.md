# berea-textos-pd

Reproducible pipeline that converts public-domain biblical texts into the `.bb`
format consumed by the [Berea · Estudio Bíblico](https://berea.app) Android app.

This repository is the curated source of truth for every public-domain Bible
distributed by Berea. The pipeline is fully reproducible: anyone can clone the
repo, run a single command, and regenerate byte-identical `.bb` files.

## What this repo is

- **Code** under MIT License (this `LICENSE`).
- **Output `.bb` files** distributed via [GitHub Releases](https://github.com/berea-app/berea-textos-pd/releases) of public-domain biblical texts.
- **Per-text attribution** declared in `manifest/manifest.json`.

## What this repo is not

- It does not host raw source archives. Sources are downloaded from the original
  publishers' canonical URLs at build time and never committed (see `sources/`).
- It does not host the Android app. The app code lives in a separate private
  repository inside the same `berea-app` GitHub organization.

## Reproducibility

```bash
git clone https://github.com/berea-app/berea-textos-pd.git
cd berea-textos-pd
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
./scripts/build_one.sh rv1909      # build a single Bible
./scripts/build_all.sh             # build every Bible in the catalogue
```

Two consecutive invocations of `build_all.sh` must produce byte-identical
`.bb` files (same SHA-256). This is enforced in CI.

## Repository layout

```
berea-textos-pd/
├── canon/                # canonical book ids (USFM lowercase) + verse aliases
├── pipeline/             # download, parse, normalize, pack, verify
│   └── parsers/          # one parser per source family (USFM, OSHB XML, …)
├── sources/              # raw downloads (gitignored)
├── output/               # generated .bb files (gitignored)
├── manifest/             # pd_texts_manifest.json + JSON schema
├── scripts/              # convenience scripts
├── tests/
└── docs/
    ├── reproducibility.md
    ├── format_bb.md      # specification of the .bb container
    └── adding_a_new_text.md
```

## Documentation

- [`DECISIONS.md`](DECISIONS.md) — editorial and technical decisions, in Spanish.
- [`docs/format_bb.md`](docs/format_bb.md) — `.bb` format specification.
- [`docs/reproducibility.md`](docs/reproducibility.md) — how to regenerate every artifact.
- [`docs/adding_a_new_text.md`](docs/adding_a_new_text.md) — checklist for contributors.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — pull-request workflow.

## License

Code: MIT (see [`LICENSE`](LICENSE)). Texts: public domain, individual
attribution per text in the manifest.

---

# berea-textos-pd (Español)

Pipeline reproducible que convierte textos bíblicos de dominio público al
formato `.bb` que consume la app Android [Berea · Estudio Bíblico](https://berea.app).

Cualquier persona puede clonar el repo, correr un comando y regenerar
exactamente los mismos `.bb`. La integridad textual y el linaje (qué fuente
produjo qué archivo) son verificables en cada commit.
