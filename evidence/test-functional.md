# Functional workflow test

## Summary

| Case | Proves | Threat/requirement | Environment | Date | Commit | Status |
|---|---|---|---|---|---|---|
| FUNC-01 | The automated account, catalogue, cart, checkout and order-history tests pass | Brief section 4 Application: a functioning web application with a meaningful user workflow and input validation | Local Docker | 2026-09-26 | `ee334cf` | PASS |
| FUNC-02 | A person can complete the customer purchase flow and the operator product and dashboard steps in a browser | Brief section 5.2 test (1): functional workflow test | Local Docker | — | — | NOT RUN YET |

## FUNC-01: Automated workflow tests

**Objective:** Show that the core customer workflow—registration, login, catalogue browsing, cart, checkout and order history—and its input validation behave as specified using the automated tests.

**Threat/requirement:** Brief section 4 Application: a functioning web application with at least one meaningful user workflow and input validation.

**Setup:** Local Docker Compose stack (`web`, `db`). The web image must be rebuilt with `docker compose build web` immediately before the test so the run uses the current `merge-quarantine` source.

**Command/steps:**

```bash
export MSYS_NO_PATHCONV=1   # Git Bash on Windows only: keep /app paths unchanged
docker compose run --rm -T web pytest -v -p no:cacheprovider /app/tests/test_accounts.py /app/tests/test_catalogue.py /app/tests/test_cart.py /app/tests/test_orders.py 2>&1 | tee evidence/raw/FUNC-01_$(date +%F).txt
```

**Expected result:** 0 failed, 0 errors. Every collected test passes.

**Actual result (from [raw/FUNC-01_2026-09-26.txt](raw/FUNC-01_2026-09-26.txt)):** 93 tests were collected and all 93 passed in 17.64 seconds. The raw command exited with status 0. Excerpt:

```text
collecting ... collected 93 items
tests/test_catalogue.py::test_product_list_shows_one_card_per_shoe_with_its_active_sizes PASSED [ 18%]
tests/test_catalogue.py::test_product_list_paginates_at_twelve_per_page PASSED [ 22%]
tests/test_cart.py::test_add_rejects_inactive_product PASSED [ 43%]
tests/test_orders.py::test_review_page_total_leaves_out_a_deactivated_product_like_the_cart_does PASSED [ 67%]
tests/test_orders.py::test_order_list_shows_only_the_owners_orders_most_recent_first PASSED [ 89%]
tests/test_orders.py::test_concurrent_checkouts_different_users_racing_last_unit_of_stock PASSED [100%]
============================= 93 passed in 17.64s ==============================
pytest_exit=0
```

**Status:** PASS

**Interpretation:** The current merge-quarantine source passes the automated account, catalogue, cart, checkout and order-history workflow suite. The run includes the shoe catalogue and size behavior, pagination, inactive-product handling, cart/order ownership, subtotal behavior and concurrent checkout cases. This proves the tested server behavior in the local Docker test environment; it does not prove a real browser walkthrough or AWS behavior, which are separate cases.

**Automated equivalent:** This case is itself the automated equivalent and can be rerun with the command above.

**Artefacts:** [raw/FUNC-01_2026-09-26.txt](raw/FUNC-01_2026-09-26.txt)

**Date/commit:** 2026-09-26, `ee334cf`

**Limitations/follow-up:** Local Docker only. FUNC-02 still needs the human browser walkthrough on this same merge-quarantine source. The test database is created and removed by pytest; the demo database used for FUNC-02 is separate.

**Verified by:**

**Run history:**

| Date | Commit | Environment | Status | Raw file |
|---|---|---|---|---|
| 2026-09-26 | `ee334cf` | Local Docker | PASS (93 passed) | [raw/FUNC-01_2026-09-26.txt](raw/FUNC-01_2026-09-26.txt) |

## FUNC-02: Manual browser walkthrough

**Objective:** Show that a person using a browser can complete the customer purchase flow end to end, and that an operator can manage products and open the analytics dashboard while a customer cannot.

**Threat/requirement:** Brief section 5.2 test (1): functional workflow test.

**Setup:** Fresh local database loaded following the "Demo data" section of `src/README.md` after FUNC-01. This case will be run only after the human reviewer agrees to reset the disposable local database if existing data conflicts with the import.

**Command/steps and expected result for each step:**

| Step | Action | Expected result |
|---|---|---|
| 1 | Open `/` | Redirects to the catalogue |
| 2 | Register a new account at `/register/` | The expected behavior is recorded from the current merge-quarantine implementation; any redirect or login step is reported exactly as observed |
| 3 | Add two products to the cart, then change one quantity | The cart shows both lines with the right subtotal |
| 4 | Check out | A confirmation page with an order number and total |
| 5 | Open `/orders/` | The new order is listed first |
| 6 | Log in as `demo-operator`, deactivate a product at `/products/manage/`, then reactivate it | The deactivated product disappears from `/products/`; it returns after reactivation |
| 7 | As the operator, open `/analytics/` | The dashboard renders |
| 8 | As the customer, open `/analytics/` | Access is refused |

**Actual result (in progress, 2026-09-26; each row records the tester's report):**

| Step | Reported result |
|---|---|
| 1 | Tester reported: `http://127.0.0.1:8000/products` and "shoe products". This matches the expected redirect from `/` to the shoe catalogue. The screenshot shared in the session shows the current shoe catalogue with 20 products and the current 42Factors presentation; it has not been saved as a submission artifact. |
| 2 | Tester registered the customer account `merge-shopper` and reported being redirected to `/login/`. The password was not copied into evidence. The tester then logged in successfully and reported landing at `/products`. This is recorded as the observed current behavior; registration did not automatically authenticate the new account, but a separate login completed successfully. |
| 3 | The current cart screenshot shows two different shoes: Adidas Runner "Core Black", US 9.5, S$175.00 each, quantity 2, line total S$350.00; and Adidas Yellow & Black Runner, US 9.5, S$169.00 each, quantity 1, line total S$169.00. The cart shows 2 items and subtotal S$519.00. Arithmetic check: 175.00 × 2 = 350.00; 350.00 + 169.00 = 519.00. Step 3 matched the expected result. The screenshot has not been saved as a submission artifact. |
| 4 | The checkout review screenshot shows the same two shoes, quantities and line totals, with total S$519.00 and simulated payment. The confirmation screenshot shows order #100001, status Completed, payment Simulated and Paid S$519.00. The confirmation was placed on 26 September 2026 at 15:38. The review and confirmation totals match. Step 4 matched the expected result. The screenshots have not been saved as submission artifacts. |
| 5 | The current order-history screenshot shows one order listed: #100001, dated 26 Sep 2026 at 15:38, status Completed, 2 items and total S$519.00. It is the newest and only order, so it appears first. Step 5 matched the expected result. The screenshot has not been saved as a submission artifact. |
| 6 (operator deactivation) | Tester reported that `Adidas Runner "Core Black" · US 9.5` disappeared after deactivation. The read-only database check ([raw/FUNC-02_2026-09-26_step6-deactivated-check-rerun2.txt](raw/FUNC-02_2026-09-26_step6-deactivated-check-rerun2.txt)) confirms one matching row with `active False` and 199 active products total. The public catalogue response does not render individual size options in this list view, so its zero `US 9.5` text matches is treated as inconclusive rather than as separate proof. The human observation plus database state confirm the selected size was deactivated while other sizes kept the shoe available. |
| 6 (operator reactivation) | Tester reported that the size was back after activation. A read-only double check ([raw/FUNC-02_2026-09-26_step6-reactivated-check-rerun2.txt](raw/FUNC-02_2026-09-26_step6-reactivated-check-rerun2.txt)) shows one matching row with `active True` and 200 active products total. The public list does not render individual size options, so its zero size-text match is inconclusive; the tester's current browser observation confirms the size returned. Step 6 is recorded as complete from the human observation plus database state. |
| 7 | The tester supplied a current structured description of the 42Factors dashboard, generated with Gemini. The current web log ([raw/FUNC-02_2026-09-26_step7-current-crosscheck-rerun2.txt](raw/FUNC-02_2026-09-26_step7-current-crosscheck-rerun2.txt)) records two operator `GET /analytics/` requests with status 200. The database cross-check agrees with the supplied current summary: run short ID `4ad3626c` (full run `9525f59f-5cbe-4e92-a127-5923ffc1f530`), cutoff 02 Jan 2026 00:00 SGT, refreshed 26 Sep 2026 15:26 SGT, 30-day sales S$4,205,903.16, 7,899 units, 01 Jan sales S$43,078.98 and 89 units, categories Luxury S$2,910,489.99 / 1,293 units through Classics S$147,580.38 / 1,334 units, all ten size totals, the listed top shoes, 80 flagged products, 9 without recent sales and 0 with insufficient history. No customer-segmentation rows were reported in the supplied dashboard description. Step 7 matched the expected result. Gemini use must be included in `AI_USE_DECLARATION.md`. |
| 8 | The current screenshot shows the customer at `/analytics/` receiving a plain **403 Forbidden** page. The web log ([raw/FUNC-02_2026-09-26_step8-analytics-check.txt](raw/FUNC-02_2026-09-26_step8-analytics-check.txt)) confirms the switch to customer `user_id=20002` and `GET /analytics/` with status 403 at 07:52:24. Step 8 matched the expected result. The screenshot has not been saved as a submission artifact. |

**Status:** PASS

**Interpretation:** The human browser walkthrough completed the customer registration/login, shoe catalogue, cart quantity update, simulated checkout, order history, operator size deactivation/reactivation, operator analytics dashboard and customer analytics denial. The operator dashboard and customer 403 were also confirmed in the current web log. The first setup attempt recorded that the README's host Python generator could not run because no Python runtime was installed. Python 3.13.15 was then installed for the current user, the user PATH was refreshed, and the exact generator command was rerun successfully with exit code 0 ([raw/FUNC-02_2026-09-26_generator-fixed-clean.txt](raw/FUNC-02_2026-09-26_generator-fixed-clean.txt)). The generated CSVs remain ignored/untracked outputs, but they can now be recreated from the tracked generator on a machine with Python 3.

**Automated equivalent:** FUNC-01 covers the server-side account, catalogue, cart, checkout and order-history workflow. The later security evidence should cover the operator permission and customer dashboard 403 tests independently.

**Artefacts:**

- [raw/FUNC-02_2026-09-26_setup.txt](raw/FUNC-02_2026-09-26_setup.txt): database reset, shoe import, operator seed and analytics refresh
- [raw/FUNC-02_2026-09-26_generator.txt](raw/FUNC-02_2026-09-26_generator.txt): failed host Python generator attempt
- [raw/FUNC-02_2026-09-26_step6-deactivated-check-rerun2.txt](raw/FUNC-02_2026-09-26_step6-deactivated-check-rerun2.txt) and [raw/FUNC-02_2026-09-26_step6-reactivated-check-rerun2.txt](raw/FUNC-02_2026-09-26_step6-reactivated-check-rerun2.txt): read-only size state checks
- [raw/FUNC-02_2026-09-26_step7-current-crosscheck-rerun2.txt](raw/FUNC-02-2026-09-26_step7-current-crosscheck-rerun2.txt): current dashboard figures and operator requests
- [raw/FUNC-02_2026-09-26_step8-analytics-check.txt](raw/FUNC-02-2026-09-26_step8-analytics-check.txt): customer login and 403 request
- Browser screenshots: shown in the session but not saved as files

**Date/commit:** 2026-09-26, `ee334cf`

**Limitations/follow-up:** Local Docker only; no AWS behavior is shown. The derived CSVs used by the successful import were already present locally but are not tracked, so the team should make the generator/runtime path reproducible before final submission. Gemini was used to structure the dashboard description and must be listed in `AI_USE_DECLARATION.md`. The malformed first size-check raw file and its clean reruns are retained to keep the command history honest.

**Verified by:**

**Run history:**

| Date | Commit | Environment | Status | Raw file |
|---|---|---|---|---|
| 2026-09-26 | `ee334cf` | Local Docker | PASS | [raw/FUNC-02_2026-09-26_setup.txt](raw/FUNC-02_2026-09-26_setup.txt) and the step-specific files listed above |
