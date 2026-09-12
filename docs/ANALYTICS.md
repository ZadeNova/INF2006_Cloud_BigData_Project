# Analytics contract

Required feature: explainable sales/inventory planning. ML optional, never a dependency. See [data pipeline](DATA_PIPELINE.md) for provenance/dates and [schema](SCHEMA.md) for persistence.

| Output | Definition |
|---|---|
| Sales amount | Sum historical unit price times quantity for completed lines in the window |
| Daily/category sales | Group completed totals and quantities by Singapore business date/category |
| Top sellers | Rank completed units in selected window; stable product-ID tie break |
| Average daily sales | Units in previous seven complete business days divided by seven, including zero-sale days |
| Stock coverage | Aligned stock snapshot divided by average daily units |
| Replenishment flag | Coverage <= configured lead-time days |

Exclude refunded/cancelled orders; this metric is completed-sales value, not accounting net revenue. Use historical prices and explicit business-day boundaries. Display cutoff, run/version, refresh time, units and assumptions.

Zero sales means coverage unavailable, not infinity or a confident recommendation. Label insufficient history; do not silently change the denominator. Example: 35 units/seven days = five/day; 30 stock = six days; seven-day lead time means flagged.

Historical inventory selection (DOC-001): require an explicit immutable snapshot namespace/version/cutoff matching the reporting cutoff, with a row for every reported product. Use its stock and lead time, never mutable Product values. Missing/misaligned snapshots are validation errors. Persist the selection on AnalyticsRun. InventoryVersion must be sealed before a run can reference it; snapshot rows include stock and lead time. DailyProductSales is unique per run/date/product so versioned publication does not overwrite a prior run; readers must select one completed run, never sum across versions. A live stock or lead-time change must leave historical coverage and flags unchanged on recomputation; test this when aggregation is implemented. Snapshot persistence is owned by [schema](SCHEMA.md#foundation-decisions-doc-001-and-doc-002).

## Processing and validation

Implement a repeatable aggregation command with upserts/recomputation, a database-backed job lock and transactionally published completed summaries/run version. Prevent half-refreshed dashboard results and double counting. Document the refresh window and recompute dates affected by status changes.

Run one designated scheduler, not a job on every ASG instance. Document and test restart/re-run when its host fails. If caching is added, include period/run version in keys and show freshness.

Independently calculate tiny-fixture results. Test cancelled/refunded exclusion, historical price changes, zero sales, partial history, date boundaries, exact flag threshold and repeat-run idempotency. Add actual commands/results to analytics/README and evidence/test-data-ai.md.

Synthetic patterns do not prove commercial demand, seasonality or behaviour. Stockouts hide unmet demand; seven-day rates and fixed lead times simplify reality. This informs a simulated stock review, not a validated forecast.

Optional RFM K-means begins only after required work passes. Evaluate cluster profiles/sizes, silhouette and stability; do not report classification accuracy without true labels. Omit if time or synthetic distributions do not support a meaningful result.
