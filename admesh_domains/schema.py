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


SCHEMA_VERSION = "0.2"

VALID_TYPES = {"ADCIRC", "SMS_2DM"}
VALID_CATEGORIES = {"real-world", "synthetic"}


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
    created_date: Optional[str] = None
    refinement_level: Optional[str] = None
    features: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)

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

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("_base_dir", None)
        d.pop("_domain_name", None)
        return {k: v for k, v in d.items() if v is not None and v != []}

    @classmethod
    def from_dict(
        cls,
        data: dict,
        domain_name: Optional[str] = None,
        base_dir: Optional[Path] = None,
    ) -> "Mesh":
        known = {f.name for f in cls.__dataclass_fields__.values() if not f.name.startswith("_")}
        kwargs = {k: v for k, v in data.items() if k in known}
        instance = cls(**kwargs)
        instance._domain_name = domain_name
        instance._base_dir = base_dir
        return instance


@dataclass
class Domain:
    """A geographic region or logical group containing one or more meshes."""

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
        if "/" in self.name:
            raise SchemaError(f"Domain.name must not contain '/' (reserved): {self.name!r}")
        if self.category not in VALID_CATEGORIES:
            raise SchemaError(
                f"Domain.category must be one of {sorted(VALID_CATEGORIES)}, "
                f"got {self.category!r}"
            )
        if self.bounding_box is not None:
            self.bounding_box.validate()
        if not self.meshes:
            raise SchemaError(f"Domain {self.name!r} must have at least one mesh")
        seen_ids: set[str] = set()
        for m in self.meshes:
            m.validate()
            if m.id in seen_ids:
                raise SchemaError(
                    f"Domain {self.name!r}: duplicate mesh id {m.id!r}"
                )
            seen_ids.add(m.id)

    def find_mesh(
        self,
        id: Optional[str] = None,
        contributor: Optional[str] = None,
        min_node_count: Optional[int] = None,
        max_size_mb: Optional[float] = None,
    ) -> list[Mesh]:
        """Return meshes within this domain matching all given filters."""
        out = []
        for m in self.meshes:
            if id is not None and m.id != id and id not in (m.aliases or []):
                continue
            if contributor is not None and m.contributor != contributor:
                continue
            if min_node_count is not None:
                if m.node_count is None or m.node_count < min_node_count:
                    continue
            if max_size_mb is not None and m.size_mb > max_size_mb:
                continue
            out.append(m)
        return out

    def get_mesh(self, id: str) -> Mesh:
        """Return a single mesh by id (or alias). Raises KeyError if not found."""
        for m in self.meshes:
            if m.id == id or id in (m.aliases or []):
                return m
        raise KeyError(f"Domain {self.name!r} has no mesh with id {id!r}")

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "full_name": self.full_name,
            "description": self.description,
            "category": self.category,
            "region": self.region,
            "applications": self.applications,
        }
        if self.bounding_box is not None:
            d["bounding_box"] = self.bounding_box.to_dict()
        d["meshes"] = [m.to_dict() for m in self.meshes]
        return {k: v for k, v in d.items() if v is not None and v != []}

    @classmethod
    def from_dict(cls, data: dict, base_dir: Optional[Path] = None) -> "Domain":
        bbox_raw = data.get("bounding_box")
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
