# Data Model: HuggingFace Publisher

Companion to [spec.md](spec.md) and [plan.md](plan.md). Defines the shape of the data that flows in and out of the publisher.

## Inputs

### Manifest (input)

The validated `Manifest` object from `admesh_domains.load_manifest()`. Already has the full Domain → Meshes hierarchy. Schema version comes from `admesh_domains.SCHEMA_VERSION` (`"0.2"` at time of writing).

### Local files

Mesh files at `registry_data/meshes/<filename>` on the runner's filesystem (path resolved via `Mesh.path`). The publisher reads them only to compute sha256 and to upload — it does not parse or validate the fort.14 contents.

### Prior `manifest.parquet` from HF

If a prior parquet sidecar exists in the HF dataset (`manifest.parquet` at repo root, `revision="main"`), the publisher downloads it into a temp file and reads the `content_sha256` column to populate a dedup map keyed by `hf_path`. On the first publish there is no prior sidecar; the dedup map starts empty and every file is uploaded.

## Outputs

### `manifest.parquet` (Parquet sidecar)

One row per Mesh, flat schema, written to the HF dataset root.

| Column | pyarrow type | Source |
|---|---|---|
| `domain` | `string` | parent `Domain.name` |
| `mesh_id` | `string` | `Mesh.id` |
| `full_id` | `string` | `<domain>/<mesh_id>` |
| `filename` | `string` | `Mesh.filename` |
| `description` | `string` (nullable) | `Mesh.description` |
| `size_mb` | `float64` | `Mesh.size_mb` |
| `type` | `string` | `Mesh.type` |
| `element_type` | `string` (nullable) | `Mesh.element_type` |
| `refinement_level` | `string` (nullable) | `Mesh.refinement_level` |
| `node_count` | `int64` (nullable) | `Mesh.node_count` |
| `aliases` | `list<string>` | `Mesh.aliases` |
| `category` | `string` | parent `Domain.category` |
| `region` | `string` (nullable) | parent `Domain.region` |
| `applications` | `list<string>` | parent `Domain.applications` |
| `content_sha256` | `string` | computed at publish time |
| `hf_path` | `string` | `meshes/<domain>/<filename>` |

**Parquet file metadata** (key/value):

- `admesh_schema_version`: matches `admesh_domains.SCHEMA_VERSION`
- `admesh_publish_tag`: the release tag (e.g. `v0.2.0`)
- `admesh_total_meshes`: stringified row count

### Mesh files in HF

Layout: `meshes/<domain_name>/<original_filename>`. Original filenames preserved (no rename, no extension synthesis). E.g.

```
meshes/WNAT/WNAT_Hagen.14
meshes/WNAT/WNAT_Onur.14
meshes/Rectangles/rectangular_mesh_triangle1.14
meshes/MiscTests/dom.2dm
```

### Dataset card (`README.md`)

Rendered from `admesh_domains/templates/dataset_card.md.j2`. Markdown front-matter plus body. Front-matter keys YAML-validated by HF: `license`, `tags`, `pretty_name`, `size_categories`. Body sections: summary, totals table, domain catalog, quickstart code block, citation/source link.

## Hash derivation

```python
def compute_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
```

Single-pass `read_bytes()` is fine: largest mesh today is ~15 MB. If we ever import meshes >100 MB, switch to a chunked `update()` loop. Not premature now.

## Sidecar lifecycle

```
                     ┌────────────────────────┐
   tag pushed ──────►│ load_manifest()        │
                     │ validate, all-files-ok │
                     └────────────┬───────────┘
                                  ▼
                     ┌────────────────────────┐
                     │ fetch_prior_hashes()   │
                     │ (download manifest.    │
                     │  parquet from HF main) │
                     └────────────┬───────────┘
                                  ▼
                     ┌────────────────────────┐
                     │ for each Mesh:         │
                     │   compute_sha256()     │
                     │   if hash == prior:    │
                     │     skip upload        │
                     │   else:                │
                     │     queue upload       │
                     └────────────┬───────────┘
                                  ▼
                     ┌────────────────────────┐
                     │ build_parquet_sidecar()│
                     │ render_dataset_card()  │
                     └────────────┬───────────┘
                                  ▼
                     ┌────────────────────────┐
                     │ create_commit(         │
                     │   ops = uploads        │
                     │        + parquet write │
                     │        + readme write, │
                     │   revision = main)     │
                     │ create_tag(v.X.Y.Z)    │
                     └────────────────────────┘
```

## Cross-platform cache (T-002)

`huggingface_hub.constants.HF_HUB_CACHE` resolves at import time to:

| OS | Path |
|---|---|
| Linux | `~/.cache/huggingface/hub` (XDG-compliant) |
| macOS | `~/Library/Caches/huggingface/hub` |
| Windows | `%LOCALAPPDATA%\huggingface\hub` |

Users can override by setting `HF_HOME` or `HF_HUB_CACHE` env vars. `Mesh.load()` honors these automatically by delegating to `hf_hub_download`.
