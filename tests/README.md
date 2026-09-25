# Automated tests

pytest with pytest-django against real PostgreSQL (an isolated test database that pytest creates and drops; no SQLite substitute). Tests are mounted read-only at `/app/tests`. 392 tests passed in a local Docker run on 25 September 2026 (after the test trim on `f72a872`, see [../docs/reviews/test-trim.md](../docs/reviews/test-trim.md)); re-run before quoting a number. Run from the repository root after the Docker quickstart in [../src/README.md](../src/README.md):

```powershell
docker compose run --rm web pytest -q -p no:cacheprovider /app/tests
docker compose run --rm web pytest -q -p no:cacheprovider /app/tests/test_cart.py   # one module
```

The image copies `src/` at build time and only `tests/` is mounted, so run `docker compose build web` after changing application code, or the tests run against stale code.

| Module | Covers |
|---|---|
| `test_settings.py`, `test_schema.py` | Configuration failure cases, production cookie/TLS/HSTS defaults, the image's RDS certificate bundle, non-superuser database role; schema constraints and triggers |
| `test_health.py`, `test_db_unavailable.py`, `test_request_logging.py` | Liveness, the database-unavailable 503, JSON request logs and secret redaction |
| `test_accounts.py`, `test_catalogue.py` | Registration, login, logout, safe redirects; catalogue, operator toggle, `seed_demo` |
| `test_cart.py`, `test_orders.py` | Cart rules and HTMX contract; checkout, idempotency, history, and real-thread concurrency tests |
| `test_security_negative.py` | CSRF, anonymous access, forged fields and quantity manipulation across every mutation |
| `test_analytics_ranges.py`, `test_analytics_view.py`, `test_analytics_refresh.py`, `test_analytics_snapshot.py`, `test_analytics_queries.py` | Date ranges, the SQL view, refresh and locking, inventory snapshots, dashboard queries |
| `test_analytics_dashboard.py` | The `/analytics/` view: permissions, HTMX fragment, context, and the optional segment panel |
| `test_customer_segments_command.py` | The `load_customer_segments` command |
| `test_aws_capability_check.py` | The read-only AWS lab probe (`src/tools/aws_capability_check.py`), run against a fake CLI; nothing is contacted |
| `test_import.py` | Dataset import, replay, conflicts, date shifts, sealed inventory |
| `test_frontend.py` | Presentation pages, including the statistics preview |

`analytics/tests/` holds seven tests: four for the independent pandas verifier (`test_verify_refresh.py`) and three for the offline segmentation script (`test_segment_customers.py`). They need pandas and, for segmentation, scikit-learn, and run outside the web image (see [../analytics/README.md](../analytics/README.md)). `db_helpers.py` and `analytics_helpers.py` are shared builders, not tests.

Locking and concurrency tests use real independent connections. A passing suite is not by itself a functional or security claim; record the command, date and outcome in the files under [../evidence/](../evidence/README.md). No load, scaling or AWS test exists yet.
