"""Maintainer step (``make publish-extract``): publish ``data/raw/*.parquet`` as release assets.

Runs on the host (needs ``gh``), standard library only. Creates or updates the release
``data-<overture release>`` **in the separate, public data repository**, uploads every raw
file, then writes the committed ``pipeline/manifest.json`` (URL + SHA-256 + size per file)
that :mod:`pipeline.load_data` downloads and verifies against.

Why a second repository: this code repository is private, and release assets on a private
repository cannot be fetched without a token. The data repository holds nothing but
releases, so the reviewer's ``make load-data`` works over plain HTTPS.

Usage: ``python backend/pipeline/publish.py [--tag data-2026-08-19.0] [--no-upload]``
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from pipeline.release import OVERTURE_RELEASE  # noqa: E402

# Public, data-only repository that hosts the release assets (see module docstring).
DATA_REPO = "NicoPC12/urbview-data"

RAW_DIR = HERE.parent.parent / "data" / "raw"
MANIFEST = HERE / "manifest.json"
FILES = ("district", "segment", "infrastructure", "land_use", "land", "building")


def sha256(path: Path) -> str:
    """Hex digest of a file, streamed."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(*cmd: str) -> str:
    """Run a host command and return stdout, failing loudly."""
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603


def upload(tag: str, paths: list[Path]) -> None:
    """Create the release if needed, then upload (or replace) every asset."""
    files = [str(p) for p in paths]
    notes = (
        "Output of `make extract` for l'Eixample on Overture release "
        f"{OVERTURE_RELEASE}. Downloaded and checksum-verified by `make load-data`."
    )
    view = ["gh", "release", "view", tag, "--repo", DATA_REPO]
    exists = subprocess.run(view, capture_output=True).returncode == 0  # noqa: S603
    if not exists:
        run(
            "gh", "release", "create", tag, "--repo", DATA_REPO,
            "--title", f"Prepared extract {tag}", "--notes", notes,
        )  # fmt: skip
    run("gh", "release", "upload", tag, *files, "--repo", DATA_REPO, "--clobber")


def main() -> int:
    """Upload the raw files and write the manifest."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default=f"data-{OVERTURE_RELEASE}", help="release tag")
    parser.add_argument("--no-upload", action="store_true", help="only rewrite the manifest")
    args = parser.parse_args()

    paths = [RAW_DIR / f"{name}.parquet" for name in FILES]
    missing = [p.name for p in paths if not p.exists()]
    if missing:
        print(f"missing {missing}; run `make extract` first", file=sys.stderr)
        return 1
    if not args.no_upload:
        upload(args.tag, paths)

    manifest = {
        "release_tag": args.tag,
        "overture_release": OVERTURE_RELEASE,
        "base_url": f"https://github.com/{DATA_REPO}/releases/download/{args.tag}",
        "written_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "files": {p.name: {"sha256": sha256(p), "bytes": p.stat().st_size} for p in paths},
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    total = sum(p.stat().st_size for p in paths) / 1e6
    print(f"wrote {MANIFEST} ({len(paths)} files, {total:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
