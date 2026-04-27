# Archived Site Pages

This directory contains retired website pages from spec 010 (Site MVP Redesign).

All `.html.bak` files are **preserved versions** of pages removed from the main navigation for MVP focus. They can be restored by:

1. Copying the `.html.bak` file back to `site/src/` (without the `.bak` extension)
2. Re-adding the page link to `site/src/js/nav.js` in the PAGES array

## Archived Pages

| Page | File | Reason |
|------|------|--------|
| Statistics | statistics.html.bak | Stats moved to Home; full dashboard deferred to v1.0 |
| Create | create.html.bak | Out of scope for registry MVP (not a mesh generator) |
| Test Suites | tests.html.bak | Redundant with Browse tab; moved to Python API |
| Feedback | feedback.html.bak | GitHub link in footer is sufficient |

## Restoration Guide

To restore a page, e.g., `statistics.html.bak`:

```bash
# Copy back to src/
cp site/archived/statistics.html.bak site/src/statistics.html

# Update nav.js to re-add the link
# In site/src/js/nav.js, add to PAGES array:
# ["statistics.html", "Statistics"],
```

See `specs/010-site-mvp-redesign/RETIRED.md` for detailed restoration notes for each page.
