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

    def test_domain_with_no_meshes_succeeds(self, tmp_path):
        body = """
schema_version = "0.3"
[metadata]
version = "1.0.0"
[[domains]]
name = "Empty"
"""
        m = load_manifest(self._write_manifest(tmp_path, body))
        assert len(m.domains) == 1
        assert m.domains[0].name == "Empty"
        assert len(m.domains[0].meshes) == 0


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


class TestContentUid:
    """Tests for Mesh.content_uid (Issue #65, spec 064 §A)."""

    def test_content_uid_defaults_none(self):
        m = Mesh(id="x@v1", filename="x.14")
        assert m.content_uid is None
        assert "content_uid" not in m.to_dict()

    def test_content_uid_round_trip(self):
        good = "sha256-v1:" + "a" * 64
        m = Mesh.from_dict({"id": "x@v1", "filename": "x.14", "content_uid": good})
        assert m.content_uid == good
        m.validate()
        assert m.to_dict().get("content_uid") == good

    def test_content_uid_rejects_bad_prefix(self):
        m = Mesh(id="x@v1", filename="x.14", content_uid="md5:" + "a" * 64)
        with pytest.raises(SchemaError):
            m.validate()

    def test_content_uid_rejects_short_hex(self):
        m = Mesh(id="x@v1", filename="x.14", content_uid="sha256-v1:abc")
        with pytest.raises(SchemaError):
            m.validate()

    def test_content_uid_rejects_non_hex(self):
        m = Mesh(id="x@v1", filename="x.14", content_uid="sha256-v1:" + "g" * 64)
        with pytest.raises(SchemaError):
            m.validate()

    def test_compute_returns_none_when_file_missing(self, tmp_path):
        m = Mesh.from_dict(
            {"id": "x@v1", "filename": "nope.14"},
            domain_name="D",
            base_dir=tmp_path,
        )
        assert m.compute_content_uid() is None

    def test_compute_returns_prefixed_sha256(self, tmp_path):
        (tmp_path / "meshes").mkdir()
        (tmp_path / "meshes" / "x.14").write_bytes(b"hello\nworld\n")
        m = Mesh.from_dict(
            {"id": "x@v1", "filename": "x.14"},
            domain_name="D",
            base_dir=tmp_path,
        )
        uid = m.compute_content_uid()
        assert uid is not None
        assert uid.startswith("sha256-v1:")
        assert len(uid) == len("sha256-v1:") + 64

    def test_compute_canonicalizes_line_endings(self, tmp_path):
        """Same payload with LF vs CRLF must produce the same UID."""
        (tmp_path / "meshes").mkdir()
        (tmp_path / "meshes" / "lf.14").write_bytes(b"a\nb\nc\n")
        (tmp_path / "meshes" / "crlf.14").write_bytes(b"a\r\nb\r\nc\r\n")
        lf = Mesh.from_dict(
            {"id": "lf@v1", "filename": "lf.14"},
            domain_name="D", base_dir=tmp_path,
        )
        crlf = Mesh.from_dict(
            {"id": "crlf@v1", "filename": "crlf.14"},
            domain_name="D", base_dir=tmp_path,
        )
        assert lf.compute_content_uid() == crlf.compute_content_uid()

    def test_compute_canonicalizes_trailing_whitespace(self, tmp_path):
        """Trailing spaces/tabs on a line must not change the UID."""
        (tmp_path / "meshes").mkdir()
        (tmp_path / "meshes" / "clean.14").write_bytes(b"a\nb\n")
        (tmp_path / "meshes" / "dirty.14").write_bytes(b"a   \nb\t\n")
        clean = Mesh.from_dict(
            {"id": "c@v1", "filename": "clean.14"},
            domain_name="D", base_dir=tmp_path,
        )
        dirty = Mesh.from_dict(
            {"id": "d@v1", "filename": "dirty.14"},
            domain_name="D", base_dir=tmp_path,
        )
        assert clean.compute_content_uid() == dirty.compute_content_uid()

    def test_compute_distinguishes_different_content(self, tmp_path):
        (tmp_path / "meshes").mkdir()
        (tmp_path / "meshes" / "a.14").write_bytes(b"hello\n")
        (tmp_path / "meshes" / "b.14").write_bytes(b"world\n")
        a = Mesh.from_dict({"id": "a@v1", "filename": "a.14"}, domain_name="D", base_dir=tmp_path)
        b = Mesh.from_dict({"id": "b@v1", "filename": "b.14"}, domain_name="D", base_dir=tmp_path)
        assert a.compute_content_uid() != b.compute_content_uid()


class TestManifestHelpers:
    def test_get_domain_case_insensitive(self, loaded_manifest):
        assert loaded_manifest.get_domain("wnat") is loaded_manifest.get_domain("WNAT")

    def test_domain_names_returns_list(self, loaded_manifest):
        assert "WNAT" in loaded_manifest.domain_names()

    def test_find_by_uid_returns_none_when_absent(self, loaded_manifest):
        assert loaded_manifest.find_by_uid("sha256-v1:" + "0" * 64) is None

    def test_find_by_uid_roundtrip(self, loaded_manifest):
        # Pick any mesh, assign a UID via the in-memory model, then look it up.
        mesh = next(loaded_manifest.all_meshes())
        target_uid = "sha256-v1:" + "f" * 64
        mesh.content_uid = target_uid
        found = loaded_manifest.find_by_uid(target_uid)
        assert found is mesh
