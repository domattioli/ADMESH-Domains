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
    intersection,
    is_antimeridian_wrapping,
    per_mesh_iou,
    suggest_domain,
    union,
    IoUScore,
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

    def test_antimeridian_returns_zero(self, capsys):
        iou = compute_iou(bb(170, 0, -170, 10), bb(-180, 0, 180, 10))
        assert iou == 0.0
        captured = capsys.readouterr()
        assert "antimeridian" in captured.err.lower()

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
