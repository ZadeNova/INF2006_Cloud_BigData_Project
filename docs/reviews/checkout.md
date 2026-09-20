# Checkout review

Task ID `checkout`. Round 1 of the independent backend review gate ([DEVELOPMENT.md](../DEVELOPMENT.md#backend-review-gate)); brief: [astra-review.md](../plans/astra-review.md). Report received 20 September 2026 from the project's teammate running Astra as the independent reviewer (model and reasoning level are not stated in the report). Log written by the coordinator (the user with Claude Code) from that report; the reviewer did not write to the repository.

- **Base and snapshot:** `0c13334..ce174af`. Reviewed PR head `d0922916e12c9df6c582c369032b70c975c967b4` (branch `erfan/backend-auth`), verified against GitHub.
- **Owned paths:** `src/orders/services.py`, `src/orders/views.py`, `src/orders/urls.py`, `OrderItem.line_total` in `src/orders/models.py`, `src/templates/orders/checkout.html` and `detail.html`, `tests/test_orders.py`.
- **Specs:** [SCHEMA.md](../SCHEMA.md) checkout transaction, [API.md](../API.md) checkout rows, [SECURITY.md](../SECURITY.md), plan [batch-04-checkout.md](../plans/batch-04-checkout.md).
- **Status:** Round 1 complete; **two actionable findings open**. Not approved.

## Checks and limitations

Environment for every task in this round: the committed source and tests were built directly from Git into a separate Docker image using the repository Dockerfile and pinned dependencies, with the pinned PostgreSQL image, a disposable database and the non-superuser application role. Fresh migrations, `manage.py check` and `makemigrations --check --dry-run` passed; the full suite passed (301 tests). The literal root Compose commands were not run (they would build the main checkout, not the reviewed branch). The reviewer's host checkout stayed on `main` and was not edited.

Task-specific: the existing checkout tests passed within the full suite. The two stale-review scenarios and the different-content same-key race were reproduced (Django test client; two real PostgreSQL connections synchronised just before the order insert, which does not replace database locking or uniqueness behaviour). The existing race tests cover equivalent requests and last-unit contention, but not these cases.

## Findings

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| CHK-001 | High | `orders/views.py:39`, `orders/services.py:103` | Batch 4 says the review page is the purchase contract. Reproduced through Django's client. | The session pin is shared by every tab and records only row IDs. Review A, add B in another tab, open checkout there, then submit the original page: the order contains A **and B**. Separately, changing A from quantity 1 to 9 after review purchases 9 without another review. Bind the submitted page to a server-held review version containing IDs and quantities; reject stale or changed reviews before writing. This is a concrete defect in the current pin design, not a request to change the accepted live-price rule. | Pending | Pending |
| CHK-002 | High | `orders/services.py:147` | SCHEMA checkout step 2 and API: different contents with the same key must conflict. Reproduced with two real PostgreSQL connections. | Two requests for different pinned products, using the same user and key, both return the winning order. The losing request reaches the `IntegrityError` handler, which returns the winner without comparing fingerprints. Compare the attempted fingerprint with the winner before returning; raise `CheckoutConflictError` on mismatch. Apply the same rule to the earlier winner-return path when pinned rows disappear, while preserving genuine empty-cart replay. | Pending | Pending |

## Coordinator notes

- Code re-read on 20 September 2026: `checkout()` locks cart rows by the pinned IDs only and reads `quantity` from the locked row at submit time; the pin is stored per session and overwritten by every checkout page render; both winner-return paths (`IntegrityError` handler and the `len(locked_items) != len(item_ids)` branch) return the existing order without comparing fingerprints. CHK-001 and CHK-002 are confirmed as described.
- **Proposed fix (awaiting the user's decision):** post a fingerprint of the displayed lines with the form; the server compares it with the locked current cart (CHK-001) and with an existing order's stored fingerprint for the same key (CHK-002). This would replace the session-held item IDs, change the "client submits nothing" wording in API.md, and requires updating the batch 4 plan and reworking the pin-based tests.
- The reviewer identified no further owner decision for this task. Open question for the reviewer: were the checkout locking tests mutation-tested like the cart ones?
