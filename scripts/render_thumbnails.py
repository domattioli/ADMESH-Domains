#!/usr/bin/env python3
"""Render mesh topology thumbnails (PNG) from fort.14 and .2dm files.

Pre-bakes PNG thumbnails showing element edges for all meshes in the registry.
Supports ADCIRC (fort.14) and SMS 2DM formats.

Usage:
    python scripts/render_thumbnails.py [--manifest PATH] [--meshes DIR] [--out DIR] [--verbose]
    python scripts/render_thumbnails.py --mesh <path> --output <path>  # Single mesh
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore


REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_fort14(content: str) -> tuple[list[tuple[float, float]], list[list[int]]]:
    """Parse ADCIRC fort.14 file and extract nodes and elements.

    Returns: (nodes, elements)
      - nodes: list of (lon, lat) tuples
      - elements: list of connectivity lists (variable length for triangles/quads)
    """
    lines = content.strip().split('\n')
    nodes = []
    elements = []
    mode = None
    node_idx = 0
    elem_idx = 0

    for i, line in enumerate(lines):
        line = line.strip()
        if not line or line.startswith('!'):
            continue

        if i < 10:
            try:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        ne, np_val = int(parts[0]), int(parts[1])
                        if ne > 0 and np_val > 0:
                            mode = 'nodes'
                            total_nodes = np_val
                            total_elements = ne
                            continue
                    except (ValueError, IndexError):
                        pass
            except Exception:
                pass

        if mode == 'nodes' and node_idx < total_nodes:
            try:
                parts = line.split()
                if len(parts) >= 3:
                    node_num = int(parts[0])
                    lon = float(parts[1])
                    lat = float(parts[2])
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
                    elem_num = int(parts[0])
                    elem_type = int(parts[1])
                    if elem_type == 3:
                        connectivity = [int(parts[2]) - 1, int(parts[3]) - 1, int(parts[4]) - 1]
                    elif elem_type == 4:
                        connectivity = [
                            int(parts[2]) - 1, int(parts[3]) - 1,
                            int(parts[4]) - 1, int(parts[5]) - 1
                        ]
                    else:
                        continue
                    elements.append(connectivity)
                    elem_idx += 1
            except (ValueError, IndexError):
                pass

    if not nodes or not elements:
        raise ValueError("No nodes or elements found in fort.14 file")
    return nodes, elements


def parse_2dm(content: str) -> tuple[list[tuple[float, float]], list[list[int]]]:
    """Parse SMS 2DM file and extract nodes and elements."""
    lines = content.strip().split('\n')
    nodes = {}
    elements = []
    node_count = 0

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
                lon = float(parts[2])
                lat = float(parts[3])
                nodes[node_id] = (lon, lat)
                node_count += 1
            except (ValueError, IndexError):
                pass

        elif parts[0] in ('E3', 'E4'):
            try:
                if parts[0] == 'E3':
                    connectivity = [int(parts[2]) - 1, int(parts[3]) - 1, int(parts[4]) - 1]
                else:
                    connectivity = [
                        int(parts[2]) - 1, int(parts[3]) - 1,
                        int(parts[4]) - 1, int(parts[5]) - 1
                    ]
                elements.append(connectivity)
            except (ValueError, IndexError):
                pass

    if not nodes or not elements:
        raise ValueError("No nodes or elements found in 2DM file")

    sorted_nodes = sorted(nodes.items())
    nodes_list = [node for _, node in sorted_nodes]
    return nodes_list, elements


def render_mesh_thumbnail(
    nodes: list[tuple[float, float]],
    elements: list[list[int]],
    output_path: Path,
    width: int = 240,
    height: int = 180,
) -> None:
    """Render mesh topology to PNG using matplotlib (memory-efficient)."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError(
            "matplotlib required for thumbnail generation. "
            "Install with: pip install 'admesh-domains[publish]'"
        )

    if not nodes or not elements:
        raise ValueError("Cannot render: no nodes or elements")

    xs = [n[0] for n in nodes]
    ys = [n[1] for n in nodes]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    range_x = max_x - min_x if max_x > min_x else 1.0
    range_y = max_y - min_y if max_y > min_y else 1.0
    pad = 0.05
    extent = [
        min_x - pad * range_x, max_x + pad * range_x,
        min_y - pad * range_y, max_y + pad * range_y,
    ]

    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.set_aspect('equal')
    ax.axis('off')

    for elem in elements:
        try:
            if len(elem) < 3:
                continue
            for i in range(len(elem)):
                n1_idx = elem[i]
                n2_idx = elem[(i + 1) % len(elem)]
                if n1_idx < len(nodes) and n2_idx < len(nodes):
                    n1 = nodes[n1_idx]
                    n2 = nodes[n2_idx]
                    ax.plot([n1[0], n2[0]], [n1[1], n2[1]], 'k-', linewidth=0.3, alpha=0.6)
        except (IndexError, TypeError):
            pass

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor='white')
    plt.close('all')

    import gc
    gc.collect()


def render_single_mesh(mesh_path: Path, output_path: Path) -> None:
    """Render a single mesh file to PNG."""
    mesh_path = Path(mesh_path)
    if not mesh_path.exists():
        raise FileNotFoundError(f"Mesh file not found: {mesh_path}")

    content = mesh_path.read_text()

    if mesh_path.suffix == '.14':
        nodes, elements = parse_fort14(content)
    elif mesh_path.suffix == '.2dm':
        nodes, elements = parse_2dm(content)
    else:
        raise ValueError(f"Unsupported mesh format: {mesh_path.suffix}")

    render_mesh_thumbnail(nodes, elements, Path(output_path))
    print(f"✓ Rendered {mesh_path.name} -> {output_path}")


def render_all_meshes(manifest_path: Path, meshes_dir: Path, out_dir: Path, verbose: bool = False) -> int:
    """Render all meshes from manifest to PNG thumbnails."""
    manifest_path = Path(manifest_path)
    meshes_dir = Path(meshes_dir)
    out_dir = Path(out_dir)

    if not manifest_path.exists():
        print(f"error: manifest not found: {manifest_path}", file=sys.stderr)
        return 2

    raw = tomllib.loads(manifest_path.read_text())
    total = 0
    success = 0
    failed = []

    for domain in raw.get("domains", []):
        domain_name = domain["name"]
        for mesh in domain.get("meshes", []):
            mesh_id = mesh["id"]
            filename = mesh["filename"]
            mesh_path = meshes_dir / filename

            total += 1
            thumb_path = out_dir / domain_name / f"{mesh_id}.png"

            if not mesh_path.exists():
                if verbose:
                    print(f"✗ Mesh file not found: {mesh_path}")
                failed.append((mesh_id, f"file not found: {mesh_path}"))
                continue

            try:
                content = mesh_path.read_text()

                if filename.endswith('.14'):
                    nodes, elements = parse_fort14(content)
                elif filename.endswith('.2dm'):
                    nodes, elements = parse_2dm(content)
                else:
                    if verbose:
                        print(f"✗ Unsupported format: {filename}")
                    failed.append((mesh_id, f"unsupported format: {filename.split('.')[-1]}"))
                    continue

                render_mesh_thumbnail(nodes, elements, thumb_path)
                success += 1
                if verbose:
                    print(f"✓ {domain_name}/{mesh_id}")

            except Exception as e:
                if verbose:
                    print(f"✗ {domain_name}/{mesh_id}: {e}")
                failed.append((mesh_id, str(e)))

    print(f"\nRendered {success}/{total} meshes to {out_dir}")
    if failed:
        print(f"Failed: {len(failed)}")
        for mesh_id, reason in failed:
            print(f"  - {mesh_id}: {reason}")

    return 0 if not failed else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--manifest", type=Path, default=REPO_ROOT / "registry_data" / "manifest.toml")
    p.add_argument("--meshes", type=Path, default=REPO_ROOT / "registry_data" / "meshes")
    p.add_argument("--out", type=Path, default=REPO_ROOT / "registry_data" / "thumbnails")
    p.add_argument("--mesh", type=Path, help="Single mesh file to render")
    p.add_argument("--output", type=Path, help="Output PNG path (used with --mesh)")
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = p.parse_args(argv)

    if args.mesh:
        if not args.output:
            print("error: --output required when using --mesh", file=sys.stderr)
            return 2
        try:
            render_single_mesh(args.mesh, args.output)
            return 0
        except Exception as e:
            print(f"error: {e}", file=sys.stderr)
            return 1

    return render_all_meshes(args.manifest, args.meshes, args.out, verbose=args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
