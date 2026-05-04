# SPEC: Pre-bake mesh thumbnails at build time (Issue #10)

## Goal
Replace bbox-only SVG placeholders with actual mesh geometry PNG thumbnails for the Browse > Thumbnails site view, improving visual discoverability of meshes without requiring edge rendering at browsetime.

## Why
- Users currently see identical SVG boxes for meshes with similar bounding boxes, making them indistinguishable
- Pre-baked PNGs show actual mesh topology (element edges), revealing structure differences (refinement, resolution, coastal features)
- Improves site responsiveness (no client-side mesh rendering)
- Respects Principle II: thumbnails are data assets, not bundled in the wheel

## Acceptance Criteria
- [ ] New script `scripts/render_thumbnails.py` created and functional
- [ ] Script reads fort.14 / .2dm files from registry_data/meshes/
- [ ] Renders 240x180 PNG showing element edges via matplotlib
- [ ] Writes to registry_data/thumbnails/{domain}/{mesh_id}.png
- [ ] All 41 existing meshes have thumbnails post-rollout
- [ ] Site browse view uses PNG when available, falls back to SVG when missing
- [ ] Thumbnails NOT bundled in wheel (MANIFEST.in updated)
- [ ] CI regenerates thumbnails when manifest.toml changes
- [ ] Thumbnail paths can be hosted on HF alongside meshes (lazy-load pattern)

## Deliverables

### Code Changes (small)
1. **scripts/render_thumbnails.py**: Batch render script for all meshes
2. **scripts/build_site.py**: Optional thumbnail inclusion at build time
3. **MANIFEST.in**: Exclude registry_data/thumbnails/ from sdist
4. **site/** (if exists): Reference thumbnail PNG paths in browse view
5. **.github/workflows/**: CI job to regenerate thumbnails on manifest changes

### Data Changes (one-time)
- **registry_data/thumbnails/{domain}/{mesh_id}.png**: Actual PNG files (git-tracked or HF-hosted)

### No Changes Needed
- manifest.toml (no schema changes, thumbnails are derived assets)
- admesh_domains/__init__.py (no version bump — data asset, not code)
- pyproject.toml (matplotlib already in [publish] extra)

## Constraints
- Pure Python rendering (matplotlib.patches for polygons) — no external renderers
- 240x180 aspect ratio (standard thumbnail size)
- matplotlib usage behind [publish] extra (already satisfied)
- Thumbnails NOT in wheel (Principle II)
- Deterministic output (same seed for colors/style across reruns)
- Release track: **Data** (asset-only change) → no PyPI bump, HF publish-data.yml updates registry

## Implementation Strategy
1. **Phase 1:** Survey current site structure and identify thumbnail integration points
2. **Phase 2:** Create render script using matplotlib.patches to draw mesh topology
3. **Phase 3:** Batch-generate all 41 thumbnails and commit to registry_data/thumbnails/
4. **Phase 4:** Update site build script and browse view template to reference PNGs
5. **Phase 5:** Add CI workflow for automatic regeneration
6. **Phase 6:** Document thumbnail generation and update README

## Risks
- **Mesh parsing:** Some fort.14 files may have malformed headers → need robust error handling
- **Matplotlib performance:** Rendering 41+ meshes sequentially may be slow → consider parallelization
- **Git storage:** PNGs in git can bloat repo size (~1-2 MB per thumbnail * 41 = ~41-82 MB) → consider HF-only hosting as fallback
- **Determinism:** matplotlib rendering may vary slightly across versions → pin matplotlib in [publish] extra

## Testing Strategy
- Render a sample mesh and visually inspect PNG
- Verify all 41 meshes render without error
- Confirm fallback to SVG when PNG missing
- Check site build time impact

## Estimate
**Medium:** ~4-5 hours. Straightforward script + batch job, but needs:
- fort.14 parsing (may reuse existing bbox parser)
- matplotlib rendering (new code)
- site integration (depends on existing site structure)
- CI plumbing (GitHub Actions)
