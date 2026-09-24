# Dataset acceptance and import reproduction

Phase 1 uses independent pandas analysis in `profile_dataset.py`. The application
importer uses standard-library CSV/Decimal/dates; pandas and its pinned transitive
dependencies in `requirements.txt` are not in the web image. Source/mapping:
[data/README.md](../data/README.md), [dictionary](../data/DATA_DICTIONARY.md).

From the repository root, with a separate analytics environment:

```powershell
python -m venv .venv/analytics
.venv/analytics/Scripts/python -m pip install -r analytics/requirements.txt
.venv/analytics/Scripts/python analytics/profile_dataset.py --source data/raw
```

`--source` defaults to `data/raw`; output is always repository `data/PROFILE.md`.
Exit 0 means integrity checks pass; exit 1 means integrity failure. Neither the
exit code nor positive variance means the dataset is accepted. Before import, record
an explicit manual decision for the checksummed release in data/README.md, resolving
the planned flat-noise criterion against descriptive sales/inventory use. Variability
alone does not establish trend, seasonality or forecast quality.
No ML or K-means analysis is performed.
Customer-order distribution and recency diagnostics are deferred with optional ML.
No peak-memory measurement/cloud-instance suitability claim is made; bulk-create
batching does not bound total importer memory. Measure on the selected cloud instance
before using it for the deployment import.

## Executed verification, 22 September 2026

Review follow-up: the earlier overall acceptance PASS is superseded. Current profiler
exit status covers integrity only. On 22 September 2026 the user explicitly accepted
the checksummed release for descriptive sales/inventory use despite flat-noise risk
(DATA-003); this is not a forecasting or seasonality claim. DATA-001/002 fixes passed **25 focused tests in 1.79s** and **406 full-suite
tests in 13.68s** on fresh scratch PostgreSQL. Current generated profile SHA-256:
`367fd85353565c1f86366464d8b5c091b138e0d7386957c0140205da114d5d5b`.
Original verification below is retained as history; [review log](../docs/reviews/analytics-data-import.md)
owns review rounds and limitations. No further full-source import was run during remediation while the
manual acceptance decision was pending; the user has now supplied that decision.

Base `3deed85024e841bd9dccc99c1860ca379d5012bc`, branch `CL/Analytics`.
Isolated Compose project `inf2006-dataset-review`, freshly created PostgreSQL volume;
no shared database modified. Pinned Python 3.13/PostgreSQL 17 images. Host profiling
used Python 3.13.7/pandas 2.3.2 and was also reproduced in a disposable Compose
container with the pinned analytics dependencies:

```powershell
docker compose -p inf2006-dataset-review build web
docker compose -p inf2006-dataset-review up --wait --wait-timeout 90 db
docker compose -p inf2006-dataset-review run --rm --no-deps migrate
docker compose -p inf2006-dataset-review run --rm --no-deps --user 0 --volume "${PWD}:/work" --workdir /work web sh -c 'python -m venv /tmp/profile-env && /tmp/profile-env/bin/pip install -r analytics/requirements.txt && /tmp/profile-env/bin/python analytics/profile_dataset.py --source data/raw'
docker compose -p inf2006-dataset-review run --rm --no-deps web python manage.py import_dataset --source /app/data/raw --namespace synthetic/revision-a/demo/v1
# Same command again: every row unchanged
docker compose -p inf2006-dataset-review run --rm --no-deps web python manage.py import_dataset --source /app/data/raw --namespace synthetic/revision-a/demo/v1
docker compose -p inf2006-dataset-review run --rm --no-deps web pytest -q -p no:cacheprovider /app/tests/test_import.py
docker compose -p inf2006-dataset-review run --rm --no-deps web pytest -q -p no:cacheprovider /app/tests
docker compose -p inf2006-dataset-review run --rm --no-deps web python manage.py check
docker compose -p inf2006-dataset-review run --rm --no-deps web python manage.py makemigrations --check --dry-run
docker compose -p inf2006-dataset-review up --build -d --wait --wait-timeout 90 web
git diff --check
```

The temporary analytics venv disappears with its container; application requirements
are unchanged. [PROFILE.md](../data/PROFILE.md) was reviewed: exact counts, zero
integrity rejects, variable sales, weak weekly pattern and 31.67–39.75% of products
without completed sales in sampled seven-day windows.

| Database status | Orders | Lines | Application line total | Source order total |
|---|---:|---:|---:|---:|
| cancelled | 2,976 | 6,991 | 1,818,915.27 | 1,906,021.49 |
| completed | 89,114 | 212,030 | 55,821,834.61 | 58,393,630.56 |
| refunded (including partial) | 7,910 | 18,516 | 4,843,639.32 | 5,064,932.11 |

Independent standard-library CSV Decimal sums matched SQL `SUM(quantity * unit_price)`
per status. SQL compared every Order.total with its lines: **zero mismatches**.
Counts and the complete sealed 1,200-product inventory matched. Replay reported
created=0 and unchanged=20,000 users/profiles, 1,200 products, 100,000 orders,
237,537 items, one version and 1,200 snapshots.

Real HTTP spot-checks used `docker compose -p inf2006-dataset-review exec -T web python manage.py shell`
with urllib/cookies against Gunicorn. `GET /products/` returned 200 and all 12 expected
imported products on page one. A random password was deliberately set for imported
customer `C000001` only in scratch; a CSRF-protected `POST /login/` succeeded;
`/orders/` and the detail for external order `O0042269` returned 200 with expected
line products. No credentials were printed/saved. This checks actual HTTP rendering,
not browser visual layout.

Tests cover hand-checkable mappings/rounding, replay after real checkout and
credential/cart/session/product changes, late transaction rollback, source conflicts,
reject propagation, namespace isolation, date shifts/leap day/future refusal, seeded
stock, inventory sealing/replay and `seed_demo --no-products`. Final focused run:
**23 passed in 1.40s**; full suite: **404 passed in 14.12s**, including all 381 existing
tests. Django check reported no issues; migration drift check found no changes;
`git diff --check` passed. A further full-source replay preserved the deliberately
set scratch customer's password hash. All six raw checksums remained unchanged.
Repeated host/Compose profile Markdown SHA-256:
`9bfb9c8168f112581ce87bba7ec1057eb7ec301dd1ae3967729475f89e2a9835`.

Cleanup succeeded with `docker compose -p inf2006-dataset-review down --volumes --remove-orphans`:
only the task-created scratch containers, network and database volume were removed.

AI assistance: OpenAI Codex implemented the profiler/importer, tests/docs and ran local
checks. This does not attribute agent-run checks to human teammates. Independent
Astra Medium round-2 review is now CLEAR; dataset roadmap Phases 1–2 are complete locally.
The later review independently passed 406 tests and repeated full-source import/replay
and SQL reconciliation; see the review log for the exact snapshot and limitations. Real-data analytics refresh, dashboard, ML, S3/AWS, load testing
and visual browser QA were not run.

## Phase 3: independent refresh verification

Implemented locally on 22 September 2026; independent review status is in
[analytics-phase3.md](../docs/reviews/analytics-phase3.md). Exact commands, run IDs,
counts, timings and limitations are in [executed evidence](../evidence/test-data-ai.md).
Both full-data refreshes matched exactly. pandas found zero daily/monetary/coverage
mismatches; all 410 combined tests passed. No production reporting change was needed.

With application database environment variables configured, export the production
comparison target separately, then run the independent verifier:

```sh
python analytics/export_coverage.py --run-id <UUID> --output coverage.json
python analytics/verify_refresh.py --run-id <UUID> --coverage-target coverage.json
```

The exporter needs the application dependencies/settings; the verifier needs only
`analytics/requirements.txt`. It connects directly using `POSTGRES_DB`, `POSTGRES_USER`,
`POSTGRES_PASSWORD`, `POSTGRES_HOST`, optional `POSTGRES_PORT` (5432), and optional
`POSTGRES_SSLMODE`/`POSTGRES_SSLROOTCERT`, or an explicit `--database-url`. Keep secrets
in the environment. The verifier imports no Django or application business code.
It reads raw tables and checks exactly one completed run and sealed inventory;
production daily rows and the JSON export are comparison targets only. Missing or
mismatched targets, invalid runs/inventory/configuration and discrepancies exit non-zero.
A successful comparison exits 0 and prints a JSON summary without customer fields.

For historical imports always pass the importer-reported namespace, cutoff and
inventory version to refresh. Do not run snapshot_inventory to backdate live stock.
Run IDs in the evidence identify a removed disposable database; reproduce import
and refresh to obtain new IDs. Four independent tests live in `analytics/tests/`,
outside ordinary web tests because pandas is intentionally absent from the web image.
The evidence gives the combined 410-test invocation using the built `/app` settings.

Independent Astra Medium round-1 review is **CLEAR**. Phase 3 is complete locally;
all task scratch resources were removed after review. Nothing was committed or pushed.
