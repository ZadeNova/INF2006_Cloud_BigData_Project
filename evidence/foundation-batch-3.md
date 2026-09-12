# Foundation batch 3 verification

12 September 2026. Base b137d63. PostgreSQL 17.11 / Python 3.13.15 / Django 5.2.17 in the digest-pinned local Docker environment. Domain tables were initially empty; no dataset has been downloaded/imported and no business routes are implemented.

```powershell
docker compose -f src/compose.yaml build
docker compose -f src/compose.yaml run --rm web python manage.py check
docker compose -f src/compose.yaml run --rm web python manage.py migrate --noinput
docker compose -f src/compose.yaml run --rm web python manage.py makemigrations --check --dry-run
docker compose -f src/compose.yaml run --rm web pytest -q -p no:cacheprovider /app/tests/test_schema.py /app/tests/test_settings.py
```

Results: build/check passed; accounts/catalogue/cart/orders/reporting initial migrations and reporting inventory-guard migration applied successfully; no model drift. pytest built a fresh isolated PostgreSQL test database and passed 40 tests in 2.51s. [Raw pytest output](foundation-batch-3-output.txt).

Covered: nonnegative/finite prices including PostgreSQL numeric NaN; stock/lead time; source namespace uniqueness/immutability; one cart/line per owner/product and quantity bounds; user-scoped key uniqueness and live/historical order origins; historical price retention and protected references; cross-mode order-line rejection; immutable sealed snapshot rows/cutoff/membership; empty/misaligned inventory rejection; run cutoff alignment and versioned summary selection. Test fixtures use no working passwords or real personal data.

DOC-001 persistence check changes live Product stock/lead time and confirms stored historical inputs remain 30 units/seven days (independent example: 35 sales units/seven days gives six days of coverage). This is not an executed analytics refresh or checkout. DOC-002 is resolved at the contract/schema boundary: create-only import, protected mutable state, source/mode namespaces and explicit disposable reset policy. End-to-end import-after-checkout and aggregation-recompute regressions remain mandatory follow-up tests when those commands exist.

Custom trigger reversal/reapplication is checked separately on the empty local domain tables; no user data is reset. Application services, frontend, data acceptance and AWS remain outside this batch.

Executed guard reversal: docker compose -f src/compose.yaml run --rm web python manage.py migrate reporting 0001 --noinput (Unapplying reporting.0002_inventory_guards OK). Reapplied with migrate --noinput (Applying reporting.0002_inventory_guards OK), then migrate --check exited 0. This only removed/recreated guards on empty local domain tables; no model/table rollback was attempted.
