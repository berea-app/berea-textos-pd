# output/

Build artifacts. **Never committed** — see `.gitignore`.

The pipeline writes `.bb` files here. Final distribution happens via GitHub
Releases: when a release tag is pushed, `.github/workflows/release.yml` runs
the pipeline, uploads every `.bb` from this directory as a release asset, and
publishes the regenerated `manifest/pd_texts_manifest.json` alongside.

To clear:

```bash
rm -f output/*.bb
```
