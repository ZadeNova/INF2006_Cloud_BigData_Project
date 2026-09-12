# Foundation batch 4 and final local verification

12 September 2026. Base dd10f3a. Docker Desktop Linux containers on Windows; Python 3.13.15, Django 5.2.17, PostgreSQL 17.11. Only task-owned inf2006-foundation services were controlled. No AWS resources or business workflows were created.

## Automated checks

```powershell
docker compose -f src/compose.yaml config --quiet
docker compose -f src/compose.yaml build
docker compose -f src/compose.yaml run --rm web python manage.py check_database
docker compose -f src/compose.yaml run --rm web pytest -q -p no:cacheprovider /app/tests
```

Passed: Compose validation/build, database connectivity and applied migrations, 48 tests in 4.92s. [Raw pytest output](foundation-batch-4-output.txt). The eight added checks cover zero-query GET/HEAD health, no cookies, no-store JSON, database independence, unsafe-method rejection, invalid Host rejection, internal redirect exemption, sanitized database failure and pending-migration readiness (some assertions share tests). Earlier schema/config tests run in the same suite on fresh PostgreSQL test DBs.

## Live failure/recovery and persistence

Executed up -d --wait --wait-timeout 60 web; HTTP GET http://127.0.0.1:8000/health/ returned 200 with status ok and Docker reported web healthy. Read migration count using psql SELECT count(*) FROM django_migrations (21).

Executed docker compose -f src/compose.yaml stop db while leaving web running. HTTP health still returned 200. docker compose -f src/compose.yaml exec -T web python manage.py check_database exited nonzero with CommandError: Database unavailable. The failure contains no connection details. A finally block restarted db with up -d --wait --wait-timeout 60 db. The same readiness command then returned database ok/migrations applied.

Executed docker compose -f src/compose.yaml down (without --volumes), then up -d --wait --wait-timeout 60 web. Both containers became healthy; migration count remained 21 and check_database passed without reapplying migrations. This proves local schema metadata survives container replacement on the named volume; it is not an authenticated-user failover or cloud resilience test. Django check then reported no issues and makemigrations --check --dry-run reported no changes. [Sanitized runtime output](foundation-runtime-output.txt).

## Scope and handover

Backend foundation only: scaffold/dependency lock, Docker/PostgreSQL/environment settings, initial schema/migrations, liveness and operator readiness. DOC-001/002 contract and persistence corrections passed batch 3 independent review; DOC-003 was already corrected. End-to-end import-after-checkout and historical aggregation recomputation remain unrun until their follow-up features exist.

No authentication/catalogue/cart routes, base template/styling/HTMX, dataset acceptance/import, analytics command, Terraform/AWS deployment, scaling or TLS certificate proof. Reserved frontend paths/names/fields are in ../docs/API.md; reserved business names cannot yet be reversed. Current root URL intentionally returns 404.

Review gate: independent Astra Medium batch 4 review passed with no actionable findings. [Review record](../docs/reviews/foundation-batch-4.md). All four foundation batches pass; remaining Phase 1 work stays open. Local link targets in 14 changed Markdown files were checked with no missing targets, and staged diff whitespace checks passed.

Final cleanup: docker compose -f src/compose.yaml down succeeded after verification; the task-created web/db containers and network are stopped/removed, and the PostgreSQL named volume is retained. The user can restart with the documented quickstart. Docker-only environment initialization was also executed and preserved the existing .env.
