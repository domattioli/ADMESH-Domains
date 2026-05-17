"""Unit tests for Mesh.validate() — element_type and related fields."""

from __future__ import annotations

import pytest

from admesh_domains import Mesh, SchemaError, VALID_ELEMENT_TYPES


class TestElementTypeValidation:
    def test_valid_triangle_accepted(self):
        m = Mesh(id="x@v1", filename="x.14", element_type="triangle")
        m.validate()  # must not raise

    def test_valid_quadrilateral_accepted(self):
        m = Mesh(id="x@v1", filename="x.14", element_type="quadrilateral")
        m.validate()

    def test_valid_mixed_element_accepted(self):
        m = Mesh(id="x@v1", filename="x.14", element_type="Mixed-Element")
        m.validate()

    def test_none_accepted_backward_compatible(self):
        m = Mesh(id="x@v1", filename="x.14", element_type=None)
        m.validate()  # None = unspecified; always allowed

    def test_missing_element_type_accepted(self):
        m = Mesh(id="x@v1", filename="x.14")
        assert m.element_type is None
        m.validate()

    def test_invalid_type_raises_schema_error(self):
        m = Mesh(id="x@v1", filename="x.14", element_type="hexahedral")
        with pytest.raises(SchemaError, match="element_type"):
            m.validate()

    def test_lowercase_mixed_rejected(self):
        m = Mesh(id="x@v1", filename="x.14", element_type="mixed-element")
        with pytest.raises(SchemaError, match="element_type"):
            m.validate()

    def test_arbitrary_string_rejected(self):
        m = Mesh(id="x@v1", filename="x.14", element_type="tri")
        with pytest.raises(SchemaError, match="element_type"):
            m.validate()

    def test_valid_element_types_constant_has_three_values(self):
        assert VALID_ELEMENT_TYPES == {"triangle", "quadrilateral", "Mixed-Element"}

    def test_element_type_round_trip_from_dict(self):
        d = {"id": "x@v1", "filename": "x.14", "element_type": "Mixed-Element"}
        m = Mesh.from_dict(d)
        assert m.element_type == "Mixed-Element"
        assert m.to_dict().get("element_type") == "Mixed-Element"

    def test_element_type_omitted_when_none(self):
        m = Mesh(id="x@v1", filename="x.14")
        assert "element_type" not in m.to_dict()
