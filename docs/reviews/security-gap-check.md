# Security gap check review

Task ID `security-gap-check`. Round 1 of the independent backend review gate ([DEVELOPMENT.md](../DEVELOPMENT.md#backend-review-gate)); brief: [astra-review.md](../plans/astra-review.md). Report received 20 September 2026 from the project's teammate running Astra as the independent reviewer (model and reasoning level are not stated in the report). Log written by the coordinator (the user with Claude Code) from that report.

- **Snapshot:** PR head `d0922916e12c9df6c582c369032b70c975c967b4` (`d092291`); cross-cutting, no base.
- **Scope:** the implemented code against [SECURITY.md](../SECURITY.md), [API.md](../API.md) and [TESTING.md](../TESTING.md).
- **Status:** Gate cleared at `7eea9b7` (round 4, 22 September 2026). SEC-002 and SEC-003 resolved in round 2; SEC-001 repeated in round 2, then resolved in round 3; R3-001 and R3-002 resolved in round 4. Fixes were made by the user with Claude, not Astra Low.

## Checks and limitations

Environment: built from Git into a separate Docker image with pinned dependencies and PostgreSQL, disposable database, non-superuser role; fresh migrations, `manage.py check` and `makemigrations --check --dry-run` passed; full suite 301 passed. The literal root Compose commands were not run; the host checkout was not edited. No real dataset, pandas cross-check, AWS deployment, cross-instance recovery, load test or frontend styling verification was performed.

SEC-002 was reproduced by injecting a temporary `OperationalError` at the cart database boundary.

## Findings

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| SEC-001 | Medium | `config/settings.py:39`, `Dockerfile:10` | SECURITY requires request IDs, durations and sanitised errors. Scoped inspection of application configuration and logging. | There is no request-ID or duration instrumentation or application logging configuration fulfilling this contract. The Gunicorn error logger does not supply the missing fields. Add a small request-logging integration with an explicit safe field list, and verify a controlled failure can be correlated without logging cookies, credentials or request payloads. | Fixed: `RequestLoggingMiddleware` and `config.jsonlog.JsonFormatter` with a `LOGGING` setting: one JSON line per request (request ID, method, path without query string, status, duration, numeric user ID, exception class), `X-Request-ID` returned and reused only if safe, exceptions reduced to class plus stack frames (never message, source, locals, headers, cookies or bodies), health and static at DEBUG, no database access for logging. Verified: 18 tests including a login POST leaking no password or cookie, a controlled failure correlated by request ID across the request line and Django's error record without its message, and the outage case; real container output inspected. Mutation checks: leaking the exception message fails 2 tests, accepting any request ID fails 5. The Gunicorn error log is unchanged. | Round 2: Partially resolved, **REPEATED** (`django.security` messages were logged unchanged, so a CSRF rejection leaked the Referer query string; reproduced through the Django client). Fixed in `ce1c788` by the user with Claude (plan [sec-001-log-message-fix.md](../plans/sec-001-log-message-fix.md)). Round 3: **Resolved** |
| SEC-002 | Medium | `cart/views.py:25`, `orders/views.py:76` | API requires 503 for temporary dependency unavailability. Injected a temporary `OperationalError` at the cart database boundary. | A temporary database failure produces HTTP 500, with no business-route 503 handling. Add narrow handling for recognised transient dependency failures, with a safe response and the documented HTMX behaviour. For uncertain checkout outcomes, preserve the existing key so retry can resolve the committed order. Do not turn integrity or programming errors into retryable failures. | Fixed: `config.middleware.DatabaseUnavailableMiddleware` (`process_exception`) answers 503 with `Retry-After: 5`, `Cache-Control: no-store` and a database-free page for `OperationalError` and `InterfaceError` only; `site.js` shows an inline notice for HTMX 503s (HTMX does not swap error responses; the JS is not covered by an automated browser test). Checkout keeps its idempotency key across the 503. Verified: outage on cart, checkout, history and catalogue routes, an HTMX mutation, a closed connection, integrity and programming errors staying 500, `/health/` unaffected, and a retry after a commit-then-connection-loss resolving to the one committed order. Mutation checks: middleware removed fails 9 tests; treating every `DatabaseError` as transient fails 3. | Resolved (round 2, `d092291..b282a60`) |
| SEC-003 | Medium | `tests/test_orders.py:275`, `tests/test_cart.py:264`, `tests/test_catalogue.py` | SECURITY's negative-test list. | Required negative coverage is incomplete: anonymous checkout tests GET only; server-price tests change the database price rather than submit forged price, owner or total fields; CSRF tests omit the operator toggle and cart update and delete, including HTMX mutations. Add targeted tests with `enforce_csrf_checks=True` and assert both rejection and unchanged business state. | Fixed with `tests/test_security_negative.py` (72 tests, no application change): CSRF (no token, wrong header, wrong form field) on cart add, update, delete, the operator toggle and checkout, each normal and HTMX, asserting 403 and unchanged state, with a valid-token control for each; anonymous checkout POST and anonymous normal and HTMX cart mutations; customer and anonymous use of the operator toggle; forged price, owner, total, status, namespace and idempotency-key fields on checkout and forged owner and cart fields on cart add; eleven bad quantities on add and update. Mutation check: removing the CSRF middleware fails 30 tests. | Resolved (round 2, `d092291..b282a60`) |

## Negative-test mapping and other observations

- Covered and passing: foreign cart and order access, quantity bounds, duplicate checkout, missing CSRF on checkout, cart add and logout.
- Unavailable until later work, so limitations and not new defects: non-operator analytics (dashboard not built) and anonymous S3 denial (no cloud deployment).
- Present and acceptable: production debug rejection, explicit allowed hosts, database sessions and secure-cookie settings. Proxy trust is opt-in through `DJANGO_TRUST_PROXY`; actual proxy header stripping or replacement needs deployment verification. Session lifetime is explicitly 14 days and documented in `src/README`, which also plans a designated `clearsessions` runner (infrastructure work), so "no cleanup plan" is not reported as a gap.
- Login throttling is absent but not required by the agreed contract, so no blocking finding.

## Coordinator notes

SEC-001 corresponds to B2 in [cloud-independent-prep.md](../plans/cloud-independent-prep.md) and was already suspected in the brief. SEC-002 also strengthens the resilience story ("never confirm checkout if the database is unavailable"). Decision: none.

## Re-review history

Rounds 2 to 4 of the independent review are done and the gate is **cleared at `7eea9b7`** (round 4, 22 September 2026). Fixes were made by the user with Claude, not Astra Low. Astra's round reports are PR #1 comments; this section is the concise record.

| Round | Snapshot | Result |
|---|---|---|
| 2 | `d092291..b282a60` | 429 tests, fresh migrations, `manage.py check` and `makemigrations --check --dry-run` passed on the reviewed snapshot (Astra). SEC-002 and SEC-003 resolved; SEC-001 repeated (see the table), which under the gate rules stopped the task until the user chose to fix it directly |
| 3 | `b282a60..282a1ec` | Bounded to the SEC-001 fix and the test trim; this task's findings were not reopened. |
| 4 | `282a1ec..7eea9b7` | Bounded to the R3-001/R3-002 fixes; this task's findings were not reopened. Gate cleared. |

### New findings after round 1

| ID | Severity | File/line | Issue | Outcome |
|---|---|---|---|---|
| R3-001 | P2 (coverage regression) | `tests/test_accounts.py` | Round 3: the test trim removed the anonymous `GET /register/` test. Astra replaced `RegisterView.get` with a 405 in memory and all 14 surviving account tests still passed. Only a POST re-render was covered, which is a different path. | **Resolved** in `7eea9b7` (round 4): one parametrised test covers anonymous GET of the register and login pages (200 and template). Mutations now fail: register GET 1 failed / 15 passed, login GET 2 failed / 14 passed. |
| R3-002 | Advisory | `AGENTS.md:69` | The test-budget paragraph was too categorical ("one regression test", "different code paths") and could be read as removing a useful formatter-level check just because an HTTP-level check also protects the same finding. | **Resolved** in `7eea9b7`: wording now allows one focused regression per independently breakable behaviour and judges duplication by what defect a case detects. |

Round 3 also checked: the fixed security-log message across Django's `SuspiciousOperation` family and CSRF (status codes, logger names and request IDs retained, no exception text), the test trims (no distinct behaviour lost apart from R3-001), the new 999-ceiling, session-deletion and order-total tests (each fails under the matching in-memory mutation), and the SELinux `:z` Compose mount labels (harmless on hosts without SELinux). Round 3 ran the 8 changed modules (234 passed), `check` and `makemigrations --check`; hosted CI on the head was success (379 passed is the author's count, Astra could not read the raw job log). Round 4 ran `test_accounts.py` (16 passed) and confirmed hosted CI success on `7eea9b7`; it did not rerun the full suite, `check` or `makemigrations` because the delta was tests and guidance only.

### Open observations (non-blocking, from round 4)

- `test_logout_deletes_the_session_server_side_not_just_in_the_browser` also fails if `LoginView.get` breaks, because its replay step does a GET. Cleanup when that file is next touched: request a neutral page and assert `response.wsgi_request.user.is_authenticated` is false, keeping the session-row deletion assertion.
- Known and accepted, unchanged: the 503 middleware does not cover a database failure in another middleware's response phase (for example a session save); the `site.js` 503 notice has no automated browser test; no login throttling; Gunicorn error log unchanged.
