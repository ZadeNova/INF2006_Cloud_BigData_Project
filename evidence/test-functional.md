# Functional workflow test

- **Objective:** TODO
- **Setup:** TODO
- **Command/steps:** TODO
- **Expected result:** TODO
- **Actual result:** TODO
- **Date:** TODO
- **Artefact path:** TODO (e.g. logs, output files referenced here)

Foundation-only evidence (12 September 2026): [local startup and health/readiness](../docs/reviews/foundation-batch-4.md), [schema constraints](../docs/reviews/foundation-batch-3.md). The ecommerce workflow (register, browse, cart, checkout, order history, operator page) is implemented and has automated tests ([tests/README.md](../tests/README.md)), but no functional run is recorded in this file yet; the foundation checks above do not complete it.


## Phase 6 local release verification — 25–26 September 2026

Objective: verify the integrated current application and truthful operator segmentation display on the unchanged accepted dataset. Setup: clean baseline `430e4c8` plus the reviewed Phase 6 diff, isolated PostgreSQL resources and rebuilt `inf2006-phase6-final`; exact image/source identities and command receipts are in [the release record](../docs/reviews/ml-local-release-readiness.md).

Final-image `/app/tests` run: 472 passed, 8 opt-in bootstrap cases skipped; separate disposable bootstrap module run: 9 passed, including all eight skipped cases and one overlapping case. Django system and migration-drift checks passed. The accepted full-data workflow and live browser results are recorded in the release record; this automated suite is not itself browser evidence. Existing human-execution, cloud and submission-template fields above remain incomplete and are not filled with invented contributions.


Luna Max live browser checks passed: loaded/unavailable ML states, current-run identity/lifetime copy, recipe disclosure by keyboard, light/dark desktop/mobile layouts, actual HTMX filters and visible focus below the sticky header. On the final image a fresh Luna Max verifier checked 7D→30D→Back→Forward: both charts redrew with matching URL/span/data, history kept normal BODY focus, and mobile390×844 filter focus stayed visible. Desktop checks used1280×720 and final history check1259×711. Loaded/theme checks preceded the last JS-only correction with unchanged template/CSS; final history/unavailable/focus checks used the final image. Exact values, image identity and independent review clearance are in the release record. Screenshot observations were inline; no nonexistent screenshot artifact is claimed.
