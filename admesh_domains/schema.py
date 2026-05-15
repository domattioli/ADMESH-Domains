"""Data models for the ADMESH registry.

Two-level model:
  - Domain: a geographic region or logical group (e.g. "WNAT", "TestCases").
  - Mesh:   a specific realization of a Domain (a particular .14 file with
            its own resolution, contributor, version, etc.).

A Domain has one or more Meshes. Users typically search by Domain
(give me a WNAT mesh) and then pick a Mesh by node count, contributor,
features, etc.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


SCHEMA_VERSION = "0.3"

VALID_TYPES = {"ADCIRC", "SMS_2DM", "ADCIRC_GRD"}
VALID_CATEGORIES = {"real-world", "synthetic"}
VALID_KINDS = {"mesh", "boundary"}
VALID_ELEMENT_TYPES = {"triangle", "quadrilateral", "mixed"}
VALID_LICENSES = {
    "public-domain",
    "CC0-1.0",
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "MIT",
    "proprietary",
    "unknown",
}
REDISTRIBUTABLE_LICENSES = {
    "public-domain", "CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0", "MIT",
}


class SchemaError(ValueError):
    """Raised when an entry fails schema validation."""


@dataclass
class BoundingBox:
    """Geographic bounding box (decimal degrees, antimeridian-safe)."""

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    def validate(self) -> None:
        if self.min_lat > self.max_lat:
            raise SchemaError(
                f"BoundingBox: min_lat ({self.min_lat}) > max_lat ({self.max_lat})"
            )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Mesh:
    """A specific realization of a Domain (one mesh file)."""

    id: str
    filename: str
    description: Optional[str] = None
    size_mb: float = 0.0
    node_count: Optional[int] = None
    element_count: Optional[int] = None
    element_type: Optional[str] = None
    type: str = "ADCIRC"
    contributor: Optional[str] = None
    uploaded_date: Optional[str] = None
    modified_date: Optional[str] = None
    refinement_level: Optional[str] = None
    features: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    bounding_box: Optional[BoundingBox] = None
    license: str = "unknown"
    test_case: bool = False
    kind: str = "mesh"

    _domain_name: Optional[str] = field(default=None, repr=False, compare=False)
    _base_dir: Optional[Path] = field(default=None, repr=False, compare=False)

    def validate(self) -> None:
        if not self.id or not isinstance(self.id, str):
            raise SchemaError(f"Mesh.id must be a non-empty string, got {self.id!r}")
        if not self.filename or not isinstance(self.filename, str):
            raise SchemaError(f"Mesh.filename must be a non-empty string")
        if self.type not in VALID_TYPES:
            raise SchemaError(
                f"Mesh.type must be one of {sorted(VALID_TYPES)}, got {self.type!r}"
            )
        if self.size_mb < 0:
            raise SchemaError(f"Mesh.size_mb must be >= 0, got {self.size_mb}")
        if self.license not in VALID_LICENSES:
            raise SchemaError(
                f"Mesh.license must be one of {sorted(VALID_LICENSES)}, "
                f"got {self.license!r}"
            )
        if self.kind not in VALID_KINDS:
            raise SchemaError(
                f"Mesh.kind must be one of {sorted(VALID_KINDS)}, got {self.kind!r}"
            )
        if self.element_type is not None and self.element_type not in VALID_ELEMENT_TYPES:
            raise SchemaError(
                f"Mesh.element_type must be one of {sorted(VALID_ELEMENT_TYPES)}, "
                f"got {self.element_type!r}"
            )

    @property
    def mirror_eligible(self) -> bool:
        """True iff this mesh's license permits redistribution via the HF mirror."""
        return self.license in REDISTRIBUTABLE_LICENSES

    @property
    def full_id(self) -> str:
        """Composite ID like 'WNAT/Hagen@v1' (domain + mesh id)."""
        if self._domain_name is None:
            return self.id
        return f"{self._domain_name}/{self.id}"

    @property
    def path(self) -> Optional[Path]:
        """Local path to the mesh file, if base_dir is set."""
        if self._base_dir is None:
            return None
        return self._base_dir / "meshes" / self.filename

    def exists(self) -> bool:
        p = self.path
        return p is not None and p.exists()

    def read_text(self) -> str:
        p = self.path
        if p is None:
            raise FileNotFoundError(
                f"No base_dir configured for {self.full_id}; cannot resolve path"
            )
        if not p.exists():
            raise FileNotFoundError(f"Mesh file not found: {p}")
        return p.read_text()

    def load(self, *, hf_repo: Optional[str] = None, token: Optional[str] = None) -> Path:
        """Download this mesh from the HuggingFace mirror and return a local Path.

        Uses ``huggingface_hub.hf_hub_download``, which handles caching, progress
        bars, and resumable downloads. The cache lives at ``HF_HUB_CACHE``
        (typically ``~/.cache/huggingface/hub`` on Linux).

        Requires the ``[hf]`` extra: ``pip install admesh-domains[hf]``.
        """
        try:
            from huggingface_hub import hf_hub_download
        except ImportError as e:
            raise ImportError(
                "Mesh.load() requires huggingface_hub. "
                "Install with: pip install admesh-domains[hf]"
            ) from e
        if hf_repo is None:
            from .publisher import DEFAULT_HF_REPO
            hf_repo = DEFAULT_HF_REPO
        domain = self._domain_name or "_unknown"
        local = hf_hub_download(
            repo_id=hf_repo,
            filename=f"meshes/{domain}/{self.filename}",
            repo_type="dataset",
            token=token,
        )
        return Path(local)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("_base_dir", None)
        d.pop("_domain_name", None)
        defaults = {"kind": "mesh"}
        return {
            k: v for k, v in d.items()
            if v is not None and v != [] and v is not False and defaults.get(k) != v
        }

    @classmethod
    def from_dict(
        cls,
        data: dict,
        domain_name: Optional[str] = None,
        base_dir: Optional[Path] = None,
    ) -> "Mesh":
        known = {f.name for f in cls.__dataclass_fields__.values() if not f.name.startswith("_")}
        kwargs = {k: v for k, v in data.items() if k in known}
        bbox_raw = kwargs.pop("bounding_box", None)
        if bbox_raw is not None and not isinstance(bbox_raw, BoundingBox):
            bbox_raw = BoundingBox(**bbox_raw)
        instance = cls(bounding_box=bbox_raw, **kwargs)
        instance._domain_name = domain_name
        instance._base_dir = base_dir
        return instance


@dataclass
class Domain:
    """A geographic region or logical group with optional mesh realizations.

    A Domain represents the geographic extent and boundary conditions of a
    coastal simulation area. A Domain can exist without Meshes (boundary
    geometry only) or with one or more Meshes (discretized realizations).
    Use `find_domains(has_meshes=True)` to filter for domains with meshes only.
    """

    name: str
    full_name: Optional[str] = None
    description: Optional[str] = None
    category: str = "real-world"
    region: Optional[str] = None
    applications: list[str] = field(default_factory=list)
    bounding_box: Optional[BoundingBox] = None
    meshes: list[Mesh] = field(default_factory=list)

    def validate(self) -> None:
        if not self.name or not isinstance(self.name, str):
            raise SchemaError(f"Domain.name must be a non-empty string, got {self.name!r}")
        if self.category not in VALID_CATEGORIES:
            raise SchemaError(
                f"Domain.category must be one of {sorted(VALID_CATEGORIES)}, "
                f"got {self.category!r}"
            )
        if self.bounding_box is not None:
            self.bounding_box.validate()
        for mesh in self.meshes:
            mesh.validate()

    @property
    def has_meshes(self) -> bool:
        return len(self.meshes) > 0

    def get_mesh(self, mesh_id: str) -> "Mesh":
        for mesh in self.meshes:
            if mesh.id == mesh_id:
                return mesh
        raise KeyError(f"No mesh with id {mesh_id!r} in domain {self.name!r}")

    def to_dict(self) -> dict:
        d = asdict(self)
        defaults = {"category": "real-world"}
        d["meshes"] = [m.to_dict() for m in self.meshes]
        if self.bounding_box:
            d["bounding_box"] = self.bounding_box.to_dict()
        return {
            k: v for k, v in d.items()
            if v is not None and v != [] and v is not False and defaults.get(k) != v
        }

    @classmethod
    def from_dict(
        cls,
        data: dict,
        base_dir: Optional[Path] = None,
    ) -> "Domain":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in data.items() if k in known}
        bbox_raw = kwargs.pop("bounding_box", None)
        bbox = BoundingBox(**bbox_raw) if bbox_raw else None
        meshes_raw = data.get("meshes", [])
        domain_name = data["name"]
        meshes = [
            Mesh.from_dict(m, domain_name=domain_name, base_dir=base_dir)
            for m in meshes_raw
        ]
        return cls(
            name=domain_name,
            full_name=data.get("full_name"),
            description=data.get("description"),
            category=data.get("category", "real-world"),
            region=data.get("region"),
            applications=data.get("applications", []),
            bounding_box=bbox,
            meshes=meshes,
        )


@dataclass
class RegistryMetadata:
    """Top-level [metadata] section of the manifest."""

    version: str = SCHEMA_VERSION
    description: str = ""
    created: Optional[str] = None
    source_repositories: list[str] = field(default_factory=list)
    total_domains: int = 0
    total_meshes: int = 0
    total_size_mb: float = 0.0
