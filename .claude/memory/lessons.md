
## 2026-04-26 — Issue #6: Parquet sidecar missing new schema fields

**Lesson**: When additive schema fields are added to `Mesh` (spec 009: `kind`, `test_case`, `uploaded_date`, `modified_date`, `contributor`), the publisher's `_MESH_COLUMNS` dict initializer and `pa.schema([...])` in `build_parquet_sidecar` must be updated in the **same PR**. The TOML is the source of truth (Constitution I), but the Parquet sidecar is what downstream HF consumers actually read — a schema drift between them is silent and hard to detect.

**Fix pattern**: Add new `Mesh` fields to both the `rows` dict keys and the `pa.schema` list in `publisher.py`, plus a round-trip column-presence test in `tests/test_publisher.py`. This is a Code-track change (publisher logic) → bumps PyPI patch version.

**PR**: fix/issue-6-parquet-missing-fields (v0.3.3)
