# Security control test

## Summary

| Case | Proves | Threat/requirement | Environment | Date | Commit | Status |
|---|---|---|---|---|---|---|
| SEC-01 | A user cannot read or change another user's orders or cart items | T1 broken access control / IDOR (OWASP A01:2025) | Local Docker | 2026-09-26 | `ee334cf` | PASS |
| SEC-02 | A customer cannot use operator functions | T2 privilege escalation (A01) | Local Docker | 2026-09-26 | `ee334cf` | PASS |
| SEC-03 | State-changing requests without valid CSRF tokens are refused without mutation | T3 CSRF (A01) | Local Docker | 2026-09-26 | `ee334cf` | PASS |
| SEC-04 | Forged prices, owners, totals, statuses and bad quantities are ignored or rejected | T4 tampering (A06) | Local Docker | 2026-09-26 | `ee334cf` | PASS |
| SEC-05 | Concurrent checkout does not duplicate orders or oversell stock | T5 duplicate checkout / overselling (A06) | Local Docker | 2026-09-26 | `ee334cf` | PASS |
| SEC-06 | Stored HTML/JavaScript product input is escaped | T6 stored XSS (A05) | Local Docker | 2026-09-26 | `ee334cf` | PASS |
| SEC-07 | A commonly used password is rejected at registration | T7 weak passwords (A07), partial control | Local Docker | 2026-09-26 | `ee334cf` | PASS |
| SEC-08 | Passwords, cookies, tokens and query strings are absent from logs | T8 secrets in logs (A09) | Local Docker | 2026-09-26 | `ee334cf` | PASS |
| SEC-ALL | All local security cases in one sequential command | T1–T8 | Local Docker | 2026-09-26 | `ee334cf` | PASS |
| SEC-12 | Production settings fail closed (secret, hosts, debug, HSTS value, probe host, release id); Secure cookies, HTTPS redirect, HSTS and `verify-full` RDS TLS are set in production mode; non-superuser database role; shared database sessions | T7 (cookie flags only), T10, T11, T17 (role) | Local Docker | 2026-10-01 | `e6732ff` | PASS |
| SEC-13 | Production reads secrets from Secrets Manager with no plaintext fallback, a wrong schema is refused, errors are redacted, static SDK credentials are rejected | T8 secrets handling (loader) | Local Docker | 2026-10-01 | `e6732ff` | PASS |
| SEC-14 | Health endpoint: no database queries, validated Host, exact internal-probe exception, redirect exemption, sanitised database failure | T11 misconfiguration (host handling) | Local Docker | 2026-10-01 | `e6732ff` | PASS |
| SEC-15 | Structured request logs: one line per request, unsafe request IDs replaced, no password, cookie, query string or exception message | T12 detection, T8 logs | Local Docker | 2026-10-01 | `e6732ff` | PASS |
| SEC-16 | Imported customers get unusable passwords | T17 personal data / account takeover | Local Docker | 2026-10-01 | `e6732ff` | PASS |
| SEC-ALL rerun | The same 25 test IDs as the 26 September SEC-ALL, rerun on the current commit | T1–T8 | Local Docker | 2026-10-01 | `e6732ff` | PASS |
| SCAN-01 to SCAN-07 | Secret scan, SAST, dependency audit, `check --deploy`, Dockerfile lint, image scan, IaC scan, with triage | T8, T11, supply chain | Local Docker (not CI) | 2026-10-01 | `e6732ff` | **Findings triaged; 4 open items**, see [security-scan-triage.md](security-scan-triage.md) |
| SEC-09 | RDS and S3 are not publicly reachable | Cloud private data/storage controls | AWS | — | — | PLANNED |
| SEC-10 | HTTPS is enforced | Cloud transport security | AWS | — | — | PLANNED |
| SEC-11 | Runtime secrets come from Secrets Manager | Cloud secret handling | AWS | — | — | PLANNED |

**Shared setup:** the web image was rebuilt with `docker compose build web` at merge-quarantine commit `ee334cf`. The local Docker `web` and `db` services were healthy. Each pytest command used its own disposable test database and no demo data. Git Bash on Windows ran with `MSYS_NO_PATHCONV=1` so `/app/tests/...` paths remained container paths.

**Commands:** the SEC-01 to SEC-08 raw files from 26 September do not store the command line, so each case lists the command reconstructed from the test IDs printed in its raw output. Cases SEC-12 onward and the 2026-10-01 rerun store the exact command as the first lines of their raw file.

**Wrapper note:** a first wrapper attempt ran SEC-01 successfully but then failed to append its exit marker because the Bash script mistakenly called the PowerShell-only command `Tee-Object`. That wrapper issue is retained in the first raw file; it is not an application or test failure. The clean sequential rerun files with `_rerun` suffixes are the authoritative results below.

## SEC-01: Broken access control / IDOR

**Objective:** Verify that a user cannot retrieve another user's order or modify/delete another user's cart item by using its identifier.

**Threat/requirement:** T1 broken access control / IDOR, OWASP A01:2025.

**Command (reconstructed from the raw output):** `docker compose run --rm --no-deps web pytest -v -p no:cacheprovider /app/tests/test_cart.py::test_delete_does_not_touch_a_foreign_cart_item /app/tests/test_cart.py::test_update_on_foreign_item_returns_404_and_does_not_mutate /app/tests/test_orders.py::test_order_detail_returns_404_for_foreign_order_200_for_owner /app/tests/test_orders.py::test_order_list_shows_only_the_owners_orders_most_recent_first`

**Expected result:** 4 passed, 0 failed, 0 errors.

**Actual result:** 4 passed in 1.19s; pytest exit 0. [Raw output](raw/SEC-01_2026-09-26_rerun.txt).

**Status:** PASS

**Interpretation:** The owner can retrieve an order, while another user cannot; the order list is owner-scoped; foreign cart update and delete attempts do not mutate the owner’s item. This is local server-side evidence, not an AWS test.

**Automated equivalent:** The case is itself automated.

**Date/commit:** 2026-09-26, `ee334cf`

**Limitations/follow-up:** The first wrapper’s partial output is retained separately; the clean rerun is authoritative.

## SEC-02: Privilege escalation

**Objective:** Verify that a customer cannot toggle a product or access the analytics dashboard, including through HTMX.

**Threat/requirement:** T2 privilege escalation, OWASP A01:2025.

**Command (reconstructed from the raw output):** `docker compose run --rm --no-deps web pytest -v -p no:cacheprovider /app/tests/test_analytics_dashboard.py::test_customer_is_forbidden_even_with_htmx /app/tests/test_security_negative.py::test_a_customer_cannot_use_the_operator_toggle`

**Expected result:** 3 passed, 0 failed, 0 errors.

**Actual result:** 3 passed in 1.11s; pytest exit 0. [Raw output](raw/SEC-02_2026-09-26_rerun.txt).

**Status:** PASS

**Interpretation:** The customer product-toggle request and both normal/HTMX customer dashboard requests are refused. The tests exercise server-side permission checks rather than merely hiding controls in the template.

**Automated equivalent:** FUNC-02 step 8 also observed a customer 403 in the browser.

**Date/commit:** 2026-09-26, `ee334cf`

**Limitations/follow-up:** Local only; AWS IAM and network controls remain planned.

## SEC-03: CSRF

**Objective:** Verify that invalid CSRF tokens are rejected on cart add/update/delete, product toggle and checkout, and that logout without a token is rejected without state changes.

**Threat/requirement:** T3 cross-site request forgery, OWASP A01:2025.

**Command (reconstructed from the raw output):** `docker compose run --rm --no-deps web pytest -v -p no:cacheprovider /app/tests/test_accounts.py::test_logout_without_csrf_token_is_rejected /app/tests/test_security_negative.py::test_a_mutation_without_a_valid_csrf_token_is_rejected_and_changes_nothing`

**Expected result:** 6 passed, 0 failed, 0 errors.

**Actual result:** 6 passed in 1.02s; pytest exit 0. [Raw output](raw/SEC-03_2026-09-26_rerun.txt).

**Status:** PASS

**Interpretation:** Five state-changing routes reject the invalid token and preserve business state; logout without a token is also rejected. The test enables real CSRF checks instead of relying on the test client’s default bypass.

**Automated equivalent:** The case is itself automated.

**Date/commit:** 2026-09-26, `ee334cf`

**Limitations/follow-up:** Local configuration only; production HTTPS cookie behavior is not demonstrated here.

## SEC-04: Price, owner, status and quantity tampering

**Objective:** Verify that forged fields cannot change prices, order owners, cart owners, totals or statuses, and invalid quantities create no cart item.

**Threat/requirement:** T4 tampering, OWASP A06:2025.

**Command (reconstructed from the raw output):** `docker compose run --rm --no-deps web pytest -v -p no:cacheprovider /app/tests/test_security_negative.py::test_cart_add_ignores_forged_owner_cart_and_price_fields /app/tests/test_security_negative.py::test_cart_add_rejects_bad_quantities_without_creating_anything /app/tests/test_security_negative.py::test_checkout_ignores_forged_price_owner_total_and_status_fields`

**Expected result:** 5 passed, 0 failed, 0 errors.

**Actual result:** 5 passed in 1.00s; pytest exit 0. [Raw output](raw/SEC-04_2026-09-26_rerun.txt).

**Status:** PASS

**Interpretation:** Forged prices, totals, owners and status values are ignored; the server derives the order from the authenticated user and live product data. Zero, non-numeric and missing quantities create no cart item.

**Automated equivalent:** The case is itself automated.

**Date/commit:** 2026-09-26, `ee334cf`

**Limitations/follow-up:** Local only; no deployed request-tampering test has run.

## SEC-05: Duplicate checkout and overselling

**Objective:** Verify idempotency under the same request key and safe behavior when two users race for the last unit.

**Threat/requirement:** T5 duplicate checkout and overselling, OWASP A06:2025.

**Command (reconstructed from the raw output):** `docker compose run --rm --no-deps web pytest -v -p no:cacheprovider /app/tests/test_orders.py::test_concurrent_checkouts_different_users_racing_last_unit_of_stock /app/tests/test_orders.py::test_concurrent_checkouts_same_idempotency_key_create_exactly_one_order`

**Expected result:** 2 passed, 0 failed, 0 errors.

**Actual result:** 2 passed in 1.07s; pytest exit 0. [Raw output](raw/SEC-05_2026-09-26_rerun.txt).

**Status:** PASS

**Interpretation:** Concurrent reuse of one idempotency key creates one order, and two users racing for one unit produce one successful order and one stock conflict without negative stock. This is a focused concurrency check, not a load benchmark or multi-instance AWS test.

**Automated equivalent:** The case is itself automated.

**Date/commit:** 2026-09-26, `ee334cf`

**Limitations/follow-up:** Two concurrent threads and one local PostgreSQL instance only.

## SEC-06: Stored XSS

**Objective:** Verify that a product name containing an HTML/JavaScript payload is rendered as escaped text.

**Threat/requirement:** T6 stored cross-site scripting, OWASP A05:2025.

**Command (reconstructed from the raw output):** `docker compose run --rm --no-deps web pytest -v -p no:cacheprovider /app/tests/test_analytics_dashboard.py::test_rendered_dashboard_escapes_product_names_and_shows_status_labels`

**Expected result:** 1 passed, 0 failed, 0 errors.

**Actual result:** 1 passed in 0.99s; pytest exit 0. [Raw output](raw/SEC-06_2026-09-26_rerun.txt).

**Status:** PASS

**Interpretation:** The dashboard contains escaped payload text and not a live HTML tag, so the tested stored product-name payload is not executed by the browser. This does not provide a Content Security Policy.

**Automated equivalent:** The case is itself automated.

**Date/commit:** 2026-09-26, `ee334cf`

**Limitations/follow-up:** One dashboard payload was tested; no CSP is claimed.

## SEC-07: Weak passwords

**Objective:** Verify that registration rejects a commonly used password and creates no account.

**Threat/requirement:** T7 weak passwords, OWASP A07:2025. Partial control: this case does not provide login throttling or MFA.

**Command (reconstructed from the raw output):** `docker compose run --rm --no-deps web pytest -v -p no:cacheprovider /app/tests/test_accounts.py::test_registration_enforces_the_password_validators`

**Expected result:** 1 passed, 0 failed, 0 errors.

**Actual result:** 1 passed in 0.83s; pytest exit 0. [Raw output](raw/SEC-07_2026-09-26_rerun.txt).

**Status:** PASS

**Interpretation:** The password validator rejects the common password and the test confirms no account is created. Repeated-login throttling and MFA remain limitations.

**Automated equivalent:** The case is itself automated.

**Date/commit:** 2026-09-26, `ee334cf`

**Limitations/follow-up:** No throttling or MFA is implemented/evidenced.

## SEC-08: Secrets and personal data in logs

**Objective:** Verify that passwords, cookies, CSRF/bearer tokens, query strings and an attacker-supplied referrer are not written to application/security logs.

**Threat/requirement:** T8 secrets in logs, OWASP A09:2025.

**Command (reconstructed from the raw output):** `docker compose run --rm --no-deps web pytest -v -p no:cacheprovider /app/tests/test_request_logging.py::test_a_login_post_logs_neither_the_password_nor_the_cookie /app/tests/test_request_logging.py::test_a_rejected_referer_is_not_echoed_into_the_security_log /app/tests/test_request_logging.py::test_query_strings_are_not_logged`

**Expected result:** 3 passed, 0 failed, 0 errors.

**Actual result:** 3 passed in 1.35s; pytest exit 0. [Raw output](raw/SEC-08_2026-09-26_rerun.txt).

**Status:** PASS

**Interpretation:** Login secrets/cookies/tokens, query-string values and a sensitive referrer are excluded from the tested log output while the request remains traceable. This covers application/security logs locally, not CloudWatch.

**Automated equivalent:** The case is itself automated; MON-01 remains a separate live-log case.

**Date/commit:** 2026-09-26, `ee334cf`

**Limitations/follow-up:** CloudWatch and deployed log retention are not tested.

## SEC-ALL: Combined local security run

**Objective:** Run every selected SEC-01 to SEC-08 test in one sequential command.

**Threat/requirement:** T1–T8.

**Expected result:** 25 passed, 0 failed, 0 errors.

**Actual result:** 25 passed in 2.74s; pytest exit 0. [Raw output](raw/SEC-ALL_2026-09-26_rerun.txt).

**Status:** PASS

**Interpretation:** The combined run confirms the selected local security matrix has 25 passing test cases: 4 + 3 + 6 + 5 + 2 + 1 + 1 + 3. The cases ran sequentially, avoiding shared test-database collisions.

**Automated equivalent:** The case is itself automated.

**Date/commit:** 2026-09-26, `ee334cf`

**Limitations/follow-up:** Local only; SEC-09 to SEC-11 remain planned for AWS.

## Rerun and additional local cases, 2026-10-01

**Shared setup:** `docker compose build web` at `e6732ff` (application source unchanged since 27 September), PostgreSQL started with `docker compose up --wait db`, migrations applied. Each pytest run uses its own disposable test database and no demo data. The first two lines of every raw file record the date, commit and exact command. **Expected result** for each case was "every selected test passes, 0 failed, 0 errors"; the test count is taken from the run, not fixed beforehand (the cases were run and then written up, so the counts are not independent predictions).

### SEC-12: Production configuration

**Objective:** Verify that production settings refuse unsafe configuration and enable secure cookies, HTTPS redirect, HSTS and verified database TLS.

**Threat/requirement:** T10, T11, and the cookie part of T7; the non-superuser database role (T9, T17).

**Command:** `docker compose run --rm --no-deps web pytest -v -p no:cacheprovider /app/tests/test_settings.py`

**Actual result:** 14 passed in 5.54s; exit 0. [Raw output](raw/SEC-12_2026-10-01.txt).

**Status:** PASS

**Interpretation:** The nine parametrised cases show startup fails for an empty or short secret key, wildcard hosts, an unknown environment, a non-boolean or production debug flag, a bad HSTS value, a non-private probe host and an unsafe release id. `test_production_configuration` asserts debug off, Secure session and CSRF cookies, SSL redirect, HSTS 3600 s and `sslmode=verify-full`; the rest cover the non-superuser role, the RDS certificate bundle, shared database sessions and non-secret startup output.

**Limitations/follow-up:** Settings-level only. Behaviour through the deployed ALB is SEC-10. HSTS is intentionally short (3600 s) and without subdomains or preload (SCAN-04).

### SEC-13: Secret loading

**Objective:** Verify production secret retrieval rules.

**Threat/requirement:** T8 secrets exposure.

**Command:** `docker compose run --rm --no-deps web pytest -v -p no:cacheprovider /app/tests/test_secrets.py`

**Actual result:** 9 passed in 0.41s; exit 0. [Raw output](raw/SEC-13_2026-10-01.txt).

**Status:** PASS

**Interpretation:** Production retrieves once and overrides plaintext credentials; a missing production selection cannot fall back to plaintext; incomplete or wrong secret schemas are refused; SDK errors are redacted with the cause suppressed; static SDK credentials are rejected; local mode never imports or calls AWS.

**Limitations/follow-up:** The AWS call is mocked. Retrieval by a running instance is SEC-11 (planned).

### SEC-14: Health endpoint and Host handling

**Objective:** Verify the health route cannot be used to bypass host validation or leak internals.

**Threat/requirement:** T11 security misconfiguration.

**Command:** `docker compose run --rm --no-deps web pytest -v -p no:cacheprovider /app/tests/test_health.py`

**Actual result:** 10 passed in 1.26s; exit 0. [Raw output](raw/SEC-14_2026-10-01.txt).

**Status:** PASS

**Interpretation:** The health route runs no database query, rejects mutations, validates the Host header, allows only the exact internal probe address while normal host validation still applies elsewhere, and returns a sanitised message when the database is down.

**Limitations/follow-up:** Local client only; the real ALB probe is not tested here.

### SEC-15: Request logging

**Objective:** Verify the log format and what it omits.

**Threat/requirement:** T12 detection, T8 logs.

**Command:** `docker compose run --rm --no-deps web pytest -v -p no:cacheprovider /app/tests/test_request_logging.py`

**Actual result:** 19 passed in 3.15s; exit 0. [Raw output](raw/SEC-15_2026-10-01.txt).

**Status:** PASS

**Interpretation:** One JSON line per request with documented fields; unsafe incoming request IDs are replaced and safe ones kept; no password, cookie, query string or exception message is logged; Django security-logger messages are replaced by a fixed one; logging never queries the database. SEC-08 selects three of these tests; this case runs the whole file.

**Limitations/follow-up:** Local standard output only. CloudWatch ingestion and the 5xx alarm are MON-02 (planned).

### SEC-16: Imported customers cannot log in

**Objective:** Verify imported customers receive an unusable password.

**Threat/requirement:** T17 (account takeover through imported identities).

**Command:** `docker compose run --rm --no-deps web pytest -v -p no:cacheprovider /app/tests/test_import.py::test_counts_mappings_rounding_and_sealed_inventory`

**Actual result:** 1 passed in 1.46s; exit 0. [Raw output](raw/SEC-16_2026-10-01.txt).

**Status:** PASS

**Interpretation:** The test asserts `not user.has_usable_password()` for imported profiles, along with its import-count checks.

**Limitations/follow-up:** Does not cover the customer-segment display references (`CUS-<id>`, no usernames); that part of T17 remains unrecorded.

### SEC-ALL rerun

**Objective:** Rerun the 25 test IDs of the 26 September SEC-ALL on the current commit.

**Command:** the 25 node IDs are listed in the first line of the raw file; `docker compose run --rm --no-deps web pytest -v -p no:cacheprovider <ids>`.

**Actual result:** 25 passed in 4.17s; exit 0. [Raw output](raw/SEC-ALL-rerun_2026-10-01.txt). **Status:** PASS.

### SCAN-01 to SCAN-07: automated security scans

Seven tools, raw output and a finding-by-finding triage are in [security-scan-triage.md](security-scan-triage.md). Headline: no secret in git history or the tree (one false positive), no known vulnerable pinned Python dependency, no Dockerfile lint finding. Open items: 21 fixable Debian package findings in the image (needs a newer pinned base digest, a frozen change) and the infrastructure items listed there for the Terraform owner. These scans ran locally, not in CI.

## SEC-09 to SEC-11: Cloud controls

**Status:** PLANNED. These require the AWS deployment and real resource names; no AWS commands were run by this evidence workflow.

**Verified by:**
