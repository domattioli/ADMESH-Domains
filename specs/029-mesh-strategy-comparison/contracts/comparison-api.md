# Comparison API Contract (Phase 1)

## Endpoint: GET /api/domains/{domain_id}/mesh-variants

**Purpose**: Fetch all available mesh variants for a given domain.

## Notes

- Not all domains have all 3 variants. Endpoint returns available variants only.
- If domain has <2 variants, frontend displays what's available + note "Other variants not available in registry"
- Metrics are read directly from manifest.toml (no new computation required)
- Node/element counts and size come from mesh metadata
- No quality metrics in Phase 1 (can be added in v0.5 if mesh files parsed for quality data)

## Recommendation Heuristic (Phase 1)

**Simple rule**: Best = lowest element count (favoring efficiency).

```python
def recommend_variant(variants):
    ranked = sorted(variants, key=lambda v: v['element_count'])
    best = ranked[0]
    return f"⭐ {best['strategy'].title()} has the fewest elements ({best['element_count']}) and is best for efficiency."
```

## Implementation (Backend)

### Option A: Extend existing API endpoint
- Add new route to admesh_domains CLI or Flask backend
- Query manifest.toml for domain
- Return all meshes in domain with variant strategy inference

### Option B: Client-side aggregation (recommended for Phase 1)
- Frontend fetches domain list, then for each domain, calls existing endpoint
- Filters meshes by domain
- Groups by strategy (heuristic: filename contains "quad" / "mixed" / "triangle")
- Displays available strategies

**Recommendation**: Start with Option B (no backend changes needed). Implement Option A as cleanup in v0.5.
