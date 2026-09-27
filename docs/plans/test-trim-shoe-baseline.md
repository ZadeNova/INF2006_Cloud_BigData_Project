# Test trim after the shoe-baseline gate

Written 27 September 2026, branch `syah&hermann/ML`. Approved by the user from the redundancy audit
recorded in [shoe-baseline-gate.md](../reviews/shoe-baseline-gate.md) (round 3). Removes 7 cases; each
case catches no defect that a kept case does not also catch.

| Change | Kept case that still catches the defect |
|---|---|
| Remove `test_catalogue.py::test_toggle_forbidden_for_non_operators` | `test_security_negative.py::test_a_customer_cannot_use_the_operator_toggle` (same anonymous/customer 403 and unchanged-state assertions; cited by SEC-02) |
| Remove `test_catalogue.py::test_chosen_size_is_added_to_the_cart` | `test_cart.py::test_add_creates_a_new_cart_item`: a size is a Product ID posted to `cart:add`, the same path |
| `test_toggle_is_idempotent_under_double_submit`: keep deactivate, drop activate | The view sets the posted value with no per-direction branch; one direction still catches a flip-toggle regression |
| `test_add_ignores_a_next_outside_the_shop`: keep `//evil.example/products/` and `/products/manage/`, drop `https://…` and `/orders/` | All four fail the same `/products/` prefix check except the manage exclusion |
| `test_toggle_ignores_a_next_outside_the_manage_list`: keep `//evil.example/`, drop `https://…` and `/cart/` | All three fail the same `/products/manage/` prefix check |

Not changed: the anonymous cart matrix, `BAD_QUANTITIES` (SEC-04 cites its parameter IDs) and the
segment-loader matrix. Historical raw evidence (for example `FUNC-01_2026-09-26.txt`) lists removed test
names; it records a past run and is left unchanged.

Verification: `pytest /app/tests/test_catalogue.py /app/tests/test_cart.py` in the web image.
