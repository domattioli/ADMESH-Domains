"""Build the static GitHub Pages site for ADMESH-Domains.

Reads `registry_data/manifest.toml`, writes `site/dist/manifest.json` plus a
copy of every static asset under `site/src/`. Stdlib only.

Usage:
    python scripts/build_site.py [--manifest PATH] [--src DIR] [--out DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "registry_data" / "manifest.toml"
DEFAULT_SRC = REPO_ROOT / "site" / "src"
DEFAULT_OUT = REPO_ROOT / "site" / "dist"

HF_BASE = "https://huggingface.co/datasets/domattioli/ADMESH-Domains/resolve/main/meshes"


def _is_geographic(bbox: dict | None) -> bool:
    if not bbox:
        return False
    return (
        -180.0 <= bbox["min_lon"] <= 180.0
        and -180.0 <= bbox["max_lon"] <= 180.0
        and -90.0 <= bbox["min_lat"] <= 90.0
        and -90.0 <= bbox["max_lat"] <= 90.0
    )


def _compute_hash(file_path: Path) -> str:
    """Compute SHA256 hash of file contents; return first 8 chars."""
    sha = hashlib.sha256(file_path.read_bytes()).hexdigest()
    return sha[:8]


def _rename_asset_with_hash(src_file: Path, dest_file: Path) -> tuple[str, str]:
    """
    Copy asset and rename with content hash.
    Returns (original_name, hashed_name).
    For JS/CSS: script.js -> script.{hash}.js
    For others: copy unchanged.
    """
    file_hash = _compute_hash(src_file)
    stem = dest_file.stem
    suffix = dest_file.suffix

    if suffix in {".js", ".css"}:
        hashed_name = f"{stem}.{file_hash}{suffix}"
        hashed_path = dest_file.parent / hashed_name
        shutil.copy2(src_file, hashed_path)
        return (dest_file.name, hashed_name)
    else:
        shutil.copy2(src_file, dest_file)
        return (dest_file.name, dest_file.name)


def _update_html_asset_refs(out_dir: Path, asset_map: dict[str, str]) -> None:
    """Update HTML files to reference hashed asset names."""
    for html_file in out_dir.glob("*.html"):
        content = html_file.read_text()
        for original, hashed in asset_map.items():
            if original != hashed:
                pattern = rf'(["\'])(?P<path>(?:[a-zA-Z0-9/_.-]*/)?)' + re.escape(original)
                replacement = r'\g<1>\g<path>' + hashed
                content = re.sub(pattern, replacement, content)
        html_file.write_text(content)


def build_manifest_json(manifest_toml: Path) -> dict:
    raw = tomllib.loads(manifest_toml.read_text())
    domains_out = []
    total_meshes = 0
    total_size_mb = 0.0

    for d in raw.get("domains", []):
        meshes = []
        for m in d.get("meshes", []):
            bbox = m.get("bounding_box")
            filename = m["filename"]
            meshes.append({
                "id": m["id"],
                "full_id": f"{d['name']}/{m['id']}",
                "filename": filename,
                "type": m.get("type", "ADCIRC"),
                "size_mb": m.get("size_mb"),
                "node_count": m.get("node_count"),
                "element_type": m.get("element_type"),
                "refinement_level": m.get("refinement_level"),
                "license": m.get("license"),
                "contributor": m.get("contributor"),
                "uploaded_date": m.get("uploaded_date"),
                "modified_date": m.get("modified_date"),
                "description": m.get("description"),
                "bounding_box": bbox,
                "geographic": _is_geographic(bbox),
                "test_case": bool(m.get("test_case", False)),
                "kind": m.get("kind", "mesh"),
                "download_url": f"{HF_BASE}/{d['name']}/{filename}",
            })
            total_meshes += 1
            total_size_mb += float(m.get("size_mb") or 0.0)
        domains_out.append({
            "name": d["name"],
            "full_name": d.get("full_name", d["name"]),
            "category": d.get("category", "real-world"),
            "region": d.get("region"),
            "applications": d.get("applications", []),
            "description": d.get("description"),
            "bounding_box": d.get("bounding_box"),
            "meshes": meshes,
        })

    return {
        "schema_version": raw.get("schema_version", "0.2"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "totals": {
            "domains": len(domains_out),
            "meshes": total_meshes,
            "size_mb": round(total_size_mb, 2),
        },
        "domains": domains_out,
    }


def copy_assets(src: Path, out: Path) -> tuple[int, dict[str, str]]:
    """Copy assets from src to out, hashing JS/CSS files for cache-busting.
    Returns (file_count, asset_map) where asset_map is {original_name: hashed_name}.
    """
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    asset_map = {}
    file_count = 0

    for src_file in src.rglob("*"):
        if not src_file.is_file():
            continue
        rel_path = src_file.relative_to(src)
        dest_file = out / rel_path

        if not dest_file.parent.exists():
            dest_file.parent.mkdir(parents=True)

        original, hashed = _rename_asset_with_hash(src_file, dest_file)
        if original != hashed:
            asset_map[original] = hashed
        file_count += 1

    return file_count, asset_map


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--src", type=Path, default=DEFAULT_SRC)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = p.parse_args(argv)

    if not args.manifest.exists():
        print(f"error: manifest not found: {args.manifest}", file=sys.stderr)
        return 2
    if not args.src.exists():
        print(f"error: site src not found: {args.src}", file=sys.stderr)
        return 2

    file_count, asset_map = copy_assets(args.src, args.out)
    _update_html_asset_refs(args.out, asset_map)
    manifest = build_manifest_json(args.manifest)
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2))

    t = manifest["totals"]
    hashed_count = len(asset_map)
    print(
        f"built site: {file_count} static files ({hashed_count} hashed) + manifest.json "
        f"({t['domains']} domains, {t['meshes']} meshes, {t['size_mb']} MB) -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
