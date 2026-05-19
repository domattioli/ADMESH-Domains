"""Load and parse the TOML manifest of registered domains."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional

from .schema import Domain, Mesh, RegistryMetadata, SchemaError

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError as e:
        raise ImportError(
            "Python 3.11+ required, or install 'tomli' for older versions"
        ) from e


class ManifestNotFoundError(FileNotFoundError):
    """Raised when the manifest file cannot be located."""


class ManifestValidationError(ValueError):
    """Raised when the manifest fails schema validation."""


def _default_manifest_path() -> Path:
    """Return the path to the bundled registry manifest.

    Looks first inside the installed package (admesh_domains/data/manifest.toml),
    then falls back to ../registry_data/manifest.toml for development checkouts.
    """
    pkg_dir = Path(__file__).resolve().parent
    bundled = pkg_dir / "data" / "manifest.toml"
    if bundled.exists():
        return bundled
    return pkg_dir.parent / "registry_data" / "manifest.toml"


@dataclass
class Manifest:
    """In-memory representation of the parsed registry manifest."""

    metadata: RegistryMetadata
    domains: list[Domain] = field(default_factory=list)
    source_path: Optional[Path] = None

    def __len__(self) -> int:
        return len(self.domains)

    def __iter__(self) -> Iterator[Domain]:
        return iter(self.domains)

    def get_domain(self, name: str) -> Optional[Domain]:
        """Find a domain by exact name match (case-insensitive)."""
        for d in self.domains:
            if d.name.lower() == name.lower():
                return d
        return None

    def domain_names(self) -> list[str]:
        return [d.name for d in self.domains]

    def all_meshes(self) -> Iterator[Mesh]:
        """Iterate every mesh across all domains."""
        for d in self.domains:
            for m in d.meshes:
                yield m

    def find_by_uid(self, uid: str) -> Optional[Mesh]:
        """Return the first mesh whose ``content_uid`` matches, or ``None``."""
        for m in self.all_meshes():
            if m.content_uid == uid:
                return m
        return None

    @property
    def total_meshes(self) -> int:
        return sum(len(d.meshes) for d in self.domains)


def load_manifest(path: Optional[str | Path] = None) -> Manifest:
    """Load a registry manifest from a TOML file.

    If `path` is None, the bundled `data/manifest.toml` is used.
    Raises ManifestNotFoundError if the file is missing,
    ManifestValidationError if any entry fails schema validation.
    """
    if path is None:
        manifest_path = _default_manifest_path()
    else:
        manifest_path = Path(path)

    if not manifest_path.exists():
        raise ManifestNotFoundError(f"Manifest not found: {manifest_path}")

    with open(manifest_path, "rb") as f:
        data = tomllib.load(f)

    base_dir = manifest_path.parent

    metadata_raw = data.get("metadata", {})
    metadata = RegistryMetadata(
        version=metadata_raw.get("version", "1.0.0"),
        description=metadata_raw.get("description", ""),
        created=metadata_raw.get("created"),
        source_repositories=metadata_raw.get("source_repositories", []),
        total_domains=metadata_raw.get("total_domains", 0),
        total_meshes=metadata_raw.get("total_meshes", 0),
        total_size_mb=metadata_raw.get("total_size_mb", 0.0),
    )

    raw_domains = data.get("domains", [])
    if not isinstance(raw_domains, list):
        raise ManifestValidationError(
            f"[domains] section must be an array of tables, "
            f"got {type(raw_domains).__name__}"
        )

    domains: list[Domain] = []
    seen_names: set[str] = set()
    for i, entry in enumerate(raw_domains):
        try:
            domain = Domain.from_dict(entry, base_dir=base_dir)
            domain.validate()
        except (TypeError, KeyError, SchemaError) as e:
            raise ManifestValidationError(
                f"Invalid domain entry at index {i} "
                f"(name={entry.get('name', '<missing>')!r}): {e}"
            ) from e
        if domain.name in seen_names:
            raise ManifestValidationError(
                f"Duplicate domain name {domain.name!r}"
            )
        seen_names.add(domain.name)
        domains.append(domain)

    return Manifest(metadata=metadata, domains=domains, source_path=manifest_path)
