# Checkout review fixes: CHK-001 and CHK-002

Written before implementation, per `CLAUDE.md`'s "Discuss / Plan" step. Source: round 1 of the independent review, log [docs/reviews/checkout.md](../reviews/checkout.md). Revises the pin design in [batch-04-checkout.md](batch-04-checkout.md); everything else in that plan (locking order, savepoint, exception mapping, live-price rule) is unchanged.

## What was wrong

- **CHK-001:** the review page's contents were held as cart-item IDs in the *session*, which every tab shares, and quantities were never recorded. A second tab's checkout page overwrote the pin, so the first tab's "Place order" bought what the second tab showed; a quantity changed after review was bought as changed.
- **CHK-002:** when a same-key request found an existing order (the `IntegrityError` handler, the vanished-rows branch, and the "pinned rows are gone" replay path), it returned that order without checking it matched the request, so different contents with the same key did not conflict.

## Design

Each review page now carries its own contents, and the server treats that claim as untrusted.

1. **Review fingerprint.** `services.fingerprint_for(lines)` (the existing SHA-256 of the namespace plus sorted `(product external_id, quantity)` pairs; price excluded, so the accepted live-price rule is unchanged) is computed from the cart lines the page displays and posted in a hidden field `review`. It replaces the session-held item IDs (`SESSION_ITEM_IDS` is removed). The idempotency key stays in the session.
2. **Checkout verifies against the truth.** `checkout(user, idempotency_key, review)` locks *all* of the user's cart rows and the products (same order as before: cart rows, then products by primary key), recomputes the fingerprint from the locked rows and requires it to equal `review`; otherwise `CartChangedError` and nothing is written. A forged or stale `review` can therefore only cause a rejection: the order is always exactly the current cart, and it must equal what was reviewed.
3. **One replay rule.** An existing order for `(user, key)` is returned only if its stored `request_fingerprint` equals `review`; otherwise `CheckoutConflictError`. The rule is applied at every point that returns an existing order: before the transaction, again inside it once the cart lock is held (a concurrent same-key request that committed while we waited), and in the `IntegrityError` safety net. This replaces the old "if no pinned rows survive, return the existing order" path, so a cleared cart no longer bypasses the check, and genuine replays (same key and same review) still succeed after the cart was emptied.
4. **View.** GET computes the fingerprint of the displayed items and renders it; POST reads `review`, requires a 64-character lowercase hex value (missing or malformed redirects to the checkout page, like a missing session key) and calls the service. Key lifecycle is unchanged: kept on `CartChangedError` (no order was created, so re-reviewing may reuse it), inactive/invalid product and insufficient stock; cleared on success, conflict and empty cart.

## Behaviour changes to note

- **An item added (or a quantity changed, or an item removed) after the review page loaded now blocks the order** with "Your cart changed since you reviewed it. Please review it again." and shows the fresh review page. Previously an item added later was silently left in the cart and the reviewed items were bought. This is stricter and simpler; the alternative (buy the reviewed subset and ignore additions) would need the page to carry per-item detail and was not chosen. Say if you prefer it.
- A second tab's checkout page no longer affects the first tab's page.
- The POST body now carries `review`; `docs/API.md` is updated (it previously said the client submits nothing).

## Tests (`tests/test_orders.py`)

Existing pin-based tests are reworked to submit the fingerprint the page rendered (helpers read it from the response context). New tests:

- Two-tab reproduction of CHK-001: review A in tab 1, add B and render tab 2, submit tab 1's page: blocked, no order, cart intact; tab 2's page then buys A and B.
- Quantity raised after review (1 to 9): blocked, stock unchanged; the re-rendered page buys 9.
- Added item, removed item and forged (wrong but well-formed) `review`: blocked with "changed", never "empty".
- Missing or malformed `review`: redirected, no order.
- CHK-002: same key with a different review conflicts (409 through the view, `CheckoutConflictError` through the service), including after the cart was cleared; same key and same review still replays; an identical re-add replays without touching the cart.
- Safety net: with the pre-checks forced to miss, the `IntegrityError` handler returns the winner only when its fingerprint matches and conflicts otherwise.
- Concurrency (real PostgreSQL connections, barrier): equivalent same-key requests give exactly one order; same key with a valid and an invalid review never yields a second success for the invalid one.

## Verification

`docker compose build web`, focused `tests/test_orders.py`, then the full suite; `manage.py check`; `makemigrations --check --dry-run` (no model change); a live two-tab walkthrough is optional (the tests reproduce it). Update `docs/API.md`, `docs/plans/batch-04-checkout.md` (pointer), `docs/reviews/checkout.md` (Low fix column; re-review outcome stays Pending) and the tracker later. Astra re-reviews the fix diff; the finding IDs are preserved.
