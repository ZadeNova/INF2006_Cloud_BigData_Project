# Opus review fixes: OPUS-001, OPUS-002, OPUS-003

Written 24 September 2026 from [opus-delta-review.md](../reviews/opus-delta-review.md). The user asked for all three to be fixed, then committed.

| ID | Change | Files |
|---|---|---|
| OPUS-001 | `RedirectView` on `/` allows only GET and HEAD, restoring the 405 for other methods that `/` had as a `require_safe` view. New test: `POST /` is 405. | `src/config/urls.py`, `tests/test_frontend.py` |
| OPUS-002 | The checkout summary row reads "N product(s)" with N counting **available** lines, so it agrees with the subtotal beside it. The view supplies `available_count`. The existing deactivated-line test also asserts the row. | `src/orders/views.py`, `src/templates/orders/checkout.html`, `tests/test_orders.py` |
| OPUS-003 | The brand link goes to `catalogue:product_list` and `LOGOUT_REDIRECT_URL` becomes `/products/` (matching `LOGIN_REDIRECT_URL`), removing the extra hop through `/`. The logout test now expects `/products/`. `/` keeps working for direct visits. | `src/templates/base.html`, `src/config/settings.py`, `tests/test_accounts.py` |

Verification: the full suite (a shared template and a setting change), `manage.py check`, then one live HTTP check of the three behaviours. Then update the review log to resolved, the tracker and the review brief. Commit only when asked.
