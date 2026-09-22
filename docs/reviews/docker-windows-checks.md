# Windows Docker verification follow-up

Date: 22 September 2026. Base: merged main `0887e8185d49b758a2c5d94167df9bfd72a3b454`. User requested the previously blocked local Docker checks after repairing Docker Desktop. Initial working tree was clean. Scope: local checkout behavior for the PostgreSQL initializer and CI-equivalent verification; application logic unchanged.

References: [development review gate](../DEVELOPMENT.md#backend-review-gate), [testing](../TESTING.md#continuous-integration), [local startup](../../src/README.md), [original PR review](pr-2-final.md). Task-owned files: `.gitattributes`, this log and the implementation tracker. The initializer's working bytes were restored to its existing committed content; its source is unchanged. An unrelated untracked `tmp/pdfs/` directory appeared during verification and was left untouched.

## Finding and independent review

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| DOCKER-001 | P2 | `src/docker/10-local-role.sh:1`; `.gitattributes` | Supported Windows Docker startup must initialize the local application role/database. Fresh PostgreSQL exited 127: initializer could not execute, required file not found. Git reported `i/lf w/crlf`; CRLF corrupted the Linux shebang. | Enforce LF checkout for the Linux initializer without changing script logic. | `/root/docker_lf_fix`, explicit `gpt-6-astra` / `low`, added `src/docker/*.sh text eol=lf`, retaining the raw-CSV preservation rule. Restored original script bytes. Working bytes and checkout-filter output with `core.autocrlf=true` match HEAD blob `1b4d19187f5c708462844b12683d6e3608d7acdf`. | `/root/docker_lf_review`, explicit `gpt-6-astra` / `medium`, independently verified byte identity, LF-only filter output, Compose linkage and scope; resolved, no new actionable findings. Gate clear after coordinator supplied passing Docker results. |

Reviewer was read-only and independent of the fixer. Snapshot: base above plus the two-line `.gitattributes` addition. Coordinator owns this log. This is a separate script-checkout defect; the earlier raw-CSV finding remains resolved.

## Executed verification

Docker Desktop Linux containers on Windows; repository-pinned Python 3.13/PostgreSQL 17 images and pinned application dependencies. Isolated Compose project `inf2006-pr2-review`; no pre-existing project database volume. The failed first initialization was removed before retrying against a fresh volume.

All following commands passed after the fix, from the repository root:

```powershell
docker compose -p inf2006-pr2-review build web
docker compose -p inf2006-pr2-review up --wait --wait-timeout 90 db
docker compose -p inf2006-pr2-review run --rm --no-deps migrate
docker compose -p inf2006-pr2-review run --rm --no-deps web python manage.py check
docker compose -p inf2006-pr2-review run --rm --no-deps web python manage.py makemigrations --check --dry-run
docker compose -p inf2006-pr2-review run --rm --no-deps web python manage.py check_database
docker compose -p inf2006-pr2-review run --rm --no-deps web pytest -q -p no:cacheprovider /app/tests
docker compose -p inf2006-pr2-review down --volumes --remove-orphans
```

- Image built, including dependency consistency and static collection; database initialized and became healthy.
- All fresh migrations applied, including reporting SQL/constraints. Django reported no issues; no missing migrations detected.
- Database readiness returned `{"database": "ok", "migrations": "applied"}`.
- Full suite: **381 passed in 13.64 seconds**, including PostgreSQL concurrency cases.
- Cleanup passed; no containers or volumes remain for this disposable project. No existing application database was removed.
- `git diff --check` passed. No new tests were added for the checkout rule; direct filter/byte verification and fresh database initialization exercise the failure.

The earlier Docker Engine HTTP 500 limitation is resolved. No browser walkthrough, AWS/S3, load test, cross-instance recovery or full dataset acceptance/import was performed. This record accompanies the scoped attribute fix in the post-merge follow-up commit.
