# Automated tests

pytest with pytest-django against real PostgreSQL (an isolated test database that pytest creates and drops; no SQLite substitute). Tests are mounted read-only at `/app/tests`. Latest recorded full-suite run: 503 passed and 8 skipped in a local Docker run on 27 September 2026 at `c1ed7c6`. The 8 skips are the opt-in `test_db_bootstrap.py` cases that need an explicit disposable `BOOTSTRAP_TEST_DSN`. This is the only place the count is kept; update it here after a re-run instead of quoting a number elsewhere. Run from the repository root after the Docker quickstart in [../src/README.md](../src/README.md):

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
| `test_import.py` | Dataset import, replay, conflicts, date shifts, sealed inventory, shoe models and sizes |
| `test_frontend.py` | Presentation pages, including the statistics preview |

`analytics/tests/` covers independent pandas reconciliation (`test_verify_refresh.py`), offline segmentation quality and batch identity (`test_segment_customers.py`), producer/loader integration (`test_segment_loader_integration.py`), fake production credential delivery (`test_startup_credentials.py`), and the derived shoe dataset build (`test_build_shoe_dataset.py`, no pandas needed). The others need pandas and, for segmentation, scikit-learn, and run outside the web image (see [../analytics/README.md](../analytics/README.md)). `db_helpers.py` and `analytics_helpers.py` are shared builders, not tests.

Locking and concurrency tests use real independent connections. A passing suite is not by itself a functional or security claim; record the command, date and outcome in the files under [../evidence/](../evidence/README.md). No load, scaling or AWS test exists yet.


## Local runtime image and TLS verification

`verify_runtime_image.py` is a manual verification helper, not an AWS/deployment test. Its
`SENTINELS` tuple lists every harmless context marker; `audit-image` checks the actual image
filesystem, UID, public CA and absence of ML packages. `make-context` copies tracked `src/`
files from the working tree, so untracked real local secrets are not copied. The destination
must be new. From the repository root (PowerShell), choose a fresh scratch directory:

```powershell
$runtimeScratch = Join-Path $env:TEMP ('inf2006-runtime-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $runtimeScratch | Out-Null
python tests/verify_runtime_image.py make-context "$runtimeScratch/context"
docker build -t inf2006-runtime-sentinel "$runtimeScratch/context"
docker run --rm --mount "type=bind,source=${PWD}/tests/verify_runtime_image.py,target=/checks/verify_runtime_image.py,readonly" inf2006-runtime-sentinel python /checks/verify_runtime_image.py audit-image
docker build -t inf2006-runtime-final src
docker run --rm --mount "type=bind,source=${PWD}/tests/verify_runtime_image.py,target=/checks/verify_runtime_image.py,readonly" inf2006-runtime-final python /checks/verify_runtime_image.py audit-image
docker image inspect inf2006-runtime-final --format '{{.Id}} {{json .RepoDigests}} {{json .Config.User}} {{json .Config.ExposedPorts}} {{json .Config.Cmd}}'
```

Expected metadata: UID/GID `10001:10001`, port `8000/tcp`, the Dockerfile's Gunicorn command.
A Docker-local ID/RepoDigest is not evidence of ECR publication; record the pushed ECR digest
separately only after an authorised push. Check Git patterns without creating Terraform files:
`git check-ignore --no-index src/infrastructure/secret.tfvars src/infrastructure/saved.tfplan`
should match; `main.tf`, `.terraform.lock.hcl`, `terraform.tfvars.example` and
`terraform.tfvars.json.example` under that directory must not match.

For a real TLS handshake, create an isolated PostgreSQL 17 fixture with the following command
(the password is deliberately disposable test data). The private key stays inside the temporary
server container. The one-day self-signed certificate has only `DNS:localhost`:

```powershell
New-Item -ItemType Directory -Path "$runtimeScratch/tls" | Out-Null
docker run -d --name inf2006-runtime-tls-db -e POSTGRES_PASSWORD=disposable-tls-only --entrypoint bash postgres:17-bookworm@sha256:051f7b7b3abdd564d5d1bd1e8c4b9c1b6e77087d1dd22020ede611c096a272e0 -c 'set -e
openssl req -x509 -newkey rsa:2048 -nodes -keyout /tmp/server.key -out /tmp/server.crt -days 1 -subj /CN=localhost -addext subjectAltName=DNS:localhost >/dev/null 2>&1
chown postgres:postgres /tmp/server.key /tmp/server.crt
chmod 600 /tmp/server.key
exec docker-entrypoint.sh postgres -c ssl=on -c ssl_cert_file=/tmp/server.crt -c ssl_key_file=/tmp/server.key'
# Wait for pg_isready to report ready; copy only the public certificate.
docker exec inf2006-runtime-tls-db pg_isready -U postgres
docker cp inf2006-runtime-tls-db:/tmp/server.crt "$runtimeScratch/tls/server.crt"
docker run --rm --network container:inf2006-runtime-tls-db --mount "type=bind,source=$runtimeScratch/tls,target=/tls,readonly" --mount "type=bind,source=${PWD}/tests/verify_runtime_image.py,target=/checks/verify_runtime_image.py,readonly" -e PYTHONPATH=/app inf2006-runtime-final python /checks/verify_runtime_image.py tls /tls/server.crt
```

The helper uses fake secret retrieval with the real shared production connection policy. It
requires an actual encrypted connection with the trusted fixture CA, rejects hostname
`127.0.0.1` against the localhost-only certificate, and rejects the unrelated RDS CA bundle.
It checks the corresponding libpq hostname-mismatch or certificate-verification reason internally;
an unrelated connection error cannot count as a passing negative check, and raw errors are not printed.
No AWS calls occur. This proves local certificate/hostname verification, not RDS/ALB/IAM access.
After review/testing, remove only the named fixture containers with their anonymous volumes,
then verify the resolved scratch path is the directory created above before recursively removing
it. Do not run broad Docker pruning or delete another task's resources.
