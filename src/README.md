# Local backend foundation

Run commands from the repository root with Docker Desktop using Linux containers. Python 3 is needed only for the optional host-side environment initializer; the application and tests run in Docker.

```powershell
python src/tools/init_env.py
docker compose -f src/compose.yaml build
docker compose -f src/compose.yaml run --rm web python manage.py migrate --noinput
docker compose -f src/compose.yaml up -d --wait --wait-timeout 60 web
docker compose -f src/compose.yaml run --rm web python manage.py check
docker compose -f src/compose.yaml run --rm web python manage.py check_database
docker compose -f src/compose.yaml run --rm web pytest -q -p no:cacheprovider /app/tests
```

The initializer creates src/.env once, generates random local secrets without printing them, and preserves an existing file. Docker-only initializer alternative in PowerShell:

```powershell
docker run --rm --mount "type=bind,source=${PWD}/src,target=/work" python:3.13-slim-bookworm@sha256:ed86c82274b3c69b52fb5820f358f0bd7df0b603332063cb5c6e32bd220c3e6e python /work/tools/init_env.py
```

Never commit .env or paste resolved Compose configuration: it contains secrets. Change APP_PORT if port 8000 is occupied.

Gunicorn serves http://127.0.0.1:8000/health/ (200 JSON status ok). GET / returns 404 because the frontend shell is intentionally not implemented. Framework auth/session migrations exist, but no authentication, catalogue/cart, checkout or analytics routes are implemented. Batch 3 supplies initial domain migrations and sealed historical inventory constraints. Run the same migrate command after rebuilding; no business routes are added.

```powershell
docker compose -f src/compose.yaml down
```

Down removes these containers/network and preserves the local database volume. Do not use down --volumes unless deliberately deleting this disposable project's data. Credentials are initialized on a fresh volume only: editing .env does not rotate an existing database password. Use a coordinated role change or a deliberate disposable reset if necessary. Re-run migrate explicitly after pulling migration changes; migrations never race on web startup.

Services: web and db, project inf2006-foundation. PostgreSQL has no published port. Web binds only to 127.0.0.1. The application role is non-superuser and owns its local database; CREATEDB is allowed locally for pytest's isolated test databases. The bootstrap password is supplied only to db, not web. This is a local Compose configuration, not an AWS deployment: production uses a suitably restricted runtime role, secure external configuration, verify-full PostgreSQL TLS with POSTGRES_SSLROOTCERT, explicit hosts and HTTPS. DJANGO_ENV defaults to production outside Compose; debug is forbidden there. Proxy trust is opt-in only behind a proxy that strips/replaces forwarded headers.

Dependencies: exact direct/transitive pip pins in requirements.txt; requirements.in is only for deliberate lock refreshes. Python and PostgreSQL images are digest-pinned. Docker packages static files at build time without application secrets; the process runs as UID 10001. Django sessions use PostgreSQL, expire after 14 days and need a later designated clearsessions maintenance runner.

Package paths: config holds settings/URLs/WSGI; accounts, catalogue, cart, orders and reporting are domain packages. Built-in Django User is retained. Frontend-owned templates/ and static/ are intentionally empty for Luna Max; API.md owns future route/form contracts. Batch verification records live under ../evidence/.

Health is liveness only and stays 200 during shared database failure. check_database is the separate connectivity/applied-migration gate and returns nonzero sanitized errors on failure. See ../evidence/foundation-batch-4.md for local failure/recovery and container-recreation results. Neither check demonstrates an ecommerce workflow or AWS availability. A later deployment must configure and test the ALB probe Host/allowed-host policy.

Keep 127.0.0.1 in the local allowed-host list because the Docker health probe uses it. Production ALB settings are a separate integration task.
