# ADMESH-Domains Catalog Schema

## Element Type Support

Meshes in the ADMESH-Domains catalog can specify their element composition via the `element_type` field.

### Supported Element Types

| Type | Meaning | Use Case | Example Constraint |
|------|---------|----------|-------------------|
| `"triangle"` | Pure triangular elements | Generic coastal modeling, flexible geometry | All elements use 3 nodes |
| `"quadrilateral"` | Pure quad elements | Structured/refined regions, channel alignment | All elements use 4 nodes |
| `"mixed"` | Triangles + quads in same mesh | Hybrid refinement (coarse quads + fine triangles) | Both 3-node and 4-node elements in same mesh |

### Field Details

- **Optional**: `element_type` is optional and defaults to `None` for backward compatibility
- **Backward compatible**: Existing meshes without `element_type` can coexist with typed meshes
- **Validation**: Invalid element types (not in the list above) raise a `SchemaError` during catalog validation

### Registration Examples

#### Pure Triangle Mesh
```toml
[[domains.meshes]]
id = "tri@v1"
filename = "triangle_mesh.14"
element_type = "triangle"
```

#### Pure Quad Mesh
```toml
[[domains.meshes]]
id = "quad@v1"
filename = "quad_mesh.14"
element_type = "quadrilateral"
```

#### Mixed-Element Mesh
```toml
[[domains.meshes]]
id = "hybrid@v1"
filename = "hybrid_mesh.14"
element_type = "mixed"
node_count = 10000
element_count = 18000
```

### Detection

When reading fort14 or 2dm files via CHILmesh, the element type is determined by the element type codes in the file:
- Type code `3` → triangle
- Type code `4` → quad
- Mix of both → `"Mixed-Element"`

The `admesh_metadata()` function in CHILmesh returns the detected `element_type`.

### Round-Trip Validation

A mesh can be exported to fort14 and re-imported while preserving the `element_type` designation:

```python
from admesh_domains import load_manifest, Mesh

# Load catalog
m = load_manifest()
domain = m.get_domain("MyDomain")
mesh = domain.get_mesh("hybrid@v1")

# Access element type
if mesh.element_type == "mixed":
    print(f"Hybrid mesh: {mesh.node_count} nodes, {mesh.element_count} elements")

# Round-trip (external system like CHILmesh)
# mesh.element_type is preserved on serialization
```

## See Also

- `registry_data/manifest.toml` — the authoritative catalog
- `admesh_domains/schema.py` — `Mesh` dataclass and validation rules
- GitHub issue #41 — specification for mixed-element support
