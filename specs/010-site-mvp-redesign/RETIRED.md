# Retired Features — Site MVP Redesign (Spec 010)

This document tracks features temporarily disabled in spec 010 for MVP focus. All code is preserved in `site/archived/` for future restoration.

## Retirement Timeline

**Retired in**: v0.3.4 (April 2026)
**Reason**: Streamline to core browse + upload functionality before expanding comparison logic
**Restoration**: When comparison feature is fully designed and domain comparison semantics are clear

## Retired Pages

### 1. Statistics (site/archived/statistics.html.bak)

**What it did**: Displayed registry-wide statistics (top contributors, domain distribution, mesh sizes)

**Why retired**: Statistics are now on the Home page. Full analytics deferred to v1.0+ dashboard.

**Restoration notes**:
- Requires `site/src/js/statistics.js` helper (preserved)
- Restore link in `site/src/js/nav.js` PAGES array
- Update navigation to re-link it

### 2. Create (site/archived/create.html.bak)

**What it did**: Interactive mesh creation form (deprecated; users should use ADmesh or external mesh tools)

**Why retired**: Out of scope for registry MVP. Registry is *curator* of existing meshes, not generator.

**Restoration notes**:
- Depends on `site/src/js/create.js` (preserved)
- If restored, clarify: is this for testing? documentation? educational?
- Consider moving to separate "Tools" section rather than main nav

### 3. Test Suites (site/archived/tests.html.bak)

**What it did**: Listed all test_case=True meshes; linked to test fixtures for downstream libraries

**Why retired**: Redundant with Browse tab (can filter by test_case). Full test discovery moved to Python API (`test_meshes()` helper, issue #11).

**Restoration notes**:
- Restore if we want a dedicated page for test fixtures
- Depends on `site/src/js/tests.js`
- Python API (admesh_domains.test_meshes) is now the canonical interface

### 4. Feedback (site/archived/feedback.html.bak)

**What it did**: Simple form linking to GitHub issues (outdated copy-paste workflow)

**Why retired**: Users should file issues directly on GitHub. Link in footer is sufficient.

**Restoration notes**:
- Consider replacing with embedded GitHub issue widget (future)
- Or just keep footer link (current approach is cleaner)

## Code Preservation

All JavaScript helpers remain in `site/src/js/`:
- `statistics.js` — helper functions for stat calculations
- `create.js` — form validation and mesh preview (educational, could be moved to docs)
- `tests.js` — test mesh filtering and listing
- `feedback.js` — (minimal; mostly form submission)

If you need to restore a page, copy it back from `site/archived/` and add the link to `nav.js` PAGES array.

## Breaking Changes

- Navigation bar no longer shows Statistics, Create, Test Suites, Feedback
- Direct links to those pages (e.g., `/statistics.html`) will 404 in production
  - Users can still access archived copies if you restore them
  - Consider 404 page redirect to "see Browse tab" or GitHub issues

## Future Roadmap

- **v0.4**: Comparison feature fully designed (domain topology, element types, etc.)
- **v0.5**: Restore "Test Suites" page as dedicated test fixture discovery (if needed)
- **v1.0**: Full dashboard with analytics, contribution tracking, mesh quality scorecards
