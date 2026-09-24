# Analytics: status and remaining work

Handover note for teammates, the independent reviewer and coding agents picking up the analytics feature. Status reconciled 23 September 2026 after PR #2 merged to `main` at `0887e81`. This reconciliation uses only repository records: Git history for merged commits and tracked files, [analytics refresh](../reviews/analytics-refresh.md), [analytics queries](../reviews/analytics-queries.md) and [final integration](../reviews/pr-2-final.md) for review outcomes, [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) for current status, and [backend-completion-roadmap.md](backend-completion-roadmap.md) for the remaining-work order. No task is marked complete from code existence alone. Formulas and rules remain owned by [ANALYTICS.md](../ANALYTICS.md), and routes by [API.md](../API.md). Where this handover conflicts with an owning source, follow the owning source and correct this handover.

## In one paragraph

The analytics backend core is merged to `main`, tested on fixture data and independently review-gate cleared: a SQL view of completed sale lines, date-range logic, a full-refresh `refresh_analytics` command, a `snapshot_inventory` command and the dashboard's read queries. Dataset roadmap Phases 1–2 are complete locally and independently review-cleared at `4704cc8`. Phase 3 has now run both refreshes and passed independent pandas reconciliation locally; its backend review status is recorded in [the Phase 3 review](../reviews/analytics-phase3.md). **Dataset switched and committed 22 September 2026**: the original selection (LaelaZ/synthetic-ecommerce on Hugging Face) was gated and access never arrived by the decision deadline; the team switched to the [Analytics Engineering Ecommerce Sales Dataset](https://www.analyticsengineering.com/datasets/ecommerce-sales) (CC BY 4.0, no account needed). The unchanged raw release is tracked under `data/raw/` at `b95905a`; all six checksums and published row counts were verified during final integration review. Integrity profiling and import passed; the user accepted descriptive use despite weak patterns. Phase 3 implementation verification passed with zero mismatches and 410 combined tests. Phase 4 is complete locally; independent Astra Medium round-3 review is CLEAR with DASH-001–005 resolved. [Review and limitations](../reviews/analytics-dashboard.md). The deterministic generator remains planned for correctness and isolated load-test fixtures, not as the primary historical source. Optional ML is deferred and may be omitted without weakening the required analytics submission.

## Done

| Item | What it is | Commit | Plan |
|---|---|---|---|
| A1 | View `reporting_completed_sale_lines` (migration `reporting/0003`) | `41ea463` | [6b](batch-06b-analytics-refresh.md) |
| A2 | `src/reporting/ranges.py`: spans, comparison span, buckets, leap-year safe | `41ea463` | 6b |
| A3 | `src/reporting/services.py` `refresh_analytics` + command: lock, publish, retention | `470becd` | 6b |
| A4 | `snapshot_inventory` service + command | `788f545` | 6b |
| A5 | `src/reporting/queries.py`: summary, buckets, categories, top sellers, coverage | `788f545` | 6b |
| Docs | Analytics contract, API contract, plans for 6a/6b/6c/generator, evidence and review briefs | `91ba04e` | n/a |

Tests: `tests/test_analytics_ranges.py`, `test_analytics_view.py`, `test_analytics_refresh.py`, `test_analytics_snapshot.py`, `test_analytics_queries.py`, shared builders in `tests/analytics_helpers.py`. Full suite at `788f545`: 301 passed, `manage.py check` clean, `makemigrations --check` reports no changes (the view is a `RunSQL` migration, no model change).

Review status: [analytics refresh](../reviews/analytics-refresh.md) passed with no actionable findings. [Analytics queries](../reviews/analytics-queries.md) cleared at `7eea9b7` after AQRY-001 and AQRY-002 were resolved; KO-1 remains an owner-accepted, disclosed approximation rather than an unresolved review finding. PR #2 then passed final integration review and merged to `main` at `0887e81`; hosted CI at the reviewed head passed 381 tests. Real-dataset execution and the pandas comparison subsequently passed locally in Phase 3; [evidence](../../evidence/test-data-ai.md). Dashboard integration is now independently review-cleared locally; final visual/keyboard rerun was unavailable. Scheduler-host-loss execution remains unverified.

Commands (all run inside the web container, for example `docker compose run --rm web python manage.py ...`):

- `snapshot_inventory --as-of YYYY-MM-DD [--namespace NS] [--name NAME]`: seals current stock and lead times as an immutable inventory version; the cutoff is 00:00 Singapore time on that date. The option is `--name` because Django reserves `--version`.
- `refresh_analytics --as-of YYYY-MM-DD [--namespace NS] [--inventory-version NAME] [--keep 5] [--timeout 300]`: needs a sealed inventory at exactly that cutoff with a row for every product. Skips with exit 0 if another refresh holds the advisory lock.

## Left to do

Ordered by dependency from [backend-completion-roadmap.md](backend-completion-roadmap.md). Sizes retain the existing estimates: S under an hour, M a session, L several.

1. **Dataset acceptance (Phase 1): complete locally**, with manual acceptance for descriptive use despite weak patterns; [review](../reviews/analytics-data-import.md).
2. **6a import (Phase 2): complete locally**, including sealed historical inventory, replay safeguards and seed_demo --no-products; independent round-2 review CLEAR at `4704cc8`.
3. **Analytics on real data (Phase 3): complete locally; independent Astra Medium round-1 gate CLEAR.** Two refreshes used the importer-created sealed historical inventory (no snapshot_inventory); daily rows and coverage were identical. pandas found zero mismatches; 410 combined tests passed. [Evidence](../../evidence/test-data-ai.md), [review](../reviews/analytics-phase3.md).
4. **A7 dashboard (Phase 4, L): complete locally; independent Astra Medium round-3 gate CLEAR.** DASH-001–005 resolved by sequential Astra Low/Luna Max remediation. Independent checks: 30 dashboard and 436 full-suite tests passed; Django/migration/static/checksum and full/fragment HTTP checks passed. Earlier browser checks and unavailable final visual rerun are distinguished in [the review](../reviews/analytics-dashboard.md), along with completed test-resource cleanup following explicit user approval.
5. **A8 deterministic generator (M to L):** retain the planned generator for the tiny hand-checkable correctness fixture and isolated load-test fixture. It is not the primary historical-import fallback. Keep its dependency choice aligned with [batch-06a-dataset-generator.md](batch-06a-dataset-generator.md); do not add `pyarrow` to the web image merely to import the downloaded CSV release.
6. **Documentation and evidence (Phase 5):**
   - `docs/SCHEMA.md`: view now documented in Phase 3. `docs/plans/batch-06b-analytics-refresh.md`: `--version` is now `--name`.
   - `docs/API.md`: analytics route and HTMX contract are implemented and independently review-cleared locally; publication remains pending.
   - Tracker entries for 6a, 6b and 6c; `analytics/README.md`; `evidence/test-data-ai.md` and `evidence/data-validation.md` from real command output; `data/README.md`, `data/DATA_DICTIONARY.md`, manifest fields after 6a. Update the [review brief](astra-review.md) queue with the analytics commits.
7. **Independent review gate:** 6b is already cleared. 6a is independently cleared. Phase 3 pandas verification is independently cleared. The 6c backend/dashboard integration is independently cleared in round 3; [review](../reviews/analytics-dashboard.md).
8. **Optional batch 6d:** K-means RFM segmentation remains deferred. Start it only after required analytics, AWS smoke deployment and evidence pass, and only if profiling shows sufficient repeat-purchase signal. It may be omitted.

The scheduler that triggers `refresh_analytics` periodically is deliberately **not** designed yet; that is an infrastructure-phase decision after the command exists (see [cloud-independent-prep.md](cloud-independent-prep.md) B6).

## Rules that are easy to break

- Always read one completed run; never sum `DailyProductSales` across runs. Readers use `queries.latest_completed_run`.
- Coverage and flags use the **sealed inventory snapshot**, never live `Product` stock, and always the seven complete business dates ending at L, whatever range the dashboard shows.
- A business date is a Singapore calendar date, weekends included. Convert timestamps in SQL with an explicit `Asia/Singapore` zone. Never hardcode 365, 366 or 30 in logic; derive spans by date arithmetic.
- Aggregation is SQL (the view, `PUBLISH_SQL`, the constants in `queries.py`), not Python or the ORM. Checkout and cart stay on the ORM.
- `refresh_analytics` never creates or falls back to an inventory; that is explicit (DOC-001).
- Compare applies to sales metrics only, never to coverage or flags, and shows "insufficient history" or "n/a" rather than a percentage against zero.
- INF2003 guardrails apply: [INF2003_BASELINE.md](../INF2003_BASELINE.md).

## Practical gotchas

- **Rebuild after changing `src/`.** The image copies `src/` at build time and only `tests/` is mounted. Run `docker compose build web` before `docker compose run ...`, or you will test stale code.
- **Sealed inventory versions cannot be deleted** (database triggers make them append-only). Do not run `snapshot_inventory` against the shared dev database casually; it leaves a permanent version that can later conflict with an import. Tests use throwaway databases and are safe.
- Use `docker compose run --rm web pytest -q -p no:cacheprovider /app/tests/test_analytics_*.py` for the analytics tests, then the whole suite when a migration or shared code changes.
- `data/raw/` is tracked and contains the unchanged Analytics Engineering release, its licence/dictionary and checksums. Do not hand-edit raw inputs; implement transformations reproducibly elsewhere and re-check hashes after checkout on another platform.
- Commits by agents require a concise subject and non-empty descriptive body. Commit or push only within the user's explicit Git scope; do not add `Co-Authored-By` unless requested.

## Decisions and current status

| Decision | Recommendation | Where |
|---|---|---|
| `snapshot_inventory` past-date guard | Decided: today's Singapore date only, disclosed approximation; review gate cleared with KO-1 recorded as owner-accepted mitigation | [analytics queries review](../reviews/analytics-queries.md) |
| Dataset: wait for access or switch | Decided 22 September: switched to the Analytics Engineering dataset, not the generator | [6a plan](batch-06a-data-import.md), `PROJECT_SCOPE_INF2006.md` §5 |
| Commit raw dataset files or only checksums | Decided and completed: unchanged raw release, licence, dictionary and checksums committed at `b95905a` | [6a decision 7](batch-06a-data-import.md) |
| Move `HtmxLoginRequiredMixin` (touches cart code awaiting review) | move it | [6c plan](batch-06c-dashboard.md) decision 1 |
| Generator location and defaults | `src/config/dataset_generator.py`, 80/10/10 status mix | [generator plan](batch-06a-dataset-generator.md) |
