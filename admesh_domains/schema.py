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
VALID_ELEMENT_TYPES = {"triangle", "quadrilateral", "Mixed-Element"}
VALID_CATEGORIES = {"real-world", "synthetic"}
VALID_KINDS = {"mesh", "boundary"}
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