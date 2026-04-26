"""Tests for admesh_domains.query — find_domains, find_meshes, get_*."""

from __future__ import annotations

import pytest

from admesh_domains import (
    find_domains,
    find_meshes,
    get_domain,
    get_mesh,
    list_domains,
    list_regions,
    list_applications,
)


class TestFindDomains:
    def test_no_filters_returns_all(self, loaded_manifest):
        assert len(find_domains(manifest=loaded_manifest)) == len(loaded_manifest)

    def test_filter_by_category_real_world(self, loaded_manifest):
        out = find_domains(category="real-world", manifest=loaded_manifest)
        assert len(out) == 8
        assert all(d.category == "real-world" for d in out)

    def test_filter_by_category_synthetic(self, loaded_manifest):
        out = find_domains(category="synthetic", manifest=loaded_manifest)
        assert len(out) == 5
        assert all(d.category == "synthetic" for d in out)

    def test_filter_by_region_north_america(self, loaded_manifest):
        out = find_domains(region="North America", manifest=loaded_manifest)
        names = {d.name for d in out}
        assert "ChesapeakeBay" in names
        assert "GreatLakes" in names
        assert "WNAT" not in names  # WNAT is Atlantic Ocean

    def test_filter_region_case_insensitive(self, loaded_manifest):
        a = find_domains(region="North America", manifest=loaded_manifest)
        b = find_domains(region="NORTH AMERICA", manifest=loaded_manifest)
        assert {d.name for d in a} == {d.name for d in b}

    def test_filter_by_application(self, loaded_manifest):
        out = find_domains(application="Lake Circulation", manifest=loaded_manifest)
        names = {d.name for d in out}
        assert {"GreatLakes", "LakeErie", "LakeMichigan"}.issubset(names)

    def test_filter_by_name_exact(self, loaded_manifest):
        out = find_domains(name="WNAT", manifest=loaded_manifest)
        assert len(out) == 1
        assert out[0].name == "WNAT"

    def test_combined_filters_are_anded(self, loaded_manifest):
        out = find_domains(
            category="real-world",
            region="Mediterranean",
            manifest=loaded_manifest,
        )
        assert len(out) == 1
        assert out[0].name == "Italy"


class TestFindMeshes:
    def test_no_filters_returns_all_meshes(self, loaded_manifest):
        out = find_meshes(manifest=loaded_manifest)
        assert len(out) == loaded_manifest.total_meshes
        assert len(out) >= 40  # registry only grows

    def test_filter_by_domain_wnat(self, loaded_manifest):
        out = find_meshes(domain="WNAT", manifest=loaded_manifest)
        ids = {m.id for m in out}
        assert {"hagen@v1", "onur@v1", "test@v1"}.issubset(ids)

    def test_filter_by_element_type_quadrilateral(self, loaded_manifest):
        out = find_meshes(element_type="quadrilateral", manifest=loaded_manifest)
        assert len(out) == 2
        assert all(m.element_type == "quadrilateral" for m in out)

    def test_filter_by_min_size_returns_subset(self, loaded_manifest):
        all_meshes = find_meshes(manifest=loaded_manifest)
        large = find_meshes(min_size_mb=5.0, manifest=loaded_manifest)
        assert len(large) < len(all_meshes)
        assert all(m.size_mb >= 5.0 for m in large)

    def test_filter_by_refinement_level(self, loaded_manifest):
        out = find_meshes(refinement_level="high", manifest=loaded_manifest)
        assert len(out) == 1
        assert "DelawareBay" in out[0].full_id


class TestGetters:
    def test_get_mesh_by_composite_id(self, loaded_manifest):
        mesh = get_mesh("WNAT/hagen@v1", manifest=loaded_manifest)
        assert mesh.id == "hagen@v1"
        assert mesh.filename == "WNAT_Hagen.14"
        assert mesh.full_id == "WNAT/hagen@v1"

    def test_get_mesh_by_alias(self, loaded_manifest):
        mesh = get_mesh("WNAT_53K_Nodes", manifest=loaded_manifest)
        assert mesh.full_id == "WNAT/hagen@v1"

    def test_get_mesh_by_filename(self, loaded_manifest):
        mesh = get_mesh("Chesapeake_Bay.14", manifest=loaded_manifest)
        assert mesh.full_id == "ChesapeakeBay/default@v1"

    def test_get_mesh_missing_raises(self, loaded_manifest):
        with pytest.raises(KeyError):
            get_mesh("NoSuchDomain/no-such@v1", manifest=loaded_manifest)

    def test_get_domain_case_insensitive(self, loaded_manifest):
        a = get_domain("WNAT", manifest=loaded_manifest)
        b = get_domain("wnat", manifest=loaded_manifest)
        assert a.name == b.name

    def test_get_domain_missing_raises(self, loaded_manifest):
        with pytest.raises(KeyError):
            get_domain("NoSuchDomain", manifest=loaded_manifest)


class TestListHelpers:
    def test_list_domains_returns_all(self, loaded_manifest):
        assert len(list_domains(manifest=loaded_manifest)) == 13

    def test_list_regions_unique_sorted(self, loaded_manifest):
        regions = list_regions(manifest=loaded_manifest)
        assert regions == sorted(set(regions))
        assert "North America" in regions

    def test_list_applications_unique_sorted(self, loaded_manifest):
        apps = list_applications(manifest=loaded_manifest)
        assert apps == sorted(set(apps))
        assert "Lake Circulation" in apps


class TestBoundingBox:
    def test_real_world_meshes_have_bbox(self, loaded_manifest):
        wnat = get_mesh("WNAT/hagen@v1", manifest=loaded_manifest)
        assert wnat.bounding_box is not None
        assert wnat.bounding_box.min_lon < wnat.bounding_box.max_lon
        assert wnat.bounding_box.min_lat < wnat.bounding_box.max_lat

    def test_chesapeake_bbox_in_expected_range(self, loaded_manifest):
        m = get_mesh("ChesapeakeBay/default@v1", manifest=loaded_manifest)
        assert -82 < m.bounding_box.min_lon < -80
        assert 27 < m.bounding_box.min_lat < 29


class TestLicenseFilter:
    def test_all_meshes_have_license(self, loaded_manifest):
        for mesh in loaded_manifest.all_meshes():
            assert mesh.license is not None and mesh.license != ""

    def test_filter_by_single_license(self, loaded_manifest):
        out = find_meshes(license="MIT", manifest=loaded_manifest)
        assert len(out) == loaded_manifest.total_meshes

    def test_filter_by_license_list(self, loaded_manifest):
        out = find_meshes(license=["MIT", "CC0-1.0"], manifest=loaded_manifest)
        assert len(out) == loaded_manifest.total_meshes

    def test_filter_by_nonexistent_license_returns_none(self, loaded_manifest):
        out = find_meshes(license="proprietary", manifest=loaded_manifest)
        assert len(out) == 0

    def test_mirror_eligible_filter(self, loaded_manifest):
        eligible = find_meshes(mirror_eligible=True, manifest=loaded_manifest)
        ineligible = find_meshes(mirror_eligible=False, manifest=loaded_manifest)
        assert len(eligible) + len(ineligible) == loaded_manifest.total_meshes
        # All current meshes are MIT, which is redistributable
        assert len(ineligible) == 0
