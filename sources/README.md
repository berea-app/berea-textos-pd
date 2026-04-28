# sources/

Raw download cache. **Never committed** — see `.gitignore`.

`pipeline/download.py` populates this directory from canonical upstream URLs.
Files are addressed by SHA-256 inside subdirectories named after the `bible_id`
they belong to:

```
sources/
├── rv1909/
│   └── spaRV1909_usfm.zip      # downloaded from ebible.org
├── westcott_hort/
│   └── ...
└── ...
```

If an upstream archive changes (i.e., its SHA-256 differs from what was
recorded in the previous build), the pipeline aborts. This is intentional:
we never silently rebuild against a moved target.

To clear the cache and force re-download:

```bash
rm -rf sources/<bible_id>
```
