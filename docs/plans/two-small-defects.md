# Two small defects: checkout subtotal and `--band-ink-soft`

Written 24 September 2026, branch `erfan/analytics`. Both defects were recorded earlier (the checkout one in the 22 September tracker entry, the token in [storefront-redesign.md](storefront-redesign.md) under Known issues) and re-confirmed against the code on 24 September. Agreed with the user before writing: fix both, as two separate commits.

## Defect 1: checkout total counts deactivated products

**Where:** `src/orders/views.py`, `CheckoutView._context` (lines 42-51) adds every line's total to `subtotal`, including lines whose product is inactive. `src/templates/orders/checkout.html` renders that value twice (product row and Total).

**Effect:** a product deactivated after it was added to the cart shows "No longer available" on the checkout page, yet its price is still in the total, while `cart/detail` excludes it (`cart.services.cart_subtotal` skips inactive items). The two pages disagree about the same basket. Nothing is mischarged: `Place order` refuses the whole order with `InactiveProductError`.

**Fix:** `_context` uses `cart.services.cart_subtotal(items)` for `subtotal` instead of its own accumulation. One business rule, one place. The line still renders, with its warning and its own `line_total`.

**Not changed (decided):**
- Lines with quantity above stock still count, as in the cart (its rule checks `active` only); checkout already rejects them with a 409 and a message.
- `Place order` stays enabled; disabling it would be new behaviour, not a fix.
- The "N products" count in the summary keeps counting all lines.

**Test (`tests/test_orders.py`):** two-item cart, deactivate one product, GET `orders:checkout`; assert `context["subtotal"]` equals the active item's line total and equals `cart_subtotal` for the same cart, and that the "No longer available" warning is present. Written first and confirmed failing against the current code.

**Review:** touches `orders/views.py` (backend-owned) but changes display arithmetic only. Include it in the next review pass; the user's Opus review is not the independent Astra gate.

## Defect 2: `--band-ink-soft` undefined in light mode

**Where:** declared only at `src/static/css/site.css:130` and `:175` (the two dark blocks); used at lines 781, 857, 887, 1237, 2291 and 2297 (`.hero-visual__label`, `.feature-band__copy > p:last-child`, `.feature-stat span`, `.site-footer__meta`, `.site-footer__links a` and its hover).

**Effect:** in light mode `color: var(--band-ink-soft)` is invalid, `color` inherits, and the muted text renders as the band's full white. Hierarchy is lost and the footer link hover has no visible change; text stays readable.

**Fix:** add `--band-ink-soft: #a3a3a3;` to the light `:root` block beside `--band-ink`. The band is dark in both themes (`#0a0a0a` light, `#000000` dark) and dark mode already uses `#a3a3a3`, so the same value applies. No rule changes.

**Verify:** grep that every `var(--...)` used in `site.css` is defined in `:root`; look at the home page band and footer in light mode during the team walkthrough.

## Steps and commits

1. Failing test, then the `_context` change, then run `tests/test_orders.py` and `tests/test_cart.py` in Docker. Commit 1 (`fix: exclude deactivated products from the checkout subtotal`).
2. Token line, grep check. Commit 2 (`fix: define --band-ink-soft for the light theme`).
3. Docs in the same commits as their fix: remove both from the known-issue notes in `README.md`, `storefront-redesign.md` and the tracker entry.

## Not in scope

The full suite, a browser walk, and any other CSS or view change. The team verification pass follows and records its results in `evidence/`.
