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
| SEC-09 | RDS and S3 are not publicly reachable | Cloud private data/storage controls | AWS | — | — | PLANNED |
| SEC-10 | HTTPS is enforced | Cloud transport security | AWS | — | — | PLANNED |
| SEC-11 | Runtime secrets come from Secrets Manager | Cloud secret handling | AWS | — | — | PLANNED |

**Shared setup:** the web image was rebuilt with `docker compose build web` at merge-quarantine commit `ee334cf`. The local Docker `web` and `db` services were healthy. Each pytest command used its own disposable test database and no demo data. Git Bash on Windows ran with `MSYS_NO_PATHCONV=1` so `/app/tests/...` paths remained container paths.

**Wrapper note:** a first wrapper attempt ran SEC-01 successfully but then failed to append its exit marker because the Bash script mistakenly called the PowerShell-only command `Tee-Object`. That wrapper issue is retained in the first raw file; it is not an application or test failure. The clean sequential rerun files with `_rerun` suffixes are the authoritative results below.

## SEC-01: Broken access control / IDOR

**Objective:** Verify that a user cannot retrieve another user's order or modify/delete another user's cart item by using its identifier.

**Threat/requirement:** T1 broken access control / IDOR, OWASP A01:2025.

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

## SEC-09 to SEC-11: Cloud controls

**Status:** PLANNED. These require the AWS deployment and real resource names; no AWS commands were run by this evidence workflow.

**Verified by:**
