"""Download and verify environment archives before local evaluation."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from engiworld.prepare_tasks import asset_path, copy_verified, download_snapshot, verify_asset


def image_entries(manifest: dict, selected: list[str] | None = None) -> list[dict]:
    entries = manifest["images"]
    if selected:
        entries = [entry for entry in entries if entry["name"] in selected]
        missing = set(selected) - {entry["name"] for entry in entries}
        if missing:
            raise ValueError(f"Image unavailable in the public dataset: {sorted(missing)}")
    return entries


def image_checksum(entry: dict) -> dict:
    return {"size": entry["package_bytes"], "sha256": entry["package_sha256"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("hf", "modelscope"), default="hf")
    parser.add_argument("--image-root", type=Path, default=Path("../environment-images"))
    parser.add_argument("--image", nargs="+", help="Snapshot names; omitted: all 15 public images")
    parser.add_argument("--check", action="store_true", help="Verify local archives without downloading")
    args = parser.parse_args(argv)
    if args.source == "modelscope" and not args.check:
        os.environ.setdefault("MODELSCOPE_DOWNLOAD_PARALLEL_WORKERS", "8")
    root = args.image_root.resolve()
    if args.check:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    else:
        snapshot = download_snapshot(args.source, "images", ["manifest.json"])
        manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
    try:
        entries = image_entries(manifest, args.image)
    except ValueError as exc:
        parser.error(str(exc))
    if args.check:
        invalid = [entry["path_in_repo"] for entry in entries
                   if not verify_asset(asset_path(root, entry["path_in_repo"]), image_checksum(entry))]
        print(json.dumps({"checked": len(entries), "missing_or_modified": invalid}, indent=2))
        return int(bool(invalid))
    snapshot = download_snapshot(args.source, "images", ["manifest.json", "SHA256SUMS", "README.md",
                                                         *[entry["path_in_repo"] for entry in entries]])
    for entry in entries:
        relative = entry["path_in_repo"]
        copy_verified(asset_path(snapshot, relative), asset_path(root, relative), image_checksum(entry))
        print(f"Verified local archive: {asset_path(root, relative)}", flush=True)
    for name in ("manifest.json", "SHA256SUMS", "README.md"):
        copy_verified(snapshot / name, root / name)
    print(json.dumps({"source": args.source, "images_verified": len(entries), "image_root": str(root)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
