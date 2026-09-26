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

## Included descriptive ML: explicit batch handoff

Each invocation retrains RFM K-means for one explicitly selected completed
`AnalyticsRun`, publishes one validated JSON export, then a separate explicit import
loads it. ML dependencies stay outside the web image. Saved-model inference,
scheduling, Lambda and a model registry are not implemented.

### Prerequisites and source association

Use the checked-out reviewed code as an ordinary user. The following Bash commands
run from the repository root; on Windows use the corresponding venv `Scripts/python.exe`
and environment-variable syntax. Keep virtual environments and outputs outside the
checkout. Use Python 3.13 with the pinned requirements:

```sh
python3.13 -m venv "$HOME/.venvs/inf2006-ml"
python3.13 -m venv "$HOME/.venvs/inf2006-web"
export ML_PY="$HOME/.venvs/inf2006-ml/bin/python"
export WEB_PY="$HOME/.venvs/inf2006-web/bin/python"
"$ML_PY" -m pip install -r analytics/requirements.txt
"$WEB_PY" -m pip install -r src/requirements.txt
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
install -d -m 700 "$HOME/inf2006-ml-output"
```

Configure `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER` and
`POSTGRES_PASSWORD` through protected environment/role-based credential delivery.
Never place a secret database URL in arguments; the batch trainer accepts no URL
argument. Use the approved read-only database role for training and the non-superuser
application role for import, both against the intended database. The loader also
needs normal Django settings (`DJANGO_ENV`, `DJANGO_SECRET_KEY`, allowed hosts).
For local PostgreSQL explicitly set `DJANGO_ENV=local` (TLS defaults to disabled).
Production defaults to `verify-full` and requires the approved `POSTGRES_SSLROOTCERT`
CA path through the [shared connection policy](../docs/AWS_INFRASTRUCTURE.md#database-runtime-preparation).
Production selects a DB-only Secrets Manager secret with `AWS_SECRET_ID`/`AWS_REGION` and role credentials; see the same handoff for its strict schema. Real RDS connectivity and IAM delivery verification remain separate readiness gates.

Provision a nonsecret UUID `ML_SOURCE_ID` once for the intended deployment/database
association and keep it in that environment's protected operational configuration.
Configure the expected value **independently** on the training and import endpoints;
do not copy it from an arbitrary export to make an import pass. A newly cloned or
recreated database gets a new association UUID. The export checks that UUID plus
PostgreSQL's actual database name and the selected run's namespace, cutoff, inventory
version and summary UUID at import. Namespace equality alone establishes no source
association. This is operator-declared traceability, not authentication: a clone with
identical run IDs, database name and mistakenly reused configuration cannot be
reliably distinguished. Use authorised database connections and custody of exports.
No credentials, hostnames or connection URLs enter the export.

### Select, train, inspect, import and verify

Migrate and populate the intended database with the existing application workflow
first. Use `refresh_analytics` with its explicit namespace/cutoff/inventory version
(see the reproduction below), or choose an existing completed run. List candidate
runs and deliberately select a UUID; there is no latest-run or newest-file default:

```sh
set -eu
"$WEB_PY" src/manage.py shell -c 'from reporting.models import AnalyticsRun; print(list(AnalyticsRun.objects.filter(status="completed").order_by("cutoff").values("id", "cutoff", "inventory__namespace", "inventory__version", "summary_version")))'
export RUN_ID='<the selected completed run UUID>'
export BATCH_FILE="$HOME/inf2006-ml-output/$RUN_ID.json"
"$ML_PY" analytics/segment_customers.py --run-id "$RUN_ID" --output "$BATCH_FILE"
"$ML_PY" -c 'import json,os; p=json.load(open(os.environ["BATCH_FILE"])); print(json.dumps({k:v for k,v in p.items() if k not in ("rows", "segment_profiles")}, indent=2))'
"$WEB_PY" src/manage.py load_customer_segments --run-id "$RUN_ID" --input "$BATCH_FILE"
"$WEB_PY" src/manage.py shell -c 'import json,os; from reporting.models import CustomerSegment; p=json.load(open(os.environ["BATCH_FILE"])); q=CustomerSegment.objects.filter(run_id=os.environ["RUN_ID"], model_version=p["model_version"]); print({"run_id":os.environ["RUN_ID"], "model_version":p["model_version"], "expected":len(p["rows"]), "stored":q.count()}); assert q.count()==len(p["rows"])'
```

Run this sequence in a fail-fast shell (`set -eu` above); stop after any failed
stage. In PowerShell check `$LASTEXITCODE` after each native Python command and
throw on nonzero. A failed training request can leave an older valid file at that
path: do not continue into import automatically. The inspection command displays
metadata only; the producer and loader perform contract/checksum validation.

For separate endpoints, transfer that exact completed file using the approved secure
transfer mechanism and set `BATCH_FILE` to its explicit destination. Load credentials
for each role from the appropriate protected environment before its command; never
reuse training credentials with elevated permissions merely to make import work.
Keep the completed export and command receipt in the authorised output location.
Do not commit customer assignment exports. The loader prints run, model version and
batch ID; inspect those against the selected file and operator record.

The trainer derives namespace and cutoff from the completed run. It uses lifetime
completed-order RFM as model inputs log1p recency, log1p frequency and log1p average order
value (default `log_rfm_aov` since 26 September 2026, review M-03), valid-silhouette k=2..4
selection (ties favour smaller k), deterministic seed/profile labels, and seed ARI.
Fitting uses the complete cohort; scoring samples at most 5,000 customers. Existing
`--preprocessing`, `--min-k`, `--max-k` and `--seed` options remain explicit and enter
configuration identity; batch candidate bounds stay within 2..4. `--model-version`
on either command is an optional equality assertion, never an arbitrary label.

The completed envelope records feature/preprocessing schema, selection/seeds,
selected k, Python/dependency versions and SHA-256 hashes of the producer, shared
contract and pinned analytics requirements. `model_version` hashes that training
configuration/provenance; it identifies a recipe, not a saved fitted model.
`batch_id` hashes the complete meaningful payload (including assignments, profiles,
source/run and training metadata), excluding only `generated_at` and `batch_id`
itself. Canonical JSON sorts object keys, ignores formatting, normalizes equivalent
JSON numbers and retains array order. Same meaningful output has the same batch ID;
changed features/results have a different batch ID even under the same recipe.
These hashes detect accidental mismatch, not authenticity or correct original RFM.

### Retry and recovery

Training or validation failure returns nonzero before publication. The trainer
writes a temporary sibling, flushes/fsyncs it, and uses atomic replacement only after
shared validation; an interrupted write or failed replacement leaves the old export.
A leftover `.rfm-*.tmp` after abrupt process termination is incomplete and must never
be imported. Rerun training with the same explicit run/output after correcting the
reported configuration/source/training problem. No feasible clustering candidate
means no completed new export; do not relabel an old file to the new run.

If import fails or its acknowledgement is uncertain, keep the valid completed file
and retry **only import**:

```sh
"$WEB_PY" src/manage.py load_customer_segments --run-id "$RUN_ID" --input "$BATCH_FILE"
```

Reusing a retained older completed export after a failed training attempt is a
deliberate recovery decision, not success of that training attempt. Inspect its run,
source, version and batch ID before taking this retry path.

A valid same-run/model import replaces the full set atomically under a run lock;
replay creates no duplicates, and different valid output for the same recipe can
replace it. Invalid input leaves existing assignments intact. If the current
eligible customer cohort changed, regenerate for that selected run and import the
new completed file. Do not edit IDs, run/version metadata or checksum to bypass
rejection. Legacy pre-envelope exports are rejected; regenerate them. Existing
stored assignments remain until an explicitly valid replacement or run deletion.

The source is mutable: exact current eligible-ID coverage is rechecked at import,
but submitted RFM values are not independently recomputed or proven historical.
Same-ID feature drift can remain undetected. No immutable source/feature snapshot
or persistent batch registry is added. Save the export for provenance; the existing
table retains run and model version only. Post-load source/role changes do not update
assignments automatically. A new analytics refresh has no assignments until its own
explicit train/import; old segments are never silently attached to it. Pending,
failed/stale lifecycle UX and clearer lifetime-period frontend copy remain deferred.
Results describe synthetic history and do not predict loyalty, churn or real demand.

## ML quality evaluation

The application's baseline is the derived shoe dataset. It was trained, loaded and evaluated
on 26 September 2026 ([shoe rerun](../evidence/test-data-ai.md#shoe-dataset-rerun--26-september-2026),
[M-03 feature fix](../evidence/test-data-ai.md#feature-fix-m-03), [hold-out](#hold-out-and-subsample-evaluation)).
The accepted raw v1.0.0 revision was evaluated earlier, on 25 September 2026; its versionable
[aggregate artifact](../evidence/ml-quality-evaluation.json) contains no customer
assignments. [Executed checks and commands](../evidence/test-data-ai.md#ml-quality-evaluation-25-september-2026)
record actual environments and limitations. The production image remains free of ML packages.

Use an isolated PostgreSQL database and a separate environment with both pinned
`src/requirements.txt` and `analytics/requirements.txt`. Supply database credentials
through environment variables; never embed them in commands. Set `PYTHONPATH` to
`src;tests` on Windows or `src:tests` on Linux, and use `DJANGO_ENV=local` plus the
normal Django secret/allowed-host configuration. Configure the independently assigned
`ML_SOURCE_ID` as above before export/import. Migrate, then reproduce the shoe baseline.
The import goes into `settings.DEMO_NAMESPACE` (`synthetic/shoes/revision-a/demo/v1`), the
namespace the dashboard reads; `--as-of` matching the import cutoff lets the refresh select
the importer's sealed inventory without naming it:

```sh
python analytics/build_shoe_dataset.py
python src/manage.py import_dataset --source data/derived/shoes --namespace synthetic/shoes/revision-a/demo/v1
python src/manage.py refresh_analytics --as-of 2026-01-02
python analytics/segment_customers.py --run-id <NEW_RUN_UUID> --output <TEMP_ASSIGNMENTS_JSON>
python src/manage.py load_customer_segments --run-id <NEW_RUN_UUID> --input <TEMP_ASSIGNMENTS_JSON>
python analytics/evaluate_holdout.py --run-id <NEW_RUN_UUID> --output evidence/ml-holdout-evaluation.json
```

Historical raw-revision evaluation only: `evaluate_segments.py` checks the raw v1.0.0 file
hashes, so it runs against the original 1,200-product import in its own namespace, not the
shoe baseline:

```sh
python src/manage.py import_dataset --source data/raw --namespace synthetic/revision-a/demo/v1
python src/manage.py refresh_analytics --as-of 2026-01-02 --namespace synthetic/revision-a/demo/v1 --inventory-version <IMPORTER_REPORTED_VERSION>
python analytics/evaluate_segments.py --run-id <RAW_RUN_UUID> --source data/raw --output evidence/ml-quality-evaluation.json
```

Set `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS` to 1 for this
reproduction. `--preprocessing baseline` retains raw frequency; `log_frequency` adds only
log1p frequency. Both keep raw recency and log1p total spend. On the raw revision the
comparison below supported `log_frequency` over the baseline. The default is now
`log_rfm_aov`: log1p recency, log1p frequency and log1p average order value (total spend
divided by orders), so purchase volume is not counted twice (review M-03). On the shoe
dataset it cut frequency/value correlation from 0.68 to 0.16 and passed criteria fixed in
advance; see [evidence/test-data-ai.md](../evidence/test-data-ai.md#feature-fix-m-03). Stored
rows and dashboard profiles still show lifetime recency, orders and spend. k is still
selected, not forced. Seed stability does not establish resampling robustness;
the hold-out evaluation below adds that check.

### Hold-out and subsample evaluation

`evaluate_holdout.py` answers review findings M-02 and M-05 without changing the published
recipe (it reuses the trainer's functions). For a completed run with cutoff T it segments
customers using only orders before T − 90 days, then reports each segment's repurchase rate,
lift and spend in [T − 90 days, T). It also refits k=2..4 on 20 random 80% subsamples and reports
mean/minimum ARI against the published labels. Output is aggregate JSON with no customer rows.
Same environment and credentials as above:

```sh
python analytics/evaluate_holdout.py --run-id <RUN_UUID> --output evidence/ml-holdout-evaluation.json
```

Options: `--holdout-days` (1..365, default 90), `--repeats` (1..200, default 20) and
`--preprocessing` (default `log_rfm_aov`), which also reports each recipe's input skew and
correlation. Pure tests:
`analytics/tests/test_evaluate_holdout.py`. The 26 September shoe-dataset result is in
[evidence/test-data-ai.md](../evidence/test-data-ai.md#hold-out-and-subsample-evaluation-m-02-m-05).

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
`POSTGRES_PASSWORD`, `POSTGRES_HOST`, optional `POSTGRES_PORT` (5432), and `POSTGRES_SSLROOTCERT`, or an explicit local `--database-url`. Production refuses URLs and reads its DB-only Secrets Manager secret. Production is the default and requires `verify-full` TLS and a readable CA bundle even for DSNs. Set `DJANGO_ENV=local` explicitly for local PostgreSQL without TLS. Keep secrets
in the environment. The verifier imports no Django or application business code.
It reads raw tables and checks exactly one completed run and sealed inventory;
production daily rows and the JSON export are comparison targets only. Missing or
mismatched targets, invalid runs/inventory/configuration and discrepancies exit non-zero.
A successful comparison exits 0 and prints a JSON summary without customer fields.

For historical imports always pass the importer-reported namespace, cutoff and
inventory version to refresh. Do not run snapshot_inventory to backdate live stock.
Run IDs in the evidence identify a removed disposable database; reproduce import
and refresh to obtain new IDs. Tests live in `analytics/tests/` for this verifier, the segmentation script, the SQL/export/import
contract, startup credential delivery and `build_shoe_dataset.py`, outside ordinary web tests because pandas is intentionally
absent from the web image. The shoe-dataset tests need no pandas: from `src/`, run
`docker compose run --rm -v "$PWD/../analytics:/app/analytics:ro" web python -m pytest /app/analytics/tests/test_build_shoe_dataset.py`.
The evidence gives the combined 410-test invocation using the built `/app` settings.

Independent Astra Medium round-1 review is **CLEAR**. Phase 3 is complete locally;
all task scratch resources were removed after review. Nothing was committed or pushed.
