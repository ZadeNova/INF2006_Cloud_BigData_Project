# Deploy readiness (B6 app-side items 1 to 3)

Status (25 September 2026): planned, then implemented on `erfan/analytics`. Backend-owned; needs the review gate.

## Why

The production settings already fail closed, but three things stop the image from running on AWS as it is. Terraform will reference the paths and variable names fixed here, so they are settled before any Terraform is written. See B6 in [cloud-independent-prep.md](cloud-independent-prep.md).

## 1. RDS certificate bundle in the image

Outside local mode Django connects with `sslmode=verify-full` and requires `POSTGRES_SSLROOTCERT`. The image holds no RDS CA bundle, so a deployed instance cannot connect.

- Vendor the AWS RDS global bundle at `src/certs/rds-global-bundle.pem` (public CA certificates, not a secret), with a `README.md` recording its source URL, download date and SHA-256, the same way `static/vendor/htmx/` is recorded. Vendored rather than downloaded at build, so builds are reproducible and need no network.
- The Dockerfile sets `ENV POSTGRES_SSLROOTCERT=/app/certs/rds-global-bundle.pem`, so a deployment does not have to pass the path. Local mode ignores it (`sslmode=disable`).
- Test: the path in the image exists and loads as a CA file through `ssl.create_default_context(cafile=...)`.

## 2. Configurable HSTS

HSTS is fixed at one year outside local mode. A browser that has seen it refuses plain HTTP for a year and removes the "proceed anyway" option on certificate warnings, which would make the self-signed fallback (HTTPS option B) unusable, and would pin a year of HTTPS on a domain bought for two weeks.

- `DJANGO_HSTS_SECONDS`, a non-negative integer. Default outside local mode: `3600`; local stays `0`. Invalid values fail at startup, like the other settings.
- Tests: add one invalid value to `test_invalid_configuration_fails`; assert the production default in `test_production_configuration`.

## 3. Application role on RDS

Locally `docker/10-local-role.sh` creates a non-superuser role that owns the application database, and the web container never gets the bootstrap password. RDS only gives a master user, which is not a true superuser (it is a member of `rds_superuser`).

- New `src/tools/db_bootstrap.py`, run once from a one-off container of the app image (psycopg is already installed). It connects with the master credentials (`BOOTSTRAP_*` variables, verify-full TLS with the bundle from item 1) and, idempotently:
  1. creates the application role `LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB`, or updates its password if it exists (so a rerun matches the secret);
  2. grants the application role to the master user, because PostgreSQL 16 and later require a non-superuser to be able to `SET ROLE` to a role before creating a database owned by it;
  3. creates the application database owned by the application role if it is missing.
- Identifiers and the password are passed through `psycopg.sql` (identifier and literal quoting), never string formatting.
- No `CREATEDB` on RDS: pytest never runs against it.
- Tests: none in the pytest suite. The web container deliberately has no bootstrap credentials and its role cannot create roles, so an in-suite test would need a second privileged connection. Verified instead against a disposable local PostgreSQL 17 as a non-superuser `CREATEROLE CREATEDB` role that imitates the RDS master: first run creates, second run is a no-op that updates the password, the app role can connect and is not a superuser.

## Self-review follow-ups (after `7c5a10c`)

- **SR-1:** a database that already exists but is owned by another role (the RDS console's "Initial database name" creates it owned by the master) made migrations fail with `permission denied for schema public`, while the tool reported success. Fix: transfer ownership to the application role with `ALTER DATABASE ... OWNER TO`; on PostgreSQL 15+ the `public` schema follows the database owner. Runbook note: leave "Initial database name" blank.
- **SR-2:** an existing role was only refused if it was a superuser, and only after its password was changed. Fix: check its attributes first and refuse any of superuser, create-role, create-database, replication or bypass-RLS before changing anything.
- Verified the same way as item 3: a disposable PostgreSQL 17 with a non-superuser master, including a master-owned database that the app role then migrates, and a pre-existing over-privileged role that is refused with its password unchanged.

## Out of scope

Terraform, the launch script, migrations on AWS, the production environment template, S3 import, `clearsessions`. These follow in the Terraform plan.

## Verification

- `docker compose build web`; `pytest tests/test_settings.py` plus the new bundle test.
- Item 3 in a disposable Compose project, cleaned up afterwards.
- `python manage.py check`.
