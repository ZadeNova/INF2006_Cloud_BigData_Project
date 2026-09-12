# Foundation tests

Run from repository root after the Docker quickstart in ../src/README.md:

```powershell
docker compose -f src/compose.yaml run --rm web pytest -q -p no:cacheprovider /app/tests/test_settings.py
```

Batch 2 verifies configuration failure cases, production cookie/TLS defaults and a real PostgreSQL non-superuser connection. pytest creates and drops its own test database. Tests are mounted read-only at /app/tests; no SQLite substitute. Other correctness/security/load suites remain pending. Actual evidence: ../evidence/foundation-batch-2.md.

Schema suite (real PostgreSQL, isolated test DB):

```powershell
docker compose -f src/compose.yaml run --rm web pytest -q -p no:cacheprovider /app/tests/test_schema.py /app/tests/test_settings.py
```

See ../evidence/foundation-batch-3.md. These are persistence/constraint tests, not checkout/import/analytics workflow evidence.

Full current foundation suite:

```powershell
docker compose -f src/compose.yaml run --rm web pytest -q -p no:cacheprovider /app/tests
```

Health/readiness and live Docker outage/recreation results: ../evidence/foundation-batch-4.md. No business workflow, frontend or AWS verification is implied.
