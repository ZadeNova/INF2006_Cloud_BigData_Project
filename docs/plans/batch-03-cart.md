# Batch 3 — persistent cart (add / update / remove)

First `docs/plans/` file, per `CLAUDE.md`'s "Discuss / Plan" workflow step: written when the plan was finalized, before implementation began.

## Context

Next roadmap batch after catalogue + operator product management (both shipped on `erfan/backend-auth`). The cart is the customer-facing counterpart: browse `/products/`, add items, manage quantities, remove items — no checkout yet (Batch 4). The route/template/HTMX contract was already pre-bound in `docs/API.md` and `docs/ARCHITECTURE.md`.

`src/cart/models.py`'s `Cart`/`CartItem` models and their constraints (`UniqueConstraint(cart, product)`, `CheckConstraint(1 <= quantity <= 999)`) already existed from the foundation batch. Everything else — `views.py`, `urls.py`, `services.py`, `forms.py`, templates, root URL wiring — was new this batch.

## Decisions made (discussed with the user before implementing)

1. `cart:add` **increments** an existing item's quantity; `cart:update` **replaces** it.
2. Exceeding 999 (add's resulting total, or update's requested value) → **reject with a validation message**, no clamping.
3. A product deactivated while already in a cart stays visible on `cart:detail` with an "unavailable" marker and stays removable; **new** adds/increases of an inactive (or wrong-namespace/nonexistent) product → 404 (existence-hiding, same convention used elsewhere). Checkout (Batch 4) is what will actually reject purchasing it.
4. Soft stock check: reject add/update when requested total > current `Product.stock`, with a message — a live, non-authoritative read, not a reservation/lock. Checkout re-checks for real under `select_for_update()`.
5. `cart:delete` is **idempotent** (deleting an already-gone/foreign item is treated as the desired end state, no error); `cart:update` stays a strict 404 for missing/foreign items — an idempotent-replace has no sensible "success" meaning against a target that was never yours, unlike delete.
6. Cart nav link added to `base.html` for authenticated users, built in from the start rather than retrofitted later (mirroring the FRONT-002 gap just fixed for catalogue).

## Race-condition handling

Two distinct races were discussed:
- **Stock race** (two users wanting the last unit) is explicitly out of scope for cart per `SCHEMA.md:15` ("No stock reservation") — correctly deferred to Batch 4's checkout locking.
- **Cart-quantity race** (same user, concurrent adds — double-click or two tabs) is in scope: `services.add_item()` locks an existing row with `select_for_update()` inside `atomic()` before incrementing; for the first-ever add of a product, the `create()` is wrapped in a nested `atomic()` savepoint, and a losing `IntegrityError` on `cart_product_unique` falls back to a locked re-query and the increment path. Same shape as the race already designed for Batch 4's order creation, just smaller.
- Verification caveat disclosed honestly: tests prove this sequentially; true concurrent-connection proof needs the `transaction=True` + threads test infra Batch 4 introduces for checkout.

## Implementation

- **`src/cart/models.py`**: added `MAX_QUANTITY = 999` (single source of truth, referenced by the `CheckConstraint`, both forms, and the service layer — no more duplicated literal), and a `CartItem.line_total` property.
- **`src/cart/services.py`** (new): `get_cart`, `add_item` (locking/race handling, 999-cap, soft stock check), `set_item_quantity` (locking, soft stock check, rejects mutation on an inactive product), `remove_item` (idempotent filter-delete), `cart_subtotal(items)` (sums an already-fetched iterable rather than re-querying, to avoid an N+1).
- **`src/cart/forms.py`** (new): `AddToCartForm`, `UpdateCartItemForm`.
- **`src/cart/views.py`** (new): `HtmxLoginRequiredMixin` (the piece that makes "`HX-Redirect` on session expiry, never login HTML in the fragment" real — overrides `handle_no_permission()`), `CartDetailView`, `CartAddView`, `CartUpdateView`, `CartDeleteView`. Mutation views share a `_respond()` helper: HTMX requests get `cart/_content.html` re-rendered at 200 (success or validation error alike, since HTMX only auto-swaps on 2xx); non-HTMX requests redirect to `cart:detail`, using `messages.error()` on failure.
- **`src/cart/urls.py`** (new) wired into `src/config/urls.py` via `path("cart/", include("cart.urls"))`.
- **Templates**: `cart/detail.html`, `cart/_content.html` (the `id="cart-content"` fragment, reusing `.operator-table`/`.operator-row` CSS rather than inventing new classes — minimal/functional, matching the "polish deferred to the frontend pass" precedent); a plain non-HTMX Add-to-Cart form added to `catalogue/_product_card.html` (shown for authenticated users, a login link otherwise — no anonymous cart); an authenticated-only "Cart" nav link in `base.html`.

## Post-implementation self-review (medium effort) — 4 findings, all fixed with the user's sign-off

1. `set_item_quantity` didn't check `product.active`, unlike `add_item` — a shopper could increase the quantity of an already-deactivated item via `cart:update`, bypassing the same guard `cart:add` enforced. Fixed: raises `CartValidationError` if the product is inactive.
2. `Cart.subtotal` (a model property) re-queried `self.items.all()` independently of the view's already-fetched, `select_related`-loaded `items`, costing a duplicate query plus one extra product lookup per item. Fixed: removed the model property; `services.cart_subtotal(items)` now sums the same queryset object the view already built and passed to the template, so it's evaluated once.
3. `docs/API.md`'s top status line still said cart routes "remain reserved contracts for follow-up tasks, not callable endpoints" — stale now that this batch implements them. Fixed.
4. The `999` quantity ceiling was a bare literal in four places (`services.py`, both form fields, the model's `CheckConstraint`). Fixed: `MAX_QUANTITY` now lives once in `models.py`, imported everywhere else.

## Verification

`docker compose up --build -d --wait`; live HTTP walkthrough — login, "Add to cart" from the catalogue, nav Cart link, view cart, quantity update via HTMX (confirmed `cart/_content.html` fragment + `id="cart-content"` returned at 200), `HX-Redirect: /login/` at 200 for an HTMX request carrying a valid CSRF cookie but no active session (the realistic session-expiry case — a bare unauthenticated request with no CSRF token correctly gets a plain 403 from CSRF middleware first, not the HTMX path, which is expected and not a bug), operator-deactivate-while-in-cart still shows "unavailable" rather than disappearing; `docker compose run --rm web pytest -q` full suite 111/111 passed before the 4 fixes; `manage.py check` clean; `makemigrations --check --dry-run` reports no changes (both before and after the `MAX_QUANTITY` constant refactor, confirming the DB constraint is unchanged). After the 4 fixes: isolated `tests/test_cart.py` re-run (26/26, including a new regression test for finding 1) per the user's request to skip the full suite for this fix-only round unless truly needed.
