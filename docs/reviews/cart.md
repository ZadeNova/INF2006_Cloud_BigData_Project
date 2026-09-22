# Cart review

Task ID `cart`. Round 1 of the independent backend review gate ([DEVELOPMENT.md](../DEVELOPMENT.md#backend-review-gate)); brief: [astra-review.md](../plans/astra-review.md). Report received 20 September 2026 from the project's teammate running Astra as the independent reviewer (model and reasoning level are not stated in the report). Log written by the coordinator (the user with Claude Code) from that report.

- **Base and snapshot:** `c0c1bfb..0c13334`. Reviewed PR head `d0922916e12c9df6c582c369032b70c975c967b4`.
- **Owned paths:** `src/cart/services.py`, `views.py`, `forms.py`, `urls.py`, `src/templates/cart/`, the Add-to-Cart control in `src/templates/catalogue/_product_card.html`, `tests/test_cart.py`.
- **Specs:** [API.md](../API.md) cart rows and HTMX contract, [SCHEMA.md](../SCHEMA.md) Cart/CartItem, plan [batch-03-cart.md](../plans/batch-03-cart.md).
- **Status:** Gate cleared. Round 2 resolved CART-001 and CART-002; rounds 3 and 4 did not reopen them (final head `7eea9b7`). Fixes were made by the user with Claude, not Astra Low.

## Checks and limitations

Environment: built from Git into a separate Docker image with pinned dependencies and PostgreSQL, disposable database, non-superuser role; fresh migrations, `manage.py check` and `makemigrations --check --dry-run` passed; full suite 301 passed. The literal root Compose commands were not run; the host checkout was not edited.

Task-specific: all 26 committed cart tests passed. CART-001 was reproduced. The lock-removal experiment (both `select_for_update` calls removed in memory) also passed 26/26, confirming CART-002. An initial mutation-harness run recreated the exception class and caused four unrelated failures; after preserving the original exception class, the corrected experiment produced the result quoted. No repository source was changed.

## Findings

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| CART-001 | High | `cart/services.py:57` | Batch 3: updating a missing item returns 404. Reproduced deletion between the view lookup and the locked service lookup. | If another tab removes the item, or checkout consumes it, after the view's initial lookup, the locked `get()` raises an uncaught `CartItem.DoesNotExist` and the request becomes a 500. Map disappearance at the authoritative locked lookup to 404. Add a regression covering that interleaving. | Fixed: `set_item_quantity` reports a vanished item as `CartItemNotFound` and the view answers 404. Verified: a view-level test that removes the item between the view's lookup and the service's, and a real-connection test where the update waits on a concurrent removal and then reports the item gone (without the row lock the update fails with a database error). | Resolved (round 2, `d092291..b282a60`) |
| CART-002 | Medium | `cart/services.py:35`, `tests/test_cart.py` | TESTING requires independent PostgreSQL transactions to prove locking. Mutation experiment: removed the cart `select_for_update` calls in memory. | **All 26 cart tests still passed with both service locking paths disabled.** The sequential tests do not protect against lost increments or prove the first-insert race and savepoint retry. Add synchronised two-connection tests for an existing row and for concurrent first insertion, checking the final quantity and the one-row invariant. | Tests added, no cart code change needed for this finding: three deterministic real-connection tests (a second connection holds the row or an uncommitted insert, the request is seen blocked, then released): lost increment on an existing row, first-insert race falling back to an increment, and update versus removal. Mutation checks: removing the `select_for_update` calls fails the lost-increment and removal tests; removing the `IntegrityError` retry fails the first-insert test. | Resolved (round 2, `d092291..b282a60`) |

## Coordinator notes

- CART-001: code re-read; `set_item_quantity` does `CartItem.objects.select_for_update().get(pk=item.pk, cart=cart)` with no handler for `DoesNotExist`. Confirmed.
- CART-002: the author had disclosed at commit time that cart concurrency was only proven sequentially; the reviewer's mutation result shows the gap is real.

Not changed (out of scope for these findings): `add_item`'s retry after a lost first-insert race can still raise `DoesNotExist` if a third actor removes the row in the instant between the failed insert and the re-read; the window needs three concurrent actors.

Decision: none.

## Re-review history

Rounds 2 to 4 of the independent review are done and the gate is **cleared at `7eea9b7`** (round 4, 22 September 2026). Fixes were made by the user with Claude, not Astra Low. Astra's round reports are PR #1 comments; this section is the concise record.

| Round | Snapshot | Result |
|---|---|---|
| 2 | `d092291..b282a60` | 429 tests, fresh migrations, `manage.py check` and `makemigrations --check --dry-run` passed on the reviewed snapshot (Astra). CART-001 and CART-002 resolved. Astra did not rerun the mutation checks; it judged from the code that removing the row lock or the insert retry would fail the new tests. The lock-wait helper in `tests/db_helpers.py` was kept as justified, with the caveat that it assumes a serial, isolated test database (scope the polling to the worker PID if parallel test runs are ever introduced) |
| 3 | `b282a60..282a1ec` | Bounded to the SEC-001 fix and the test trim; this task's findings were not reopened. |
| 4 | `282a1ec..7eea9b7` | Bounded to the R3-001/R3-002 fixes; this task's findings were not reopened. Gate cleared. |
