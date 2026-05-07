# Data Model: Compare Mesh UI

## Source: manifest.json (derived from manifest.toml)

All data is read-only from the client-side manifest.json. No writes.

## Entities

### Domain (from manifest)
- `name` (str): machine-readable ID, used as dropdown value
- `full_name` (str): human-readable label for dropdown
- `meshes` (list[Mesh]): all meshes in this domain

### Mesh (from manifest)
- `id` (str): mesh identifier
- `filename` (str): used for keyword-based strategy inference
- `element_type` (str | absent): "triangle" | "quadrilateral" | "mixed"
- `element_count` (int | absent): number of mesh elements
- `node_count` (int | absent): number of mesh nodes
- `size_mb` (float): file size in MB
- `contributor` (str): who uploaded this mesh
- `bounding_box` (BoundingBox | absent): geographic extent

### BoundingBox
- `min_lon`, `max_lon`, `min_lat`, `max_lat` (float)

### MeshVariant (client-side computed)
Represents one strategy group for a domain:
- `strategy`: "triangle" | "quad" | "mixed"
- `label`: "Triangle" | "Quad-Dominant" | "Mixed"
- `mesh`: the first Mesh matching this strategy in the domain
- `elementCount`: mesh.element_count or null
- `nodeCount`: mesh.node_count or null
- `sizeMb`: mesh.size_mb
- `contributor`: mesh.contributor
- `bboxSvg`: rendered SVG string from bounding_box

## Strategy Inference Rules

```
strategy = inferStrategy(mesh)
  if mesh.element_type == "triangle" → "triangle"
  if mesh.element_type == "quadrilateral" → "quad"
  if mesh.element_type == "mixed" → "mixed"
  if mesh.filename contains "quad" → "quad"
  if mesh.filename contains "tri" → "triangle"
  if mesh.filename contains "mixed" → "mixed"
  else → null (skip for comparison)
```

## Recommendation Logic

```
recommend(variants):
  withCounts = variants.filter(v => v.elementCount != null && v.elementCount > 0)
  if withCounts.length > 0:
    best = min(withCounts, key=elementCount)
    return "⭐ {best.label} has fewest elements ({best.elementCount}) — best for efficiency"
  withSize = variants.filter(v => v.sizeMb > 0)
  if withSize.length > 1:
    best = min(withSize, key=sizeMb)
    return "⭐ {best.label} is the smallest file ({best.sizeMb} MB)"
  return null (no banner)
```
