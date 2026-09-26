# Analytics contract

Required feature: explainable sales/inventory planning. Descriptive customer-segmentation ML is included, never a dependency of deterministic analytics or checkout. See [data pipeline](DATA_PIPELINE.md) for provenance/dates and [schema](SCHEMA.md) for persistence. Stock and lead times are generated (the source dataset has none) and sealed as an inventory snapshot; see the data pipeline for the acceptance status of the dataset.

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
| Top sellers | Rank shoe models by completed units in the selected window (all sizes of a model together), top 10; stable tie break on the model's lowest product ID. A product without a model ranks on its own |
| Size sales | Completed units and sales amount per shoe size in the selected window, smallest size first; products without a size are left out. Compared like categories |
| Average daily sales | Units in the seven complete business dates ending at *L*, divided by seven, including zero-sale dates |
| Stock coverage | Aligned stock snapshot divided by average daily units, per product (for shoes, per size, because stock is held per size) |
| Replenishment flag | Coverage <= configured lead-time days |

Exclude refunded/cancelled orders; this metric is completed-sales value, not accounting net revenue. Use historical prices and explicit business-date boundaries. Display cutoff, run/version, refresh time, units and assumptions.

Zero sales means coverage unavailable, not infinity or a confident recommendation. Example: 35 units/seven days = five/day; 30 stock = six days; seven-day lead time means flagged.

**Partial history.** If fewer than seven complete business dates exist from the history start to *L*, average daily sales, coverage and flags are unavailable and labelled "insufficient history". The denominator stays seven; it is never silently reduced to the number of dates available.

Historical inventory selection (DOC-001): require an explicit immutable snapshot namespace/version/cutoff matching the reporting cutoff, with a row for every reported product. Use its stock and lead time, never mutable Product values. Missing/misaligned snapshots are validation errors. Persist the selection on AnalyticsRun. InventoryVersion must be sealed before a run can reference it; snapshot rows include stock and lead time. DailyProductSales is unique per run/date/product so versioned publication does not overwrite a prior run; readers must select one completed run, never sum across versions. A live stock or lead-time change must leave historical coverage and flags unchanged on recomputation; test this when aggregation is implemented. Snapshot persistence is owned by [schema](SCHEMA.md#foundation-decisions-doc-001-and-doc-002).

**Live inventory snapshots (KO-1).** `snapshot_inventory` seals current live stock and lead times and accepts only today's Singapore date as `--as-of`, because live values are captured when it runs and cannot describe another cutoff. This is a disclosed approximation: the cutoff is labelled 00:00 that day, but sales between midnight and the moment of capture are already deducted from stock. Since nothing in the application raises stock (it only decreases through checkout), the captured stock is at most the true midnight stock, so coverage errs low and flags may fire slightly early, never late. That argument no longer holds if a restock feature is added; revisit it then. Historical inventories are not made by this command: the import seals generated stock against its historical reporting cutoff. The dashboard uses the sealed snapshot associated with the completed run; its general disclosure distinguishes generated historical inventory aligned to that cutoff from a live snapshot captured after midnight, which approximates the midnight cutoff, without inferring provenance the run model does not expose.

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

**Delivery.** Full page for a normal request; only the `#analytics-panel` fragment for an HTMX request (`HX-Request`), with `hx-push-url` so links and the back button work. Chart.js is pinned and served from `src/static/` (no CDN dependency, so the app runs offline); series are embedded with Django's `json_script`, and the chart is drawn on initial document load and re-created after an actual analytics-panel swap or HTMX history restoration, destroying any previous instance. History restoration redraws without moving focus. Focus/announcement moves to the panel heading only after that swap, not on initial load. Reuse the existing HTMX-aware login redirect and an operator permission check (403 for non-operators). Routes and parameters are recorded in [API](API.md).

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

## Included descriptive ML: RFM customer segmentation (K-means)

Included by the 25 September scope decision; evaluate whether the dataset has sufficient signal and report limitations. It remains additive and removable. Offline training/loading form an explicitly triggered batch workflow. Saved-model inference is optional and unimplemented; Lambda is not selected; EventBridge Scheduler is an optional side quest (decision record: [aws-terraform.md](plans/aws-terraform.md)). Keep the local path and isolate cloud integration from deterministic analytics:

- Train and evaluate offline in `analytics/` with its own requirements; the web image has no ML dependency.
- Features per customer use lifetime completed history strictly before the cutoff, independently of the dashboard date filter: recency (floor elapsed days since last order), frequency (order count) and monetary value (sum of application order totals). No source segment label enters features or evaluation truth. Stable customer-ID ordering and fixed seeds make assignments reproducible. The default model inputs (`log_rfm_aov`, adopted 26 September 2026 for review finding M-03) are standardized log1p recency, log1p frequency and log1p average order value (monetary value divided by order count), so purchase volume is not counted twice; the earlier `log_frequency` (raw recency, log1p frequency, log1p monetary) and raw-frequency baseline remain selectable. The accepted-revision [aggregate comparison](../evidence/ml-quality-evaluation.json) covers the two earlier recipes; the shoe-dataset [comparison](../evidence/ml-holdout-evaluation.json) covers the adopted one. Lifetime history still favours long-tenure customers (review M-04).
- Fit candidate k=2..4 and select the highest valid silhouette, breaking ties toward smaller k. Score a fixed seed-42 sample of at most 5,000 customers to bound pairwise memory; fit on the full cohort. Validate bounds, customer count, distinct vectors, actual fitted labels and sample labels. Keep finite negative scores; record invalid reasons. With no valid candidate, fail without overwriting a previous assignment export. Different CLI seeds also control the score sample.
- Segmentation eligibility: at least one completed order in the run inventory namespace strictly before its cutoff. Exclude staff, superusers and members of `store_operator`; an ordinary locally registered customer does not need a `CustomerProfile`. This describes past purchasing, not a minimum history sufficient for prediction.
- Evaluate cluster sizes and profiles (mean RFM and share of sales per cluster), silhouette and stability across seeds or resamples. Do not report classification accuracy without true labels. State that synthetic customers may reflect the generator's structure rather than real behaviour.
- Offline training writes JSON via `analytics/segment_customers.py`; Django command `load_customer_segments` loads
  assignments into one dedicated table keyed by model version and analytics run. Removal means deleting that module and table.
- The dashboard always explains segmentation availability for the selected completed analytics run. Loaded groups show sizes, share of sales and mean RFM; a run without assignments shows "No segmentation results loaded for this run". It does not change any deterministic metric or replenishment flag, and remains secondary to sales-driven inventory planning.

Use the simplest algorithm that can be justified for the store; more complex models are not planned.

Labels describe cluster-profile means relative to their unweighted medians: recent/older, more/fewer orders and higher/lower spend. Equality uses recent/fewer/lower. A deterministic profile rank prefix keeps labels unique, within the 40-character field. They make no loyalty, churn or future-purchase claim. Existing plain-text template rendering and alphabetical fallback ordering support these labels without a frontend change; historical high_value/core/at_risk priority remains compatible with older imports. The dashboard labels the lifetime feature period separately from its sales date filters.

`analytics/evaluate_segments.py` retains source/code hashes, cohort counts, cutoff/period, runtime, candidates, invalid reasons, seed ARI, sizes and profiles in aggregate-only evidence. It compares exactly the baseline and log-frequency alternative, without AOV or tenure normalization. One-order histories remain eligible and are counted; unequal purchasing opportunity limits interpretation. Seed stability is not resampling robustness. Raw accepted data is evaluated; the planned shoe remap needs new evaluation after validated adoption.

### Segment serving contract

Operator segment rows expose `CUS-<customer User primary key>` as `customer_reference`, including for locally registered shoppers without CustomerProfile. Source external IDs are arbitrary text and unique only within a namespace, so they are unsuitable as a universal safe display reference. The segment query/context does not fetch or expose login usernames, email or names. These stable display references reduce unnecessary exposure; they are neither authorisation nor anonymisation. Existing operator permissions remain required.

The customer list is a sample, with an overall limit of 50 and at most 25 per segment label. Within each label, rank by monetary total descending, then customer ID ascending. Allocate one row per populated label per round, ordered by existing high_value/core/at_risk priority, then other labels alphabetically. Small groups release unused capacity to other groups up to the per-group cap. When populated labels exceed available slots, only the first labels in that deterministic order receive a row; the list does not claim universal representation. After selection, group the bounded rows by the same label priority and sort members by monetary total descending/customer ID ascending. No hard-coded number of clusters is assumed.

The overview retains total group counts and metrics; sampled rows and their displayed count must be labelled separately. Selection uses a single window query without per-customer lookups. Run/model selection, eligibility, cluster names, RFM values and cutoff semantics are unchanged.

### Segment display and lifecycle contract

Use only the selected completed analytics run's assignments; never fall back to an older run. The loaded panel identifies that run, its cutoff and the selected model recipe version. Full recipe identity may be disclosed on demand rather than filling the summary with a hash. Persistence does not retain the completed export's batch ID, so the interface must not claim to identify a fitted model or immutable batch artifact.

RFM uses lifetime completed-order history strictly before that run's cutoff, independently of dashboard range and comparison controls. Eligibility and unequal-tenure limitations above still apply. Without assignments, say "No segmentation results loaded for this run"; absence does not prove that training is running, failed or stale. A failed replacement preserves valid loaded results under the import contract. A new completed analytics run requires its own explicit batch.

Read segment overview and the eager customer sample together under the same run lock used by the loader, so a concurrent replacement cannot combine summaries and rows from different publications. Keep the existing whole-context retry when run retention removes the selected run. No status model or orchestration state is introduced.

### Segment import safety contract

The export must be a JSON object with explicit matching `run_id`, nonempty derived `model_version`, top-level `k_clusters` and `silhouette_score`, a nonempty `rows` assignment array, and the completed batch envelope below. Duplicate JSON keys are rejected. `silhouette_score` must be present at both levels: use JSON `null` when undefined, otherwise a value in -1..1 with at most four decimal places (negative scores are valid). Each customer occurs once; row metadata must agree with the top level, cluster IDs must be below k, and numeric values must be finite and fit their database fields. Integers must be JSON integers, excluding booleans and numeric strings; money supports at most two decimal places. Cluster labels must agree within each cluster, but not every cluster needs an assignment. Extraction is ordered by customer ID. A supplied `--model-version` asserts the derived identity; neither training nor import may arbitrarily relabel it.

The loader requires exactly the currently eligible customer set for that completed run. If source eligibility changes between export and loading, regenerate the export. This checks current source records at import time, not an immutable historical feature snapshot. Matching IDs does not prove submitted RFM values match the original feature computation or establish model quality; same-ID feature drift can remain undetected. Immutable feature snapshots and saved-model artifacts remain deferred. Staff/group or source changes after loading are not automatically reflected until the next export/load.

Same-run/model loading replaces its assignments atomically, retaining the existing rerun contract: replay cannot duplicate assignments, and a different valid payload with the same identity replaces the prior set. Lock the analytics run while rechecking its completed status, eligibility and replacing rows so concurrent loaders cannot interleave partial publications. Invalid input leaves the prior assignments unchanged. Distinct model versions remain separate.

### Explicit batch handoff contract

Manually invoke `segment_customers.py --run-id UUID --output FILE`, then separately
`load_customer_segments --run-id UUID --input FILE`. Both selections are mandatory;
never infer the latest run or newest file. Each training invocation refits the scaler
and K-means; no saved model, scheduling or persistent batch model is introduced.
Namespace/cutoff come from the selected completed run. The existing Phase 2 serving
selection and deterministic metrics are unchanged.

The mandatory `rfm-batch-v1` envelope includes `status=completed`, generation time,
source association, run namespace/UTC cutoff/inventory version/summary UUID,
training configuration and provenance. Independently configured `ML_SOURCE_ID`
(a deployment/database UUID), the actual PostgreSQL database name and all selected
run fields must match the destination. An operator must provision a new association
for a recreated/cloned database; configuration copied with a clone can defeat that
distinction. This is declared traceability, not authentication. Namespace alone is
not source proof. No hostnames or credentials are exported.

Training configuration records lifetime-RFM feature schema, preprocessing, candidate
bounds within 2..4, selection/tie policy, published seed, stability seeds, n_init and
silhouette sample limit. Its provenance records Python/ML dependency versions and
SHA-256 hashes of producer/shared-contract source and pinned analytics requirements.
`model_version=rfm-v3-<SHA256>` hashes this complete training configuration/provenance,
independently of the run/output. It is a recipe identity, not a fitted model identity.
`batch_id` hashes the completed payload excluding only `generated_at` and itself:
source/run, recipe, selected k, metrics, rows and profiles all contribute. Canonical
JSON uses sorted keys, normalized equivalent JSON numbers and preserved array order;
formatting and time alone do not change identity. Digests detect accidental mismatch;
they do not authenticate an export, prove source truth or verify original RFM values.

Producer and loader reuse standard-library field/batch validation; ML packages never
enter the web image. Validate before writing a temporary sibling file, flush/fsync,
then atomically replace the named output. Training, validation or publication failure
must return nonzero with sanitized diagnostics and retain a valid prior export.
Incomplete temporary files are never import inputs. A valid completed export can be
retried after import failure without retraining; cohort drift requires regeneration.
Legacy files missing the envelope are rejected and must be regenerated. Keep completed
exports in the authorised output location for provenance; existing persistence stores
only run/model version and assignments, and no migration is needed. A new refresh
requires its own explicit batch. The minimal loaded/unavailable display follows the lifecycle contract above. Immutable
feature snapshots remain deferred; no persisted running/failed state is inferred. Executable operations and recovery:
[batch runbook](../analytics/README.md#included-descriptive-ml-explicit-batch-handoff).
