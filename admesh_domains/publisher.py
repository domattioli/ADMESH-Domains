"""HuggingFace dataset publisher.

Implements spec 006: takes a validated Manifest, computes per-mesh sha256
hashes, dedups against the prior manifest.parquet on HF, builds a fresh
Parquet sidecar + Jinja-rendered dataset card, and atomically commits
everything to a HuggingFace Dataset.

Public API: see specs/006-huggingface-publisher/contracts/publisher-api.md.
"""

from __future__ import annotations

import hashlib
import io
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .manifest import Manifest
from .schema import Mesh

DEFAULT_HF_REPO = "domattioli/ADMESH-Domains"
DEFAULT_REVISION = "main"
SIDECAR_FILENAME = "manifest.parquet"
README_FILENAME = "README.md"


class PublisherError(Exception):
    """Base class for all publisher-originated failures."""


class PublishTokenError(PublisherError):
    """Raised when the HF token is missing or invalid."""


class PublishValidationError(PublisherError):
    """Raised when the manifest or local files fail validation."""


@dataclass
class PublishResult:
    """Outcome of a publish() call."""

    tag: str
    hf_repo: str
    dry_run: bool
    commit_sha: Optional[str] = None
    uploaded: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    total_meshes: int = 0
    total_size_mb: float = 0.0

    def summary(self) -> str:
        prefix = "[DRY-RUN] " if self.dry_run else ""
        return (
            f"{prefix}Publish {self.tag} to {self.hf_repo}: "
            f"{len(self.uploaded)} uploaded, "
            f"{len(self.skipped)} skipped, "
            f"{len(self.deleted)} deleted "
            f"({self.total_meshes} meshes, {self.total_size_mb:.1f} MB total)"
        )


def compute_sha256(path: Path) -> str:
    """Return lowercase hex sha256 of a file."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hf_path_for(mesh: Mesh) -> str:
    """The HF dataset-relative path where a mesh file is stored."""
    domain = mesh._domain_name or "_unknown"
    return f"meshes/{domain}/{mesh.filename}"


def _resolve_token(token: Optional[str], *, required: bool = True) -> Optional[str]:
    if token:
        return token
    env = os.environ.get("HF_TOKEN")
    if env:
        return env
    if required:
        raise PublishTokenError(
            "No HF token provided. Pass token= or set the HF_TOKEN env var."
        )
    return None


def _validate_local_files(manifest: Manifest) -> None:
    missing = []
    for mesh in manifest.all_meshes():
        if mesh.path is None or not mesh.path.exists():
            missing.append(f"{mesh.full_id} -> {mesh.path}")
    if missing:
        raise PublishValidationError(
            f"{len(missing)} mesh file(s) missing on disk:\n  "
            + "\n  ".join(missing[:10])
            + (f"\n  ... and {len(missing) - 10} more" if len(missing) > 10 else "")
        )


def fetch_prior_hashes(hf_repo: str, token: str) -> dict[str, str]:
    """Read prior content_sha256 values from the previous manifest.parquet on HF.

    Returns {hf_path: sha256}. Empty dict on first publish or fetch failure.
    """
    try:
        from huggingface_hub import hf_hub_download
        from huggingface_hub.errors import EntryNotFoundError, RepositoryNotFoundError
        import pyarrow.parquet as pq
    except ImportError as e:
        raise PublisherError(
            "Missing publisher dependencies. Install with: "
            "pip install admesh-domains[publish]"
        ) from e

    try:
        local_path = hf_hub_download(
            repo_id=hf_repo,
            filename=SIDECAR_FILENAME,
            repo_type="dataset",
            revision=DEFAULT_REVISION,
            token=token,
        )
    except (EntryNotFoundError, RepositoryNotFoundError):
        return {}
    except Exception as e:
        print(f"[warn] Could not fetch prior sidecar ({e!r}); treating as first publish")
        return {}

    table = pq.read_table(local_path, columns=["hf_path", "content_sha256"])
    return dict(zip(table["hf_path"].to_pylist(), table["content_sha256"].to_pylist()))


def build_parquet_sidecar(
    manifest: Manifest,
    hashes: dict[str, str],
    tag: str,
) -> bytes:
    """Build the Parquet sidecar bytes (one row per mesh)."""
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as e:
        raise PublisherError(
            "pyarrow not available. Install with: pip install admesh-domains[publish]"
        ) from e

    rows: dict[str, list] = {k: [] for k in (
        "domain", "mesh_id", "full_id", "filename", "description",
        "size_mb", "type", "element_type", "refinement_level", "node_count",
        "aliases", "category", "region", "applications",
        "bbox_min_lon", "bbox_min_lat", "bbox_max_lon", "bbox_max_lat",
        "content_sha256", "hf_path",
    )}
    for d in manifest.domains:
        for mesh in d.meshes:
            hp = hf_path_for(mesh)
            rows["domain"].append(d.name)
            rows["mesh_id"].append(mesh.id)
            rows["full_id"].append(mesh.full_id)
            rows["filename"].append(mesh.filename)
            rows["description"].append(mesh.description)
            rows["size_mb"].append(float(mesh.size_mb))
            rows["type"].append(mesh.type)
            rows["element_type"].append(mesh.element_type)
            rows["refinement_level"].append(mesh.refinement_level)
            rows["node_count"].append(mesh.node_count)
            rows["aliases"].append(list(mesh.aliases or []))
            rows["category"].append(d.category)
            rows["region"].append(d.region)
            rows["applications"].append(list(d.applications or []))
            bb = mesh.bounding_box
            rows["bbox_min_lon"].append(bb.min_lon if bb else None)
            rows["bbox_min_lat"].append(bb.min_lat if bb else None)
            rows["bbox_max_lon"].append(bb.max_lon if bb else None)
            rows["bbox_max_lat"].append(bb.max_lat if bb else None)
            rows["content_sha256"].append(hashes[hp])
            rows["hf_path"].append(hp)

    schema = pa.schema([
        pa.field("domain", pa.string()),
        pa.field("mesh_id", pa.string()),
        pa.field("full_id", pa.string()),
        pa.field("filename", pa.string()),
        pa.field("description", pa.string()),
        pa.field("size_mb", pa.float64()),
        pa.field("type", pa.string()),
        pa.field("element_type", pa.string()),
        pa.field("refinement_level", pa.string()),
        pa.field("node_count", pa.int64()),
        pa.field("aliases", pa.list_(pa.string())),
        pa.field("category", pa.string()),
        pa.field("region", pa.string()),
        pa.field("applications", pa.list_(pa.string())),
        pa.field("bbox_min_lon", pa.float64()),
        pa.field("bbox_min_lat", pa.float64()),
        pa.field("bbox_max_lon", pa.float64()),
        pa.field("bbox_max_lat", pa.float64()),
        pa.field("content_sha256", pa.string()),
        pa.field("hf_path", pa.string()),
    ], metadata={
        b"admesh_schema_version": b"0.2",
        b"admesh_publish_tag": tag.encode("utf-8"),
        b"admesh_total_meshes": str(len(rows["full_id"])).encode("utf-8"),
    })
    table = pa.Table.from_pydict(rows, schema=schema)
    buf = io.BytesIO()
    pq.write_table(table, buf, compression="snappy")
    return buf.getvalue()


def render_dataset_card(manifest: Manifest, tag: str, hf_repo: str = DEFAULT_HF_REPO) -> str:
    """Render the HF dataset card README from the bundled Jinja template."""
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
    except ImportError as e:
        raise PublisherError(
            "jinja2 not available. Install with: pip install admesh-domains[publish]"
        ) from e

    template_dir = Path(__file__).resolve().parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(disabled_extensions=("md", "j2")),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    template = env.get_template("dataset_card.md.j2")

    real_world = [d for d in manifest.domains if d.category == "real-world"]
    synthetic = [d for d in manifest.domains if d.category == "synthetic"]
    total_size_mb = sum(m.size_mb for m in manifest.all_meshes())

    from .schema import SCHEMA_VERSION
    return template.render(
        tag=tag,
        hf_repo=hf_repo,
        schema_version=SCHEMA_VERSION,
        manifest_version=manifest.metadata.version,
        total_domains=len(manifest.domains),
        total_meshes=manifest.total_meshes,
        total_size_mb=round(total_size_mb, 1),
        real_world=real_world,
        synthetic=synthetic,
    )


def publish(
    manifest: Manifest,
    tag: str,
    *,
    hf_repo: str = DEFAULT_HF_REPO,
    token: Optional[str] = None,
    dry_run: bool = False,
) -> PublishResult:
    """Publish a manifest to HuggingFace Datasets. See contracts doc for details.

    For dry_run=True the token is optional (only needed for write commits).
    For real publishes, the token must be provided or set in HF_TOKEN.
    """
    resolved_token = _resolve_token(token, required=not dry_run)
    _validate_local_files(manifest)

    # Compute current hashes for every mesh (keyed by hf_path).
    current_hashes: dict[str, str] = {}
    current_paths: dict[str, Path] = {}
    for mesh in manifest.all_meshes():
        hp = hf_path_for(mesh)
        current_hashes[hp] = compute_sha256(mesh.path)
        current_paths[hp] = mesh.path

    # Compare against prior sidecar to determine upload/skip/delete sets.
    prior = fetch_prior_hashes(hf_repo, resolved_token)
    uploaded: list[str] = []
    skipped: list[str] = []
    for hp, h in current_hashes.items():
        if prior.get(hp) == h:
            skipped.append(hp)
        else:
            uploaded.append(hp)
    deleted = [hp for hp in prior.keys() if hp not in current_hashes]

    # Build the always-rewritten artifacts.
    parquet_bytes = build_parquet_sidecar(manifest, current_hashes, tag)
    readme_text = render_dataset_card(manifest, tag, hf_repo=hf_repo)

    total_size_mb = sum(m.size_mb for m in manifest.all_meshes())
    result = PublishResult(
        tag=tag,
        hf_repo=hf_repo,
        dry_run=dry_run,
        uploaded=uploaded,
        skipped=skipped,
        deleted=deleted,
        total_meshes=manifest.total_meshes,
        total_size_mb=round(total_size_mb, 1),
    )

    if dry_run:
        return result

    try:
        from huggingface_hub import HfApi, CommitOperationAdd, CommitOperationDelete
    except ImportError as e:
        raise PublisherError(
            "huggingface_hub not available. Install with: pip install admesh-domains[publish]"
        ) from e

    api = HfApi(token=resolved_token)
    operations: list = []
    for hp in uploaded:
        operations.append(CommitOperationAdd(
            path_in_repo=hp,
            path_or_fileobj=str(current_paths[hp]),
        ))
    for hp in deleted:
        operations.append(CommitOperationDelete(path_in_repo=hp))
    operations.append(CommitOperationAdd(
        path_in_repo=SIDECAR_FILENAME,
        path_or_fileobj=parquet_bytes,
    ))
    operations.append(CommitOperationAdd(
        path_in_repo=README_FILENAME,
        path_or_fileobj=readme_text.encode("utf-8"),
    ))

    commit_info = api.create_commit(
        repo_id=hf_repo,
        repo_type="dataset",
        operations=operations,
        commit_message=f"Publish {tag}",
        commit_description=(
            f"admesh-domains release {tag}: "
            f"{len(uploaded)} uploaded, {len(skipped)} skipped, {len(deleted)} deleted"
        ),
        revision=DEFAULT_REVISION,
    )
    result.commit_sha = getattr(commit_info, "oid", None) or str(commit_info)

    # Tag the resulting revision so users can pin to it.
    try:
        api.create_tag(
            repo_id=hf_repo,
            repo_type="dataset",
            tag=tag,
            revision=DEFAULT_REVISION,
            tag_message=f"admesh-domains {tag}",
        )
    except Exception as e:
        # Tag-already-exists is acceptable on idempotent re-publish; surface
        # other failures as a warning rather than failing the whole publish.
        print(f"[warn] create_tag({tag}) failed: {e!r}")

    return result
