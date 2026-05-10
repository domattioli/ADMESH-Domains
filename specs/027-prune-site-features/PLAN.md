# PLAN — Spec 027 Site Prune

## Phases

### Phase 1: Remove orphan HTML pages
Delete the 5 orphan HTML files in `site/src/`. They have `.bak` siblings preserved in `site/archived/` per spec 010's RETIRED.md.

### Phase 2: Remove orphan JS modules
Delete the 5 corresponding JS files in `site/src/js/`. None of them are imported by the surviving pages (verified: `grep -rE "create.js|feedback.js|preview.js|statistics.js|tests.js" site/src/`).

### Phase 3: Patch surviving references
- `site/src/404.html` — drop the `preview.html` recovery link.
- `site/src/js/nav.js` — replace `<a href="feedback.html">Feedback</a>` in the footer with `<a href="https://github.com/domattioli/ADMESH-Domains/issues">Feedback</a>` so user-facing entry to feedback is preserved without shipping a dead page. Also remove the now-obsolete archived-pages comment block (it duplicates `site/archived/README.md`).

### Phase 4: Validate
- Run `python scripts/build_site.py` — must succeed and not reference deleted files.
- Run `pytest tests/` — must pass.
- Manually verify the `_site/` output contains only the surviving pages.

### Phase 5: Commit + comment
- Atomic commit on `daily-issue-fixing`.
- Comment on issue #27 summarizing the cleanup. Leave the issue open for human review (Code track convention per routine).

## HF Skills integration
**None.** This is a site-only Code-track change. No Hub operations.

## Workflow trigger
- **No PyPI release.** This is a site change only. Site is published by `pages.yml` on push to `main`. Do not bump version.
- `daily-issue-fixing` → human review → merge to `main` → GitHub Pages rebuild.
