"""ADMESH Domains: a registry of ADCIRC-compatible mesh domains.

Two-level data model:
    Domain -> Meshes
A Domain is a geographic region or logical group; a Mesh is a specific
realization (one .14 file with its own resolution, contributor, etc.).
"""

from .schema import (
    SCHEMA_VERSION,
    BoundingBox,
    Domain,
    Mesh,
    RegistryMetadata,
    SchemaError,
)
from .manifest import (
    Manifest,
    ManifestNotFoundError,
    ManifestValidationError,
    load_manifest,
)
from .query import (
    find_domains,
    find_meshes,
    get_domain,
    get_mesh,
    list_applications,
    list_domains,
    list_regions,
)

__version__ = "0.3.3"

__all__ = [
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
]
