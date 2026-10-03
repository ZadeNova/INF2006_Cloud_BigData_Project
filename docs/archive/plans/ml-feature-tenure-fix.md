# ML feature fix (review finding M-03)

Status: executed 26 September 2026 (M-03 only; M-04 tenure stays a recorded limitation). `log_rfm_aov`
passed all criteria and is the default; results in `evidence/test-data-ai.md#feature-fix-m-03`.

## Finding

From [latest-opus5.5-review.md](../latest-opus5.5-review.md), M-03: recency is left raw (skew
1.41) and total spend correlates with order count (r=0.74), so purchase volume counts twice and
outweighs recency. Fix: log-transform recency, and use average order value instead of total spend.

## Design

New preprocessing option `log_rfm_aov` in `analytics/segment_customers.py`, from the same
per-customer query (no new data):

| Feature | Formula |
|---|---|
| Recency | `log1p(recency_days)` |
| Frequency | `log1p(frequency_orders)` |
| Average order value | `log1p(monetary_total / frequency_orders)` |

All three standardised, as now.

- Stored rows and dashboard profiles keep lifetime `recency_days`, `frequency_orders`,
  `monetary_total`; only the clustering inputs change. Segment names still describe lifetime
  profile means, which remain factual for each group. `FEATURE_SCHEMA` is unchanged; the recipe
  version changes automatically because it hashes configuration and code.
- `src/reporting/segment_contract.py` accepts the new preprocessing value; old exports still load.
- **Default switch criteria, fixed before running** (shoe dataset): all k=2..4 candidates valid;
  selected k has 80% subsample ARI minimum ≥ 0.90; smallest segment ≥ 5% of customers. If any
  fails, `log_frequency` stays default and the comparison and reason are recorded.
- Silhouette is not compared across recipes (different feature spaces). The comparison reports
  feature skew and correlation (the M-03 problem itself), plus stability, sizes, profiles and the
  hold-out result for both recipes.

## Changes

- `analytics/segment_customers.py`: `log_rfm_aov` in `feature_matrix` and CLI; default per criteria.
- `src/reporting/segment_contract.py`: accept `log_rfm_aov`.
- `analytics/evaluate_holdout.py`: `--preprocessing`, plus per-recipe feature skew/correlation.
- Tests: new-feature and contract tests; existing pure ML and loader suites rerun.
- Docs: `analytics/README.md`, dashboard segment copy if it names features, `docs/ANALYTICS.md` if it
  names features.
- Evidence (disposable project): evaluate both recipes; with the adopted default retrain, load and
  check `/analytics/`; update `ml-holdout-evaluation.json`, `test-data-ai.md`, a new DATA-02 row.

## Not in scope

M-04 (lookback/tenure), loader or schema change, `evaluate_segments.py` (raw-dataset tool).
