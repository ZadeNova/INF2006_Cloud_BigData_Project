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
