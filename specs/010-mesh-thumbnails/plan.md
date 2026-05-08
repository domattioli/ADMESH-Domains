# PLAN: Pre-bake mesh thumbnails (Issue #10)

## Phase 1: Survey Site Integration Points
1. Understand current browse.js `bboxSvg()` function and thumbnail rendering flow
2. Identify where thumbnail PNG URL should be added to mesh JSON (build_site.py)
3. Check site assets structure and directory for thumbnails
4. Review current Thumbnails view button and container

**Outcome:** Know exactly where thumbnails integrate and what changes are needed.

## Phase 2: Create Thumbnail Render Script
1. Create `scripts/render_thumbnails.py` with argparse CLI
2. Implement fort.14 header parser to extract mesh coordinates (reuse bbox parsing)
3. Implement matplotlib-based mesh topology renderer:
   - Draw element edges (lines connecting nodes)
   - Use 240x180 PNG size
   - Apply consistent color scheme (dark/light theme aware)
   - Handle both triangle and quad meshes
4. Batch process all meshes in registry_data/meshes/ with error handling
5. Write to registry_data/thumbnails/{domain}/{mesh_id}.png
6. Add docstring and usage comments

**Outcome:** Standalone script that can render any fort.14 to PNG.

## Phase 3: Update Build Script
1. Modify `scripts/build_site.py` to call render_thumbnails.py (or inline the logic)
2. Add thumbnail URL to mesh JSON output if PNG exists:
   - Check if registry_data/thumbnails/{domain}/{mesh_id}.png exists
   - If yes, add `"thumbnail_url": "https://huggingface.co/datasets/domattioli/ADMESH-Domains/resolve/main/thumbnails/{domain}/{mesh_id}.png"`
   - If no, omit field (browse.js will fallback to SVG)
3. Update manifest.json generation logic

**Outcome:** build_site.py generates thumbnail URLs in manifest.json.

## Phase 4: Update Site JavaScript
1. Modify `site/src/js/browse.js` in `bboxSvg()` function:
   - Accept optional thumbnail_url parameter
   - If thumbnail_url exists, return `<img src=...>` element instead of SVG
   - Fallback to bbox SVG if thumbnail_url missing or image fails to load
2. Update `renderThumbs()` to pass thumbnail_url to bboxSvg()

**Outcome:** Browse Thumbnails view displays PNG when available.

## Phase 5: Generate Initial Thumbnails
1. Run `scripts/render_thumbnails.py registry_data/manifest.toml registry_data/meshes/ registry_data/thumbnails/`
2. Verify all 41 meshes render without error
3. Spot-check a few PNG files for quality (visual inspection)
4. Commit thumbnails to git: `git add registry_data/thumbnails/`

**Outcome:** All 41 meshes have PNG thumbnails in the repo.

## Phase 6: Update Build Configuration
1. Edit MANIFEST.in to exclude registry_data/thumbnails/ from wheel:
   - Add: `exclude registry_data/thumbnails/`
2. Verify wheel build excludes thumbnails:
   - `python -m build && unzip -l dist/admesh_domains-*.whl | grep -i thumbnail` (should be empty)

**Outcome:** Thumbnails NOT bundled in PyPI wheel (Principle II).

## Phase 7: CI Integration (Optional for This Session)
1. Add GitHub Actions workflow step to regenerate thumbnails when manifest.toml changes
   - Trigger: on PR that modifies registry_data/manifest.toml
   - Job: run render_thumbnails.py and commit/push results
   - **Note:** This can be deferred if workflow permissions are complex

**Outcome:** Thumbnails auto-regenerated when manifest changes.

## Phase 8: Testing & Validation
1. Run site build locally: `python scripts/build_site.py`
2. Verify manifest.json contains thumbnail_url fields
3. Test browse view in browser (if dev server available) or inspect HTML
4. Verify fallback to SVG when thumbnail_url missing (test with one mesh)
5. Validate file sizes: each PNG should be ~20-50 KB

**Outcome:** Site renders thumbnails correctly, fallbacks work.

## Phase 9: Documentation & Closure
1. Update README.md or docs with thumbnail generation instructions
2. Add docstring to render_thumbnails.py with examples
3. Update CLAUDE.md if workflow changed
4. Commit everything: `git add .`

**Outcome:** Documented, complete feature ready for merge.

## Dependencies
- Phase 1 (survey) → Phase 2-4 (implementation can run in parallel)
- Phase 2 (render script) → Phase 3 (build integration) → Phase 5 (generate)
- Phase 5 (generated files) → Phase 6, 8 (validation)
- Phase 8 (testing) → Phase 9 (docs/closure)

## Estimated Timeline
- Phase 1: 15 min (survey)
- Phase 2: 45 min (render script + matplotlib integration)
- Phase 3: 20 min (build script updates)
- Phase 4: 15 min (browse.js updates)
- Phase 5: 30 min (generate + verify 41 meshes)
- Phase 6: 10 min (MANIFEST.in + wheel validation)
- Phase 7: ~30 min (CI job) — optional, defer if time-constrained
- Phase 8: 20 min (testing)
- Phase 9: 15 min (docs)
**Total: ~3.5-4 hours (with Phase 7) or ~3 hours (without Phase 7)**
