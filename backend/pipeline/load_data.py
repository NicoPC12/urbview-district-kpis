"""``make load-data``: fetch the prepared extract, verify it, build the warehouse.

The brief asks for two things that pull against each other: commit the extraction script
but not the data, and go from clean clone to running app in under fifteen minutes. The
real Overture pull (``make extract``) takes ~13 minutes on its own, so by default this
downloads the *same files that script produces*, published as a GitHub Release asset, and
verifies each against the SHA-256 in :data:`MANIFEST` before building. Nothing large is in
Git history, the reviewer is not waiting on S3, and ``make extract`` remains the
re-runnable source of truth.

Idempotent: a file whose checksum already matches is not downloaded again. A checksum
mismatch fails loudly. If the asset cannot be downloaded at all (for example the repository
is private and the reviewer has no token), it falls back to the real pull from S3 so the
command still succeeds — slower, but within the fifteen-minute budget.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from pipeline import build, extract

MANIFEST = Path(__file__).resolve().parent / "manifest.json"
RAW_DIR = build.RAW_DIR


def log(message: str) -> None:
    """Flush-print so progress shows through ``docker compose exec``."""
    print(message, flush=True)


def download(url: str, target: Path) -> None:
    """Stream ``url`` to ``target`` atomically."""
    tmp = target.with_suffix(target.suffix + ".tmp")
    request = urllib.request.Request(url, headers={"User-Agent": "urbview-load-data"})
    with urllib.request.urlopen(request, timeout=60) as response, tmp.open("wb") as out:  # noqa: S310
        while chunk := response.read(1 << 20):
            out.write(chunk)
    tmp.replace(target)


def fetch_extract() -> bool:
    """Ensure every manifest file is in ``data/raw`` with the right hash.

    Returns False when the release asset is unreachable, so the caller can fall back to S3.
    """
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    base_url: str = manifest["base_url"].rstrip("/")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    log(f"prepared extract: {manifest['release_tag']} (Overture {manifest['overture_release']})")
    for name, info in manifest["files"].items():
        target = RAW_DIR / name
        expected = info["sha256"]
        if target.exists() and build.sha256(target) == expected:
            log(f"  {name}: present, checksum ok")
            continue
        started = time.time()
        log(f"  {name}: downloading {info['bytes'] / 1e6:.1f} MB ...")
        try:
            download(f"{base_url}/{name}", target)
        except (urllib.error.URLError, OSError) as exc:
            log(f"  {name}: download failed ({exc})")
            return False
        actual = build.sha256(target)
        if actual != expected:
            target.unlink()
            raise SystemExit(
                f"{name}: checksum mismatch (expected {expected[:12]}…, got {actual[:12]}…). "
                "The release asset may have been replaced; re-run `make extract` to rebuild it."
            )
        log(f"  {name}: ok in {time.time() - started:.0f}s")
    return True


def main() -> int:
    """Entry point for ``python -m pipeline.load_data``."""
    started = time.time()
    if not fetch_extract():
        log(
            "release asset unreachable (private repository without a token, or offline) — "
            "falling back to the Overture S3 pull, ~10 minutes"
        )
        extract.extract_all(extract.connect())
    code = build.main()
    log(f"load-data done in {time.time() - started:.0f}s")
    return code


if __name__ == "__main__":
    sys.exit(main())
