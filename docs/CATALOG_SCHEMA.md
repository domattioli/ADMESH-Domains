# Catalog Schema Reference

Reference for fields in the ADMESH-Domains registry (`manifest.toml`). Schema version: **0.3**.

---

## Mesh Fields

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `id` | string | yes | — | Composite ID, e.g. `hagen@v1` |
| `filename` | string | yes | — | Bare filename, e.g. `WNAT_Hagen_v1.14` |
| `type` | string | yes | `"ADCIRC"` | File format: `ADCIRC`, `SMS_2DM`, `ADCIRC_GRD` |
| `size_mb` | float | yes | `0.0` | File size in MB |
| `node_count` | int | no | `null` | Total node count from file header |
| `element_count` | int | no | `null` | Total element count from file header |
| `element_type` | string | no | `null` | Element geometry — see below |
| `license` | string | yes | `"unknown"` | SPDX identifier or `"unknown"` |
| `contributor` | string | no | `null` | Full name, e.g. `"J. Smith"` |
| `description` | string | no | `null` | Free-text description |
| `uploaded_date` | string | no | `null` | ISO 8601 date added to registry |
| `modified_date` | string | no | `null` | ISO 8601 date file was last changed |
| `refinement_level` | string | no | `null` | Coarse / medium / fine / very_fine |
| `features` | list[str] | no | `[]` | Feature tags, e.g. `["barrier_islands"]` |
| `aliases` | list[str] | no | `[]` | Alternate names for search |
| `bounding_box` | table | no | `null` | `{min_lon, min_lat, max_lon, max_lat}` |
| `kind` | string | no | `"mesh"` | `"mesh"` or `"boundary"` |
| `test_case` | bool | no | `false` | Surface on Test Suites tab |

---

## Element Type

`element_type` encodes the geometry of mesh elements.

### Valid values

| Value | Description |
|---|---|
| `"triangle"` | All elements are 3-node triangles |
| `"quadrilateral"` | All elements are 4-node quadrilaterals |
| `"Mixed-Element"` | Mesh contains both triangles and quadrilaterals |
| `null` (omitted) | Element type unspecified; accepted for backward compatibility |

### Validation rules

- If present, value must exactly match one of the three strings above (case-sensitive).
- `"mixed-element"` and `"Mixed-element"` are **not** valid — use `"Mixed-Element"`.
- `null` / omitted = unspecified; always passes validation.
- Enforced by `Mesh.validate()` → raises `SchemaError` on invalid value.

### Registration example (TOML)

```toml
[[domains.meshes]]
id = "mixed_gulf@v1"
filename = "gulf_mixed.14"
type = "ADCIRC"
size_mb = 12.4
node_count = 85000
element_count = 160000
element_type = "Mixed-Element"
license = "CC-BY-4.0"
contributor = "J. Smith"
```

### How to detect element type

For fort.14 files, element connectivity lines start with an element ID followed by the node count per element:

```
<element_id>  <npe>  <node1>  <node2>  ...
```

- `npe == 3` → triangle
- `npe == 4` → quadrilateral
- Mix of 3 and 4 → `Mixed-Element`

---

## Domain Fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | yes | Unique, no `/` |
| `full_name` | string | no | Human-readable display name |
| `category` | string | no | `"real-world"` or `"synthetic"` |
| `region` | string | no | Geographic region label |
| `description` | string | no | Free-text description |
| `applications` | list[str] | no | Application tags |
| `bounding_box` | table | no | Union bbox over all geographic meshes |

---

## Schema versioning

`SCHEMA_VERSION = "0.3"` — stored in `manifest.toml` header and `admesh_domains/schema.py`.

- Breaking changes (field rename, removal, type change) → bump version.
- Additive changes (new optional field) → no bump.
