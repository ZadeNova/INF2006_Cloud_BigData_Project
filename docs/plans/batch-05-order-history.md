# Batch 5 — order history

Written before implementation, per `CLAUDE.md`'s "Discuss / Plan" step.

## Context

Next roadmap batch after checkout (Batch 4, shipped `ce174af`). Checkout already built `orders:detail` (single-order receipt) since it needed a landing page; this batch adds `orders:list` (`GET /orders/`), the owner's paginated order history — closing out `docs/API.md`'s remaining reserved contract for the `orders` app. Unlike checkout, this batch has no concurrency, no locking, and no schema-locked constraints beyond what already exists — it's a read-only, owner-scoped list.

## Decisions made (discussed with the user)

1. Follow standard ecommerce order-history conventions: each row shows order number, placed date, status, **item count** (distinct line items — `Count("items")`, e.g. an order of 2 different products shows "2" regardless of per-line quantity) and total, matching how most ecommerce sites present order history at a glance.
2. Pagination: **10 per page** (deliberately not matching catalogue's 12 — the user's explicit choice).
3. No `services.py` function for this batch — plain `ListView.get_queryset()`, mirroring `catalogue.ProductListView` (`src/catalogue/views.py:16`) rather than `ARCHITECTURE.md`'s explicit-business-function convention, since that convention targets mutations/business rules (checkout, cart), not a straightforward filtered read.

## Implementation

- **`src/orders/views.py`**: add `OrderListView(LoginRequiredMixin, ListView)` — `model = Order`, `template_name = "orders/list.html"`, `context_object_name = "orders"`, `paginate_by = 10`; `get_queryset()` returns `Order.objects.filter(owner=self.request.user).annotate(item_count=Count("items")).order_by("-placed_at")` (single query, no N+1 — reuses the existing `order_owner_date` index on `(owner, -placed_at)`, which was already shaped for exactly this query).
- **`src/orders/urls.py`**: add `path("orders/", OrderListView.as_view(), name="list")` (placed before the existing `orders/<int:pk>/` detail route for readability; no resolution ambiguity since the two patterns have different path shapes).
- **`src/templates/orders/list.html`** (new): reuses `.operator-table`/`.operator-row` like every other batch; each row links to `orders:detail`; empty state ("You haven't placed any orders yet. Continue shopping.") matching cart/checkout's existing empty-state precedent; pagination nav matching `catalogue/manage_list.html`'s existing pattern.
- **`src/templates/orders/detail.html`**: add a "View all orders" link back to `orders:list` (small addition to the existing receipt page).
- **`src/templates/base.html`**: add an authenticated-only "Orders" nav link next to the existing "Cart" link — built in from the start rather than retrofitted later (same discoverability lesson as FRONT-002/cart's nav link).
- No model changes, no migration.

## Tests (`tests/test_orders.py`, extended)

Pagination boundary (11 orders → page 1 has 10, page 2 has 1); ownership isolation (user A never sees user B's orders in the list, same convention as `test_users_only_see_their_own_cart`); ordering (most recent `placed_at` first); item-count correctness (an order with N distinct products shows N, independent of per-line quantity); empty state; auth required (redirect for anonymous).

## Verification

`docker compose up --build -d --wait`; live HTTP walkthrough (place a couple of orders, view `/orders/`, confirm ordering/item-count/pagination, confirm nav link, confirm "View all orders" link from a receipt page); `docker compose run --rm web pytest -q` (full suite, no regressions expected); `manage.py check`; `makemigrations --check --dry-run` (expect no changes — no model changes this batch); low/medium-effort Claude self-review; update `docs/IMPLEMENTATION_PLAN.md` and `docs/API.md` (flip `GET /orders/` from reserved to implemented, add an `orders:list` row to the reserved-contracts reference table matching the `orders:detail` row added last batch); commit — user pushes.
