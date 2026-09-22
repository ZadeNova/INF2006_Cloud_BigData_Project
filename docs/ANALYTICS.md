# Analytics contract

Required feature: explainable sales/inventory planning. ML optional, never a dependency. See [data pipeline](DATA_PIPELINE.md) for provenance/dates and [schema](SCHEMA.md) for persistence. Stock and lead times are generated (the source dataset has none) and sealed as an inventory snapshot; see the data pipeline for the acceptance status of the dataset.

## Definitions

- **Business date:** a Singapore calendar date, midnight to midnight in `Asia/Singapore`. Weekends and public holidays are ordinary business dates; nothing here means Monday to Friday. Stored as `DailyProductSales.business_date`.
- **Complete:** a business date that ended at or before the run's cutoff.
- ***L*:** the latest complete business date at the cutoff. `refresh_analytics --as-of D` sets the cutoff to 00:00 `Asia/Singapore` on date `D`, so *L* is always `D - 1`.
- **Run window:** every run stores 366 business dates, *L*-365 .. *L*, which is enough for year to date in a leap year. `window_start` is the start of *L*-365 in `Asia/Singapore`; `cutoff` is the as-of cutoff.
- **History start:** the earliest business date that has a row in the run (the source carries no product listing dates). Business dates before it mean "no data", not "zero sales"; from the history start onward, an absent row means zero sales. `DailyProductSales` is stored sparsely (only date/product pairs with completed sales); the date spine that zero-fills chart series is applied at read time, not during refresh.

## Metrics

| Output | Definition |
|---|---|
| Sales amount | Sum historical unit price times quantity for completed lines in the window |
| Daily/category sales | Group completed totals and quantities by business date/category |
| Top sellers | Rank completed units in the selected window, top 10; stable product-ID tie break |
| Average daily sales | Units in the seven complete business dates ending at *L*, divided by seven, including zero-sale dates |
| Stock coverage | Aligned stock snapshot divided by average daily units |
| Replenishment flag | Coverage <= configured lead-time days |

Exclude refunded/cancelled orders; this metric is completed-sales value, not accounting net revenue. Use historical prices and explicit business-date boundaries. Display cutoff, run/version, refresh time, units and assumptions.

Zero sales means coverage unavailable, not infinity or a confident recommendation. Example: 35 units/seven days = five/day; 30 stock = six days; seven-day lead time means flagged.

**Partial history.** If fewer than seven complete business dates exist from the history start to *L*, average daily sales, coverage and flags are unavailable and labelled "insufficient history". The denominator stays seven; it is never silently reduced to the number of dates available.

Historical inventory selection (DOC-001): require an explicit immutable snapshot namespace/version/cutoff matching the reporting cutoff, with a row for every reported product. Use its stock and lead time, never mutable Product values. Missing/misaligned snapshots are validation errors. Persist the selection on AnalyticsRun. InventoryVersion must be sealed before a run can reference it; snapshot rows include stock and lead time. DailyProductSales is unique per run/date/product so versioned publication does not overwrite a prior run; readers must select one completed run, never sum across versions. A live stock or lead-time change must leave historical coverage and flags unchanged on recomputation; test this when aggregation is implemented. Snapshot persistence is owned by [schema](SCHEMA.md#foundation-decisions-doc-001-and-doc-002).

**Live inventory snapshots (KO-1).** `snapshot_inventory` seals current live stock and lead times and accepts only today's Singapore date as `--as-of`, because live values are captured when it runs and cannot describe another cutoff. This is a disclosed approximation: the cutoff is labelled 00:00 that day, but sales between midnight and the moment of capture are already deducted from stock. Since nothing in the application raises stock (it only decreases through checkout), the captured stock is at most the true midnight stock, so coverage errs low and flags may fire slightly early, never late. That argument no longer holds if a restock feature is added; revisit it then. Historical inventories are not made by this command: the import seals its generated stock at import time. The dashboard states that stock is a snapshot captured on the refresh day.

## Dashboard (`GET /analytics/`, operator only)

The dashboard is one Django view, not a separate API. It never aggregates order lines: it reads the latest **completed** run's `DailyProductSales` plus the sealed inventory snapshot. There is no run selector; past runs are a backend guarantee (audit, rollback, evidence), not a UI feature. The page shows the run's cutoff, refresh time and version.

**Reporting range.** Ranges end at the run's cutoff, not at wall-clock today. They are inclusive spans of business dates ending at *L*:

| `range` | Span | Notes |
|---|---|---|
| `7d` | *L*-6 .. *L* | |
| `30d` | *L*-29 .. *L* | Default |
| `90d` | *L*-89 .. *L* | |
| `mtd` | first day of *L*'s month .. *L* | |
| `ytd` | 1 January of *L*'s year .. *L* | Up to 366 business dates |

Validate `range` against this whitelist (a Django form choice); an invalid value re-renders with the default range and a visible message. A custom from/to range is a later addition and must be validated server-side, ordered, inside the run window and capped at 366 business dates. The cap is 366 so year to date always fits in a leap year.

**Chart granularity.** Daily points for spans up to 90 business dates (at most 90 points), ISO weeks (Monday start, via `date_trunc('week', ...)`) above that (at most 54 points). Edge weeks contain only the dates inside the span. Tables are unaffected by grouping.

**Compare (`compare=1`).** Optional toggle. It applies only to the range-dependent sales metrics: sales amount, units, the daily/category series and top sellers. Average daily sales, coverage and replenishment flags are never compared. The comparison span is the equal-length block of business dates immediately before the selected span (`start - length .. start - 1`), the same rule for every preset. The chart shows it as a second series aligned bucket by bucket: its buckets are the selected span's buckets shifted back by the span length, so weekly edge clipping never misaligns the two series. It is available only when the whole comparison span lies inside the run window and starts on or after the history start; otherwise show "insufficient history". If the comparison span has zero sales, the difference is "n/a", never infinity or a percentage against zero. Whether a given preset can be compared depends on how much history the run window actually holds, not on an assumption about the dataset's shape. With the selected source covering January 2023 to December 2025, year to date is generally comparable — but the rule above, not the dataset, decides.

**Range independence.** Average daily sales, coverage and replenishment flags always use the seven complete business dates ending at *L*, whatever range is selected. The page states this beside the flags so changing the range never appears to change them.

**Delivery.** Full page for a normal request; only the `#analytics-panel` fragment for an HTMX request (`HX-Request`), with `hx-push-url` so links and the back button work. Chart.js is pinned and served from `src/static/` (no CDN dependency, so the app runs offline); series are embedded with Django's `json_script`, and the chart is re-created on `htmx:load`, destroying any previous instance. Reuse the existing HTMX-aware login redirect and an operator permission check (403 for non-operators). Routes and parameters are recorded in [API](API.md).

## Calendar correctness

Dataset acceptance (22 September 2026): source orders carry explicit UTC `Z` offsets,
which the importer preserves. Published UTC coverage ends 31 December 2025, but the
last Singapore order is 1 January 2026 at 07:59:03. The unshifted generated inventory
cutoff is therefore 2 January 2026 at 00:00 Singapore. Naive signup dates assume
Singapore. `--shift-anchor` is an exclusive midnight cutoff; a constant whole-day
offset puts the latest order on the preceding date. This clarifies source handling
without changing reporting formulas; see [data provenance](../data/README.md).

Never hardcode 365, 366 or 30 in logic. Derive spans, day counts and comparison spans from date arithmetic, and derive any per-date denominator from the actual span (the seven-date average stays fixed at seven by definition). Convert stored UTC timestamps to `Asia/Singapore` in SQL with an explicit time zone; Singapore has no daylight saving. The source dataset covers January 2023 to December 2025 and so contains 29 February 2024. The unshifted historical fixture keeps that real leap day; the shifted demo fixture moves every date by a recorded whole-number-of-days offset, which may move it off 29 February, so leap-day behaviour is verified with explicit-date test fixtures rather than the imported data either way. A shift must be a fixed number of days, never adding a year, which is invalid for 29 February.

## Processing and validation

**Aggregation is SQL.** A database view over completed sale lines, created with `RunSQL`, holds the completed-status exclusion and the business-date conversion in one place. `refresh_analytics --as-of <date>` populates `DailyProductSales` with a parameterized `INSERT ... SELECT ... GROUP BY`, using a `generate_series` date spine and window functions where needed. Coverage and flags are derived at read time from `DailyProductSales` and the sealed snapshot; no separate coverage table is stored. Do not aggregate in Python or the ORM. Keep queries in `.sql` files or one documented module. Checkout and cart stay on the ORM.

**Full refresh.** Each run recomputes its whole 366-date window from the raw data, so a re-run with the same inputs gives the same result. Incremental refresh is out of scope unless measurement shows a need.

**Publication and locking.** A Postgres advisory lock guards the command as a safety net: an accidental concurrent invocation exits without writing. Publish transactionally: readers only ever see `completed` runs, and a failed or interrupted refresh leaves no completed partial run. Run under a `statement_timeout`. Recompute dates affected by status changes (a refund changes a past date) simply by re-running the full refresh.

**Retention.** After a new run completes, keep the newest 5 completed runs and delete only older completed runs; deleting a run cascades to its daily rows. A dashboard request selects the run ID once and uses it for every query in that request. Because at least two runs are always kept, the run a concurrent reader has just selected (the previous latest) is not the one deleted; a request that outlives several further publishes could still find its run gone, and must then re-select the latest run rather than raise an error. Inventory versions and snapshots are append-only and are not pruned.

**Triggering.** Run the command from one designated scheduler, not from every autoscaled web instance (see the scope). The mechanism (cron, systemd timer or another) is decided after the command and dashboard are implemented, in the infrastructure phase; the implementation delivers only the idempotent, locked command. Document and test restart/re-run when the scheduler host fails. If caching is ever added, include period/run version in keys and show freshness; none is planned, because the dashboard reads a small precomputed table.

**Scale.** Dashboard read cost depends on products times business dates in the range, not on order volume; refresh cost depends on order lines. Bound ranges (366 dates), top-N and chart points as above. No standalone database benchmark is required for INF2006; diagnose the analytics page and RDS under the load test and report the limits. A large-scale comparison belongs to INF2003 (see [INF2003 baseline](INF2003_BASELINE.md)).

**Validation.** Independently calculate tiny-fixture results, and cross-check the database output against an independent pandas recomputation in `analytics/` (a plain script, not a notebook). Test cancelled/refunded exclusion, historical price changes, zero sales, partial history (fewer than seven complete business dates gives "insufficient history" with the denominator still seven), business-date boundaries, exact flag threshold and repeat-run idempotency. Also test: each range preset's start and end at a fixed cutoff; the run window and history start; compare rules including "insufficient history" and "n/a" cases and that flags are not compared; leap-day fixtures (seven-date average across 28 February to 1 March 2024, February 2024 month to date of 29 dates, year to date on 29 February of 60 dates, a comparison span containing 29 February); retention pruning; a concurrent-invocation lock test; and operator-only access with the HTMX fragment/full-page split. Add actual commands/results to analytics/README and evidence/test-data-ai.md.

Synthetic patterns do not prove commercial demand, seasonality or behaviour. Stockouts hide unmet demand; seven-day rates and fixed lead times simplify reality. A product with no sales cannot be told apart from a product not yet listed. This informs a simulated stock review, not a validated forecast.

## Optional ML: RFM customer segmentation (K-means)

Begins only after the required work passes and the dataset profile shows customers with enough order history to segment; omit it if the result is not meaningful. It is additive and removable:

- Train and evaluate offline in `analytics/` with its own requirements; the web image has no ML dependency.
- Features per customer, as of the run cutoff and using only completed orders before it: recency (days since last order), frequency (order count) and monetary value (sum of order totals). Scale the features, transform skewed monetary values, fit K-means with a fixed random seed and choose k by silhouette over a small range.
- Evaluate cluster sizes and profiles (mean RFM and share of sales per cluster), silhouette and stability across seeds or resamples. Do not report classification accuracy without true labels. State that synthetic customers may reflect the generator's structure rather than real behaviour.
- A management command loads cluster assignments into one dedicated table, keyed by model version and analytics run. Removal means deleting that module and table.
- The dashboard shows a segment panel (sizes, share of sales, mean RFM) only when assignments exist for the run. It tells the operator which customer groups drive sales; it does not change any deterministic metric or replenishment flag, and it is secondary to the sales-driven inventory planning.

Use the simplest algorithm that can be justified for the store; more complex models are not planned.
