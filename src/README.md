# Local development

Run commands from the repository root with Docker Desktop using Linux containers and Docker Compose 2.20 or later (root configuration uses Compose include). Python 3 is needed only for the optional host-side, one-time environment initializer; the application and dependencies run in Docker. A Docker-only initializer is shown below.

## Startup

Run from the repository root with Docker Desktop running. On a fresh clone only, generate local configuration (existing files are preserved):

```powershell
python src/tools/init_env.py
```

Then use standard Docker Compose:

```powershell
docker compose up --build  # First start or after code/dependency/migration changes
docker compose up          # Start an already-built checkout
docker compose down        # Stop and remove containers; preserve database data
```

Use `docker compose up --build -d` to run in the background. Open http://127.0.0.1:8000/ (or your configured APP_PORT). Root Compose uses the configuration under src/ and its local .env. A one-off migration service must finish successfully before web starts; migrations do not run in every web worker. This is local development behaviour, not the AWS deployment strategy.

Tests and diagnostics are separate from startup:

```powershell
docker compose run --rm web pytest -q -p no:cacheprovider /app/tests
docker compose run --rm web python manage.py check_database
```

No dev.py wrapper is needed. Do not use `down --volumes` unless deliberately deleting the disposable project's data.

## Optional editor setup

For VS Code/Pylance source analysis, create the ignored project-local editor environment once, then reload the window or select `.venv\\Scripts\\python.exe` as the interpreter:

```powershell
python -m venv .venv
.venv\\Scripts\\python.exe -m pip install -r src\\requirements.txt
```

The workspace settings point Pylance at this environment and add `src/` for project imports. Docker remains the supported application/runtime environment.

## Configuration and additional checks

To run the Django system check independently:

```powershell
docker compose run --rm web python manage.py check
```

The initializer creates src/.env once, generates random local secrets without printing them, and preserves an existing file. Docker-only initializer alternative in PowerShell:

```powershell
docker run --rm --mount "type=bind,source=${PWD}/src,target=/work" python:3.13-slim-bookworm@sha256:ed86c82274b3c69b52fb5820f358f0bd7df0b603332063cb5c6e32bd220c3e6e python /work/tools/init_env.py
```

Never commit .env or paste resolved Compose configuration: it contains secrets. Change APP_PORT if port 8000 is occupied.

Gunicorn serves the application at http://127.0.0.1:8000/ (which redirects to the catalogue) and the liveness probe at http://127.0.0.1:8000/health/ (200 JSON status ok). Implemented routes: `/register/`, `/login/`, `/logout/`; `/products/` (public catalogue) and `/products/manage/` (operator); `/cart/`; `/checkout/`, `/orders/`, `/orders/<id>/`; and `/analytics/` (operator dashboard). `/foundation/` is the Phase 1 design preview and `/foundation/statistics/` a design-only page with invented numbers. [API.md](../docs/API.md) owns the route contract. The local migration service applies pending migrations before web starts.

Management commands (run as `docker compose run --rm web python manage.py <command>`):

| Command | Purpose |
|---|---|
| `seed_demo --seed 42 [--no-products]` | Create the demo operator (`store_operator` group) and, unless `--no-products`, the 20 demo shoes in 10 sizes each (200 products) from `catalogue/shoes.py`. Create-only. |
| `import_dataset --source /app/data/derived/shoes --namespace NS` | Import the derived shoe dataset (or `/app/data/raw` for the original) with sealed historical inventory. Needs a namespace with no demo products; see [data/README.md](../data/README.md). |
| `snapshot_inventory --as-of YYYY-MM-DD` | Seal live stock as an immutable inventory version (today's Singapore date only). Leaves a permanent version, so avoid it on the shared dev database. |
| `refresh_analytics --as-of YYYY-MM-DD` | Rebuild the daily sales summary for the dashboard. Details in [analytics status](../docs/plans/analytics-status.md). |
| `load_customer_segments --run-id ID --input FILE` | Load the optional customer segments made by `analytics/segment_customers.py` for one analytics run; see [analytics/README.md](../analytics/README.md). |
| `check_database` | Connectivity and applied-migration gate. |

On SELinux hosts (Fedora) the compose bind mounts carry the `:z` label; no manual `chcon` is needed.

## Demo data

A fresh start has an empty store and an empty dashboard. This loads the derived shoe dataset (20 shoes in 10 sizes, so 200 products, and 100,000 historical orders) and a completed analytics run. First build the derived files on the host from the repository root (Python 3, standard library only; `data/raw/` is not changed):

```powershell
python analytics/build_shoe_dataset.py
```

Run the rest on a **new database**: if `seed_demo` has ever run without `--no-products`, its demo shoes sit in the same namespace and the import refuses with a conflict. To start over, `docker compose down --volumes` deletes the local database (this is the only case where that is intended).

```powershell
docker compose up --build -d
docker compose run --rm web python manage.py import_dataset --source /app/data/derived/shoes --namespace synthetic/shoes/revision-a/demo/v1
docker compose run --rm web python manage.py seed_demo --no-products
docker compose run --rm web python manage.py refresh_analytics --as-of 2026-01-02
```

- The import takes about 20 seconds and prints row counts, the cutoff `2026-01-02T00:00:00+08:00` and the sealed inventory name. Re-running it changes nothing (every row reports `unchanged`).
- `seed_demo --no-products` creates the operator `demo-operator`. Locally its password is the fallback in `src/catalogue/management/commands/seed_demo.py` unless `DEMO_OPERATOR_PASSWORD` is set; outside local the variable is required.
- `--as-of 2026-01-02` matches the import's cutoff, so the refresh uses the importer's sealed inventory without naming it. The dashboard then covers 1 January 2025 to 1 January 2026.
- Imported customers have unusable passwords by design. To shop, register a new account at `/register/`. Live orders placed today fall after the historical cutoff, so they do not appear on this dashboard run.

Shoe dataset verified on 26 September 2026 in a disposable Compose project on a fresh volume: 20 shoe models and 200 products, 100,000 orders and 237,537 lines imported with zero rejects and replayed unchanged; refresh wrote 41,345 daily rows; the pandas cross-check found zero mismatches. The earlier raw-dataset run on 24 September 2026: 1,200 products and 237,537 order lines imported with zero rejects, refresh wrote 65,589 daily rows, and over HTTP `/` redirected to the catalogue, the operator login succeeded and `/analytics/` rendered with data for the default and `90d` compare views.

```powershell
docker compose down
```

Down removes these containers/network and preserves the local database volume. Do not use down --volumes unless deliberately deleting this disposable project's data. Credentials are initialized on a fresh volume only: editing .env does not rotate an existing database password. Use a coordinated role change or a deliberate disposable reset if necessary. After pulling migration changes, use `docker compose up --build`; the single local migration service gates web startup. Coordinate shared-database changes separately; do not run concurrent Compose deployments against the same local database.

Services: web, db and a one-off migration service, project inf2006-foundation. PostgreSQL has no published port. Web binds only to 127.0.0.1. The application role is non-superuser and owns its local database; CREATEDB is allowed locally for pytest's isolated test databases. The bootstrap password is supplied only to db, not web. This is a local Compose configuration, not an AWS deployment: production uses a suitably restricted runtime role, secure external configuration, verify-full PostgreSQL TLS with POSTGRES_SSLROOTCERT, explicit hosts and HTTPS. DJANGO_ENV defaults to production outside Compose; debug is forbidden there. Proxy trust is opt-in only behind a proxy that strips/replaces forwarded headers.

Dependencies: exact direct/transitive pip pins in requirements.txt; requirements.in is only for deliberate lock refreshes. Python and PostgreSQL images are digest-pinned. Docker packages static files at build time without application secrets; the process runs as UID 10001. Django sessions use PostgreSQL, expire after 14 days and need a later designated clearsessions maintenance runner.

Package paths: config holds settings/URLs/WSGI; accounts, catalogue, cart, orders and reporting are domain packages. Built-in Django User is retained. Frontend-owned templates/ contains the shared shell, foundation preview and presentation fragment; static/ contains the shared stylesheet and minimal navigation/HTMX focus script. Future business route/form contracts are owned by API.md. Batch review summaries live under ../docs/reviews/.

Health is liveness only and stays 200 during shared database failure. check_database is the separate connectivity/applied-migration gate and returns nonzero sanitized errors on failure. See ../docs/reviews/foundation-batch-4.md for local failure/recovery and container-recreation results. Neither check demonstrates an ecommerce workflow or AWS availability. A later deployment must configure and test the ALB probe Host/allowed-host policy.

Keep 127.0.0.1 in the local allowed-host list because the Docker health probe uses it. Production ALB settings are a separate integration task.
