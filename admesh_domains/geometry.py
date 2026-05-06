"""Geometric helpers for the auto-suggester (spec 007).

Pure-stdlib bbox arithmetic, IoU, and mesh-file bbox extraction. Used by
the ``admesh-domains domain {suggest,audit}`` CLI commands and exposed for
external tooling. No third-party dependencies.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .schema import BoundingBox, Domain
from .manifest import Manifest


# Confidence thresholds (per spec 007 C-3).
CONFIDENT_THRESHOLD = 0.5
UNCERTAIN_THRESHOLD = 0.05


# ---------------------------------------------------------------------------
# Bbox arithmetic
# ---------------------------------------------------------------------------

def is_antimeridian_wrapping(bb: BoundingBox) -> bool:
    """True iff the bbox crosses the dateline (min_lon > max_lon)."""
    return bb.min_lon > bb.max_lon


def area(bb: BoundingBox) -> float:
    """Width * height in coordinate units. 0 for zero-area or wrapping bboxes."""
    if is_antimeridian_wrapping(bb):
        return 0.0
    w = max(0.0, bb.max_lon - bb.min_lon)
    h = max(0.0, bb.max_lat - bb.min_lat)
    return w * h


def intersection(a: BoundingBox, b: BoundingBox) -> Optional[BoundingBox]:
    """Smallest bbox covering the intersection, or None if disjoint."""
    if is_antimeridian_wrapping(a) or is_antimeridian_wrapping(b):
        return None
    min_lon = max(a.min_lon, b.min_lon)
    min_lat = max(a.min_lat, b.min_lat)
    max_lon = min(a.max_lon, b.max_lon)
    max_lat = min(a.max_lat, b.max_lat)
    if min_lon >= max_lon or min_lat >= max_lat:
        return None
    return BoundingBox(min_lon, min_lat, max_lon, max_lat)


def union(a: BoundingBox, b: BoundingBox) -> BoundingBox:
    """Smallest bbox covering both inputs (ignores antimeridian — caller's problem)."""
    return BoundingBox(
        min_lon=min(a.min_lon, b.min_lon),
        min_lat=min(a.min_lat, b.min_lat),
        max_lon=max(a.max_lon, b.max_lon),
        max_lat=max(a.max_lat, b.max_lat),
    )


def centroid(bb: BoundingBox) -> tuple[float, float]:
    """Center point of the bbox (lon, lat)."""
    return ((bb.min_lon + bb.max_lon) / 2, (bb.min_lat + bb.max_lat) / 2)


def _split_antimeridian_bbox(bb: BoundingBox) -> list[BoundingBox]:
    """Split an antimeridian-wrapping bbox into east/west halves around the dateline.

    For a bbox with min_lon > max_lon (wrapping), returns two non-wrapping bboxes:
    - East: [min_lon, min_lat, 180, max_lat]
    - West: [-180, min_lat, max_lon, max_lat]

    For non-wrapping bboxes, returns [bb] unchanged.
    """
    if not is_antimeridian_wrapping(bb):
        return [bb]
    return [
        BoundingBox(bb.min_lon, bb.min_lat, 180, bb.max_lat),
        BoundingBox(-180, bb.min_lat, bb.max_lon, bb.max_lat),
    ]


def compute_iou(a: BoundingBox, b: BoundingBox) -> float:
    """Intersection-over-union of two bboxes, supporting antimeridian-wrapping.

    Handles antimeridian-wrapping bboxes (min_lon > max_lon) by splitting them
    into east/west halves and computing the combined intersection and union areas.
    Returns 0.0 for disjoint or zero-area inputs.
    """
    parts_a = _split_antimeridian_bbox(a)
    parts_b = _split_antimeridian_bbox(b)

    total_inter_area = 0.0
    for pa in parts_a:
        for pb in parts_b:
            inter = intersection(pa, pb)
            if inter is not None:
                total_inter_area += area(inter)

    total_area_a = sum(area(pa) for pa in parts_a)
    total_area_b = sum(area(pb) for pb in parts_b)
    union_area = total_area_a + total_area_b - total_inter_area

    if union_area <= 0:
        return 0.0
    return total_inter_area / union_area


def centroid_distance(a: BoundingBox, b: BoundingBox) -> float:
    """Euclidean distance between centroids in coordinate units (degrees if lat/lon)."""
    ax, ay = centroid(a)
    bx, by = centroid(b)
    return math.hypot(ax - bx, ay - by)


# ---------------------------------------------------------------------------
# Domain-level helpers
# ---------------------------------------------------------------------------

def domain_union_bbox(domain: Domain) -> Optional[BoundingBox]:
    """Smallest bbox covering all of a Domain's meshes' bboxes (geographic only).

    Returns None if the Domain has no geographic-bbox meshes (e.g. all coords
    are projected/synthetic).
    """
    out: Optional[BoundingBox] = None
    for m in domain.meshes:
        bb = m.bounding_box
        if bb is None or is_antimeridian_wrapping(bb):
            continue
        # Heuristic: only include in union if the bbox sits in lat/lon range
        if not (-180 <= bb.min_lon <= 180 and -90 <= bb.min_lat <= 90):
            continue
        out = bb if out is None else union(out, bb)
    return out


def per_mesh_iou(new_bbox: BoundingBox, domain: Domain) -> float:
    """Max IoU of ``new_bbox`` against any single mesh in ``domain``."""
    best = 0.0
    for m in domain.meshes:
        if m.bounding_box is None:
            continue
        iou = compute_iou(new_bbox, m.bounding_box)
        if iou > best:
            best = iou
    return best


# ---------------------------------------------------------------------------
# Tier 2: Boundary polygon matching (optional, requires shapely)
# ---------------------------------------------------------------------------

def extract_boundary_polygon(mesh_path: Path) -> Optional[object]:
    """Extract the outer boundary polygon from a fort.14 / .2dm mesh file.

    Returns a shapely.Polygon representing the mesh's outer boundary
    (traced from edges belonging to only one element), or None if extraction fails.

    Raises ImportError if shapely is not installed.
    """
    try:
        from shapely.geometry import Polygon as ShapelyPolygon
    except ImportError as e:
        raise ImportError(
            "boundary extraction requires shapely; install with "
            "`pip install admesh-domains[suggest]`"
        ) from e

    try:
        path = Path(mesh_path)
        if path.suffix == ".2dm":
            return _extract_boundary_from_2dm(path)
        else:
            return _extract_boundary_from_fort14(path)
    except Exception as e:
        print(f"WARNING: failed to extract boundary from {mesh_path}: {e}",
              file=sys.stderr)
        return None


def _extract_boundary_from_fort14(path: Path) -> Optional[object]:
    """Extract boundary from fort.14 file."""
    try:
        from shapely.geometry import Polygon as ShapelyPolygon
    except ImportError:
        raise ImportError("shapely required")

    # Parse fort.14: collect nodes and element connectivity
    nodes = {}  # nodeID -> (x, y)
    edges = {}  # (nodeA, nodeB) -> count (how many elements share this edge)

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        f.readline()  # AGRID
        ne_nn = f.readline().split()
        if len(ne_nn) < 2:
            return None
        try:
            ne, nn = int(ne_nn[0]), int(ne_nn[1])
        except ValueError:
            # Some meshes may have non-standard header formats
            return None

        # Read nodes
        for _ in range(nn):
            parts = f.readline().split()
            if len(parts) >= 3:
                node_id = int(parts[0])
                x, y = float(parts[1]), float(parts[2])
                nodes[node_id] = (x, y)

        # Read elements and count edge adjacency
        for _ in range(ne):
            parts = f.readline().split()
            if len(parts) < 4:
                continue
            try:
                elem_type = int(parts[1])
                elem_nodes = [int(p) for p in parts[2:2+elem_type]]
            except (ValueError, IndexError):
                # Skip malformed element lines
                continue

            # Record edges (as sorted pairs to avoid duplicates)
            for i in range(len(elem_nodes)):
                n1 = elem_nodes[i]
                n2 = elem_nodes[(i + 1) % len(elem_nodes)]
                edge = tuple(sorted([n1, n2]))
                edges[edge] = edges.get(edge, 0) + 1

    # Extract boundary edges (degree = 1)
    boundary_edges = [(n1, n2) for (n1, n2), count in edges.items() if count == 1]
    if not boundary_edges:
        return None

    # Order boundary edges into a closed polygon
    boundary_polygon = _order_edges_to_polygon(boundary_edges, nodes)
    return boundary_polygon


def _extract_boundary_from_2dm(path: Path) -> Optional[object]:
    """Extract boundary from .2dm file (note: .2dm files may not have element connectivity).

    For now, return None since .2dm typically has only node coordinates, not element connectivity.
    """
    # TODO: implement if needed. For now, assume .2dm files are not used for boundary matching.
    return None


def _order_edges_to_polygon(edges: list[tuple[int, int]], nodes: dict[int, tuple]) -> Optional[object]:
    """Order unordered edges into a closed polygon.

    Args:
        edges: List of (nodeA, nodeB) tuples representing boundary edges.
        nodes: Dict mapping nodeID -> (x, y) coordinates.

    Returns:
        shapely.Polygon or None if ordering fails.
    """
    try:
        from shapely.geometry import Polygon as ShapelyPolygon
    except ImportError:
        raise ImportError("shapely required")

    if not edges:
        return None

    # Build adjacency: for each node, list of neighbors
    adj = {}
    for n1, n2 in edges:
        if n1 not in adj:
            adj[n1] = []
        if n2 not in adj:
            adj[n2] = []
        adj[n1].append(n2)
        adj[n2].append(n1)

    # Trace polygon starting from first edge
    path = [edges[0][0], edges[0][1]]
    visited = {edges[0]}

    while len(visited) < len(edges):
        current = path[-1]
        next_node = None

        # Find next unvisited neighbor
        for neighbor in adj.get(current, []):
            edge = tuple(sorted([current, neighbor]))
            if edge not in visited:
                next_node = neighbor
                visited.add(edge)
                break

        if next_node is None:
            break  # No more edges (incomplete polygon)

        path.append(next_node)

    # Check if polygon is closed
    if len(visited) < len(edges) or path[0] != path[-1]:
        if path[0] == path[-1]:
            pass  # Already closed
        else:
            path.append(path[0])  # Close it

    # Extract coordinates and create polygon
    coords = []
    for node_id in path:
        if node_id in nodes:
            coords.append(nodes[node_id])

    if len(coords) < 3:
        return None

    try:
        return ShapelyPolygon(coords)
    except Exception:
        return None


def polygon_iou(poly_a: Optional[object], poly_b: Optional[object]) -> float:
    """Compute intersection-over-union of two shapely Polygons.

    Args:
        poly_a, poly_b: shapely.Polygon objects (or None).

    Returns:
        IoU in range [0, 1]. Returns 0 if either input is None or invalid.
    """
    if poly_a is None or poly_b is None:
        return 0.0

    try:
        inter = poly_a.intersection(poly_b)
        union = poly_a.union(poly_b)
        if union.area > 0:
            return inter.area / union.area
        return 0.0
    except Exception:
        return 0.0


def hausdorff_distance(poly_a: Optional[object], poly_b: Optional[object]) -> Optional[float]:
    """Compute Hausdorff distance between two shapely Polygons.

    Args:
        poly_a, poly_b: shapely.Polygon objects (or None).

    Returns:
        Hausdorff distance in degrees, or None if computation fails.
        The distance is converted to kilometers using mean Earth radius (6371 km).
    """
    if poly_a is None or poly_b is None:
        return None

    try:
        # Hausdorff distance in degrees
        dist_deg = poly_a.hausdorff_distance(poly_b)
        # Convert to kilometers (very rough: 1 degree ≈ 111 km at equator)
        dist_km = dist_deg * 111.0
        return dist_km
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Suggestion API
# ---------------------------------------------------------------------------

def _confidence(iou: float) -> str:
    if iou >= CONFIDENT_THRESHOLD:
        return "confident"
    if iou >= UNCERTAIN_THRESHOLD:
        return "uncertain"
    return "low"


@dataclass
class IoUScore:
    """One Domain's match scores against a candidate mesh's bbox (Tier 1 + Tier 2)."""

    domain_name: str
    per_mesh_iou: float
    union_iou: float
    centroid_distance_deg: Optional[float]
    confidence: str  # confident | uncertain | low
    boundary_hausdorff_km: Optional[float] = None  # Tier 2
    boundary_polygon_iou: Optional[float] = None   # Tier 2

    def to_dict(self) -> dict:
        d = {
            "domain": self.domain_name,
            "per_mesh_iou": round(self.per_mesh_iou, 4),
            "union_iou": round(self.union_iou, 4),
            "centroid_distance_deg": (
                round(self.centroid_distance_deg, 4)
                if self.centroid_distance_deg is not None else None
            ),
            "confidence": self.confidence,
        }
        if self.boundary_hausdorff_km is not None:
            d["boundary_hausdorff_km"] = round(self.boundary_hausdorff_km, 2)
        if self.boundary_polygon_iou is not None:
            d["boundary_polygon_iou"] = round(self.boundary_polygon_iou, 4)
        return d


def suggest_domain(
    new_bbox: BoundingBox, manifest: Manifest, tier: int = 1,
    new_mesh_path: Optional[Path] = None
) -> list[IoUScore]:
    """Rank every Domain by IoU against ``new_bbox`` (highest per-mesh IoU first).

    Args:
        new_bbox: The candidate mesh's bounding box.
        manifest: The registry manifest.
        tier: 1 (bbox only) or 2 (bbox + boundary polygon). Default 1.
        new_mesh_path: Path to new mesh file (required for tier=2). If tier=2 but
                       new_mesh_path is None, falls back to tier 1.

    Returns:
        Sorted list of IoUScore objects.
    """
    scores: list[IoUScore] = []

    # For Tier 2, try to extract boundary polygon.
    new_boundary = None
    if tier == 2:
        try:
            if new_mesh_path is None:
                print("WARNING: tier=2 requested but no mesh path provided; falling back to tier=1",
                      file=sys.stderr)
                tier = 1
            else:
                new_boundary = extract_boundary_polygon(new_mesh_path)
                if new_boundary is None:
                    print(f"WARNING: could not extract boundary from {new_mesh_path}; "
                          "falling back to tier=1", file=sys.stderr)
                    tier = 1
        except ImportError:
            print("WARNING: boundary matching requires shapely; install with "
                  "`pip install admesh-domains[suggest]`", file=sys.stderr)
            tier = 1

    for d in manifest.domains:
        u = domain_union_bbox(d)
        if u is None:
            continue  # Domain has no geographic-bbox meshes; can't compare
        pm = per_mesh_iou(new_bbox, d)
        ui = compute_iou(new_bbox, u)
        cd = centroid_distance(new_bbox, u) if pm > 0 else None

        # Tier 2: add boundary metrics if available
        boundary_hausdorff = None
        boundary_polygon_iou = None
        if tier == 2 and new_boundary is not None:
            # Compare boundaries with each mesh in the Domain.
            best_hausdorff = float('inf')
            best_polygon_iou = 0.0
            for mesh in d.meshes:
                if mesh.bounding_box is None:
                    continue
                try:
                    mesh_boundary = extract_boundary_polygon(Path(mesh.path))
                    if mesh_boundary is not None:
                        hd = hausdorff_distance(new_boundary, mesh_boundary)
                        piou = polygon_iou(new_boundary, mesh_boundary)
                        if hd is not None and hd < best_hausdorff:
                            best_hausdorff = hd
                        if piou > best_polygon_iou:
                            best_polygon_iou = piou
                except Exception:
                    continue
            if best_hausdorff < float('inf'):
                boundary_hausdorff = best_hausdorff
            if best_polygon_iou > 0.0:
                boundary_polygon_iou = best_polygon_iou

        scores.append(IoUScore(
            domain_name=d.name,
            per_mesh_iou=pm,
            union_iou=ui,
            centroid_distance_deg=cd,
            confidence=_confidence(pm),
            boundary_hausdorff_km=boundary_hausdorff,
            boundary_polygon_iou=boundary_polygon_iou,
        ))

    # Sort by Tier 2 metrics if available, else by Tier 1.
    if tier == 2:
        scores.sort(key=lambda s: (
            -(s.boundary_polygon_iou if s.boundary_polygon_iou is not None else 0.0),
            -s.per_mesh_iou,
        ))
    else:
        scores.sort(key=lambda s: (-s.per_mesh_iou, -s.union_iou))

    return scores


# ---------------------------------------------------------------------------
# Mesh-file bbox parsing
# ---------------------------------------------------------------------------
# Single source of truth for both runtime suggestion (CLI) and the
# scripts/extract_bboxes.py one-shot tool.

def bbox_from_fort14(path: Path) -> Optional[BoundingBox]:
    """Parse an ADCIRC fort.14-format file and return its node-coord bbox.

    Layout:
      line 1:  AGRID name
      line 2:  NE NN  (num elements, num nodes)
      next NN: nodeID  x  y  depth   (whitespace-delimited)
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            f.readline()  # AGRID
            ne_nn = f.readline().split()
            if len(ne_nn) < 2:
                return None
            nn = int(ne_nn[1])
            min_lon = min_lat = float("inf")
            max_lon = max_lat = float("-inf")
            for _ in range(nn):
                parts = f.readline().split()
                if len(parts) < 3:
                    return None
                x, y = float(parts[1]), float(parts[2])
                if x < min_lon: min_lon = x
                if x > max_lon: max_lon = x
                if y < min_lat: min_lat = y
                if y > max_lat: max_lat = y
            return BoundingBox(min_lon, min_lat, max_lon, max_lat)
    except (ValueError, IndexError, OSError):
        return None


def bbox_from_2dm(path: Path) -> Optional[BoundingBox]:
    """Parse an SMS .2dm-format file (lines ``ND id x y z``)."""
    try:
        min_lon = min_lat = float("inf")
        max_lon = max_lat = float("-inf")
        n = 0
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("ND "):
                    parts = line.split()
                    if len(parts) >= 4:
                        x, y = float(parts[2]), float(parts[3])
                        if x < min_lon: min_lon = x
                        if x > max_lon: max_lon = x
                        if y < min_lat: min_lat = y
                        if y > max_lat: max_lat = y
                        n += 1
        if n == 0:
            return None
        return BoundingBox(min_lon, min_lat, max_lon, max_lat)
    except (ValueError, OSError):
        return None


def bbox_from_mesh_file(path: Path) -> Optional[BoundingBox]:
    """Dispatch to the right parser by extension.

    Recognized: ``.14`` / ``.fort.14`` / ``.grd`` (ADCIRC) and ``.2dm`` (SMS).
    Anything else falls through to the fort.14 parser as a best-effort.
    """
    if path.suffix == ".2dm":
        return bbox_from_2dm(path)
    return bbox_from_fort14(path)
