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
    """One Domain's match scores against a candidate mesh's bbox."""

    domain_name: str
    per_mesh_iou: float
    union_iou: float
    centroid_distance_deg: Optional[float]
    confidence: str  # confident | uncertain | low

    def to_dict(self) -> dict:
        return {
            "domain": self.domain_name,
            "per_mesh_iou": round(self.per_mesh_iou, 4),
            "union_iou": round(self.union_iou, 4),
            "centroid_distance_deg": (
                round(self.centroid_distance_deg, 4)
                if self.centroid_distance_deg is not None else None
            ),
            "confidence": self.confidence,
        }


def suggest_domain(new_bbox: BoundingBox, manifest: Manifest) -> list[IoUScore]:
    """Rank every Domain by IoU against ``new_bbox`` (highest per-mesh IoU first)."""
    scores: list[IoUScore] = []
    for d in manifest.domains:
        u = domain_union_bbox(d)
        if u is None:
            continue  # Domain has no geographic-bbox meshes; can't compare
        pm = per_mesh_iou(new_bbox, d)
        ui = compute_iou(new_bbox, u)
        cd = centroid_distance(new_bbox, u) if pm > 0 else None
        scores.append(IoUScore(
            domain_name=d.name,
            per_mesh_iou=pm,
            union_iou=ui,
            centroid_distance_deg=cd,
            confidence=_confidence(pm),
        ))
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
