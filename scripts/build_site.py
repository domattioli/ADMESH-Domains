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


_JS_IMPORT_RE = re.compile(
    r'(?P<prefix>(?:import|export)\b[^"\']*?from\s+)(?P<quote>["\'])(?P<spec>\./[^"\']+?)(?P=quote)'
)


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


def _parse_js_imports(src_file: Path) -> set[str]:
    """Return set of relative import specifiers found in a JS module."""
    if src_file.suffix != ".js":
        return set()
    try:
        text = src_file.read_text()
    except (OSError, UnicodeDecodeError):
        return set()
    return {m.group("spec") for m in _JS_IMPORT_RE.finditer(text)}


def _rewrite_js_imports(text: str, asset_map: dict[str, str]) -> str:
    """Rewrite relative JS imports to point at hashed filenames."""
    def replace(match: re.Match[str]) -> str:
        spec = match.group("spec")
        base = spec.rsplit("/", 1)[-1]
        if base not in asset_map or asset_map[base] == base:
            return match.group(0)
        prefix, _, _ = spec.rpartition(base)
        new_spec = f"{prefix}{asset_map[base]}"
        return f'{match.group("prefix")}{match.group("quote")}{new_spec}{match.group("quote")}'
    return _JS_IMPORT_RE.sub(replace, text)


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
    thumb_dir = manifest_toml.parent / "thumbnails"

    for d in raw.get("domains", []):
        meshes = []
        for m in d.get("meshes", []):
            bbox = m.get("bounding_box")
            filename = m["filename"]
            mesh_dict = {
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
            }
            thumb_path = thumb_dir / d["name"] / f"{m['id']}.png"
            if thumb_path.exists():
                mesh_dict["thumbnail_url"] = f"https://huggingface.co/datasets/domattioli/ADMESH-Domains/resolve/main/thumbnails/{d['name']}/{m['id']}.png"
            meshes.append(mesh_dict)
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

    JS modules are hashed in dependency order so that intra-bundle `import ...
    from "./dep.js"` statements can be rewritten to the hashed dep name before
    the importer itself is hashed. Without this, the browser fetches the bare
    `./dep.js` URL, hits 404, and the site renders as a skeleton.
    """
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    asset_map: dict[str, str] = {}
    file_count = 0
    js_files: list[Path] = []

    for src_file in src.rglob("*"):
        if not src_file.is_file():
            continue
        rel_path = src_file.relative_to(src)
        dest_file = out / rel_path
        if not dest_file.parent.exists():
            dest_file.parent.mkdir(parents=True)

        if src_file.suffix == ".js":
            js_files.append(src_file)
            file_count += 1
            continue

        original, hashed = _rename_asset_with_hash(src_file, dest_file)
        if original != hashed:
            asset_map[original] = hashed
        file_count += 1

    deps: dict[Path, set[str]] = {f: _parse_js_imports(f) for f in js_files}
    name_to_path = {f.name: f for f in js_files}
    remaining = set(js_files)
    while remaining:
        ready = [
            f for f in remaining
            if all(
                spec.rsplit("/", 1)[-1] not in name_to_path
                or name_to_path[spec.rsplit("/", 1)[-1]] not in remaining
                for spec in deps[f]
            )
        ]
        if not ready:
            raise RuntimeError(
                f"JS import cycle detected among: {sorted(p.name for p in remaining)}"
            )
        for src_file in ready:
            rel_path = src_file.relative_to(src)
            dest_file = out / rel_path
            text = src_file.read_text()
            rewritten = _rewrite_js_imports(text, asset_map)
            tmp = dest_file.parent / f".{dest_file.name}.staging"
            tmp.write_text(rewritten)
            file_hash = _compute_hash(tmp)
            hashed_name = f"{dest_file.stem}.{file_hash}{dest_file.suffix}"
            tmp.rename(dest_file.parent / hashed_name)
            asset_map[dest_file.name] = hashed_name
        remaining -= set(ready)

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
