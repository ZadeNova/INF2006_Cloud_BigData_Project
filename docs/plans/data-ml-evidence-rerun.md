# DATA-01 / DATA-02 evidence rerun on the shoe dataset

Status: executed 26 September 2026, DATA-01 and DATA-02 PASS; results in
`evidence/test-data-ai.md#shoe-dataset-rerun--26-september-2026`. Verification and evidence only;
no application code change. Deviation: the dashboard reads only `settings.DEMO_NAMESPACE`, so the
pipeline was repeated in that namespace for the HTTP check.

## Why

`evidence/README.md` lists DATA-01 as "existing prior record; not rerun here" (2026-09-22) and
DATA-02 as PLANNED. All recorded analytics/ML runs used `data/raw/`. Since the quarantine merge
(`0442665`) the application imports the derived shoe dataset `data/derived/shoes/`, which recomputes
line prices. ML monetary features therefore change, and `evidence/test-data-ai.md` states a
feature-changing shoe revision needs fresh evaluation. The shoe refresh check in `data/README.md`
was never recorded as evidence.

## Scope

- DATA-01: import the shoe dataset, run `refresh_analytics`, then check it with the independent
  pandas verifier (`export_coverage.py` + `verify_refresh.py`).
- DATA-02: run the pinned ML test suites, train with `segment_customers.py` on the completed run,
  import with `load_customer_segments`, confirm stored count equals exported rows, and confirm the
  operator `/analytics/` page renders the "Customer segments" section for that run.
- Record results in `evidence/test-data-ai.md`, update the DATA-01/DATA-02 rows in
  `evidence/README.md`, and save raw output as `evidence/raw/DATA-0x_2026-09-26*.txt`.

Out of scope: `evaluate_segments.py` (hard-wired to the raw revision's checksums; changing it is a
code change), AWS, load testing, the uncommitted catalogue work in the tree.

## Method

1. Build the derived dataset on the host (`python analytics/build_shoe_dataset.py`, standard
   library) and check it against the committed `data/derived/shoes/checksums.txt`.
2. Disposable Compose project `inf2006-data-check` (own database volume, `APP_PORT=8010`), so the
   everyday `inf2006-foundation` database is untouched. Build, start db, migrate.
3. `import_dataset --source /app/data/derived/shoes` into a fresh namespace; record the reported
   inventory version. `refresh_analytics --as-of 2026-01-02` with that namespace/version.
4. Runner container from the same image with a throwaway venv holding `analytics/requirements.txt`
   (as in the 22 September reproduction). Run export/verify (DATA-01), then the ML tests, training,
   import and stored-count check (DATA-02), with a task-only `ML_SOURCE_ID` UUID.
5. Start `web` in that project, log in as a task-created operator and fetch `/analytics/` over HTTP,
   checking the segments section and recipe version; then a browser look if feasible.
6. Tear down only `inf2006-data-check` (`down --volumes --remove-orphans`).

Local simplification: training and import both use the Compose application role rather than
separate read-only/writer roles; recorded as a limitation.

## Pass criteria

- DATA-01: verifier exit 0 with zero daily/unit/amount/coverage mismatches.
- DATA-02: ML tests pass; training and import exit 0; stored rows = exported rows; dashboard shows
  the segments section for the run. Selected k, silhouette and seed ARI are recorded as descriptive
  metrics, not as a quality claim.
