"""Integration tests for Mixed-Element mesh support.

Covers: fort.14 parse → Mesh catalog entry → round-trip serialization.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from admesh_domains import Mesh, SchemaError, VALID_ELEMENT_TYPES
from admesh_domains.geometry import bbox_from_fort14


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "meshes"
MIXED_DEMO = FIXTURE_DIR / "mixed_demo.fort14"


class TestMixedElementFort14RoundTrip:
    def test_fixture_exists(self):
        assert MIXED_DEMO.exists(), f"fixture missing: {MIXED_DEMO}"

    def test_bbox_parsed_from_mixed_fort14(self):
        bb = bbox_from_fort14(MIXED_DEMO)
        assert bb is not None
        assert bb.min_lon == pytest.approx(-80.0)
        assert bb.max_lon == pytest.approx(-78.0)
        assert bb.min_lat == pytest.approx(25.0)
        assert bb.max_lat == pytest.approx(26.0)

    def test_mesh_entry_with_mixed_element_validates(self):
        bb = bbox_from_fort14(MIXED_DEMO)
        m = Mesh(
            id="mixed_demo@v1",
            filename="mixed_demo.fort14",
            element_type="Mixed-Element",
            bounding_box=bb,
            size_mb=0.001,
            node_count=6,
            element_count=5,
        )
        m.validate()  # must not raise

    def test_round_trip_preserves_element_type(self):
        original = Mesh(
            id="mixed_demo@v1",
            filename="mixed_demo.fort14",
            element_type="Mixed-Element",
        )
        data = original.to_dict()
        restored = Mesh.from_dict(data)
        assert restored.element_type == "Mixed-Element"

    def test_all_element_types_round_trip(self):
        for etype in VALID_ELEMENT_TYPES:
            m = Mesh(id="x@v1", filename="x.14", element_type=etype)
            m.validate()
            restored = Mesh.from_dict(m.to_dict())
            assert restored.element_type == etype

    def test_invalid_element_type_caught_before_catalog(self):
        m = Mesh(id="x@v1", filename="x.14", element_type="hybrid")
        with pytest.raises(SchemaError, match="element_type"):
            m.validate()
