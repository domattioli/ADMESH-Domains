#!/usr/bin/env python3
"""Parse fort.14 / .2dm mesh files and extract bounding boxes.

fort.14 layout:
  line 1: AGRID (header / mesh name)
  line 2: NE NN     (num elements, num nodes)
  next NN lines: nodeID  x  y  depth   (whitespace-delimited)
  next NE lines: elementID nverts node1 ... nodeN
  ...

.2dm (SMS) is a sibling format with `ND <id> <x> <y> <z>` lines.

This script writes the bbox back into both manifest.toml files in-place.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional


def extract_bbox(path: Path) -> Optional[tuple[float, float, float, float]]:
    """Dispatch via admesh_domains.geometry. Returns plain tuple for legacy callers."""
    from admesh_domains.geometry import bbox_from_mesh_file
    bb = bbox_from_mesh_file(path)
    if bb is None:
        print(f"  WARN: failed to parse {path.name}")
        return None
    return bb.min_lon, bb.min_lat, bb.max_lon, bb.max_lat


# Back-compat aliases (kept for any external script that imports them):
def bbox_from_fort14(path: Path):
    from admesh_domains.geometry import bbox_from_fort14 as _fort14
    bb = _fort14(path)
    return None if bb is None else (bb.min_lon, bb.min_lat, bb.max_lon, bb.max_lat)


def bbox_from_2dm(path: Path):
    from admesh_domains.geometry import bbox_from_2dm as _2dm
    bb = _2dm(path)
    return None if bb is None else (bb.min_lon, bb.min_lat, bb.max_lon, bb.max_lat)


def insert_bbox_into_manifest(manifest_text: str, filename: str, bbox: tuple) -> str:
    """Insert a bounding_box assignment after the matching `filename = "..."` line."""
    target = f'filename = "{filename}"'
    lines = manifest_text.splitlines()
    out: list[str] = []
    for line in lines:
        out.append(line)
        if line.strip() == target:
            out.append(
                f"bounding_box = {{ "
                f"min_lon = {bbox[0]:.6f}, min_lat = {bbox[1]:.6f}, "
                f"max_lon = {bbox[2]:.6f}, max_lat = {bbox[3]:.6f} "
                "}"
            )
    return "\n".join(out) + ("\n" if manifest_text.endswith("\n") else "")


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    meshes_dir = repo / "registry_data" / "meshes"
    manifests = [
        repo / "registry_data" / "manifest.toml",
        repo / "admesh_domains" / "data" / "manifest.toml",
    ]

    if not meshes_dir.exists():
        print(f"ERROR: meshes dir not found: {meshes_dir}", file=sys.stderr)
        return 1

    bboxes: dict[str, tuple[float, float, float, float]] = {}
    for mesh_path in sorted(meshes_dir.iterdir()):
        if not mesh_path.is_file():
            continue
        bbox = extract_bbox(mesh_path)
        if bbox is None:
            print(f"  SKIP {mesh_path.name} (unparseable)")
            continue
        bboxes[mesh_path.name] = bbox
        print(
            f"  {mesh_path.name:50} "
            f"({bbox[0]:9.3f}, {bbox[1]:8.3f}) -> ({bbox[2]:9.3f}, {bbox[3]:8.3f})"
        )

    print(f"\nExtracted bboxes for {len(bboxes)} meshes\n")

    for mp in manifests:
        text = mp.read_text()
        original = text
        for filename, bbox in bboxes.items():
            # Skip if already has a bounding_box for this mesh
            if f'filename = "{filename}"' in text:
                # Make sure we don't double-insert
                marker = f'filename = "{filename}"\nbounding_box ='
                if marker in text:
                    continue
                text = insert_bbox_into_manifest(text, filename, bbox)
        if text != original:
            mp.write_text(text)
            print(f"Updated {mp}")
        else:
            print(f"No changes to {mp}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
