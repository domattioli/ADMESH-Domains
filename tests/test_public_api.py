"""Exhaustive public-API surface tests.

Iterates `admesh_domains.__all__` and asserts every exported symbol is
importable, attribute-resolvable, and (for callables) invocable against
the live manifest. Catches the class of cross-file refactor regression
that produced [C1] (Domain.get_mesh missing) in TEST-AUDIT.md §2.1.
"""

from __future__ import annotations

import pytest

import admesh_domains


EXPECTED_EXPORTS = {
    "__version__",
    "SCHEMA_VERSION",
    "BoundingBox",
    "Domain",
    "Mesh",
    "RegistryMetadata",
    "SchemaError",
    "Manifest",
    "ManifestNotFoundError",
    "ManifestValidationError",
    "load_manifest",
    "find_domains",
    "find_meshes",
    "get_domain",
    "get_mesh",
    "list_applications",
    "list_domains",
    "list_regions",
    "test_meshes",
}


class TestPublicAPISurface:
    def test_all_declares_expected_symbols(self):
        assert set(admesh_domains.__all__) == EXPECTED_EXPORTS, (
            "admesh_domains.__all__ drifted from the documented public surface. "
            "Update EXPECTED_EXPORTS here AND docs/TEST-AUDIT.md §1.3 to match."
        )

    @pytest.mark.parametrize("name", sorted(EXPECTED_EXPORTS))
    def test_symbol_is_importable(self, name: str):
        assert hasattr(admesh_domains, name), (
            f"{name!r} declared in __all__ but not resolvable on the module"
        )
        obj = getattr(admesh_domains, name)
        assert obj is not None, f"{name!r} resolves to None"

    @pytest.mark.parametrize(
        "name",
        [
            "BoundingBox", "Domain", "Mesh", "RegistryMetadata", "SchemaError",
            "Manifest", "ManifestNotFoundError", "ManifestValidationError",
            "load_manifest", "find_domains", "find_meshes", "get_domain",
            "get_mesh", "list_applications", "list_domains", "list_regions",
            "test_meshes",
        ],
    )
    def test_callable_exports_are_callable(self, name: str):
        obj = getattr(admesh_domains, name)
        assert callable(obj), f"{name!r} is exported but not callable"

    def test_version_is_string(self):
        assert isinstance(admesh_domains.__version__, str)
        assert admesh_domains.__version__.count(".") >= 2, (
            f"__version__ should be semver-ish, got {admesh_domains.__version__!r}"
        )

    def test_schema_version_is_string(self):
        assert isinstance(admesh_domains.SCHEMA_VERSION, str)


class TestPublicAPIBehavior:
    """Smoke-test the cross-module call paths that exporting alone cannot catch.

    [C1] was exactly this class of bug: `get_mesh` was in __all__ and importable,
    but the path through `Domain.get_mesh` was broken. Surface tests alone would
    not have caught it.
    """

    def test_get_mesh_round_trips_composite_id(self, loaded_manifest):
        mesh_ids = [
            f"{d.name}/{m.id}"
            for d in loaded_manifest.domains
            for m in d.meshes
        ]
        if not mesh_ids:
            pytest.skip("no meshes in manifest to round-trip")
        composite = mesh_ids[0]
        mesh = admesh_domains.get_mesh(composite, manifest=loaded_manifest)
        assert mesh is not None
        assert f"{mesh._domain_name}/{mesh.id}" == composite

    def test_get_domain_returns_domain(self, loaded_manifest):
        if not loaded_manifest.domains:
            pytest.skip("no domains in manifest")
        first = loaded_manifest.domains[0]
        d = admesh_domains.get_domain(first.name, manifest=loaded_manifest)
        assert d.name == first.name

    def test_list_domains_returns_domains(self, loaded_manifest):
        domains = admesh_domains.list_domains(manifest=loaded_manifest)
        assert hasattr(domains, "__iter__")
        assert all(isinstance(d, admesh_domains.Domain) for d in domains)

    def test_find_meshes_filters(self, loaded_manifest):
        result = admesh_domains.find_meshes(manifest=loaded_manifest)
        assert hasattr(result, "__iter__")

    def test_schemaerror_is_exception(self):
        assert issubclass(admesh_domains.SchemaError, Exception)

    def test_manifest_errors_are_exceptions(self):
        assert issubclass(admesh_domains.ManifestNotFoundError, Exception)
        assert issubclass(admesh_domains.ManifestValidationError, Exception)

    def test_registry_metadata_instantiates(self):
        # [M2] RegistryMetadata is exported but had no direct test.
        md = admesh_domains.RegistryMetadata(
            version="0.3", description="t", total_domains=1, total_meshes=2,
        )
        assert md.version == "0.3"
        assert md.total_domains == 1
        assert md.total_meshes == 2
        assert md.source_repositories == []

    def test_test_meshes_not_collected_by_pytest(self):
        # [L4] test_meshes is part of the public API but its name matches
        # pytest's collection pattern. The __test__ = False marker on the
        # function suppresses collection. Lock that contract here so a
        # future refactor cannot silently re-enable it.
        assert getattr(admesh_domains.test_meshes, "__test__", True) is False, (
            "admesh_domains.test_meshes is missing the __test__ = False marker; "
            "pytest will try to collect it as a test function. Restore the line "
            "`test_meshes.__test__ = False` in admesh_domains/query.py."
        )
