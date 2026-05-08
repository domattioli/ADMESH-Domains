#!/usr/bin/env python3
"""Fast mesh thumbnail renderer using PIL (Pillow) instead of matplotlib."""

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore


REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_fort14_fast(content: str) -> tuple[list[tuple[float, float]], list[list[int]]]:
    """Quick fort.14 parser."""
    lines = content.strip().split('\n')
    nodes = []
    elements = []
    total_nodes = total_elements = 0

    for i, line in enumerate(lines):
        line = line.strip()
        if not line or line.startswith('!'):
            continue

        if i < 10:
            try:
                parts = line.split()
                if len(parts) >= 2:
                    ne, np_val = int(parts[0]), int(parts[1])
                    if ne > 0 and np_val > 0:
                        total_nodes = np_val
                        total_elements = ne
                        break
            except (ValueError, IndexError):
                pass

    node_idx = 0
    elem_idx = 0
    mode = 'nodes'

    for line in lines:
        line = line.strip()
        if not line or line.startswith('!'):
            continue

        if mode == 'nodes' and node_idx < total_nodes:
            try:
                parts = line.split()
                if len(parts) >= 3:
                    lon, lat = float(parts[1]), float(parts[2])
                    nodes.append((lon, lat))
                    node_idx += 1
                    if node_idx == total_nodes:
                        mode = 'elements'
            except (ValueError, IndexError):
                pass

        elif mode == 'elements' and elem_idx < total_elements:
            try:
                parts = line.split()
                if len(parts) >= 4:
                    elem_type = int(parts[1])
                    if elem_type == 3:
                        connectivity = [int(parts[2]) - 1, int(parts[3]) - 1, int(parts[4]) - 1]
                    elif elem_type == 4:
                        connectivity = [int(parts[2]) - 1, int(parts[3]) - 1, int(parts[4]) - 1, int(parts[5]) - 1]
                    else:
                        continue
                    elements.append(connectivity)
                    elem_idx += 1
            except (ValueError, IndexError):
                pass

    return nodes, elements


def parse_2dm_fast(content: str) -> tuple[list[tuple[float, float]], list[list[int]]]:
    """Quick 2DM parser."""
    lines = content.strip().split('\n')
    nodes = {}
    elements = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        if not parts:
            continue

        if parts[0] == 'ND':
            try:
                node_id = int(parts[1])
                lon, lat = float(parts[2]), float(parts[3])
                nodes[node_id] = (lon, lat)
            except (ValueError, IndexError):
                pass

        elif parts[0] in ('E3', 'E4'):
            try:
                if parts[0] == 'E3':
                    connectivity = [int(parts[2]) - 1, int(parts[3]) - 1, int(parts[4]) - 1]
                else:
                    connectivity = [int(parts[2]) - 1, int(parts[3]) - 1, int(parts[4]) - 1, int(parts[5]) - 1]
                elements.append(connectivity)
            except (ValueError, IndexError):
                pass

    if not nodes or not elements:
        raise ValueError("No nodes or elements in 2DM")

    sorted_nodes = sorted(nodes.items())
    nodes_list = [node for _, node in sorted_nodes]
    return nodes_list, elements


def render_with_pil(
    nodes: list[tuple[float, float]],
    elements: list[list[int]],
    output_path: Path,
    width: int = 240,
    height: int = 180,
) -> None:
    """Render using PIL."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        raise ImportError("Pillow required. Install with: pip install pillow")

    if not nodes or not elements:
        raise ValueError("No nodes or elements")

    xs = [n[0] for n in nodes]
    ys = [n[1] for n in nodes]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    range_x = max_x - min_x if max_x > min_x else 1.0
    range_y = max_y - min_y if max_y > min_y else 1.0

    def coord_to_pixel(lon: float, lat: float) -> tuple[int, int]:
        nx = (lon - min_x + 0.05 * range_x) / (range_x * 1.1)
        ny = (lat - min_y + 0.05 * range_y) / (range_y * 1.1)
        px = int(nx * width)
        py = int((1 - ny) * height)
        return (px, py)

    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)

    for elem in elements:
        if len(elem) < 3:
            continue
        for i in range(len(elem)):
            n1 = nodes[elem[i]]
            n2 = nodes[elem[(i + 1) % len(elem)]]
            p1 = coord_to_pixel(n1[0], n1[1])
            p2 = coord_to_pixel(n2[0], n2[1])
            draw.line([p1, p2], fill='black', width=1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, 'PNG')


def main(manifest_path: Path, meshes_dir: Path, out_dir: Path) -> int:
    """Render all meshes."""
    manifest_path = Path(manifest_path)
    meshes_dir = Path(meshes_dir)
    out_dir = Path(out_dir)

    raw = tomllib.loads(manifest_path.read_text())
    total = success = 0
    failed = []

    for domain in raw.get("domains", []):
        domain_name = domain["name"]
        for mesh in domain.get("meshes", []):
            total += 1
            filename = mesh["filename"]
            mesh_path = meshes_dir / filename
            thumb_path = out_dir / domain_name / f"{mesh['id']}.png"

            if not mesh_path.exists():
                failed.append((mesh['id'], "file not found"))
                continue

            try:
                content = mesh_path.read_text()
                if filename.endswith('.2dm'):
                    nodes, elements = parse_2dm_fast(content)
                else:
                    nodes, elements = parse_fort14_fast(content)
                render_with_pil(nodes, elements, thumb_path)
                success += 1
                print(f"✓ {domain_name}/{mesh['id']}")
            except Exception as e:
                failed.append((mesh['id'], str(e)))
                print(f"✗ {mesh['id']}: {e}")

    print(f"\nDone: {success}/{total}")
    return 0 if not failed else 1


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', type=Path, default=REPO_ROOT / 'registry_data' / 'manifest.toml')
    p.add_argument('--meshes', type=Path, default=REPO_ROOT / 'registry_data' / 'meshes')
    p.add_argument('--out', type=Path, default=REPO_ROOT / 'registry_data' / 'thumbnails')
    args = p.parse_args()
    raise SystemExit(main(args.manifest, args.meshes, args.out))
