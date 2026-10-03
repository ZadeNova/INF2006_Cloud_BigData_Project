# ML hold-out and subsample evaluation (review findings M-02, M-05)

Status: executed 26 September 2026; result in
`evidence/test-data-ai.md#hold-out-and-subsample-evaluation-m-02-m-05`. The segments showed no
repurchase difference (the synthetic data has none to find); k=2 subsample ARI 0.989.

## Why

[latest-opus5.5-review.md](../latest-opus5.5-review.md) found that the ML evidence only describes
cluster geometry. M-02: nothing shows the segments say anything about later behaviour, and the
rubric asks for "credible evaluation". M-05: "stability" only reruns other seeds on the same data;
refitting on subsamples is the stronger check and ANALYTICS.md allows seeds **or resamples**.

## Scope

New standalone script `analytics/evaluate_holdout.py`. It reuses `fetch_run`, `fetch_rfm`,
`feature_matrix`, `fit_candidates` and `fit_segments` from `segment_customers.py` unchanged, so
the published recipe and its `rfm-v3-<sha256>` version stay the same. It writes one aggregate
JSON (no customer rows) to `evidence/ml-holdout-evaluation.json`.

1. **Time-split check (M-02).** For a completed run with cutoff T, set T0 = T − 90 days
   (`--holdout-days`, default 90). Segment customers with the exact published recipe using only
   completed orders before T0. Then read each of those customers' completed orders in [T0, T)
   and report per segment: customers, repurchase rate (share with at least one order), mean
   orders, mean spend, share of window spend, and lift against the overall repurchase rate.
   Customers whose first order falls inside the window are counted but not scored.
2. **Subsample stability (M-05).** On the full cohort at T, for k = 2, 3, 4: fit the published
   seed-42 model, then refit on 20 random 80% subsamples and report mean, minimum and standard
   deviation of ARI against the published labels on the same customers.

Tests: `analytics/tests/test_evaluate_holdout.py`, pure (no Django or database), on small
synthetic frames: outcome aggregation per segment, exclusion of window-only customers, lift
arithmetic, and subsample ARI near 1 for well-separated clusters. Add the file to the pure ML
step in `.github/workflows/ci.yml`.

Docs: `analytics/README.md` (command), `evidence/test-data-ai.md` (executed result),
`evidence/README.md` (new DATA-02 row), `project_manifest.yaml` `data_ai.evaluation` (point at the
new artifact), and fix the stale ML sentence at `README.md:35`.

## Not in scope

- M-03 (raw recency, total spend) and M-04 (lifetime window, tenure bias) change the published
  model; they stay as recorded limitations. The time-split result is reported honestly either way.
- No change to `segment_customers.py`, the loader, the dashboard or the database.

## Run

Same disposable Compose method as [data-ml-evidence-rerun.md](data-ml-evidence-rerun.md): build
the shoe dataset, import, refresh at `2026-01-02`, run the script in the runner venv with pinned
threads, copy the aggregate JSON out, tear the project down.

## Pass criteria

Tests pass; the script exits 0 and writes valid JSON without customer IDs. The result is recorded
as measured; a weak or reversed repurchase pattern is reported, not tuned away.
