# Data Model for Mesh Comparison (Phase 1)

## Overview

Mesh comparison reuses existing registry data structures. No new database tables or schema changes needed for MVP.

## Existing Data Structures

### Domain
From `admesh_domains.schema.Domain`:
- `name` (str): machine-readable domain ID (e.g., "Gibraltar")
- `full_name` (str): human-readable name (e.g., "Strait of Gibraltar")
- `category` (str): "real-world" or "synthetic"
- `region` (str): geographic region
- `applications` (list[str]): use cases
- `meshes` (list[Mesh]): all meshes in this domain

### Mesh
From `admesh_domains.schema.Mesh`:
- `id` (str): mesh identifier within domain (e.g., "default@v1")
- `filename` (str): mesh file name
- `node_count` (int): number of nodes in mesh
- `element_count` (int): number of elements in mesh
- `element_type` (str): "triangle", "quadrilateral", "mixed"
- `size_mb` (float): mesh file size in MB
- `description` (str): human-readable description
- `contributor` (str): who contributed this mesh
- `bounding_box` (BoundingBox): geographic extent
- `uploaded_date` (str): ISO date
- `license` (str): license for mesh data

## Comparison-Specific Mapping

**Strategy Inference**: Group meshes by element_type (or filename convention):
- `strategy = "triangle"` → element_type == "triangle" OR filename contains "triangle"
- `strategy = "quad-dominant"` → element_type == "quadrilateral" OR filename contains "quad"
- `strategy = "mixed"` → element_type == "mixed" OR filename contains "mixed"

## Metrics Displayed (MVP)

For each variant:
- **Element Count**: `mesh.element_count` (discrete elements)
- **Node Count**: `mesh.node_count` (vertices)
- **File Size**: `mesh.size_mb` (storage footprint)
- **Element Type**: `mesh.element_type` (triangle/quad/mixed)

**Not included in Phase 1**:
- Quality metrics (min/max/avg element quality, aspect ratios) — requires parsing mesh files
- Computational cost / runtime — requires profiling/benchmarking
- Memory footprint — requires profiling

## Recommendation Heuristic

**Phase 1 Rule**: Best = lowest element_count (fewest elements = simpler mesh = easier to compute on)

**Justification**: Element count is the primary driver of mesh quality/computation cost. Users can inspect individual metrics to refine decisions.

**Phase 2+ Rule** (future): 
- Could add quality-aware heuristics: `score = element_count - bonus_if_high_quality`
- Could add element-type heuristics: "quad-dominant is best for regular regions"

## No Database Changes Required

✓ All data comes from existing manifest.toml
✓ No new schema fields needed for Phase 1
✓ No migration required
✓ Read-only access (no writes to registry)
