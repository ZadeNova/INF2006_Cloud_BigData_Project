# Documentation drift after the ML merge: F-05 and S-005

Written 25 September 2026, branch `erfan/analytics` at `9e07dcf`, from [latest-opus5.5-review.md](../../latest-opus5.5-review.md). The user asked for these two findings only. Each was checked against the code before this plan; the customer-segmentation merge (`958ba3e`) made several documents false.

| ID | File | Statement that is now wrong | Correction |
|---|---|---|---|
| F-05 | `README.md` line 36 | "Not implemented: ... the optional customer segmentation" | Move segmentation to the implemented list, marked optional, offline, descriptive only on synthetic data, and not yet through the review gate |
| F-05 | `docs/SCHEMA.md` | No `CustomerSegment` row (`AGENTS.md` requires the schema contract to change with a model) | Add the row from `reporting/models.py` and migration `0005_customersegment.py` |
| F-05 | `tests/README.md` | "four tests" for `analytics/tests/`; the module table omits the new test modules | Seven tests (four in `test_verify_refresh.py`, three in `test_segment_customers.py`); add `test_customer_segments_command.py` and `test_aws_capability_check.py` to the table |
| F-05 | `analytics/README.md` line 157 | "Four independent tests live in `analytics/tests/`" | Seven, with the two files |
| F-05 | `project_manifest.yaml` `data_ai` | Evaluation cites only the Phase 3 result and "410 combined tests"; no mention of ML | Keep the Phase 3 facts and date them; add one sentence for the optional ML that says its evaluation metrics are not committed yet (finding M-06) |
| S-005 | `src/templates/foundation/statistics.html` banner | "The real dashboard is a later batch ... it will live on its own protected operator route" | Say the real dashboard is `/analytics/` (operator sign-in required); keep the two sentences the tests assert |

Adjacent and in the same spirit: `src/README.md`'s command table lacks `load_customer_segments`; add the row. Test totals: the README and the manifest quote counts from earlier runs, so run the full suite once on this head and cite that number with today's date.

Not in scope: the ML fixes (M-01 to M-10), the AWS probe fixes (W-01, W-02), accessibility, and the team and AI declaration files (the user will fill those in at the end).

Verification: `tests/test_frontend.py` (banner assertions) and the full suite, `manage.py check`, and a link check on the edited files. Documentation and one template line only; no commit until asked.
