"""Download upstream sources to ``sources/<bible_id>/``.

The cache is content-addressed: a file is reused if its SHA-256 matches the
expected one, otherwise it is re-fetched. If the recorded SHA differs from
the fetched one, the pipeline aborts loudly — we never silently rebuild
against a moved target.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import requests

SOURCES_DIR = Path(__file__).resolve().parent.parent / "sources"


class UpstreamChanged(RuntimeError):
    """Raised when the upstream archive's SHA-256 differs from the expected one."""


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(
    bible_id: str,
    url: str,
    filename: str,
    *,
    expected_sha256: str | None = None,
    timeout_seconds: int = 60,
) -> Path:
    """Download ``url`` into ``sources/<bible_id>/<filename>``.

    Returns the local path. Verifies SHA-256 against ``expected_sha256`` when
    provided; raises ``UpstreamChanged`` on mismatch.
    """
    out_dir = SOURCES_DIR / bible_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename

    if out_path.exists():
        actual = _sha256_file(out_path)
        if expected_sha256 and actual != expected_sha256:
            out_path.unlink()
        else:
            return out_path

    with requests.get(url, stream=True, timeout=timeout_seconds) as r:
        r.raise_for_status()
        with out_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)

    actual = _sha256_file(out_path)
    if expected_sha256 and actual != expected_sha256:
        out_path.unlink()
        raise UpstreamChanged(
            f"{bible_id}: upstream archive at {url} has SHA-256 {actual}, "
            f"expected {expected_sha256}. Investigate before rebuilding."
        )
    return out_path


def sha256_of(path: Path) -> str:
    return _sha256_file(path)
