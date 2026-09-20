# Security gap check review

Task ID `security-gap-check`. Round 1 of the independent backend review gate ([DEVELOPMENT.md](../DEVELOPMENT.md#backend-review-gate)); brief: [astra-review.md](../plans/astra-review.md). Report received 20 September 2026 from the project's teammate running Astra as the independent reviewer (model and reasoning level are not stated in the report). Log written by the coordinator (the user with Claude Code) from that report.

- **Snapshot:** PR head `d0922916e12c9df6c582c369032b70c975c967b4` (`d092291`); cross-cutting, no base.
- **Scope:** the implemented code against [SECURITY.md](../SECURITY.md), [API.md](../API.md) and [TESTING.md](../TESTING.md).
- **Status:** Round 1 complete; **three actionable findings open** (all Medium). Not approved.

## Checks and limitations

Environment: built from Git into a separate Docker image with pinned dependencies and PostgreSQL, disposable database, non-superuser role; fresh migrations, `manage.py check` and `makemigrations --check --dry-run` passed; full suite 301 passed. The literal root Compose commands were not run; the host checkout was not edited. No real dataset, pandas cross-check, AWS deployment, cross-instance recovery, load test or frontend styling verification was performed.

SEC-002 was reproduced by injecting a temporary `OperationalError` at the cart database boundary.

## Findings

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| SEC-001 | Medium | `config/settings.py:39`, `Dockerfile:10` | SECURITY requires request IDs, durations and sanitised errors. Scoped inspection of application configuration and logging. | There is no request-ID or duration instrumentation or application logging configuration fulfilling this contract. The Gunicorn error logger does not supply the missing fields. Add a small request-logging integration with an explicit safe field list, and verify a controlled failure can be correlated without logging cookies, credentials or request payloads. | Pending | Pending |
| SEC-002 | Medium | `cart/views.py:25`, `orders/views.py:76` | API requires 503 for temporary dependency unavailability. Injected a temporary `OperationalError` at the cart database boundary. | A temporary database failure produces HTTP 500, with no business-route 503 handling. Add narrow handling for recognised transient dependency failures, with a safe response and the documented HTMX behaviour. For uncertain checkout outcomes, preserve the existing key so retry can resolve the committed order. Do not turn integrity or programming errors into retryable failures. | Pending | Pending |
| SEC-003 | Medium | `tests/test_orders.py:275`, `tests/test_cart.py:264`, `tests/test_catalogue.py` | SECURITY's negative-test list. | Required negative coverage is incomplete: anonymous checkout tests GET only; server-price tests change the database price rather than submit forged price, owner or total fields; CSRF tests omit the operator toggle and cart update and delete, including HTMX mutations. Add targeted tests with `enforce_csrf_checks=True` and assert both rejection and unchanged business state. | Pending | Pending |

## Negative-test mapping and other observations

- Covered and passing: foreign cart and order access, quantity bounds, duplicate checkout, missing CSRF on checkout, cart add and logout.
- Unavailable until later work, so limitations and not new defects: non-operator analytics (dashboard not built) and anonymous S3 denial (no cloud deployment).
- Present and acceptable: production debug rejection, explicit allowed hosts, database sessions and secure-cookie settings. Proxy trust is opt-in through `DJANGO_TRUST_PROXY`; actual proxy header stripping or replacement needs deployment verification. Session lifetime is explicitly 14 days and documented in `src/README`, which also plans a designated `clearsessions` runner (infrastructure work), so "no cleanup plan" is not reported as a gap.
- Login throttling is absent but not required by the agreed contract, so no blocking finding.

## Coordinator notes

SEC-001 corresponds to B2 in [cloud-independent-prep.md](../plans/cloud-independent-prep.md) and was already suspected in the brief. SEC-002 also strengthens the resilience story ("never confirm checkout if the database is unavailable"). Decision: none.
