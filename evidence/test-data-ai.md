# Data/analytics validation — 22 September 2026

Phase 3 on `CL/Analytics`, clean starting base `4704cc89c3a70af4d82a91d3543aff999fcff28d`.
Review status: [independent review log](../docs/reviews/analytics-phase3.md).
No production reporting code, model or migration changes were needed. No commit/push.

## Actual execution

New disposable Compose project `inf2006-phase3-verify`, PostgreSQL 17 and pinned Python
3.13 application image; separate pandas environment in task container. No shared DB
or previous reviewer scratch DB used. Namespace:
`synthetic/analytics-engineering/historical/phase3-v1`; seed 42, no date shift.
Importer-created sealed inventory ID 1:
`import-v1-9884d29e2bf9a64778c63858230ebd71223569b293c28c8acb895b1920e10d0f`.
Cutoff `2026-01-02T00:00:00+08:00`; no live snapshot created/substituted.

Import created 20,000 users/profiles, 1,200 products, 100,000 orders, 237,537 lines,
one version and 1,200 snapshots, with zero rejects. Wall time including container
startup: 26.02s. Full history has 89,114 completed orders and 212,030 completed lines;
the reporting window is narrower.

| Result | Actual |
|---|---|
| First refresh run | `2a40f855-c5e5-4982-821d-ca826891b35f` |
| Second/latest run | `986aca11-9ea5-44fc-a2e9-070a82c9ae70` |
| Latest summary version | `aee61f0d-21db-4ed7-9b31-650e84d5b38c` |
| Business dates | 2025-01-01 through 2026-01-01 inclusive |
| Completed orders / lines considered | 29,898 / 71,079 |
| Expected / persisted daily rows | 65,589 / 65,589 |
| Window units / sales amount | 98,185 / 18,732,854.98 |
| Daily-row / units / monetary mismatches | 0 / 0 / 0 |
| Coverage/flag mismatches | 0 |
| Insufficient-history products | 0 |
| No-recent-sales products | 431 of 1,200 (35.92%) |
| Flagged products | 307 |
| Maximum absolute monetary difference | 0.00 |
| pandas result | PASS, exit 0 |
| Refresh durations | 1.5s then 1.6s |
| Verifier wall time, including docker exec | 7.76s |

Ordered daily tuples and all 1,200 coverage rows were exactly equal across both runs.
Each run contained 65,589 daily rows; selecting one run gave no double-counting.

## Reproduction

PowerShell from repository root after standard local secret setup. Use a new disposable
project name if this one exists. Substitute newly printed run IDs on repetition.

```powershell
docker compose -p inf2006-phase3-verify up --wait --wait-timeout 90 db
docker compose -p inf2006-phase3-verify build web
docker compose -p inf2006-phase3-verify run --rm --no-deps migrate
docker compose -p inf2006-phase3-verify run --rm --no-deps web python manage.py import_dataset --source /app/data/raw --namespace synthetic/analytics-engineering/historical/phase3-v1
docker compose -p inf2006-phase3-verify run --rm --no-deps web python manage.py refresh_analytics --namespace synthetic/analytics-engineering/historical/phase3-v1 --as-of 2026-01-02 --inventory-version import-v1-9884d29e2bf9a64778c63858230ebd71223569b293c28c8acb895b1920e10d0f
# Executed the identical refresh command a second time.
docker compose -p inf2006-phase3-verify run -d --no-deps --name inf2006-phase3-runner --user 0 --volume "${PWD}:/work:ro" web sleep infinity
docker exec inf2006-phase3-runner sh -c 'python -m venv --system-site-packages /tmp/analytics-env && /tmp/analytics-env/bin/pip install -r /work/analytics/requirements.txt'
docker exec inf2006-phase3-runner /tmp/analytics-env/bin/python /work/analytics/export_coverage.py --run-id 986aca11-9ea5-44fc-a2e9-070a82c9ae70 --output /tmp/coverage.json
docker exec inf2006-phase3-runner /tmp/analytics-env/bin/python /work/analytics/verify_refresh.py --run-id 986aca11-9ea5-44fc-a2e9-070a82c9ae70 --coverage-target /tmp/coverage.json
```

Repeat equality was asserted through `manage.py shell` in that project:

```python
from reporting.models import AnalyticsRun, DailyProductSales
from reporting.queries import coverage
ids = ['2a40f855-c5e5-4982-821d-ca826891b35f', '986aca11-9ea5-44fc-a2e9-070a82c9ae70']
runs = [AnalyticsRun.objects.get(pk=key) for key in ids]
rows = [list(DailyProductSales.objects.filter(run=run).order_by('business_date', 'product_id')
    .values_list('business_date', 'product_id', 'units', 'sales_amount')) for run in runs]
assert rows[0] == rows[1]
assert coverage(runs[0]) == coverage(runs[1])
```

The export helper calls the production query solely to capture a comparison target.
The verifier imports no Django/application code and reads no reporting view. Raw
parameterized SELECTs feed independent pandas dates/status selection, historical
line-price Decimal sums, a seven-date zero-filled calculation and sealed inventory.
Daily summaries are comparison targets only. Target run/version metadata must match.

## Checks

- Focused verifier: **4 passed in 1.29s**, including deliberate one-cent mismatch exit 1.
- Existing ranges, refresh, snapshot, queries, SQL view and import: **176 passed in 4.96s**.
- Full combined application/verifier suite: **410 passed in 14.52s**.
- Django system check: no issues. Migration drift: no changes.
- Profile reproduced exactly, SHA-256 `367fd85353565c1f86366464d8b5c091b138e0d7386957c0140205da114d5d5b`.
  All six raw CSV checksums matched.

```powershell
docker exec -e PYTHONPATH=/work/src inf2006-phase3-runner /tmp/analytics-env/bin/python -m pytest -c /work/src/pytest.ini -q -p no:cacheprovider /work/analytics/tests/test_verify_refresh.py
docker exec -e PYTHONPATH=/work/src inf2006-phase3-runner /tmp/analytics-env/bin/python -m pytest -c /work/src/pytest.ini -q -p no:cacheprovider /work/tests/test_analytics_ranges.py /work/tests/test_analytics_refresh.py /work/tests/test_analytics_snapshot.py /work/tests/test_analytics_queries.py /work/tests/test_analytics_view.py /work/tests/test_import.py
docker exec -e PYTHONPATH=/app inf2006-phase3-runner /tmp/analytics-env/bin/python -m pytest -c /app/pytest.ini -q -p no:cacheprovider --tb=short /app/tests /work/analytics/tests
docker exec inf2006-phase3-runner python manage.py check
docker exec inf2006-phase3-runner python manage.py makemigrations --check --dry-run
docker exec inf2006-phase3-runner sh -c 'cp /work/analytics/profile_dataset.py /tmp/profile_dataset.py && mkdir -p /data && /tmp/analytics-env/bin/python /tmp/profile_dataset.py --source /work/data/raw && sha256sum /data/PROFILE.md /work/data/PROFILE.md && cd /work/data/raw && sha256sum -c checksums.txt'
git diff --check
```

Initial full-suite invocation used `/work/src` settings: 70 failed, 340 passed because
the mounted source lacked the collected static manifest. The corrected `/app` settings
command above passed, with no production fix. Independent tests live in analytics/tests;
the ordinary web image excludes pandas, so the combined command explicitly runs them.

## Limitations and attribution

Accepted synthetic descriptive demonstration only: weak weekly patterns, generated
stock/lead times, and substantial no-recent-sales coverage. No forecasting, meaningful
seasonality or commercial-demand validity claimed. Source USD numerics use the disclosed
SGD simulation convention without conversion; discounts/tax/shipping and refunded/cancelled
orders are excluded by contract. Partial history keeps denominator seven and unavailable
coverage; the existing query returns a numeric average for the future UI to hide.

No peak-memory measurement/cloud sizing, dashboard/browser, AWS/RDS/S3, scheduler
recovery, load generator or ML verification. Agent-run work is attributed to OpenAI
Codex, not human teammates. Cleanup and review outcome are recorded in the review log.

Final status: independent Astra Medium round-1 gate **CLEAR**, no actionable findings.
Task containers, PostgreSQL volume and network were removed after review; all three
project-label resource listings were empty. See the review log for commands and scope.

## ML quality evaluation 25 September 2026

Phase 3 ML quality starts at `529a0f9ee428af15524988dab2a2ccf74175b1b4` on
`erfan/analytics`. Review status and cleanup: [ML quality review](../docs/reviews/ml-quality-evaluation.md).
The versionable [aggregate artifact](ml-quality-evaluation.json) holds source hashes,
working-code hashes/diff identity, runtime versions, population/eligibility, exact
features, candidate metrics, profiles, selection and unrun experiments. No assignment
exports are retained in Git. This is agent-executed evidence, not teammate execution.

The 26 September integration rebase rewrote that starting commit (`529a0f9` maps to
`ab90415` in the [commit mapping](../docs/reviews/ml-upstream-integration.md#commit-mapping)),
so the artifact's `identity.git_head` no longer resolves here and its
`identity.working_files_sha256` no longer match the current files. The commits after it
changed only plumbing: Secrets Manager/TLS connection setup, the completed-batch envelope
in `src/reporting/segment_contract.py`, and the boto3 pins added to
`analytics/requirements.txt`. `feature_matrix`, `fit_candidates`, `fit_segments`,
`_segment_name_mapping` and `_stability_against_published` are untouched, as are the
numpy/pandas/scikit-learn/scipy pins, so the recorded metrics and selection still describe
the current model code. The artifact also predates the `selection.policy` field and still
carries the retired `rfm-kmeans-v2` label; recipe identity is now `rfm-v3-<sha256>`.
Regenerating it would refresh those identity fields without changing a measured value.

All six raw CSV SHA-256 values matched the accepted release in [data/README.md](../data/README.md).
The shoe remap is plan-only; a validated adopted revision needs fresh evaluation.
Task-only PostgreSQL 17 used `inf2006-phase3-20260925-db-1`, matching task network,
tmpfs storage and loopback port 57704. Existing containers, networks and volumes
were preserved. Credentials were generated only for this task, supplied through
environment and never included in commands/output. The database stays available
through independent review; its cleanup belongs in the review record.

The unchanged importer loaded 20,000 customers, 1,200 products, 100,000 orders and
237,537 lines with zero rejects. Inventory identity matched the manifest:
`import-v1-9884d29e2bf9a64778c63858230ebd71223569b293c28c8acb895b1920e10d0f`.
Run `bb3e4ce4-9485-47a3-94df-6d6e1cdac98c` completed 65,589 daily rows; fixed cutoff
`2026-01-02T00:00:00+08:00`, namespace `synthetic/revision-a/demo/v1`, no shift.
ML uses lifetime completed history, not that run's dashboard date window. Of 20,000
source customers, 19,766 qualified, 234 lacked a completed pre-cutoff order, and zero
were privileged. Included one-order customers: 1,099. No tenure normalization was
applied; this limitation is explicit. Source segment labels were neither inputs nor truth.

Measured skew: recency 1.411, frequency 0.591, monetary 0.851, log-monetary −1.454.
The one alternative changed raw frequency to log1p frequency (skew −0.417), leaving
raw recency and log1p monetary unchanged. All three features are standardized.
Frequency/log-monetary correlation 0.743 and negative log-monetary skew remain
limitations; no additional transforms were tested.

| Preprocessing | k | Sampled silhouette | Seed ARI mean | Cluster sizes |
|---|---:|---:|---:|---|
| Original baseline | 2 | 0.3885 | 0.9768 | 12,509 / 7,257 |
| Original baseline | 3 | 0.3333 | 0.9419 | 7,456 / 9,033 / 3,277 |
| Original baseline | 4 | 0.3176 | 0.7316 | 8,945 / 2,768 / 2,640 / 5,413 |
| Log frequency | 2 | 0.4347 | 0.9840 | 13,679 / 6,087 |
| Log frequency | 3 | 0.3360 | 0.9843 | 7,624 / 2,751 / 9,391 |
| Log frequency | 4 | 0.3497 | 0.7963 | 6,094 / 1,675 / 8,902 / 3,095 |

All six candidates were valid; no experiment failed. Fits use all customers; silhouette
uses the same seed-42 sample of 5,000 to bound pairwise memory. ARI compares published
seed 42 with 99, 123 and 777. Log-frequency k=2 improves sampled separation by 0.0462,
retains strong seed stability and substantial interpretable groups, supporting the
single preprocessing change for this revision. k remains selected by valid silhouette
(ties prefer smaller k), never forced to obtain a particular label. Resampling was
not run: chosen k=2 has strong seed stability and clear profiles; no resampling
robustness or predictive-performance claim is made.

Selected means: recent/more-orders/higher-spend group has recency 150.03 days,
frequency 5.45 and monetary 3,503.85; older/fewer-orders/lower-spend group has
415.94 days, 2.38 orders and 1,296.64. These are relative profile labels, not churn
or loyalty labels. Labels fit the existing 40-character field and plain template
rendering; alphabetical fallback serving order remains compatible. No frontend edit
or browser check occurred. Further dashboard lifetime-period copy remains deferred.

Executed host commands after configuring only the task database environment:

```powershell
.venv/Scripts/python.exe src/manage.py migrate --noinput
.venv/Scripts/python.exe src/manage.py import_dataset --source data/raw --namespace synthetic/revision-a/demo/v1
.venv/Scripts/python.exe src/manage.py refresh_analytics --as-of 2026-01-02 --namespace synthetic/revision-a/demo/v1 --inventory-version import-v1-9884d29e2bf9a64778c63858230ebd71223569b293c28c8acb895b1920e10d0f
.venv/Scripts/python.exe analytics/evaluate_segments.py --run-id bb3e4ce4-9485-47a3-94df-6d6e1cdac98c --source data/raw --output evidence/ml-quality-evaluation.json
.venv/Scripts/python.exe analytics/segment_customers.py --run-id bb3e4ce4-9485-47a3-94df-6d6e1cdac98c --output "$env:TEMP/inf2006-phase3-20260925/segments.json"
.venv/Scripts/python.exe src/manage.py load_customer_segments --run-id bb3e4ce4-9485-47a3-94df-6d6e1cdac98c --input "$env:TEMP/inf2006-phase3-20260925/segments.json" --model-version rfm-kmeans-v2
.venv/Scripts/python.exe -m pytest -q -c src/pytest.ini -p no:cacheprovider --tb=short analytics/tests/test_segment_customers.py analytics/tests/test_segment_loader_integration.py analytics/tests/test_verify_refresh.py tests/test_customer_segments_command.py
.venv/Scripts/python.exe src/manage.py check
.venv/Scripts/python.exe src/manage.py makemigrations --check --dry-run
git diff --check
```

Host Python 3.12.10 with pinned analytics libraries produced the aggregate artifact.
Full-cohort export and strict load succeeded: 19,766 v2 assignments, selected k=2,
silhouette 0.4347, seed ARI mean 0.9840/std 0.0111, lifetime sales S$55,821,834.61.
The initial focused host suite passed **60 tests in 15.75s**. Final source was also
tested in pinned Python 3.13 containers as follows; this separates runtime evidence
from the host training result. Django checks found no issues/migration drift and
whitespace validation passed.

Pure ML CI-equivalent command (no Django installed), **13 passed in 3.86s**:

```powershell
docker run --rm --mount "type=bind,source=$PWD,target=/work,readonly" --workdir /work -e PYTHONDONTWRITEBYTECODE=1 -e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 python:3.13-slim-bookworm@sha256:ed86c82274b3c69b52fb5820f358f0bd7df0b603332063cb5c6e32bd220c3e6e sh -c 'pip install -q -r analytics/requirements.txt pytest==9.1.1 iniconfig==2.3.0 packaging==26.3 pluggy==1.6.0 Pygments==2.21.0 && python -m pytest -q -c /dev/null -p no:cacheprovider analytics/tests/test_segment_customers.py'
```

Separate Django-dependent pinned-container command, **47 passed in 25.55s**:

```powershell
docker run --rm --mount "type=bind,source=$PWD,target=/work,readonly" --workdir /work -e PYTHONDONTWRITEBYTECODE=1 -e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 -e PYTHONPATH=/work/src:/work/tests -e DJANGO_ENV -e DJANGO_ALLOWED_HOSTS -e DJANGO_SECRET_KEY -e POSTGRES_DB -e POSTGRES_USER -e POSTGRES_PASSWORD -e POSTGRES_HOST=host.docker.internal -e POSTGRES_PORT python:3.13-slim-bookworm@sha256:ed86c82274b3c69b52fb5820f358f0bd7df0b603332063cb5c6e32bd220c3e6e sh -c 'pip install -q -r src/requirements.txt -r analytics/requirements.txt && python -m pytest -q -c /work/src/pytest.ini -p no:cacheprovider /work/analytics/tests/test_segment_loader_integration.py /work/analytics/tests/test_verify_refresh.py /work/tests/test_customer_segments_command.py'
```

The local integration equivalent supplies `/work/src` settings and `/work/tests`
helpers with host-database networking; hosted CI uses its built `/app` and Compose
database. All intended modules collected, no silent skips. Both ephemeral test
containers removed themselves. The production Dockerfile and requirements were
unchanged; ML libraries were installed only in disposable test environments.

No failed tests or experiments occurred. Initial read-only sandbox access to Docker
was denied; approved escalation permitted the task-only operations. Hosted Actions,
application image build, full suite, browser, resampling, predictive validation,
immutable snapshots, saved-model inference and AWS were not run. Prior source
acceptance and these geometric metrics do not establish real customer behaviour.

Independent review round 1 found MLQ-001: the producer allowed k=32,768 while the
strict loader accepts at most 32,767. The producer bound/message now match the
loader; the existing boundary regression rejects 32,768 without adding test cases.
The following host regression run passed **56 tests in 18.98s**:

```powershell
.venv/Scripts/python.exe -m pytest -q -c src/pytest.ini -p no:cacheprovider --tb=short analytics/tests/test_segment_customers.py analytics/tests/test_segment_loader_integration.py tests/test_customer_segments_command.py
```

The same aggregate-evaluation command above was rerun after this correction to
refresh code/diff identity; the bounded k=2..4 metrics and selection were unchanged.
The earlier pinned-container results precede this boundary-only correction; its
independent re-review status is owned by the review log.


## ML explicit batch handoff - 25 September 2026

Objective: verify explicit completed-run training, validated atomic file publication,
source-bound import and retry without retraining. This is a representative synthetic
fixture, not reevaluation of the accepted raw dataset or AWS evidence. Baseline
`d934859`; Phase 3 historical evidence above remains unchanged.

Task-only PostgreSQL 17 used project `inf2006-phase4-20260925`, loopback port 57705,
`phase4_ml` database, tmpfs storage and no named volume. The pre-existing stopped
`inf2006-ml-loader-db-1` was untouched. Task configuration and exports are under
`$env:TEMP/inf2006-phase4-20260925`; credentials are omitted. The source association
UUID was `a61f7944-0a1e-459d-95bc-df05fc8c1bb3`. Roles were separate:
`phase4_reader` had CONNECT, schema USAGE and table SELECT; non-superuser
`phase4_writer` additionally had INSERT/DELETE on `reporting_customersegment`,
UPDATE on `reporting_analyticsrun` for the run lock, and USAGE on the segment ID
sequence. The bootstrap owner was used only for fixture/migrations/tests.

Host commands (Python 3.12.10 project venv; source task env privately):

```powershell
. "$env:TEMP/inf2006-phase4-20260925/env.ps1"
$env:PYTHONPATH="$PWD/src;$PWD/tests"
docker compose -p inf2006-phase4-20260925 -f "$env:TEMP/inf2006-phase4-20260925/compose.yaml" up -d --wait db
.venv/Scripts/python src/manage.py migrate --noinput
.venv/Scripts/python -m pytest -q -c src/pytest.ini -p no:cacheprovider analytics/tests/test_segment_customers.py analytics/tests/test_segment_loader_integration.py analytics/tests/test_verify_refresh.py tests/test_customer_segments_command.py
.venv/Scripts/python src/manage.py check
.venv/Scripts/python src/manage.py makemigrations --check --dry-run
```

Final host result: **69 passed in 21.60s**, system check 0 issues, no migration drift.
The initial run omitted the test helper path and failed collection; the next found a
float/Decimal canonical-digest mismatch (68 passed, 1 failed). Central numeric
normalization fixed it; the existing real producer/import integration covers it.

The following compact fixture recipe retains the helper calls actually executed
across setup steps, consolidated for reproduction in a fresh isolated migrated DB.
Use `DJANGO_SETTINGS_MODULE=config.settings`, call `django.setup()` first, and keep
`PYTHONPATH=src;tests` (Windows) or `src:tests` (Linux):

```python
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.management import call_command
from analytics_helpers import make_products, make_inventory, add_order, NS
from reporting.models import AnalyticsRun
products = make_products()
inventory = make_inventory(products)
for i in range(18):
    user = get_user_model().objects.create_user(username=f"phase4-synthetic-{i}")
    for j in range(1 + i % 6):
        add_order(user, f"phase4-{i}-{j}", [(products["alpha"], 1, str(10 + i * 15))],
                  inventory.cutoff - timedelta(days=1 + (i * 7) % 90 + j))
call_command("refresh_analytics", as_of=date(2024, 3, 8), namespace=NS,
             inventory_version=inventory.version)
run = AnalyticsRun.objects.get(inventory=inventory, status="completed")
print(run.pk)
```

Setup-only failed attempts passed a string instead of `date` to `call_command`, then
a UTC calendar date instead of the intended Singapore date, and attempted to demote
PostgreSQL's bootstrap superuser (PostgreSQL refuses this). The explicit date above
and separate scoped roles corrected setup; existing task fixture rows were reused.
No application source workaround or shared database reset was used.

Actual completed run: `a3bf439d-addd-431a-a5fe-13336cdf52f3`; namespace
`synthetic/revision-a/historical/v1`; cutoff `2024-03-07T16:00:00+00:00`;
18 eligible customers, 63 orders/lines, 53 daily summary rows. Explicit CLI commands:

```powershell
$taskRun='a3bf439d-addd-431a-a5fe-13336cdf52f3'
$taskBatch="$env:TEMP/inf2006-phase4-20260925/batch.json"
. "$env:TEMP/inf2006-phase4-20260925/reader.ps1"
.venv/Scripts/python analytics/segment_customers.py --run-id $taskRun --output $taskBatch
if ($LASTEXITCODE -ne 0) { throw 'Training failed' }
. "$env:TEMP/inf2006-phase4-20260925/writer.ps1"
.venv/Scripts/python src/manage.py load_customer_segments --run-id $taskRun --input $taskBatch
if ($LASTEXITCODE -ne 0) { throw 'Import failed' }
```

Both exited 0. Selected k=2, silhouette 0.3452, seed ARI mean 0.7560/std 0.3451.
These small-fixture metrics establish execution only, not model quality.
Recipe version `rfm-v3-20fa169a9c83f602a22c902138bd1ea175cbcc1ff061416a8918a6c4c03ebc99`;
batch ID `ff25e94aff05691685a869bfc8846f3cc338624e3dc1b7a607ecf517bb5f44d1`.
Raw completed-file SHA-256
`907a996559a37d697afcc7eae1f435c8505eac0269fb9dc4ae8ee3ec8a2fa10a`.
The raw-file hash includes formatting/time and differs deliberately from batch ID.

Recovery commands actually run after the initial import:

```powershell
$priorHash=(Get-FileHash -LiteralPath $taskBatch -Algorithm SHA256).Hash
. "$env:TEMP/inf2006-phase4-20260925/reader.ps1"
.venv/Scripts/python analytics/segment_customers.py --run-id $taskRun --output $taskBatch --model-version arbitrary-version
if ($LASTEXITCODE -ne 1) { throw 'Expected training assertion failure' }
if ((Get-FileHash -LiteralPath $taskBatch -Algorithm SHA256).Hash -ne $priorHash) { throw 'Prior export changed' }
. "$env:TEMP/inf2006-phase4-20260925/writer.ps1"
$env:ML_SOURCE_ID='22222222-2222-2222-2222-222222222222'
.venv/Scripts/python src/manage.py load_customer_segments --run-id $taskRun --input $taskBatch
if ($LASTEXITCODE -ne 1) { throw 'Expected source refusal' }
$env:ML_SOURCE_ID='a61f7944-0a1e-459d-95bc-df05fc8c1bb3'
.venv/Scripts/python src/manage.py load_customer_segments --run-id $taskRun --input $taskBatch
if ($LASTEXITCODE -ne 0) { throw 'Retry failed' }
if ((Get-FileHash -LiteralPath $taskBatch -Algorithm SHA256).Hash -ne $priorHash) { throw 'Retry export changed' }
```

Expected failures returned sanitized generic diagnostics. Retry succeeded without
training; the file hash stayed unchanged throughout. ORM verification compared all
18 stored rows (ordered by customer ID) against `validate_rows` output and found exact
equality; the loader role's `pg_roles.rolsuper` was false. Existing focused tests
also verify rollback on database write failure, competing loaders, post-lock cohort
checks and previous-file retention on publication failure. No customer exports are
retained in Git.

Pinned Python 3.13 CI-equivalent checks use the exact image/dependency pins below,
an ordinary container UID, read-only checkout and task-only PostgreSQL. This is
local CI-equivalent execution, not a hosted Actions run:

```powershell
docker run --rm --user 1000:1000 --mount "type=bind,source=$PWD,target=/work,readonly" --workdir /work -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 -e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 python:3.13-slim-bookworm@sha256:ed86c82274b3c69b52fb5820f358f0bd7df0b603332063cb5c6e32bd220c3e6e sh -c 'python -m venv /tmp/ml && /tmp/ml/bin/pip install -q -r analytics/requirements.txt pytest==9.1.1 iniconfig==2.3.0 packaging==26.3 pluggy==1.6.0 Pygments==2.21.0 && /tmp/ml/bin/python -m pytest -q -c /dev/null -p no:cacheprovider analytics/tests/test_segment_customers.py'
docker run --rm --user 1000:1000 --network inf2006-phase4-20260925_default --env-file "$env:TEMP/inf2006-phase4-20260925/env.list" --mount "type=bind,source=$PWD,target=/work,readonly" --workdir /work -e HOME=/tmp -e PYTHONPATH=/work/src:/work/tests -e POSTGRES_HOST=db -e POSTGRES_PORT=5432 python:3.13-slim-bookworm@sha256:ed86c82274b3c69b52fb5820f358f0bd7df0b603332063cb5c6e32bd220c3e6e sh -c 'python -m venv /tmp/check && /tmp/check/bin/pip install -q -r src/requirements.txt -r analytics/requirements.txt && /tmp/check/bin/python -m pytest -q -c src/pytest.ini -p no:cacheprovider analytics/tests/test_segment_loader_integration.py analytics/tests/test_verify_refresh.py tests/test_customer_segments_command.py'
```

Pinned results: **16 pure ML passed in 10.35s** without Django; **53 PostgreSQL /
verifier / strict-loader passed in 14.56s**. Both containers exited 0. Full suite, hosted CI, production image
build, browser, AWS and accepted full-dataset reevaluation are unrun for this phase.
Independent review and resource cleanup are recorded in the coordinator review log.


### Phase 4 review remediation MLH-002

The independent reviewer identified the unused optional database URL branch in
`segment_customers.connect`. It was removed; all callers already use environment
configuration. No connection-policy change or other implementation cleanup was made.
After this code-provenance change, the same host focused command above passed
**69 tests in 24.53s**. Pinned checks were not repeated for this removal of an unused
branch; their earlier results remain separately recorded.

The representative CLI sequence was rerun with the same run and scoped roles,
writing a separate completed output so the earlier artifact could also be retried:

```powershell
. "$env:TEMP/inf2006-phase4-20260925/env.ps1"
$env:PYTHONPATH="$PWD/src;$PWD/tests"
$taskRun=Get-Content "$env:TEMP/inf2006-phase4-20260925/run-id.txt"
. "$env:TEMP/inf2006-phase4-20260925/reader.ps1"
.venv/Scripts/python analytics/segment_customers.py --run-id $taskRun --output "$env:TEMP/inf2006-phase4-20260925/batch-round2.json"
if ($LASTEXITCODE -ne 0) { throw 'Round2 training failed' }
. "$env:TEMP/inf2006-phase4-20260925/writer.ps1"
.venv/Scripts/python src/manage.py load_customer_segments --run-id $taskRun --input "$env:TEMP/inf2006-phase4-20260925/batch-round2.json"
if ($LASTEXITCODE -ne 0) { throw 'Round2 import failed' }
.venv/Scripts/python src/manage.py load_customer_segments --run-id $taskRun --input "$env:TEMP/inf2006-phase4-20260925/batch.json"
if ($LASTEXITCODE -ne 0) { throw 'Prior completed export retry failed' }
```

All commands exited 0; exact ordered ORM rows matched `validate_rows` for both
versions (18 assignments each). The new recipe identity is
`rfm-v3-16e61fd380746e428142177bdf724c8afe10eba28b25cb14f69c9944d3f9bbf7`,
batch ID `2dcd94e7426d17bf4eb19e6896ead6b06d3538ce1e43cf101345df2de589e606`,
and raw-file SHA-256
`990b876f2071347241c128902b7e659e9138555aa25b7a5a616b36e5a056eea8`.
The metrics and assignments were unchanged. The prior export retained its original
raw-file hash and remained retryable without matching the current producer recipe.
This verifies provenance separation and recovery, not additional model evaluation.


## Phase 6 accepted-data local integration — 25–26 September 2026

Objective: reproduce accepted input through completed analytics, isolated ML training/export, validated import and operator display, including failure/retry. Exact source/image hashes, commands, browser results and limitations are in [the Phase 6 release record](../docs/reviews/ml-local-release-readiness.md).

All six raw CSV SHA-256 values still match [the evaluation](ml-quality-evaluation.json). No derived shoe dataset is present; raw v1.0.0 remains the accepted revision. Retain the existing evaluation, with no training-policy change or new claim of immutable feature provenance. Any later accepted feature-changing shoe revision still requires reevaluation.

The isolated import accepted 20,000 customers, 1,200 products, 100,000 orders and 237,537 lines with zero rejects. Inventory is `import-v1-9884d29e2bf9a64778c63858230ebd71223569b293c28c8acb895b1920e10d0f`. Completed run `0d42256e-fc61-4410-b434-a04d6f74a8d8`, cutoff `2026-01-01T16:00:00Z`, published 65,589 daily rows from 71,079 lines. Independent raw-table/coverage verification: all mismatch counts zero, maximum money difference 0.00.

Pinned read-only-role training produced 19,766 assignments, k=2, silhouette 0.4347 and seed ARI 0.984; all assignments were imported. Recipe `rfm-v3-ef86b30f1c76ca4e093bd20319478e1fb8b88bb41dd70d046a79c931e3bdfd34`; completed batch ID `fade785eec25e49e2f87c800ee77353993c03e866a57aa3c692a3dbf582dc56a`; export SHA-256 `d0f6f363a633730311cb1dadeffd0a0b8521dae486de847ac5bcdd2522dd21be`. Customer exports remain outside Git. Metrics describe synthetic historical groups, not churn/prediction or real-customer behavior.

A nonexistent explicit training run failed without changing the valid export. The first import failed safely on output-file ownership; correcting ownership of that exact private file allowed retry without retraining. An altered source envelope with recomputed digest was rejected after assignments existed; all 19,766 persisted rows retained canonical digest `190c02aebccd6b4212715050eeabc4b4f17a6af53cb6d8efabe2e9e22823b60b`. Replaying the original exact file succeeded with the same digest.

Pinned pure ML: 16 passes; Django-dependent analytics/strict loader: 54 passes; standalone startup-credential checks: 2 passes. These overlap application tests and are not summed as unique cases. Hosted CI, load and actual S3/RDS/AWS execution remain unverified. The earlier evaluation remains historical quality evidence supported by unchanged data identity, not a newly rerun experiment.


## Shoe dataset rerun — 26 September 2026

Cases DATA-01 (rerun) and DATA-02. Plan and pass criteria were written before execution in
[docs/archive/plans/data-ml-evidence-rerun.md](../docs/archive/plans/data-ml-evidence-rerun.md). Source commit
`2698b05` (`erfan/merge-quarantine`); uncommitted catalogue-page edits in the working tree touch no
analytics, import or ML code. Agent-executed (Claude Code) on the user's machine, not teammate
execution. Raw output: `raw/DATA-01_2026-09-26_*.txt` and `raw/DATA-02_2026-09-26_*.txt`.

Why rerun: since the quarantine merge (`0442665`) the application imports `data/derived/shoes/`,
which recomputes line prices. Every earlier analytics/ML record above used `data/raw/`, so ML
monetary features and per-product analytics had not been checked on the data the site now uses.

Setup: `python analytics/build_shoe_dataset.py` (host Python 3.13.0) regenerated the derived
files; all five matched the committed `data/derived/shoes/checksums.txt`. Disposable Compose
project `inf2006-data-check` (own PostgreSQL 17 volume, app on port 8010); the everyday
`inf2006-foundation` database was not touched. A runner container from the same pinned Python
3.13.15 application image held a throwaway venv with `analytics/requirements.txt` (pandas 2.3.2,
scikit-learn 1.7.2) and a task-only `ML_SOURCE_ID`; thread counts pinned to 1.

### DATA-01 — PASS

Import of namespace `synthetic/shoes/data-check/v1`: 20,000 customers, 200 products (20 shoe
models), 100,000 orders, 237,537 lines, zero rejects; replay created nothing. Inventory
`import-v1-3e9692771fda3d5bf9ad09840c3dc403866948527925e7e639f81b0aa3c025e8`, cutoff
`2026-01-02T00:00:00+08:00`. Refresh run `a31587aa-83e1-458d-971c-ed1bc04730ea` wrote 41,345
daily rows from 71,079 completed lines (business dates 2025-01-01 to 2026-01-01) in 1.1s.

| Independent pandas check (`verify_refresh.py`) | Actual |
|---|---|
| Expected / persisted daily rows | 41,345 / 41,345 |
| Daily-row / units / sales-amount / coverage-flag mismatches | 0 / 0 / 0 / 0 |
| Maximum absolute monetary difference | 0.00 |
| No-recent-sales / flagged products | 9 / 80 of 200 |
| Result | PASS, exit 0 |

### DATA-02 — PASS

Tests: pure ML `analytics/tests/test_segment_customers.py` **16 passed**; loader integration,
verifier, startup credentials and `load_customer_segments` command **56 passed** (run against the
disposable database, both in the runner container).

Training on run `a31587aa…` (lifetime completed-order RFM before the cutoff, log1p frequency and
monetary, k chosen by silhouette over 2..4) exited 0:

| Result | Actual |
|---|---|
| Eligible customers segmented | 19,766 |
| Selected k | 2 |
| Sampled silhouette | 0.4118 |
| Seed ARI mean / std (seeds 99, 123, 777 vs 42) | 0.992 / 0.0076 |
| Recipe version | `rfm-v3-46605961b7d28863e1458b9f3a147c1d3eeeb2de7d2b694f6ba0147a80b6bd03` |
| Batch ID | `9cc521b3b16ee8b8ac6a82c5887354449d6398f8f3c05bc98b2f6fca495a2954` |
| `1_recent_more_orders_higher_spend` | 13,657 customers, 87.6% of sales, recency 149.85 d, 5.43 orders, S$9,971.10 |
| `2_older_fewer_orders_lower_spend` | 6,109 customers, 12.4% of sales, recency 415.38 d, 2.44 orders, S$3,147.70 |

Segment sales sum to S$155,404,646.85, equal to the importer's completed application-line total.
Strict import exited 0 with 19,766 rows; replaying the same file exited 0 without duplicates; an
ORM check found stored = exported = 19,766.

Dashboard: `/analytics/` reads only `settings.DEMO_NAMESPACE`, so the same import, refresh,
verification, training and load were repeated in `synthetic/shoes/revision-a/demo/v1` in the same
database. Run `0084a8ae-0189-4a2c-8b6d-a1debc53712d` again gave 41,345 rows with zero mismatches,
and training gave the identical recipe, k, silhouette and ARI (batch ID differs only because the
run differs). A task-only operator with `reporting.view_analytics` logged in over real HTTP
(CSRF login 302); `GET /analytics/` returned 200 and the "Customer segments" section showed that
run, the recipe version, 19,766 customers, K=2, silhouette 0.4118 and both segment profiles. The
customer sample table is cut from the saved output.

Compared with the raw-dataset evaluation above (k=2, silhouette 0.4347, ARI 0.984, similar group
sizes and recency/frequency), the shoe remap changes monetary values but not the selected
structure.

### Limitations

Local Docker only; no AWS, S3 or hosted CI. Training and import both used the Compose application
role, not separate read-only and writer roles. `evaluate_segments.py` was not run because it
accepts only the raw revision's checksums, so the six-candidate comparison table above was not
regenerated for shoes. The HTTP check reads rendered HTML; no visual browser review. Metrics
describe synthetic history, not churn, loyalty or real demand. Customer exports were kept inside
the disposable container and removed with it; nothing customer-level is in Git. Cleanup removed
the `inf2006-data-check` containers, network and volume; label listings were empty afterwards.

### Hold-out and subsample evaluation (M-02, M-05)

Answers findings M-02 and M-05 of [the Opus 5.5 review](../docs/archive/latest-opus5.5-review.md) with
the new `analytics/evaluate_holdout.py` ([plan](../docs/archive/plans/ml-holdout-evaluation.md)); the
published recipe and its version are unchanged. Fresh disposable project `inf2006-ml-holdout`,
same shoe import (zero rejects) and refresh run `b96fbfa2-5c89-433f-91aa-77e3cb7d4c01` (41,345
daily rows). Aggregate artifact: [ml-holdout-evaluation.json](ml-holdout-evaluation.json); raw
output: `raw/DATA-02_2026-09-26_holdout.txt`. Pure tests (pinned Python 3.13 container, no
Django): `test_segment_customers.py` plus `test_evaluate_holdout.py`, **19 passed**.

**Time split (M-02).** Segments were fitted with the published recipe on orders before
2025-10-04 00:00 SGT (cutoff − 90 days): 19,663 customers, k=2, silhouette 0.411. Outcomes are
completed orders from then to the cutoff; 103 customers who first ordered inside the window are
not scored.

| Segment at split | Customers | Repurchased in next 90 days | Lift | Mean orders | Mean spend | Share of window spend |
|---|---:|---:|---:|---:|---:|---:|
| `1_recent_more_orders_higher_spend` | 13,409 | 30.70% | 1.001 | 0.363 | S$637.30 | 68.2% |
| `2_older_fewer_orders_lower_spend` | 6,254 | 30.57% | 0.997 | 0.369 | S$637.51 | 31.8% |
| All segmented customers | 19,663 | 30.66% | — | — | — | — |

Result: **the segments do not predict later purchasing on this dataset.** Repurchase rate and
spend per customer are the same in both groups; the spend-share difference only reflects group
size. An ad hoc check in the same container confirmed this is the data, not the join: 6,028
matched repurchasers plus 103 new customers equal the 6,131 outcome rows, repurchase stays
between 29.4% and 31.7% across recency and frequency quartiles, and the correlation of past
frequency or recency with window orders is 0.00 and 0.01. The synthetic generator draws future
orders independently of past behaviour, so no RFM model could predict them here. The segments
remain valid descriptions of past behaviour (who bought recently, often and a lot), which is how
the dashboard presents them; they must not be used as a churn or targeting predictor on this data.

**Subsample stability (M-05).** 20 refits on random 80% subsamples of the 19,766-customer cohort,
ARI against the published seed-42 labels on the same customers:

| k | ARI mean | ARI minimum | ARI std |
|---:|---:|---:|---:|
| 2 (selected) | 0.9888 | 0.9705 | 0.0081 |
| 3 | 0.9723 | 0.9400 | 0.0154 |
| 4 | 0.5684 | 0.4041 | 0.2237 |

The selected k=2 is robust to resampling; k=4 is not, which the earlier seed-only check did not
show and which supports keeping k within 2..3.

At this point M-03 (raw recency, total spend) and M-04 (lifetime window, tenure) were unchanged;
M-03 was fixed afterwards (next section), M-04 remains a limitation. The artifact was then
regenerated from run `dfaf0076-…` for both recipes; its `log_frequency` figures equal those above. Cleanup removed the `inf2006-ml-holdout`
containers, network and volume; label listings were empty afterwards.

### Feature fix (M-03)

Answers finding M-03 ([plan](../docs/archive/plans/ml-feature-tenure-fix.md), criteria fixed before
running). New recipe `log_rfm_aov`: standardized log1p recency, log1p frequency and log1p average
order value (total spend ÷ orders) instead of raw recency and total spend. Stored rows and the
dashboard still show lifetime recency, orders and spend. The import contract
(`src/reporting/segment_contract.py`) accepts the new value; earlier exports still load. M-04
(tenure) is not changed and stays a limitation.

Fresh disposable project `inf2006-ml-m03` with the rebuilt application image; same shoe import
(zero rejects) and refresh run `dfaf0076-c239-49b4-8c39-71d136fb4e1f` (41,345 daily rows). Tests
(`raw/DATA-02_2026-09-26_m03-tests.txt`): pure ML **22 passed** in the pinned Python 3.13 container
without Django; loader integration, verifier, startup credentials and loader command **57 passed**,
including a new test that the loader accepts `log_rfm_aov` and rejects an unknown recipe; both
suites passed again after the default switch. Both recipes were evaluated identically with
`evaluate_holdout.py --preprocessing …` (`raw/DATA-02_2026-09-26_m03-comparison.txt`;
[ml-holdout-evaluation.json](ml-holdout-evaluation.json) now holds both results and the criteria).

| Measure (model inputs, full cohort of 19,766) | `log_frequency` (previous) | `log_rfm_aov` (adopted) |
|---|---:|---:|
| Recency input skew | 1.411 | −0.901 |
| Value input skew (total spend vs average order value) | −0.988 | −0.439 |
| Frequency–value correlation | 0.677 | 0.160 |
| Recency–frequency correlation | −0.462 | −0.359 |
| Valid candidates k=2..4 | 3/3 | 3/3 |
| Selected k | 2 | 2 |
| 80% subsample ARI mean / min at k=2 | 0.989 / 0.971 | 0.976 / 0.955 |
| Subsample ARI min at k=3 / k=4 | 0.940 / 0.404 | 0.888 / 0.951 |
| Smallest segment | 30.9% | 42.6% |
| Sampled silhouette (not comparable across recipes) | 0.412 | 0.274 |
| Hold-out repurchase lift range across segments | 0.997–1.001 (k=2) | 0.978–1.010 (k=4 at the split) |

Criteria: all candidates valid, subsample ARI minimum 0.955 ≥ 0.90, smallest segment 42.6% ≥ 5%,
so `log_rfm_aov` became the default. The overlap that made purchase volume count twice drops from
0.68 to 0.16 correlation, and recency is no longer the most skewed input. Lower silhouette is
expected: the inputs no longer contain two near-duplicate volume signals that are easy to
separate. At the hold-out split the recipe selected k=4; repurchase still did not differ by
segment (29.99%–30.98% against 30.66% overall), consistent with the finding above that this
synthetic data has no predictive signal. At k=4 two segments share the description
`recent_more_orders_higher_spend`; the rank prefix keeps labels unique, and the published k=2
labels are distinct.

Adopted recipe on the full cohort (`raw/DATA-02_2026-09-26_m03-train-load.txt`): recipe
`rfm-v3-5d6488c2ad0e8d681d4c625088cb08fa825eced3a4894cd4e460d8730448ea87`, batch
`0cd1f561ceba1c78e08142f31598c108109716963b28425d59e995788262d980`, k=2, silhouette 0.2743, seed
ARI 0.9976 / 0.0029.

| Segment | Customers | Share of sales | Mean recency (days) | Mean orders | Mean lifetime spend |
|---|---:|---:|---:|---:|---:|
| `1_recent_more_orders_higher_spend` | 11,338 | 77.5% | 121.24 | 5.73 | S$10,625.49 |
| `2_older_fewer_orders_lower_spend` | 8,428 | 22.5% | 380.81 | 2.87 | S$4,144.86 |

Strict import stored 19,766 rows (= export). A task-only operator logged in over real HTTP and
`GET /analytics/` returned 200 showing that run, the new recipe version, 19,766 customers, K=2,
silhouette 0.2743 and both segments (`raw/DATA-02_2026-09-26_m03-dashboard.txt`, customer sample
cut). The earlier DATA-02 records today describe the previous `log_frequency` recipe and remain as
history. Cleanup removed the `inf2006-ml-m03` containers, network and volume; label listings were
empty afterwards.
