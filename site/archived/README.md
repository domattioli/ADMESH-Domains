# Archived Site Pages

Directory contains retired website pages from spec 010 (Site MVP Redesign).

All `.html.bak` files = **preserved versions** of pages removed from main navigation for MVP focus. Restore by:

1. Copying `.html.bak` file back to `site/src/` (without `.bak` extension)
2. Re-adding page link to `site/src/js/nav.js` in PAGES array

## Archived Pages

| Page | File | Reason |
|------|------|--------|
| Statistics | statistics.html.bak | Stats moved to Home; full dashboard deferred to v1.0 |
| Create | create.html.bak | Out of scope for registry MVP (not mesh generator) |
| Test Suites | tests.html.bak | Redundant with Browse tab; moved to Python API |
| Feedback | feedback.html.bak | GitHub link in footer is sufficient |

## Restoration Guide

To restore page, e.g. `statistics.html.bak`:

```bash
# Copy back to src/
cp site/archived/statistics.html.bak site/src/statistics.html

# Update nav.js to re-add link
# In site/src/js/nav.js, add to PAGES array:
# ["statistics.html", "Statistics"],
```

See `specs/010-site-mvp-redesign/RETIRED.md` for detailed restoration notes per page.
