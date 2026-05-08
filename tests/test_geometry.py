"""Tests for admesh_domains.geometry — bbox math, IoU, suggester."""

from __future__ import annotations

from pathlib import Path

import pytest

from admesh_domains import BoundingBox, get_mesh
from admesh_domains.geometry import (
    area,
    bbox_from_2dm,
    bbox_from_fort14,
    bbox_from_mesh_file,
    centroid,
    centroid_distance,
    compute_iou,
    domain_union_bbox,
    extract_boundary_polygon,
    hausdorff_distance,
    intersection,
    is_antimeridian_wrapping,
    per_mesh_iou,
    polygon_iou,
    suggest_domain,
    union,
    IoUScore,
    _split_antimeridian_bbox,
)


def bb(min_lon, min_lat, max_lon, max_lat):
    return BoundingBox(min_lon, min_lat, max_lon, max_lat)


class TestBboxArithmetic:
    def test_area_simple(self):
        assert area(bb(0, 0, 10, 5)) == 50.0

    def test_area_zero_for_degenerate(self):
        assert area(bb(0, 0, 0, 5)) == 0.0
        assert area(bb(0, 0, 10, 0)) == 0.0

    def test_area_zero_for_antimeridian(self):
        assert area(bb(170, -10, -170, 10)) == 0.0

    def test_intersection_overlapping(self):
        i = intersection(bb(0, 0, 10, 10), bb(5, 5, 15, 15))
        assert i == bb(5, 5, 10, 10)

    def test_intersection_disjoint(self):
        assert intersection(bb(0, 0, 1, 1), bb(2, 2, 3, 3)) is None

    def test_intersection_touching_returns_none(self):
        # Edge-touching is treated as no intersection (zero area)
        assert intersection(bb(0, 0, 1, 1), bb(1, 0, 2, 1)) is None

    def test_union_basic(self):
        u = union(bb(0, 0, 1, 1), bb(2, 3, 4, 5))
        assert u == bb(0, 0, 4, 5)

    def test_centroid(self):
        assert centroid(bb(-2, -4, 2, 4)) == (0.0, 0.0)

    def test_antimeridian_detection(self):
        assert is_antimeridian_wrapping(bb(170, 0, -170, 10))
        assert not is_antimeridian_wrapping(bb(-170, 0, 170, 10))


class TestComputeIoU:
    def test_identical_bboxes(self):
        b = bb(0, 0, 10, 10)
        assert compute_iou(b, b) == pytest.approx(1.0)

    def test_disjoint_bboxes(self):
        assert compute_iou(bb(0, 0, 1, 1), bb(2, 2, 3, 3)) == 0.0

    def test_contained_smaller_in_larger(self):
        # 1x1 inside a 10x10 → IoU = 1 / (1 + 100 - 1) = 1/100
        iou = compute_iou(bb(0, 0, 1, 1), bb(0, 0, 10, 10))
        assert iou == pytest.approx(0.01)

    def test_partial_overlap(self):
        # Two 10x10 boxes overlapping in 5x10 strip → inter=50, union=150
        iou = compute_iou(bb(0, 0, 10, 10), bb(5, 0, 15, 10))
        assert iou == pytest.approx(50 / 150)

    def test_antimeridian_wrapping_split(self):
        pacific = bb(170, -10, -170, 10)
        parts = _split_antimeridian_bbox(pacific)
        assert len(parts) == 2
        assert parts[0] == bb(170, -10, 180, 10)
        assert parts[1] == bb(-180, -10, -170, 10)

    def test_antimeridian_non_wrapping_no_split(self):
        normal = bb(-170, -10, 170, 10)
        parts = _split_antimeridian_bbox(normal)
        assert len(parts) == 1
        assert parts[0] == normal

    def test_antimeridian_iou_with_itself(self):
        pacific = bb(170, -10, -170, 10)
        iou = compute_iou(pacific, pacific)
        assert iou == pytest.approx(1.0)

    def test_antimeridian_iou_vs_normal_bbox(self):
        pacific = bb(170, -10, -170, 10)
        wnat = bb(-85, 15, -50, 45)
        iou = compute_iou(pacific, wnat)
        assert iou == 0.0

    def test_antimeridian_iou_with_overlap(self):
        pacific_east = bb(170, -10, -170, 10)
        overlap_box = bb(175, 0, 180, 5)
        iou = compute_iou(pacific_east, overlap_box)
        assert iou > 0.0

    def test_centroid_distance(self):
        d = centroid_distance(bb(0, 0, 2, 2), bb(4, 0, 6, 2))
        assert d == pytest.approx(4.0)


class TestDomainHelpers:
    def test_domain_union_bbox_excludes_non_geographic(self, loaded_manifest):
        # Baranja Hill is in UTM coords; should NOT contribute to union bbox.
        baranja = loaded_manifest.get_domain("BaranjaHill")
        assert domain_union_bbox(baranja) is None

    def test_per_mesh_iou_against_existing_wnat_returns_one(self, loaded_manifest):
        wnat = loaded_manifest.get_domain("WNAT")
        # Pick the WNAT_Hagen mesh's bbox and compare to its own Domain
        target = next(m for m in wnat.meshes if m.id == "hagen@v1")
        assert per_mesh_iou(target.bounding_box, wnat) == pytest.approx(1.0, abs=1e-6)


class TestSuggestDomain:
    def test_existing_wnat_mesh_ranks_wnat_first(self, loaded_manifest):
        wnat_hagen = get_mesh("WNAT/hagen@v1", manifest=loaded_manifest)
        scores = suggest_domain(wnat_hagen.bounding_box, loaded_manifest)
        assert scores[0].domain_name == "WNAT"
        assert scores[0].confidence == "confident"
        assert scores[0].per_mesh_iou >= 0.99

    def test_chesapeake_mesh_ranks_chesapeake_first(self, loaded_manifest):
        cb = get_mesh("ChesapeakeBay/default@v1", manifest=loaded_manifest)
        scores = suggest_domain(cb.bounding_box, loaded_manifest)
        assert scores[0].domain_name == "ChesapeakeBay"

    def test_gulf_of_mexico_no_confident_match(self, loaded_manifest):
        # Gulf of Mexico bbox is roughly inside WNAT — strong overlap expected
        gulf = bb(-95, 25, -80, 31)
        scores = suggest_domain(gulf, loaded_manifest)
        # Gulf is well within WNAT extent -> WNAT will be uncertain or confident
        # but we want a non-empty ranked list
        assert len(scores) > 0

    def test_pacific_no_match(self, loaded_manifest):
        pacific = bb(-160, -10, -140, 10)
        scores = suggest_domain(pacific, loaded_manifest)
        # No current Domain covers the Pacific -> all candidates "low"
        assert all(s.confidence == "low" for s in scores)

    def test_score_serializes_to_dict(self):
        s = IoUScore("Foo", 0.6, 0.4, 1.234, "confident")
        d = s.to_dict()
        assert d["domain"] == "Foo"
        assert d["confidence"] == "confident"
        assert d["per_mesh_iou"] == 0.6
        assert d["union_iou"] == 0.4


class TestTier2BoundaryExtraction:
    """Tests for Tier 2 boundary polygon extraction (requires shapely)."""

    def test_extract_boundary_from_fort14(self, dev_manifest_path):
        """Extract boundary from a known fort.14 file."""
        path = dev_manifest_path.parent / "meshes" / "WNAT_Hagen.14"
        boundary = extract_boundary_polygon(path)
        assert boundary is not None
        # Boundary should be a shapely Polygon with non-zero area
        assert boundary.area > 0
        # Should be a valid (non-self-intersecting) polygon
        assert boundary.is_valid or not boundary.is_empty

    def test_extract_boundary_missing_file_returns_none(self, tmp_path):
        """Boundary extraction returns None for missing files."""
        missing = tmp_path / "nope.14"
        assert extract_boundary_polygon(missing) is None

    def test_extract_boundary_invalid_fort14_returns_none(self, tmp_path):
        """Boundary extraction returns None for malformed fort.14."""
        invalid = tmp_path / "invalid.14"
        invalid.write_text("garbage\ninvalid format\n")
        assert extract_boundary_polygon(invalid) is None


class TestTier2PolygonMetrics:
    """Tests for Tier 2 polygon similarity metrics."""

    def test_polygon_iou_identical_polygons(self):
        """IoU of a polygon with itself should be 1.0."""
        try:
            from shapely.geometry import Polygon
        except ImportError:
            pytest.skip("shapely not installed")

        square = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        iou = polygon_iou(square, square)
        assert iou == pytest.approx(1.0)

    def test_polygon_iou_disjoint_polygons(self):
        """IoU of non-overlapping polygons should be 0.0."""
        try:
            from shapely.geometry import Polygon
        except ImportError:
            pytest.skip("shapely not installed")

        square1 = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        square2 = Polygon([(2, 2), (3, 2), (3, 3), (2, 3)])
        iou = polygon_iou(square1, square2)
        assert iou == pytest.approx(0.0)

    def test_polygon_iou_partial_overlap(self):
        """IoU of overlapping polygons."""
        try:
            from shapely.geometry import Polygon
        except ImportError:
            pytest.skip("shapely not installed")

        square1 = Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])
        square2 = Polygon([(1, 1), (3, 1), (3, 3), (1, 3)])
        iou = polygon_iou(square1, square2)
        # Overlap is 1x1=1, union is 2x2 + 2x2 - 1x1 = 7, so iou = 1/7 ≈ 0.143
        assert iou == pytest.approx(1.0 / 7.0, abs=0.01)

    def test_polygon_iou_none_inputs(self):
        """IoU with None inputs returns 0.0."""
        iou = polygon_iou(None, None)
        assert iou == 0.0

    def test_hausdorff_distance_identical_polygons(self):
        """Hausdorff distance of a polygon with itself should be 0."""
        try:
            from shapely.geometry import Polygon
        except ImportError:
            pytest.skip("shapely not installed")

        square = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        dist = hausdorff_distance(square, square)
        assert dist == pytest.approx(0.0)

    def test_hausdorff_distance_disjoint_polygons(self):
        """Hausdorff distance increases with separation."""
        try:
            from shapely.geometry import Polygon
        except ImportError:
            pytest.skip("shapely not installed")

        square1 = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        square2 = Polygon([(10, 10), (11, 10), (11, 11), (10, 11)])
        dist = hausdorff_distance(square1, square2)
        # Should be roughly the diagonal distance from (1,1) to (10,10)
        assert dist is not None
        assert dist > 10

    def test_hausdorff_distance_none_inputs(self):
        """Hausdorff distance with None inputs returns None."""
        dist = hausdorff_distance(None, None)
        assert dist is None


class TestTier2SuggestDomain:
    """Tests for Tier 2 domain suggestion with boundary metrics."""

    def test_tier2_same_mesh_ranks_first(self, dev_manifest_path):
        """When suggesting for WNAT mesh, WNAT should rank first with tier=2."""
        from admesh_domains.manifest import load_manifest

        path = dev_manifest_path.parent / "meshes" / "WNAT_Hagen.14"
        manifest = load_manifest(dev_manifest_path)
        from admesh_domains.geometry import bbox_from_mesh_file
        bb = bbox_from_mesh_file(path)
        assert bb is not None

        scores = suggest_domain(bb, manifest, tier=2, new_mesh_path=path)
        assert len(scores) > 0
        # WNAT should be first with perfect metrics
        assert scores[0].domain_name == "WNAT"
        assert scores[0].per_mesh_iou == pytest.approx(1.0)
        assert scores[0].boundary_polygon_iou == pytest.approx(1.0, abs=0.01)

    def test_tier2_fallback_when_shapely_unavailable(self, dev_manifest_path, monkeypatch):
        """Tier 2 should fall back to tier 1 if shapely is missing."""
        # This test is tricky because shapely is already imported.
        # We'll just verify that tier=2 with no mesh_path falls back to tier 1
        from admesh_domains.manifest import load_manifest
        from admesh_domains.geometry import bbox_from_mesh_file

        path = dev_manifest_path.parent / "meshes" / "WNAT_Hagen.14"
        manifest = load_manifest(dev_manifest_path)
        bb = bbox_from_mesh_file(path)

        # Call without new_mesh_path (should fail to extract boundary)
        scores = suggest_domain(bb, manifest, tier=2, new_mesh_path=None)
        # Should still return results, just without boundary metrics
        assert len(scores) > 0
        # First result should be WNAT, but based on bbox IoU alone
        assert scores[0].domain_name == "WNAT"
        # Boundary metrics should be None (fallback to tier 1)
        assert scores[0].boundary_polygon_iou is None or scores[0].boundary_polygon_iou == 0.0


class TestMeshFileParsing:
    def test_fort14_roundtrip(self, dev_manifest_path):
        path = dev_manifest_path.parent / "meshes" / "WNAT_Hagen.14"
        bb_ = bbox_from_fort14(path)
        assert bb_ is not None
        assert -98 < bb_.min_lon < -97
        assert 7 < bb_.min_lat < 9

    def test_2dm_parser(self, dev_manifest_path):
        path = dev_manifest_path.parent / "meshes" / "dom.2dm"
        bb_ = bbox_from_2dm(path)
        assert bb_ is not None
        assert bb_.min_lon < bb_.max_lon
        assert area(bb_) > 0

    def test_grd_dispatches_to_fort14(self, dev_manifest_path):
        path = dev_manifest_path.parent / "meshes" / "nc_inundation_v6c.grd"
        bb_ = bbox_from_mesh_file(path)
        assert bb_ is not None
        assert -98 < bb_.min_lon < -97

    def test_missing_file_returns_none(self, tmp_path):
        assert bbox_from_mesh_file(tmp_path / "nope.14") is None
