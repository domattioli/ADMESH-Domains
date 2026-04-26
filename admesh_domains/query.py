"""Query API for finding Domains and Meshes in the registry."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from .manifest import Manifest, load_manifest
from .schema import Domain, Mesh


_cached_manifest: Optional[Manifest] = None


def _get_manifest(manifest: Union[str, Path, Manifest, None]) -> Manifest:
    """Resolve a manifest argument to a loaded Manifest instance."""
    global _cached_manifest

    if isinstance(manifest, Manifest):
        return manifest

    if manifest is None:
        if _cached_manifest is None:
            _cached_manifest = load_manifest()
        return _cached_manifest

    return load_manifest(manifest)


def find_domains(
    *,
    name: Optional[str] = None,
    category: Optional[str] = None,
    region: Optional[str] = None,
    application: Optional[str] = None,
    manifest: Union[str, Path, Manifest, None] = None,
) -> list[Domain]:
    """Search for Domains matching all given filters.

    Args:
        name: Exact domain name (case-insensitive).
        category: "real-world" or "synthetic".
        region: Geographic region, e.g. "North America".
        application: Use case, e.g. "Coastal Circulation".
        manifest: Optional manifest path / instance; defaults to bundled.
    """
    m = _get_manifest(manifest)
    out: list[Domain] = []
    for d in m.domains:
        if name is not None and d.name.lower() != name.lower():
            continue
        if category is not None and d.category != category:
            continue
        if region is not None:
            if d.region is None or d.region.lower() != region.lower():
                continue
        if application is not None:
            apps = [a.lower() for a in (d.applications or [])]
            if application.lower() not in apps:
                continue
        out.append(d)
    return out


def find_meshes(
    *,
    domain: Optional[str] = None,
    mesh_id: Optional[str] = None,
    contributor: Optional[str] = None,
    type: Optional[str] = None,
    element_type: Optional[str] = None,
    refinement_level: Optional[str] = None,
    min_size_mb: Optional[float] = None,
    max_size_mb: Optional[float] = None,
    min_node_count: Optional[int] = None,
    manifest: Union[str, Path, Manifest, None] = None,
) -> list[Mesh]:
    """Search for individual Meshes across all (or one) Domain(s).

    Args:
        domain: Restrict to one Domain by name (case-insensitive).
        mesh_id: Match a Mesh.id within the chosen domain(s) (or alias).
        contributor: Filter by contributor name.
        type: Mesh format ("ADCIRC" or "SMS_2DM").
        element_type: e.g. "triangle", "quadrilateral".
        refinement_level: e.g. "high", "medium".
        min_size_mb / max_size_mb: inclusive bounds on file size.
        min_node_count: minimum mesh node count (skips meshes without one).
    """
    m = _get_manifest(manifest)
    out: list[Mesh] = []
    for d in m.domains:
        if domain is not None and d.name.lower() != domain.lower():
            continue
        for mesh in d.meshes:
            if mesh_id is not None:
                if mesh.id != mesh_id and mesh_id not in (mesh.aliases or []):
                    continue
            if contributor is not None and mesh.contributor != contributor:
                continue
            if type is not None and mesh.type != type:
                continue
            if element_type is not None and mesh.element_type != element_type:
                continue
            if refinement_level is not None and mesh.refinement_level != refinement_level:
                continue
            if min_size_mb is not None and mesh.size_mb < min_size_mb:
                continue
            if max_size_mb is not None and mesh.size_mb > max_size_mb:
                continue
            if min_node_count is not None:
                if mesh.node_count is None or mesh.node_count < min_node_count:
                    continue
            out.append(mesh)
    return out


def get_domain(name: str, manifest: Union[str, Path, Manifest, None] = None) -> Domain:
    """Look up a single Domain by name (case-insensitive). Raises KeyError."""
    d = _get_manifest(manifest).get_domain(name)
    if d is None:
        raise KeyError(f"No domain named {name!r} in manifest")
    return d


def get_mesh(full_id: str, manifest: Union[str, Path, Manifest, None] = None) -> Mesh:
    """Look up a single Mesh by composite id, e.g. 'WNAT/hagen@v1'.

    Also accepts:
      - just a mesh id ('hagen@v1') if it's unique across all domains
      - a filename or alias for backward-compat lookups

    Raises KeyError if not found, ValueError if ambiguous.
    """
    m = _get_manifest(manifest)

    if "/" in full_id:
        domain_name, mesh_id = full_id.split("/", 1)
        d = m.get_domain(domain_name)
        if d is None:
            raise KeyError(f"No domain named {domain_name!r}")
        return d.get_mesh(mesh_id)

    matches: list[Mesh] = []
    for mesh in m.all_meshes():
        if (
            mesh.id == full_id
            or full_id in (mesh.aliases or [])
            or mesh.filename == full_id
        ):
            matches.append(mesh)
    if not matches:
        raise KeyError(f"No mesh found matching {full_id!r}")
    if len(matches) > 1:
        ambiguous = ", ".join(m.full_id for m in matches)
        raise ValueError(
            f"Ambiguous mesh id {full_id!r}; matches: {ambiguous}"
        )
    return matches[0]


def list_domains(manifest: Union[str, Path, Manifest, None] = None) -> list[Domain]:
    """Return every Domain in the registry."""
    return list(_get_manifest(manifest).domains)


def list_regions(manifest: Union[str, Path, Manifest, None] = None) -> list[str]:
    """Return sorted unique regions across all domains."""
    m = _get_manifest(manifest)
    return sorted({d.region for d in m.domains if d.region})


def list_applications(manifest: Union[str, Path, Manifest, None] = None) -> list[str]:
    """Return sorted unique applications across all domains."""
    m = _get_manifest(manifest)
    apps: set[str] = set()
    for d in m.domains:
        apps.update(d.applications or [])
    return sorted(apps)
