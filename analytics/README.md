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
No peak-memory measurement/cloud-instance suitability claim is made; bulk-create
batching does not bound total importer memory. Measure on the selected cloud instance
before using it for the deployment import.

## Included descriptive ML: offline RFM K-means

ML stays outside the web image. ML uses an explicitly triggered batch workflow; saved-model inference is optional and unimplemented. EventBridge Scheduler and Lambda are not selected; local training/loading remain available. Train/evaluate offline here, then load assignments
into the app table keyed by analytics run and model version:

```powershell
docker compose run --rm --no-deps --user 0 --volume "${PWD}:/work" --workdir /work web sh -lc "python -m venv /tmp/analytics-env && /tmp/analytics-env/bin/pip install -q -r analytics/requirements.txt && /tmp/analytics-env/bin/python analytics/segment_customers.py --run-id <RUN_UUID> --output /work/analytics/segments.json --model-version rfm-kmeans-v2"
docker compose run --rm --volume "${PWD}\analytics:/work/analytics" web python manage.py load_customer_segments --run-id <RUN_UUID> --input /work/analytics/segments.json --model-version rfm-kmeans-v2
```

`segment_customers.py` reads lifetime completed orders strictly before the run cutoff, computes RFM,
scales raw recency/log1p frequency/log1p monetary, chooses k by silhouette on k=2..4,
checks stability by comparing each seed's labels against the published-label seed
(ARI mean/std), and writes JSON rows plus cluster profiles. The score uses a fixed
sample of at most 5,000 customers; fitting uses all customers. Segment names describe
relative recency/order-count/spend profile means, without churn or loyalty claims.
The dashboard shows a segment panel only when assignments exist
for the selected run.

Segment exports cover completed-order owners in the run namespace before its cutoff, excluding staff, superusers and `store_operator` members. Ordinary local shoppers need no imported profile. The loader requires matching run/model metadata and the complete current eligible cohort; regenerate when eligibility has changed. Invalid files preserve prior assignments, and same-version reruns replace atomically. `--model-version` confirms the file version rather than changing it. See [import safety contract](../docs/ANALYTICS.md#segment-import-safety-contract).

Results are descriptive on synthetic data and may reflect generator structure instead
of real customer behavior. Treat this panel as descriptive operational guidance, not a
predictive model.

## ML quality evaluation

The accepted raw v1.0.0 revision was evaluated on 25 September 2026; the shoe remap
remains a plan and needs evaluation after validated adoption. The versionable
[aggregate artifact](../evidence/ml-quality-evaluation.json) contains no customer
assignments. [Executed checks and commands](../evidence/test-data-ai.md#ml-quality-evaluation-25-september-2026)
record actual environments and limitations. The production image remains free of ML packages.

Use an isolated PostgreSQL database and a separate environment with both pinned
`src/requirements.txt` and `analytics/requirements.txt`. Supply database credentials
through environment variables; never embed them in commands. Set `PYTHONPATH` to
`src;tests` on Windows or `src:tests` on Linux, and use `DJANGO_ENV=local` plus the
normal Django secret/allowed-host configuration. Migrate, then reproduce:

```sh
python src/manage.py import_dataset --source data/raw --namespace synthetic/revision-a/demo/v1
python src/manage.py refresh_analytics --as-of 2026-01-02 --namespace synthetic/revision-a/demo/v1 --inventory-version import-v1-9884d29e2bf9a64778c63858230ebd71223569b293c28c8acb895b1920e10d0f
python analytics/evaluate_segments.py --run-id <NEW_RUN_UUID> --source data/raw --output evidence/ml-quality-evaluation.json
python analytics/segment_customers.py --run-id <NEW_RUN_UUID> --output <TEMP_ASSIGNMENTS_JSON> --model-version rfm-kmeans-v2
python src/manage.py load_customer_segments --run-id <NEW_RUN_UUID> --input <TEMP_ASSIGNMENTS_JSON> --model-version rfm-kmeans-v2
```

Set `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS` to 1 for this
reproduction. `--preprocessing baseline` retains raw frequency; default
`log_frequency` adds only log1p frequency, preserving lifetime RFM semantics. Both
retain log1p monetary. The measured comparison supports v2: k=2 has higher sampled
separation, similarly strong seed ARI and substantial interpretable groups. k is
still selected, not forced. Seed stability does not establish resampling robustness;
no resampling or predictive experiment was needed for this bounded descriptive claim.

Pure ML tests must run in an environment with analytics dependencies and pinned
pytest, without Django. PostgreSQL-dependent tests need application dependencies,
settings and test helpers; no collection skips are used:

```sh
# Pure environment (Linux; CI uses pinned Python 3.13 container)
python -m pytest -q -c /dev/null -p no:cacheprovider analytics/tests/test_segment_customers.py
# Combined application/analytics environment, configured isolated PostgreSQL
python -m pytest -q -c src/pytest.ini -p no:cacheprovider analytics/tests/test_segment_loader_integration.py analytics/tests/test_verify_refresh.py tests/test_customer_segments_command.py
```

The [dedicated CI job](../.github/workflows/ci.yml) supplies all exact runtime/test
dependency pins, uses separate pure and Django environments and cleans only its
own Compose database. Hosted CI, AWS and frontend validation remain separate claims.

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
and refresh to obtain new IDs. Tests live in `analytics/tests/` for this verifier, the segmentation script and the SQL/export/import contract,
outside ordinary web tests because pandas is intentionally absent from the web image.
The evidence gives the combined 410-test invocation using the built `/app` settings.

Independent Astra Medium round-1 review is **CLEAR**. Phase 3 is complete locally;
all task scratch resources were removed after review. Nothing was committed or pushed.
