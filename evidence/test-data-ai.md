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
