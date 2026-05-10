# Tasks — Spec 027

## T1 — Verify orphan status
**Depends on**: nothing
**Acceptance**: For each of `create.html`, `feedback.html`, `preview.html`, `statistics.html`, `tests.html`, confirm zero inbound references from the *surviving* pages (Home/Browse/Compare/Upload/Contribute/Mesh/Domain/index/styles).

## T2 — Delete orphan HTML files
**Depends on**: T1
**Acceptance**: `site/src/create.html`, `feedback.html`, `preview.html`, `statistics.html`, `tests.html` no longer exist.

## T3 — Delete orphan JS modules
**Depends on**: T2
**Acceptance**: `site/src/js/create.js`, `feedback.js`, `preview.js`, `statistics.js`, `tests.js` no longer exist.

## T4 — Patch 404.html
**Depends on**: T2
**Acceptance**: `site/src/404.html` no longer contains the substring `preview.html`. Recovery copy still points to home.

## T5 — Patch nav.js footer
**Depends on**: T2
**Acceptance**: The footer's `Feedback` link points to `https://github.com/domattioli/ADMESH-Domains/issues`. The "Archived pages" comment block is removed.

## T6 — Validate build
**Depends on**: T4, T5
**Acceptance**: `python scripts/build_site.py` succeeds. The output `_site/` (or whatever the build dir is) contains no `create.html`, `feedback.html`, `preview.html`, `statistics.html`, `tests.html`.

## T7 — Validate tests
**Depends on**: T6
**Acceptance**: `pytest tests/ -q` passes (or only fails on tests unrelated to this spec).

## T8 — Commit on daily-issue-fixing
**Depends on**: T7
**Acceptance**: One atomic commit on `daily-issue-fixing` referencing issue #27.

## T9 — Push and comment on issue
**Depends on**: T8
**Acceptance**: Branch pushed, comment posted on issue #27 with summary + commit SHA. Issue left open for human review.
