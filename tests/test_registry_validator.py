"""Tests for admesh_domains.manifest — load, validate, parse."""

from __future__ import annotations

from pathlib import Path

import pytest

from admesh_domains import (
    Domain,
    Mesh,
    BoundingBox,
    SchemaError,
    load_manifest,
    Manifest,
    ManifestNotFoundError,
    ManifestValidationError,
)


class TestLoadManifest:
    def test_default_load_succeeds(self):
        m = load_manifest()
        assert isinstance(m, Manifest)
        assert m.total_meshes > 0
        assert len(m.domains) > 0

    def test_load_explicit_path(self, dev_manifest_path):
        m = load_manifest(dev_manifest_path)
        assert m.source_path == dev_manifest_path

    def test_load_missing_raises(self, tmp_path):
        with pytest.raises(ManifestNotFoundError):
            load_manifest(tmp_path / "no-such-manifest.toml")

    def test_total_meshes_matches_sum(self, loaded_manifest):
        assert loaded_manifest.total_meshes == sum(
            len(d.meshes) for d in loaded_manifest.domains
        )

    def test_all_meshes_iterates_every_mesh(self, loaded_manifest):
        n = sum(1 for _ in loaded_manifest.all_meshes())
        assert n == loaded_manifest.total_meshes


class TestManifestValidation:
    def _write_manifest(self, tmp_path: Path, body: str) -> Path:
        p = tmp_path / "manifest.toml"
        p.write_text(body)
        return p

    def test_duplicate_domain_names_fail(self, tmp_path):
        body = """
schema_version = "0.2"
[metadata]
version = "1.0.0"
[[domains]]
name = "Foo"
[[domains.meshes]]
id = "a@v1"
filename = "a.14"
size_mb = 0.1
[[domains]]
name = "Foo"
[[domains.meshes]]
id = "b@v1"
filename = "b.14"
size_mb = 0.1
"""
        with pytest.raises(ManifestValidationError):
            load_manifest(self._write_manifest(tmp_path, body))

    def test_duplicate_mesh_ids_in_domain_fail(self, tmp_path):
        body = """
schema_version = "0.2"
[metadata]
version = "1.0.0"
[[domains]]
name = "Foo"
[[domains.meshes]]
id = "dup@v1"
filename = "a.14"
size_mb = 0.1
[[domains.meshes]]
id = "dup@v1"
filename = "b.14"
size_mb = 0.1
"""
        with pytest.raises(ManifestValidationError):
            load_manifest(self._write_manifest(tmp_path, body))

    def test_domain_with_slash_in_name_fails(self, tmp_path):
        body = """
schema_version = "0.2"
[metadata]
version = "1.0.0"
[[domains]]
name = "Foo/Bar"
[[domains.meshes]]
id = "a@v1"
filename = "a.14"
size_mb = 0.1
"""
        with pytest.raises(ManifestValidationError):
            load_manifest(self._write_manifest(tmp_path, body))

    def test_invalid_category_fails(self, tmp_path):
        body = """
schema_version = "0.2"
[metadata]
version = "1.0.0"
[[domains]]
name = "Foo"
category = "not-a-real-category"
[[domains.meshes]]
id = "a@v1"
filename = "a.14"
size_mb = 0.1
"""
        with pytest.raises(ManifestValidationError):
            load_manifest(self._write_manifest(tmp_path, body))

    def test_negative_size_mb_fails(self, tmp_path):
        body = """
schema_version = "0.2"
[metadata]
version = "1.0.0"
[[domains]]
name = "Foo"
[[domains.meshes]]
id = "a@v1"
filename = "a.14"
size_mb = -0.5
"""
        with pytest.raises(ManifestValidationError):
            load_manifest(self._write_manifest(tmp_path, body))

    def test_invalid_license_fails(self, tmp_path):
        body = """
schema_version = "0.2"
[metadata]
version = "1.0.0"
[[domains]]
name = "Foo"
[[domains.meshes]]
id = "a@v1"
filename = "a.14"
size_mb = 0.1
license = "GPL-evangelist-3000"
"""
        with pytest.raises(ManifestValidationError):
            load_manifest(self._write_manifest(tmp_path, body))

    def test_domain_with_no_meshes_fails(self, tmp_path):
        body = """
schema_version = "0.2"
[metadata]
version = "1.0.0"
[[domains]]
name = "Empty"
"""
        with pytest.raises(ManifestValidationError):
            load_manifest(self._write_manifest(tmp_path, body))


class TestSchemaPrimitives:
    def test_bbox_accepts_valid_coords(self):
        bb = BoundingBox(min_lon=-1, min_lat=-1, max_lon=1, max_lat=1)
        bb.validate()

    def test_bbox_rejects_inverted_lat(self):
        bb = BoundingBox(min_lon=-1, min_lat=10, max_lon=1, max_lat=-10)
        with pytest.raises(SchemaError):
            bb.validate()

    def test_mesh_full_id_with_domain(self):
        m = Mesh(id="x@v1", filename="x.14")
        m._domain_name = "MyDomain"
        assert m.full_id == "MyDomain/x@v1"

    def test_mesh_from_dict_parses_bbox(self):
        m = Mesh.from_dict({
            "id": "x@v1",
            "filename": "x.14",
            "bounding_box": {"min_lon": -1, "min_lat": -1, "max_lon": 1, "max_lat": 1},
        })
        assert isinstance(m.bounding_box, BoundingBox)
        assert m.bounding_box.max_lon == 1

    def test_mesh_test_case_defaults_false(self):
        m = Mesh(id="x@v1", filename="x.14")
        assert m.test_case is False

    def test_mesh_test_case_round_trip(self):
        m = Mesh.from_dict({"id": "x@v1", "filename": "x.14", "test_case": True})
        assert m.test_case is True
        assert m.to_dict().get("test_case") is True

    def test_mesh_test_case_omitted_when_false(self):
        m = Mesh(id="x@v1", filename="x.14")
        assert "test_case" not in m.to_dict()

    def test_mesh_kind_defaults_to_mesh(self):
        m = Mesh(id="x@v1", filename="x.14")
        assert m.kind == "mesh"
        assert "kind" not in m.to_dict()

    def test_mesh_kind_boundary_round_trip(self):
        m = Mesh.from_dict({"id": "x@v1", "filename": "x.14", "kind": "boundary"})
        assert m.kind == "boundary"
        assert m.to_dict().get("kind") == "boundary"

    def test_mesh_kind_invalid_rejected(self):
        m = Mesh(id="x@v1", filename="x.14", kind="grid")
        with pytest.raises(SchemaError):
            m.validate()


class TestManifestHelpers:
    def test_get_domain_case_insensitive(self, loaded_manifest):
        assert loaded_manifest.get_domain("wnat") is loaded_manifest.get_domain("WNAT")

    def test_domain_names_returns_list(self, loaded_manifest):
        assert "WNAT" in loaded_manifest.domain_names()
