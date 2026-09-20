# Analytics: status and remaining work

Handover note for teammates, the independent reviewer and coding agents picking up the analytics feature. Snapshot date: 20 September 2026, branch `erfan/backend-auth`. This file is a status summary, not a contract: formulas and rules live in [ANALYTICS.md](../ANALYTICS.md), routes in [API.md](../API.md), and the detailed plans are linked below. Where this file and a contract disagree, the contract wins; tell the user. The tracker ([IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)) has **not** been updated for these batches yet.

## In one paragraph

The backend core is built and tested on fixture data: a SQL view of completed sale lines, date-range logic, a full-refresh `refresh_analytics` command, a `snapshot_inventory` command and the dashboard's read queries. Nothing has run on real data yet, because the chosen dataset is gated (access requested by the user on 20 September, not yet confirmed) and the import is not built. The dashboard page, the pandas cross-check, the importer, the fallback generator and the optional ML are still to do. None of it has passed the independent review gate.

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

Commands (all run inside the web container, for example `docker compose run --rm web python manage.py ...`):

- `snapshot_inventory --as-of YYYY-MM-DD [--namespace NS] [--name NAME]`: seals current stock and lead times as an immutable inventory version; the cutoff is 00:00 Singapore time on that date. The option is `--name` because Django reserves `--version`.
- `refresh_analytics --as-of YYYY-MM-DD [--namespace NS] [--inventory-version NAME] [--keep 5] [--timeout 300]`: needs a sealed inventory at exactly that cutoff with a row for every product. Skips with exit 0 if another refresh holds the advisory lock.

## Left to do

Ordered by dependency. Sizes: S under an hour, M a session, L several.

1. **Done, awaiting re-review: `snapshot_inventory` today-only guard (KO-1).** The owner chose today's Singapore date only, with the live-stock approximation disclosed in ANALYTICS.md and the dashboard footer (6c). AQRY-001 (integer overflow in the flag arithmetic) and AQRY-002 (unsealed existing versions) were fixed in the same change. See [docs/reviews/analytics-queries.md](../reviews/analytics-queries.md).
2. **A9, S:** `seed_demo --no-products` (create the demo operator without the 14 hand-written products). See [6a decision 5](batch-06a-data-import.md).
3. **A7, L: dashboard (batch 6c).** Fully planned in [batch-06c-dashboard.md](batch-06c-dashboard.md); its prerequisites (A5) exist. Includes: move `HtmxLoginRequiredMixin` to `accounts/mixins.py`, the `reporting.view_analytics` permission (options-only migration `0004`) granted in `seed_demo`, the view and `#analytics-panel` fragment, vendored Chart.js (verify `collectstatic` accepts it), templates, tests. Buildable and testable without the dataset.
4. **A8, M to L: deterministic generator.** Planned in [batch-06a-dataset-generator.md](batch-06a-dataset-generator.md). The fallback if dataset access does not arrive by about 22 September, also the source of realistic data for the dashboard walkthrough, the cross-check and load fixtures. Needs the `../data:/app/data:ro` Compose mount and `pyarrow` in `requirements.in`.
5. **6a import (M to L).** [batch-06a-data-import.md](batch-06a-data-import.md): `src/config/dataset.py`, `import_dataset`, generated stock and the sealed import-time inventory, tests on tiny Parquet fixtures. The source columns are documented in the dataset card, so most of this can be built before access is granted; only the profile run, the accept-or-reject decision and the real import reconciliation need the real files.
6. **A6, M: `analytics/verify_refresh.py`.** Independent pandas recomputation compared with the database (plan in 6b). Write and smoke-test on generated or fixture data; run on real data later.
7. **Batch 6d (optional, gated): K-means RFM segmentation.** Only after the required work passes and the data profile shows enough order history per customer. Planned only in outline in [ANALYTICS.md](../ANALYTICS.md).
8. **Documentation and evidence owed:**
   - `docs/SCHEMA.md`: document the view. `docs/plans/batch-06b-analytics-refresh.md`: `--version` is now `--name`.
   - `docs/API.md`: flip the analytics route to implemented when 6c lands.
   - Tracker entries for 6a, 6b and 6c; `analytics/README.md`; `evidence/test-data-ai.md` and `evidence/data-validation.md` from real command output; `data/README.md`, `data/DATA_DICTIONARY.md`, manifest fields after 6a. Update the [review brief](astra-review.md) queue with the analytics commits.
9. **Independent review gate:** [astra-review.md](astra-review.md) lists five earlier backend tasks awaiting review; the analytics work above should join that queue in this order: 6a import, 6b (already committed as `41ea463`, `470becd`, `788f545`), then the 6c backend part.

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
- `data/raw/` is gitignored. It currently holds only the dataset card (`DATASET_CARD.md`); the Parquet files are gated on Hugging Face (`LaelaZorana/synthetic-ecommerce`, pinned revision `04ba3b7ad88904d27169e2e998b7b22c44b3029d`). Only the user can request or confirm access; do not attempt to bypass the gate, and do not paste tokens into a chat.
- Commits by agents: descriptive body, the user as sole author, no `Co-Authored-By` trailer unless the user says otherwise. Never push.

## Open decisions (user)

| Decision | Recommendation | Where |
|---|---|---|
| `snapshot_inventory` past-date guard | decided: today's Singapore date only, disclosed approximation | resolved, item 1 |
| Dataset: wait for access or switch to the generator | decide by about 22 September | [6a plan](batch-06a-data-import.md) |
| Commit raw dataset files or only checksums | decide after download | 6a decision 7 |
| Move `HtmxLoginRequiredMixin` (touches cart code awaiting review) | move it | [6c plan](batch-06c-dashboard.md) decision 1 |
| Generator location and defaults | `src/config/dataset_generator.py`, 80/10/10 status mix | [generator plan](batch-06a-dataset-generator.md) |
