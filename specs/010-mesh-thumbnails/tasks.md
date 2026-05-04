# TASKS: Pre-bake mesh thumbnails (Issue #10)

## Phase 1: Survey & Understand
- **T1.1** Review site/src/js/browse.js: understand bboxSvg() and renderThumbs()
- **T1.2** Check scripts/build_site.py: identify where mesh JSON is constructed
- **T1.3** List registry_data/meshes/ directory: count mesh files and formats
- **T1.4** Verify site/src/js/ can handle img elements (no CSP restrictions)

## Phase 2: Render Script Implementation
- **T2.1** Create scripts/render_thumbnails.py with argparse CLI
- **T2.2** Implement fort.14 header parser (reuse from geometry.py if available)
- **T2.3** Implement mesh coordinates extraction: parse nodes and element definitions
- **T2.4** Create matplotlib-based renderer:
  - Draw element edges (lines connecting node coordinates)
  - Use 240x180 PNG size with consistent margins
  - Color scheme: dark gray elements on light background
  - Handle both ADCIRC and SMS_2DM formats gracefully
- **T2.5** Add batch processing loop: iterate over all meshes
- **T2.6** Add error handling: skip malformed meshes, log warnings
- **T2.7** Test manually: `python scripts/render_thumbnails.py --mesh <path> --output <path>`
- **T2.8** Verify output PNGs are valid (not corrupted)

## Phase 3: Update Build Script
- **T3.1** Read scripts/build_site.py: locate build_manifest_json() function
- **T3.2** Add thumbnail_url generation logic:
  - Check if registry_data/thumbnails/{domain}/{mesh_id}.png exists
  - If yes, construct HF URL: https://huggingface.co/datasets/domattioli/ADMESH-Domains/resolve/main/thumbnails/{domain}/{mesh_id}.png
  - Add to mesh dict as "thumbnail_url"
- **T3.3** Verify manifest.json now includes thumbnail_url fields

## Phase 4: Update Site JavaScript
- **T4.1** Edit site/src/js/browse.js: modify bboxSvg() function signature to accept thumbnail_url
- **T4.2** Update bboxSvg() logic:
  - If thumbnail_url exists, return `<img src="{url}" alt="{id}" class="thumb-img" />`
  - Add onerror handler to fallback to SVG if image fails
  - Otherwise return bbox SVG as before
- **T4.3** Update renderThumbs() to pass m.thumbnail_url (if it exists) to bboxSvg()
- **T4.4** Test in browser (if dev server available) or inspect generated HTML

## Phase 5: Generate Thumbnails
- **T5.1** Create directory: mkdir -p registry_data/thumbnails/
- **T5.2** Run render_thumbnails.py:
  - `python scripts/render_thumbnails.py registry_data/manifest.toml registry_data/meshes/ registry_data/thumbnails/`
- **T5.3** Verify all 41 meshes produced PNG files (check file count)
- **T5.4** Spot-check 3-5 PNGs visually: open in image viewer, confirm they show mesh topology
- **T5.5** Check file sizes: should be 20-50 KB each
- **T5.6** Commit thumbnails: `git add registry_data/thumbnails/`

## Phase 6: Update Packaging Config
- **T6.1** Edit MANIFEST.in: add line `exclude registry_data/thumbnails/` (or equivalent)
- **T6.2** Test wheel build:
  - `python -m build`
  - `unzip -l dist/admesh_domains-*.whl | grep -i thumbnail` (should return empty)
- **T6.3** Verify wheel doesn't include thumbnails

## Phase 7: CI Integration (Optional, Defer if Time-constrained)
- **T7.1** Create .github/workflows/regenerate-thumbnails.yml
- **T7.2** Trigger on: `paths: ['registry_data/manifest.toml']`
- **T7.3** Job: run render_thumbnails.py, commit+push if changes
- **T7.4** Test workflow by modifying manifest and pushing to test branch

## Phase 8: Validation & Testing
- **T8.1** Run site build: `python scripts/build_site.py`
- **T8.2** Inspect site/dist/manifest.json: verify thumbnail_url present for all meshes
- **T8.3** Check that one mesh (temporarily remove its PNG) falls back to SVG
- **T8.4** Run pytest: `pytest tests/ -q` (should all pass)
- **T8.5** Verify site startup works (if dev server available)

## Phase 9: Documentation & Closure
- **T9.1** Update README.md with thumbnail generation instructions
- **T9.2** Add docstring to scripts/render_thumbnails.py with usage examples
- **T9.3** Update CLAUDE.md if any routines changed
- **T9.4** Stage all changes: `git add -A`
- **T9.5** Create final commit: `git commit -m "Resolve issue #10: Pre-bake mesh thumbnails at build time"`

## Execution Order
1. T1.1 → T1.2 → T1.3 → T1.4 (sequential: survey)
2. T2.1 → T2.2 → T2.3 → T2.4 → T2.5 → T2.6 → T2.7 → T2.8 (sequential: script)
3. T3.1 → T3.2 → T3.3 (sequential: build script)
4. T4.1 → T4.2 → T4.3 → T4.4 (sequential: site JS)
5. T5.1 → T5.2 → T5.3 → T5.4 → T5.5 → T5.6 (sequential: generate)
6. T6.1 → T6.2 → T6.3 (sequential: packaging)
7. (Optional) T7.1 → T7.2 → T7.3 → T7.4 (CI)
8. T8.1 → T8.2 → T8.3 → T8.4 → T8.5 (validation)
9. T9.1 → T9.2 → T9.3 → T9.4 → T9.5 (closure)

## Success Metrics
- ✓ 41 PNG thumbnails generated in registry_data/thumbnails/
- ✓ manifest.json includes thumbnail_url for each mesh
- ✓ browse.js loads and displays PNG thumbnails
- ✓ Fallback to SVG when thumbnail_url missing or image fails
- ✓ Wheel build does NOT include thumbnails (Principle II)
- ✓ All tests pass
- ✓ Site renders correctly with thumbnails
