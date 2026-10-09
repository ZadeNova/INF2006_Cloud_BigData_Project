# Security control test

## Results at a glance

Cloud cases (AWS: variant A on 8 October 2026, variant B on 9 October 2026, UTC; one run each). Local cases SEC-01 to SEC-08, SEC-12 to SEC-16 and SEC-ALL are all PASS (26 September and 1 October 2026) and are listed with their commits in the Summary table below; the scans are in [security-scan-triage.md](security-scan-triage.md). The A and B columns use the same wording on purpose.

| Case | What it proves | Result on A (EC2) | Result on B (Fargate) | Date (UTC) | Key artefact A | Key artefact B |
|---|---|---|---|---|---|---|
| SEC-09 | The database and the storage bucket cannot be reached from the internet; only the app tier reaches the database | **PASS**: RDS not publicly accessible and encrypted; the database group admits port 5432 only from the app group; bucket public access fully blocked, anonymous list and object requests return HTTP 403 | **PASS**: the same RDS result; the database group admits port 5432 only from B's app group (`sg-0604681cf6bb68d4c`); bucket and anonymous requests as on A | A 2026-10-08; B 2026-10-09 | [raw/SEC-09_2026-10-08_ec2_security-groups.txt](raw/SEC-09_2026-10-08_ec2_security-groups.txt) | [raw/SEC-09_2026-10-09_fargate_security-groups.txt](raw/SEC-09_2026-10-09_fargate_security-groups.txt) |
| SEC-10 | HTTPS is enforced with a TLS 1.2+ policy | **PASS**: `smoke.sh` 8 of 8; port 80 redirects (301) to HTTPS; port 443 uses `ELBSecurityPolicy-TLS13-1-2-2021-06` | **PASS**: `smoke.sh` 8 of 8; port 80 redirects (301) to HTTPS; port 443 uses `ELBSecurityPolicy-TLS13-1-2-2021-06` | A 2026-10-08; B 2026-10-09 | [raw/SEC-10_2026-10-08_ec2_listeners.txt](raw/SEC-10_2026-10-08_ec2_listeners.txt) | [raw/SEC-10_2026-10-09_fargate_listeners.txt](raw/SEC-10_2026-10-09_fargate_listeners.txt) |
| SEC-11 | Runtime secrets come from Secrets Manager, not from the launch template or task definition | **PASS**: user data names only secret names; all four consistency checks `match`; the app reports database ok and migrations applied. The instance role is the lab's broad `LabRole` | **PASS**: the task definition holds only non-secret settings and `AWS_SECRET_ID` (`secrets: null`); all four checks `match`; the app reports database ok and migrations applied. Task and execution roles are the lab's broad `LabRole` | A 2026-10-08; B 2026-10-09 | [raw/SEC-11_2026-10-08_ec2_runtime.txt](raw/SEC-11_2026-10-08_ec2_runtime.txt) | [raw/SEC-11_2026-10-09_fargate_runtime.txt](raw/SEC-11_2026-10-09_fargate_runtime.txt) |
| SEC-17 | The WAF blocks a login-guessing burst while browsing still works | **Not run on A, by decision**: the WAF is one shared module, so the block-mode test runs on B only | **PASS**: attempts 1 to 24 HTTP 200 from gunicorn, attempts 25 to 29 HTTP 403 from `awselb/2.0` (the load balancer), `GET /products/` still 200, `BlockedRequests` 5, 5 sampled `BLOCK` rows on `POST /login/` | A not run; B 2026-10-09 | none | [raw/SEC-17_2026-10-09_fargate_burst.txt](raw/SEC-17_2026-10-09_fargate_burst.txt) |
| SEC-18 | No password, cookie, CSRF token or secret key in the CloudWatch logs | **PASS**: 0 matches in 88,044 log records | **PASS**: 0 matches in 77,326 log records (the window includes the SEC-17 burst with wrong passwords in the form) | A 2026-10-08; B 2026-10-09 | [raw/SEC-18_2026-10-08_ec2_count_rerun.txt](raw/SEC-18_2026-10-08_ec2_count_rerun.txt) | [raw/SEC-18_2026-10-09_fargate_count.txt](raw/SEC-18_2026-10-09_fargate_count.txt) |

Reruns: `SEC-18` on A was run twice (the first at 17:52 UTC scanned 15,883 records before the saturation run; the `_rerun` scanned 88,044 and is cited). On B, `SEC-17_2026-10-09_fargate_samples.txt` is superseded by `SEC-17_2026-10-09_fargate_samples-burst.txt` (see SEC-17). All are kept in `raw/` and listed in [raw/INDEX.md](raw/INDEX.md).

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
| SEC-09 | RDS and S3 are not publicly reachable; only the app may reach the database | Cloud private data/storage controls | AWS, both variants | A 2026-10-08, B 2026-10-09 | `74d394a` (A), `33963c5` (B) | A PASS, B PASS |
| SEC-10 | HTTPS is enforced with a TLS 1.2+ policy | Cloud transport security | AWS, both variants | A 2026-10-08, B 2026-10-09 | `74d394a` (A), `33963c5` (B) | A PASS, B PASS |
| SEC-11 | Runtime secrets come from Secrets Manager through the lab role, never from the launch template or task definition | Cloud secret handling | AWS, both variants | A 2026-10-08, B 2026-10-09 | `74d394a` (A), `33963c5` (B) | A PASS, B PASS |
| SEC-17 | The WAF rate rule blocks a password-guessing burst on `POST /login/` while browsing still works | T7 credential guessing, edge control | AWS, B only | 2026-10-09 | `e4bc928` | Not run on A by decision (shared WAF module); B PASS |
| SEC-18 | No password, cookie, CSRF token or secret key in the CloudWatch logs after the session's traffic | T8 secrets in logs (SEC-08 on AWS) | AWS, both variants | A 2026-10-08, B 2026-10-09 | `3c910b8` (A, rerun), `e4bc928` (B) | A PASS, B PASS |

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

## SEC-09 to SEC-11, SEC-17, SEC-18: Cloud controls (variant A and variant B)

**Status (9 October 2026):** variant A was run on 8 October 2026 and variant B on 9 October 2026 (UTC). The expected results below were written on 8 October 2026, before any cloud run, and are unchanged. SEC-17 was run on B only.

**Shared setup:** the stack under test is up on the pinned image digest. Every command runs through `src/infrastructure/scripts/evidence.sh`, identically for `ec2` and `fargate`. Each raw file records its UTC time, git commit, the exact AWS commands and the exit code, and is redacted (account IDs, public IPs, email addresses) before it is written. Procedure and order: [docs/plans/evidence-session.md](../docs/plans/evidence-session.md).

### SEC-09: Database and storage are private

**Objective:** Show that neither the database nor the bucket can be reached from the internet, and that only the application tier may connect to the database.

**Command:** `src/infrastructure/scripts/evidence.sh <variant> security` (steps `SEC-09 RDS`, `SEC-09 security groups`, `SEC-09 S3`).

**Expected result:**

- RDS: `publicly_accessible: false`, `encrypted: true`, attached only to the `sg-db` group.
- Security groups: `sg-db` allows 5432 only from the app security group (no CIDR range); the app group allows 8000 only from the ALB group (no port 22, no CIDR range); the ALB group allows 80 and 443 from anywhere.
- S3: all four public-access-block settings `true`; no bucket policy, or `IsPublic: false`; anonymous list and object requests return HTTP 403.

**Actual result:**

| Variant | Result | Raw files | Status |
|---|---|---|---|
| A | RDS `inf2006-grp21-db`: `publicly_accessible: false`, `encrypted: true`, Multi-AZ off, one security group (`sg-03abb4562e4857842`, the database group). Security groups: the database group admits TCP 5432 only from the app group (no CIDR range); the app group admits TCP 8000 only from the load balancer group (no port 22, no CIDR range); the load balancer group admits 80 and 443 from `0.0.0.0/0`. S3 bucket: all four public-access-block settings `true`, policy status `IsPublic: false`, anonymous list request HTTP 403, anonymous object request HTTP 403. Every line matches the expectation. Limits: configuration read through the AWS API plus two anonymous HTTP requests from the laptop; no port scan of the database endpoint; outbound rules not examined | `raw/SEC-09_2026-10-08_ec2_rds.txt`, `raw/SEC-09_2026-10-08_ec2_security-groups.txt`, `raw/SEC-09_2026-10-08_ec2_s3.txt` (15:04:58 to 15:05:10 UTC, commit `74d394a`) | **PASS** |
| B | RDS `inf2006-grp21-db`: `publicly_accessible: false`, `encrypted: true`, Multi-AZ off, one security group (`sg-03abb4562e4857842`, the database group). Security groups: the database group admits TCP 5432 only from B's app group (no CIDR range); B's app group admits TCP 8000 only from B's load balancer group (no port 22, no CIDR range); B's load balancer group admits 80 and 443 from `0.0.0.0/0`. S3 bucket: all four public-access-block settings `true`, `IsPublic: false`, anonymous list and object requests HTTP 403. Matches the expectation. Same limits as A | `raw/SEC-09_2026-10-09_fargate_rds.txt`, `raw/SEC-09_2026-10-09_fargate_security-groups.txt`, `raw/SEC-09_2026-10-09_fargate_s3.txt` (02:02:56 to 02:03:11 UTC, commit `33963c5`) | **PASS** |

### SEC-10: HTTPS is enforced

**Objective:** Show that the shop is served only over verified TLS and that plain HTTP is redirected.

**Command:** `evidence.sh <variant> security` (steps `SEC-10 smoke`, `SEC-10 listeners`).

**Expected result:** `smoke.sh` 8 of 8 PASS (HTTP 301 to `https://`, certificate verifies, TLS 1.2 or 1.3, HSTS, `X-Content-Type-Options` and `X-Frame-Options` present). Listeners: port 80 `redirect` to HTTPS; port 443 `HTTPS` with policy `ELBSecurityPolicy-TLS13-1-2-2021-06`.

**Actual result:**

| Variant | Result | Raw files | Status |
|---|---|---|---|
| A | `smoke.sh ec2`: 8 of 8 PASS (`/health/` 200, HTTP redirects to HTTPS with 301, certificate verifies, `/login/` 200, `/products/` lists 12 distinct products, `strict-transport-security`, `x-content-type-options`, `x-frame-options` present). Listeners: port 443 `HTTPS`, policy `ELBSecurityPolicy-TLS13-1-2-2021-06`, action forward; port 80 `HTTP`, action redirect to HTTPS 443 with `HTTP_301`. Matches the expectation. Limit: the TLS version is taken from the policy name, not from a handshake test | `raw/SEC-10_2026-10-08_ec2_smoke.txt`, `raw/SEC-10_2026-10-08_ec2_listeners.txt` (15:04:48 to 15:04:58 UTC, commit `74d394a`) | **PASS** |
| B | `smoke.sh fargate`: 8 of 8 PASS (the same eight checks as on A). Listeners: port 443 `HTTPS`, policy `ELBSecurityPolicy-TLS13-1-2-2021-06`, forward; port 80 redirect to HTTPS 443 with `HTTP_301`. Matches the expectation. Same limit: the TLS version is taken from the policy name | `raw/SEC-10_2026-10-09_fargate_smoke.txt`, `raw/SEC-10_2026-10-09_fargate_listeners.txt` (02:02:47 to 02:02:56 UTC, commit `33963c5`) | **PASS** |

### SEC-11: Runtime secrets come from Secrets Manager

**Objective:** Show that the running application gets its database password and Django key from Secrets Manager through the lab role, and that no secret value is stored in the launch template (A) or task definition (B).

**Command:** `evidence.sh <variant> security` (steps `SEC-11 runtime`, `SEC-11 secrets match`, `SEC-11 the app reads them`).

**Expected result:**

- A: the launch template's instance profile is the lab profile; the decoded user data names only `AWS_SECRET_ID` (a secret's name), with no password or key value.
- B: the task and execution roles are `LabRole`; the environment holds only non-secret settings and `AWS_SECRET_ID`; there is no `secrets` value in plain text.
- `secrets.sh check`: every field `match`, key names only, no values.
- `jobs.sh <variant> check`: the app, started with the secret, reports the database reachable and migrations applied.

**Actual result:**

| Variant | Result | Raw files | Status |
|---|---|---|---|
| A | Launch template instance profile is `LabInstanceProfile`. The decoded user data lines naming a secret, password or key hold only comments, the secret names `inf2006-grp21/web` and `inf2006-grp21/$job` as `AWS_SECRET_ID`, and the registry login (`aws ecr get-login-password | docker login --password-stdin`, a token made at boot, not stored). No password or key value. `secrets.sh check`: runtime login, migration login, signing key, host and db all `match`, key names only. `jobs.sh ec2 check`: `{"database": "ok", "migrations": "applied"}`. Matches the expectation. Limit: the instance runs as the lab's broad `LabRole` because the lab denies creating narrower roles, so the secret is read through a role that can read more than this one secret | `raw/SEC-11_2026-10-08_ec2_runtime.txt`, `raw/SEC-11_2026-10-08_ec2_secrets-check.txt`, `raw/SEC-11_2026-10-08_ec2_app-check.txt` (15:05:10 to 15:05:43 UTC, commit `74d394a`) | **PASS** |
| B | Task and execution roles are `LabRole`. The task definition environment holds only non-secret settings (`APP_RELEASE_ID`, `DJANGO_ENV`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_HSTS_SECONDS`, `DJANGO_TRUST_PROXY`, `AWS_REGION`, `DJANGO_CSRF_TRUSTED_ORIGINS`) and `AWS_SECRET_ID` (`inf2006-grp21/web`); `secrets` is `null`. `secrets.sh check`: all four `match`. `jobs.sh fargate check` (a one-off task): `{"database": "ok", "migrations": "applied"}`. Matches the expectation. Same limit: the broad `LabRole` | `raw/SEC-11_2026-10-09_fargate_runtime.txt`, `raw/SEC-11_2026-10-09_fargate_secrets-check.txt`, `raw/SEC-11_2026-10-09_fargate_app-check.txt` (02:03:11 to 02:04:30 UTC, commit `33963c5`) | **PASS** |

### SEC-17: WAF blocks a login burst

**Objective:** Show that the edge rate rule on `POST /login/` (20 requests per 5 minutes per IP) blocks password guessing from one address in block mode, and that ordinary browsing is not affected.

**Setup:** The stack is switched to block mode with `evidence.sh <variant> pin 1 1 1 block` (plan and apply recorded). This is the last test on a variant, because the load tests send hundreds of logins from one IP and run in count mode.

**Command:** `evidence.sh <variant> waf`: one `POST /login/` every 3 s with a valid CSRF token and a wrong password for the non-existent user `waf-probe`, until 5 WAF blocks in a row or 80 attempts; then one `GET /products/`; then the WAF metrics and the sampled requests (request headers removed, because they carry cookies).

**Expected result:** The first POSTs return HTTP 200 (Django shows the login form again). After more than 20 POSTs, within the rule's evaluation delay (about a minute, unverified), the POSTs return 403 with `Server: awselb/2.0`, which is the load balancer's WAF response and not Django's 403. `GET /products/` still returns 200. `BlockedRequests` is above 0 for the rule. The sampled requests show `Action: BLOCK` on `POST /login/`.

**Actual result:**

| Variant | Attempt of first block | Result | Raw files | Status |
|---|---|---|---|---|
| A | not run | **Not run on A, by decision (9 October 2026).** The WAF rule is one shared Terraform module (`modules/web-entry`), so the block test is run on B only and the result is stated to cover both. On A the WAF stayed in count mode: its login-rule `CountedRequests` metric recorded values during the scale-out and saturation runs (up to 69 in one minute in the saturation run) and `BlockedRequests` stayed empty, as count mode should (`cloudwatch/waf_login_counted.csv`, `waf_login_blocked.csv` in those run folders). That shows the rule exists and sees login requests, not that it blocks | none for A | not run |
| B | attempt 25 | `POST /login/` with a valid CSRF token and a wrong password for `waf-probe`, every 3 s, from 06:54:17 UTC: **attempts 1 to 24 HTTP 200** (`server gunicorn`, Django showing the login form), **attempts 25 to 29 HTTP 403** (`server awselb/2.0`, the load balancer's WAF response, not Django's), the run stopped after 5 blocks in a row; then **`GET /products/` HTTP 200**. `BlockedRequests` for the rule `inf2006-grp21-fargate-login-rate`: sum 5 in the 06:56 UTC minute. Sampled requests for the burst window: 5 requests, all `Action: BLOCK`, `POST`, `/login/`, timestamps 06:56:19 to 06:56:38 UTC. Every item of the expectation is met; the first block came after 24 allowed attempts, within the rule's evaluation delay. Before the test the rule had been in count mode through the load runs (`CountedRequests` between 15 and 65 per minute from 14:29 to 14:43 SGT in the metrics file, which covers the saturation run) | `raw/SEC-17_2026-10-09_fargate_burst.txt`, `raw/SEC-17_2026-10-09_fargate_metrics.txt`, **`raw/SEC-17_2026-10-09_fargate_samples-burst.txt`** (authoritative; 06:49 to 07:03 UTC, commit `e4bc928`); block-mode plan and apply `raw/OPS_2026-10-09_fargate_pin-1-1-1-block_{plan,apply}.txt` | **PASS** |

**Limitation:** One source IP; a distributed guessing attack below 20 attempts per IP per 5 minutes is not stopped by this rule (stated in the threat model).

### SEC-18: No secrets in the CloudWatch logs

**Objective:** The cloud half of SEC-08: after the session's real traffic (registrations, logins, checkouts, the WAF burst with passwords in the form), the application logs in CloudWatch hold no secret value.

**Command:** `evidence.sh <variant> logs` (steps `SEC-18 count` and `SEC-18 matches`): a Logs Insights search over the session window for `password`, `csrftoken`, `csrfmiddlewaretoken`, `sessionid` and `secret_key`, case-insensitive.

**Expected result:** 0 matches. Any match is read line by line: a URL path or a log message that names a word without a value (for example a route name) is acceptable and is explained here; a value of any of them is a FAIL.

**Actual result:**

| Variant | Matches | Result | Raw files | Status |
|---|---|---|---|---|
| A | 0 | Both searches `Complete`, 0 matches over 88,044 scanned records (log group `/inf2006-grp21-ec2/app`, window 12:51 to 18:51 UTC, covering the stack's whole life). Traffic in the window: smoke, scale-out, replacement and saturation runs (logins and checkouts), the database jobs and the 400 rejections. The first run (17:52 UTC, 15,883 records) also found 0. Limits: the SEC-17 burst with wrong passwords in the form was not run on A, and the application does not log request bodies, headers or query strings by design (SEC-15), so this confirms that design under real traffic rather than discovering a leak that a log-everything setup would have had | `raw/SEC-18_2026-10-08_ec2_count_rerun.txt`, `raw/SEC-18_2026-10-08_ec2_matches_rerun.txt` (first run: the same names without `_rerun`) | **PASS** |
| B | 0 | Both searches `Complete`, 0 matches over 77,326 scanned records (window ending 07:11 UTC, covering the whole B stack including the SEC-17 burst with wrong passwords in the form, and the load runs). Same limit: the application does not log request bodies, headers or query strings by design (SEC-15). A single run; no rerun was needed | `raw/SEC-18_2026-10-09_fargate_count.txt`, `raw/SEC-18_2026-10-09_fargate_matches.txt` | **PASS** |
