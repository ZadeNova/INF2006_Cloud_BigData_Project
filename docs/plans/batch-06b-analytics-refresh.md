# Batch 6b — analytics refresh and read queries

Written before implementation, per `CLAUDE.md`'s "Discuss / Plan" step. Second of the analytics sub-batches; follows [batch-06a-data-import.md](../archive/plans/batch-06a-data-import.md). Contract: [ANALYTICS.md](../ANALYTICS.md) is authoritative for formulas, ranges, compare, retention and calendar rules; this file only says how they get built. Related: [SCHEMA.md](../SCHEMA.md).

## Context

The reporting tables (`InventoryVersion`, `InventorySnapshot`, `AnalyticsRun`, `DailyProductSales`) and their DB guards already exist ([src/reporting/models.py](../../src/reporting/models.py), migration `0002_inventory_guards`). Nothing populates or reads them. This batch adds the SQL view, the `refresh_analytics` command, a small snapshot command, the read-side queries the dashboard needs, and the independent pandas cross-check. It contains no view, template or URL; those are 6c.

6b does not depend on 6a's real data: every test uses tiny explicit-date fixtures built with the ORM. 6a supplies the data to run the cross-check against and to demo.

## Decisions to confirm before implementation

1. **`--as-of D` semantics.** The cutoff is `00:00 Asia/Singapore` on date `D`, so *L* = `D - 1` (always the day before the cutoff's date, per ANALYTICS.md definitions). **Recommended.** ANALYTICS.md gets one added sentence to say this.
2. **Sparse storage.** `DailyProductSales` stores only (date, product) pairs that had completed sales; absent rows from the history start onward mean zero. The date spine (`generate_series`) is applied at read time to zero-fill chart series, not during refresh. **Recommended**: smaller table, and the unique constraint and guards already fit it.
3. **Lock contention.** A second invocation while one holds the advisory lock prints "skipped: another refresh is running" and exits 0. It is the safety-net case, not a job failure. Choose exit non-zero instead if the user prefers loud failures.
4. **`snapshot_inventory` is in scope.** A run needs a sealed inventory at exactly its cutoff. 6a seals one at the import cutoff; a live-demo refresh at a later cutoff needs another. A small create-only command builds it from current `Product` values. **Recommended**: about 30 lines, and it makes the "place order, refresh, see it on the dashboard" demo possible. `refresh_analytics` never creates snapshots implicitly (DOC-001: explicit selection, no fallback).
5. **Read queries live here, not in 6c.** The dashboard's numbers are the correctness core and belong with their tests; 6c only wires them to a view and templates.
6. **Home of the code.** SQL and query functions in one documented module, `src/reporting/queries.py` (SQL as named constants, thin functions using `connection.cursor()`); pure date logic in `src/reporting/ranges.py`; commands in `src/reporting/management/commands/`. **Recommended** over a `.sql` file directory: fewer moving parts.
7. **Statement timeout.** `SET LOCAL statement_timeout` inside the publish transaction, default 300 seconds, overridable with `--timeout`.

## Implementation

**Migration `reporting/0003_completed_sale_lines_view.py`** (`RunSQL` with reverse `DROP VIEW`): `reporting_completed_sale_lines` over `orders_order` joined to `orders_orderitem`, `WHERE status = 'completed'`, exposing `namespace`, `order_id`, `product_id`, `quantity`, `unit_price`, `line_total`, and `business_date = (placed_at AT TIME ZONE 'Asia/Singapore')::date`. The status exclusion and time zone conversion live only here. No model change; `makemigrations --check` must still report none.

**`ranges.py`** (pure Python, no database): `latest_complete_date(cutoff)`, `resolve_span(range_key, L)` for `7d`/`30d`/`90d`/`mtd`/`ytd` with whitelist validation and default `30d`, `comparison_span(start, end)` (equal-length block immediately before), `granularity(start, end)` (daily up to 90 dates, weekly above), the 366-date cap, `buckets(start, end, granularity)` (inclusive date buckets for the span: single dates, or ISO weeks with edge weeks clipped to the span) and `shift_buckets(buckets, days)`. The comparison series uses the selected span's buckets shifted back by the span length, so bucket *k* of each series lines up even when ISO-week clipping would differ; the pair of spans is contiguous and equal-length, so the shifted buckets exactly tile the comparison span. All by date arithmetic; no hardcoded 365, 366 or 30.

**`refresh_analytics`** (`--as-of D`, `--namespace` default `DEMO_NAMESPACE`, `--inventory-version NAME`, `--keep 5`, `--timeout 300`):

1. Take a Postgres advisory lock on a fixed key; if unavailable, skip (decision 3). Released in `finally`.
2. Validate before creating anything: a sealed `InventoryVersion` for the namespace at exactly the cutoff, with a row for every `Product` in the namespace; otherwise `CommandError` and no run row.
3. Create the `AnalyticsRun` (`running`, `window_start` = start of *L*-365 in Singapore, `cutoff`) in its own committed transaction, so a failure can be recorded.
4. In one atomic block: `SET LOCAL statement_timeout`; a parameterized `INSERT INTO reporting_dailyproductsales ... SELECT business_date, product_id, SUM(quantity), SUM(line_total) FROM reporting_completed_sale_lines WHERE namespace = %s AND business_date BETWEEN %s AND %s GROUP BY 1, 2`; count the source lines processed; set `processed_count`, `status = completed`, `finished_at`. On any exception the block rolls back and a separate short transaction marks the run `failed`, so no completed partial run can exist.
5. After a successful commit, apply retention: delete completed runs beyond the newest `--keep` (default 5), never the just-completed one; deletes cascade to daily rows. Inventory rows are never pruned.
6. Print run ID, span, rows written, lines processed, duration.

No cache and no ORM aggregation. Re-running for the same inputs creates a new run with identical daily rows (full refresh, idempotent by content).

**`snapshot_inventory`** (`--as-of` today's Singapore date only, `--namespace`, `--name`; `--version` is reserved by Django, and only today is accepted because live stock cannot describe another cutoff, see KO-1 in [ANALYTICS.md](../ANALYTICS.md)): builds an `InventoryVersion`, one `InventorySnapshot` per `Product` from current `stock` and `lead_time_days`, verifies completeness, then seals, all in one transaction. Create-only: an existing version with the same name is an error unless every row matches, then it is reported as unchanged.

**`queries.py`** (read side; every function takes the run and dates, never selects across runs; all SQL, no Python aggregation):

- `latest_completed_run(namespace)`: newest `completed` run by `finished_at`, tie broken by `started_at`; `None` if none.
- `history_start(run)`: earliest `business_date` row in the run.
- `sales_summary(run, start, end)`: total sales amount and units; also for the comparison span.
- `bucket_sales(run, buckets)`: sums units and sales amount per (start, end) bucket produced by `ranges.buckets` (passed to SQL as a `VALUES` list joined to the rollup), zero-filled for buckets with no rows. Used for the selected series and, with `shift_buckets`, for the comparison series. Daily granularity is single-date buckets, so the `generate_series` date spine is not needed for the series.
- `category_sales(run, start, end)`: join to `Product.category`.
- `top_sellers(run, start, end, limit=10)`: ordered by units, then product ID.
- `coverage(run)`: for every product in the run's sealed inventory, units in the seven complete dates ending at *L* divided by seven, stock and lead time from the **snapshot**, coverage days, and the flag; `insufficient_history` when fewer than seven complete dates exist from the history start; `unavailable` (no flag) for zero sales.

## Tests

`tests/test_analytics_ranges.py` (no database): each preset's start and end at a fixed *L*; MTD on the first of the month; YTD length in leap and non-leap years (366 and 365 dates, cap 366 accepted); February 2024 MTD is 29 dates; YTD on 29 February is 60 dates; comparison span equal length and containing 29 February; granularity switch at 90/91 dates; invalid range falls back to default.

`tests/test_analytics_refresh.py` (PostgreSQL, explicit fixed dates, hand-computed expectations written in the test):

- **Correctness:** known totals per date and product; cancelled and refunded lines excluded; a historical unit price change keeps old lines at old prices; zero-sale product has no row and reads as zero; Singapore date boundary (an order at 23:30 UTC belongs to the next business date; one at 15:59 UTC does not) and the cutoff boundary (a line on the incomplete date is excluded).
- **Idempotency:** two runs for the same inputs produce identical daily rows; the reader uses only the latest completed run and never sums across runs.
- **Coverage:** the 35 units / 30 stock / 7-day lead time example flags; the exact threshold (coverage equal to lead time flags, one unit more does not); zero sales gives unavailable, not infinity; fewer than seven complete dates gives insufficient history with denominator still seven; seven-date average across 28 February to 1 March 2024; a live `Product.stock` or `lead_time_days` change after the run leaves snapshot-based coverage and flags unchanged.
- **Validation:** unsealed inventory, cutoff mismatch and a missing product row each raise `CommandError` and create no run.
- **Publication:** a failure injected mid-publish leaves the run `failed`, no completed run and no visible daily rows; readers still see the previous completed run.
- **Locking:** with the advisory lock held from another connection (`pytest.mark.django_db(transaction=True)`, real threads, `connection.close()` in `finally`, as the checkout concurrency tests), the command skips and writes nothing.
- **Retention:** run seven times, five newest completed runs remain including the latest, older ones and their daily rows are gone; a failed run is not counted as completed.
- **Views:** `snapshot_inventory` complete, sealed, create-only replay reported unchanged, conflicting replay errors.
- Queries: `top_sellers` tie break by product ID, `bucket_sales` zero-fill, weekly edge clipping and shifted comparison buckets aligning one-to-one with the selected buckets, comparison span outside the run window returns insufficient history. In `test_analytics_ranges.py`: `buckets` for a daily span, an ISO-week span with clipped edges, and `shift_buckets` tiling the previous span exactly.

## Independent cross-check (`analytics/verify_refresh.py`)

A plain pandas script (own `analytics/requirements.txt`, no Django import) that reads order lines with a bare `SELECT` (no aggregation, no view) using the app's database environment variables, recomputes daily units and sales with its own business-date conversion (`tz_convert('Asia/Singapore')`) and its own seven-date average and coverage, and compares them with `reporting_dailyproductsales` and `coverage(run)` for a given run. Exits non-zero on any mismatch and prints a summary for `evidence/test-data-ai.md`. This is the differential-testing evidence for the rubric's "independent validation".

## Verification

`docker compose up --build -d --wait`; `python manage.py migrate` (applies 0003); with 6a's data imported, run `snapshot_inventory` if needed, `refresh_analytics --as-of <date>` twice, and `analytics/verify_refresh.py` (expect zero mismatches); `docker compose run --rm web pytest -q tests/test_analytics_ranges.py tests/test_analytics_refresh.py` then the full suite; `manage.py check`; `makemigrations --check --dry-run` (no model changes). Record real commands and results in `analytics/README.md` and `evidence/test-data-ai.md`; update `docs/SCHEMA.md` (the view), `docs/ANALYTICS.md` (as-of semantics, sparse storage), `docs/IMPLEMENTATION_PLAN.md`. Claude self-review (labelled), fix approved findings, then the mandatory independent backend review gate before marking complete. Commit only when asked; the user pushes.

## Outline of 6c (superseded: see [batch-06c-dashboard.md](../archive/plans/batch-06c-dashboard.md) for the detailed plan)

`reporting` app gains `urls.py` mounted at `analytics/`, `views.py` and templates `reporting/dashboard.html` and `reporting/_panel.html`, per [API.md](../API.md). One view: validates `range`/`compare`, picks the latest completed run once per request, calls the 6b queries, renders the full page or (for `HX-Request`) only `#analytics-panel`. Needs: an operator permission (the existing mixin checks `catalogue.toggle_product_active`; add `reporting.view_analytics` granted to the `store_operator` group, with a migration and a `seed_demo` update), the HTMX login redirect mixin, Chart.js vendored into `src/static/`, a `htmx:load` chart initializer, freshness and assumptions labels, the empty state when no completed run exists, and a nav link for operators. Design pass against DESIGN.md is a separate step after the data path is verified. Tests: operator-only (403 others, HX-Redirect when logged out), fragment versus full page, range validation, compare states, empty state.

## Out of scope

Dataset acquisition and import (6a); the dashboard page (6c); ML (6d); scheduler and triggering mechanism (infrastructure phase, after the command exists); incremental refresh, caching, partitioning and any standalone database benchmark.
