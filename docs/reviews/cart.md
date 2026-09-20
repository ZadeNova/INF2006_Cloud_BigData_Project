# Cart review

Task ID `cart`. Round 1 of the independent backend review gate ([DEVELOPMENT.md](../DEVELOPMENT.md#backend-review-gate)); brief: [astra-review.md](../plans/astra-review.md). Report received 20 September 2026 from the project's teammate running Astra as the independent reviewer (model and reasoning level are not stated in the report). Log written by the coordinator (the user with Claude Code) from that report.

- **Base and snapshot:** `c0c1bfb..0c13334`. Reviewed PR head `d0922916e12c9df6c582c369032b70c975c967b4`.
- **Owned paths:** `src/cart/services.py`, `views.py`, `forms.py`, `urls.py`, `src/templates/cart/`, the Add-to-Cart control in `src/templates/catalogue/_product_card.html`, `tests/test_cart.py`.
- **Specs:** [API.md](../API.md) cart rows and HTMX contract, [SCHEMA.md](../SCHEMA.md) Cart/CartItem, plan [batch-03-cart.md](../plans/batch-03-cart.md).
- **Status:** Round 1 complete; **two actionable findings open**. Not approved.

## Checks and limitations

Environment: built from Git into a separate Docker image with pinned dependencies and PostgreSQL, disposable database, non-superuser role; fresh migrations, `manage.py check` and `makemigrations --check --dry-run` passed; full suite 301 passed. The literal root Compose commands were not run; the host checkout was not edited.

Task-specific: all 26 committed cart tests passed. CART-001 was reproduced. The lock-removal experiment (both `select_for_update` calls removed in memory) also passed 26/26, confirming CART-002. An initial mutation-harness run recreated the exception class and caused four unrelated failures; after preserving the original exception class, the corrected experiment produced the result quoted. No repository source was changed.

## Findings

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| CART-001 | High | `cart/services.py:57` | Batch 3: updating a missing item returns 404. Reproduced deletion between the view lookup and the locked service lookup. | If another tab removes the item, or checkout consumes it, after the view's initial lookup, the locked `get()` raises an uncaught `CartItem.DoesNotExist` and the request becomes a 500. Map disappearance at the authoritative locked lookup to 404. Add a regression covering that interleaving. | Pending | Pending |
| CART-002 | Medium | `cart/services.py:35`, `tests/test_cart.py` | TESTING requires independent PostgreSQL transactions to prove locking. Mutation experiment: removed the cart `select_for_update` calls in memory. | **All 26 cart tests still passed with both service locking paths disabled.** The sequential tests do not protect against lost increments or prove the first-insert race and savepoint retry. Add synchronised two-connection tests for an existing row and for concurrent first insertion, checking the final quantity and the one-row invariant. | Pending | Pending |

## Coordinator notes

- CART-001: code re-read; `set_item_quantity` does `CartItem.objects.select_for_update().get(pk=item.pk, cart=cart)` with no handler for `DoesNotExist`. Confirmed.
- CART-002: the author had disclosed at commit time that cart concurrency was only proven sequentially; the reviewer's mutation result shows the gap is real.

Decision: none.
