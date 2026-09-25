# Test trim (25 September 2026)

Source: the fresh-session review of `erfan/analytics` at `f72a872` ([log](../reviews/test-trim.md)). The user approved plan item 6, the test trim, on its own; items 1 and 2 (loader privacy, ML k choice) are discussed next.

## Rule

AGENTS.md "Simplicity and maintainability": cover each rule once at its layer, and parametrise only across inputs that reach different code paths. A case is removed only when mutation evidence (or, where marked, a stated equivalence) shows a kept test catches every defect it catches. Protected: real-thread concurrency, database constraint/trigger tests, checkout idempotency and locking, security negatives for distinct routes, leap-year and date-boundary cases that are not covered elsewhere.

## Changes (466 → 392 collected)

| File | Change | Cases |
|---|---|---|
| `test_security_negative.py` | CSRF rejection: one forged form field per route (the app's HTMX posts the form field, never the header); controls lose the HTMX copy; bad quantities keep `0`, `abc`, empty | −19 |
| `test_cart.py` | Delete the anonymous add pair and the `[0, 1000]` update bounds (duplicated in `test_security_negative.py`) | −4 |
| `test_orders.py` | Malformed review keeps empty and `not-hex`; delete `test_checkout_requires_login` (the anonymous POST test covers the same mixin) | −4 |
| `test_analytics_ranges.py` | Delete `coerce_range` test (dead code, S-007), the comparison matrix, the rolling-length test; granularity keeps 90/91; tiling keeps `90d`/`ytd` at 31 Dec 2024; `latest_complete_date` drops the 10:00 and 2 Jan cases | −32 |
| `test_analytics_dashboard.py` | Range derivation: one key (`90d`); `test_get_only`: one method | −6 |
| `test_db_unavailable.py` | Two routes: an anonymous catalogue GET (the outage reaches the view's own query, which no test covered) and a logged-in checkout POST | −4 |
| `test_request_logging.py` | Unsafe request ID keeps too short, too long, newline injection | −2 |
| `test_schema.py` | Cart quantity keeps 0 and 1000; remove the illustrative constant arithmetic | −1 |
| `test_analytics_snapshot.py` | Date offset keeps −1 and +1 | −1 |
| `test_accounts.py` | Delete `test_logout_requires_post` (Django's LogoutView behaviour) | −1 |

Source change: delete `reporting.ranges.coerce_range` (S-007; no caller outside its test).

Not in this change: new tests (F-02, F-03, S-001, M-01) and the vacuous `demo-operator` assertion, which belong with plan items 1 to 4.

## Verification

Full suite, `manage.py check`, `makemigrations --check --dry-run`; re-run the CSRF-exempt mutant against the rewritten CSRF test, and a swallowing-view mutant against the new anonymous outage case.
