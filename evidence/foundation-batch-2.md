# Foundation batch 2 verification

12 September 2026, Windows PowerShell / Docker Desktop Linux amd64. Base: fca20e7. Local-only configuration; no AWS resources. Python 3.13.15, PostgreSQL 17.11 and Django 5.2.17; images digest-pinned in Dockerfile/Compose, dependencies locked.

Executed from repository root:

```powershell
python src/tools/init_env.py
docker compose -f src/compose.yaml config --quiet
docker compose -f src/compose.yaml build
docker compose -f src/compose.yaml run --rm web python manage.py check
docker compose -f src/compose.yaml run --rm web python manage.py migrate --noinput
docker compose -f src/compose.yaml run --rm web pytest -q -p no:cacheprovider /app/tests/test_settings.py
docker compose -f src/compose.yaml up -d web
Invoke-WebRequest http://127.0.0.1:8000/ -SkipHttpErrorCheck
docker compose -f src/compose.yaml exec web id
```

Final results: all commands succeeded; Django check has zero issues; all auth/contenttypes/sessions framework migrations applied on a clean local DB; 9 configuration/PostgreSQL tests passed (2.28s final rerun). HTTP root returns expected 404 because no routes are implemented in this batch. Web UID/GID is 10001. PostgreSQL role test confirms non-superuser. Raw final pytest output: [foundation-batch-2-output.txt](foundation-batch-2-output.txt).

Initializer first created private local .env without printing secrets. Second invocation printed Existing .env preserved; SHA-256 comparison confirmed unchanged bytes (hash omitted). git check-ignore confirms src/.env ignored. Compose exposes only web on 127.0.0.1:8000; database port is not published; web environment mapping excludes the bootstrap admin password. Static collection builds without app secrets or DB access. Model and health drafts are excluded from this batch's image.

Initial failed attempt: revoking SUPERUSER from PostgreSQL's bootstrap account was rejected; the non-superuser test then failed (1 failed, 8 passed). Corrected initialization creates a distinct non-superuser application role and database using a separate bootstrap account. Stopped only task-created containers; verified volume labels for inf2006-foundation_postgres_data, removed that disposable failed volume, and repeated clean initialization successfully. No user data existed and no earlier commit was changed.

Limitations: no custom schema/authentication/catalogue/cart/health/HTMX or AWS verification yet. Production configuration defaults are tested, not a deployment claim. Local role has CREATEDB for isolated pytest databases; production role privileges require the later infrastructure task. Services are running for subsequent batches; down preserves the database volume.
