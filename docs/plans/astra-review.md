# Astra review brief

Purpose: the single entry point for the independent Astra Medium reviewer. It lists every backend task that is implemented but has **not** passed the mandatory review gate, with the exact commits, owned paths, specifications, tests, decisions already made, and the specific things worth scrutinising. Procedure, logging format, finding table and the stop-and-escalate rule are in [DEVELOPMENT.md](../DEVELOPMENT.md#backend-review-gate) and [AGENTS.md](../../AGENTS.md); this file does not replace them.

Rules that matter for the reviewer:
- Read-only. No edits, staging, commits or deployment. Focused non-mutating checks (for example running a test file) are allowed; report anything you could not run as a limitation, not a pass.
- Independent: the reviewer must not have authored the implementation. All tasks below were implemented by the user with Claude Code (per the session-role note in `CLAUDE.md`), not by Astra Low.
- Log each task in its own `docs/reviews/<task-id>.md` (one file per task, all rounds, stable finding IDs). The coordinator writes the log.
- Do not turn style preferences or legacy issues in other tasks into blockers. Do flag mistakes, spec gaps, security issues, unhandled failure paths, duplicated logic, dead code and missing or weak tests.
- Do not re-litigate the recorded decisions below unless you can show a defect. A genuine spec ambiguity goes to the user.

Verification recorded by the author at the last commit (`a11247b`): full suite 135 passed, `manage.py check` clean, `makemigrations --check --dry-run` reports no changes, run through Docker Compose (`docker compose run --rm web pytest -q`). The reviewer should rerun what it can rather than trusting these.

Frontend and visual work (templates, CSS) is outside this backend gate. The checkout, receipt and order-history pages are functional-only by design; a design pass is deferred and is not a finding.

## Review queue

| Task ID | Scope | Reviewed snapshot | Base |
|---|---|---|---|
| `auth-registration` | Register, login, logout | `cafe528` | `4795f9f` |
| `catalogue-operator` | Catalogue listing, `store_operator` role, `seed_demo`, follow-up fixes | `c0c1bfb` (includes `962d751`, `6ca93b8`, `9cee9d2`) | `cafe528` |
| `cart` | Persistent cart | `0c13334` | `c0c1bfb` |
| `checkout` | Cart to order, atomic and idempotent (highest risk) | `ce174af` | `0c13334` |
| `order-history` | Owner order list | `a11247b` | `ce174af` |
| `security-gap-check` | Cross-cutting check against `docs/SECURITY.md` | working tree at `9e32dde` | n/a |

Suggested order: checkout first (most complexity and risk), then cart, catalogue-operator, auth-registration, order-history, then the cross-cutting security check. For a snapshot use `git diff <base>..<snapshot> -- <owned paths>`; all reviewed code is committed, so nothing untracked is missed. Ignore the documentation-only and `CLAUDE.md` commits between them.

## `checkout`

- **Owned paths:** `src/orders/services.py`, `src/orders/views.py`, `src/orders/urls.py`, `src/orders/models.py` (`OrderItem.line_total` property only), `src/templates/orders/checkout.html`, `detail.html`, `tests/test_orders.py`.
- **Specs:** [SCHEMA.md](../SCHEMA.md) "Checkout transaction" and constraints, [API.md](../API.md) checkout rows, [SECURITY.md](../SECURITY.md), plan [batch-04-checkout.md](batch-04-checkout.md) (revised over three review passes before coding).
- **Tests:** `tests/test_orders.py` (checkout cases including two `transaction=True` real-thread concurrency tests: same-key double submit gives one order, two users racing the last unit give one success).
- **Decisions already made (do not reopen without a defect):**
  - The ORM, not raw SQL, with `select_for_update()`.
  - The idempotency key and the pinned cart item IDs live in the session, refreshed on every render; the key is cleared only on a terminal outcome.
  - The fingerprint hashes namespace plus sorted `(product external_id, quantity)` and excludes price, so a replay after a price change still returns the original order.
  - Cart items are locked with `of=("self",)` and products in a separate query ordered by primary key; cart items are deleted by explicit locked PKs.
  - Order creation sits in a nested savepoint with `except IntegrityError`, re-raising if no winning order exists.
  - Insufficient stock returns 409 and keeps the key; inactive or invalid product returns 200.
  - The lock on shared products serializes concurrent checkouts of the same product (accepted trade-off). Clearing the session key happens outside the database transaction (self-healing, accepted).
- **Scrutinise:**
  - Any path where stock can go negative or an order can be created without its lines and stock deduction, including a failure between steps.
  - Deadlock potential: lock ordering across cart items, products and the order insert.
  - Replay correctness: same key and same contents returns the existing order; same key with different contents conflicts; the empty-cart check must not shadow the replay path.
  - Whether the session-pinned item list can be abused or go stale in a way that buys something the user did not review.
  - The exception-to-HTTP mapping in the view and whether every failure leaves a coherent session state.
  - Test strength: do the concurrency tests actually fail if the locking is removed?

## `cart`

- **Owned paths:** `src/cart/services.py`, `views.py`, `forms.py`, `urls.py`, `src/templates/cart/`, the Add-to-Cart control in `src/templates/catalogue/_product_card.html`, `tests/test_cart.py`.
- **Specs:** [API.md](../API.md) cart rows and HTMX contract, [SCHEMA.md](../SCHEMA.md) Cart/CartItem, plan [batch-03-cart.md](batch-03-cart.md).
- **Decisions:** add increments, update replaces; over 999 rejected, not clamped; a deactivated product already in a cart stays visible and removable but cannot be added to or increased; delete is idempotent while update returns 404 for foreign or missing items; stock check at add time is soft and non-authoritative (checkout is authoritative).
- **Scrutinise:** the same-user concurrent-add race (lock on the existing row, savepoint plus `IntegrityError` retry for a first add), the HTMX login redirect (`HX-Redirect`, never login HTML inside the fragment), CSRF on every mutation, foreign-object 404s, and whether the tests exercise the concurrency or only the sequential path (the author disclosed that cart concurrency is only proven sequentially).

## `catalogue-operator`

- **Owned paths:** `src/catalogue/` (models, views, urls, `management/commands/seed_demo.py`, the permission migration), `tests/test_catalogue.py`, related `src/config/urls.py` and settings entries.
- **Specs:** [API.md](../API.md), [SCHEMA.md](../SCHEMA.md) Product, the scope note on the operator role (a deliberate narrow addition beyond the brief). Earlier external findings AUTHCAT-001, 002, 003 and FRONT-001, 002 were fixed in `c0c1bfb`; the reviewer should confirm the fixes hold, especially: `seed_demo` cannot promote an existing non-seed account to operator; no unguarded fallback password outside local; the toggle sets an explicit state so a duplicate submit does not reverse intent.
- **Decisions:** the operator can only activate or deactivate; products are otherwise seeded or imported; the operator views return 403 (not a login redirect) for anonymous and non-operator users; the demo operator password comes from `DEMO_OPERATOR_PASSWORD` with a local-only fallback.
- **Scrutinise:** the permission checks on both operator routes, the lost-update handling in the toggle, pagination stability and reachability of all products, namespace filtering on the public list, and any way a customer could see or change an inactive product.

## `auth-registration`

- **Owned paths:** `src/accounts/` (urls, views), the related settings (`LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`), `tests/test_accounts.py`.
- **Specs:** [API.md](../API.md) auth rows, [SECURITY.md](../SECURITY.md), [SCHEMA.md](../SCHEMA.md) (no `CustomerProfile` is created for locally registered users).
- **Decisions:** Django's built-in views and forms are reused; logout is POST with CSRF; authenticated users are redirected away from register and login.
- **Scrutinise:** safe handling of the `next` parameter (open redirect), password validation, whether registration can collide with reserved or imported usernames, session rotation on login, and the note that the original commit was authored when `/products/` did not exist yet.

## `order-history`

- **Owned paths:** `OrderListView` in `src/orders/views.py`, `src/orders/urls.py`, `src/templates/orders/list.html`, the nav and receipt links, the history tests in `tests/test_orders.py`.
- **Specs:** [API.md](../API.md), plan [batch-05-order-history.md](batch-05-order-history.md).
- **Decisions:** a plain `ListView` (no service function); ten per page; item count means distinct lines, not total units; ordering is `-placed_at, -pk` so pagination is stable.
- **Scrutinise:** ownership isolation, that the annotation cannot multiply rows or totals, index use against `order_owner_date`, and pagination bounds handling.

## `security-gap-check`

A cross-cutting review of the implemented code against [SECURITY.md](../SECURITY.md); findings only, fixes need user approval. Items the author already suspects are gaps (verify, do not assume):

- No application logging configuration exists (`LOGGING` is absent from `settings.py`), so the request ID, duration and sanitised-error requirement is unimplemented.
- No login throttling or lockout was added. It is not required by the contract but is a common expectation; classify severity accordingly.
- Expired-session cleanup is required by the contract ("plan expired-session cleanup") and has no mechanism yet.
- Session lifetime is 14 days (`SESSION_COOKIE_AGE`); confirm this is intended.
- Confirm debug is off and allowed hosts are enforced outside local, and that `SECURE_PROXY_SSL_HEADER` is only set under the intended condition.
- Sessions use the database backend (`SESSION_ENGINE = "django.contrib.sessions.backends.db"`), which matches the shared-state rule. Cross-instance behaviour cannot be verified until a multi-instance deployment exists; record that as a limitation.
- Negative tests required by the contract: unauthenticated checkout, foreign cart or order access, non-operator analytics (not built yet), missing or invalid CSRF, quantity or price manipulation, duplicate checkout, anonymous S3 access (cloud, not yet). Map each to an existing test or record it as missing.

## Upcoming review queue (not implemented yet)

These will need the same gate when they exist, in this order: `analytics-data-import` (batch 6a, [plan](batch-06a-data-import.md)), `analytics-refresh` (batch 6b, [plan](batch-06b-analytics-refresh.md)), and the backend part of the analytics dashboard (batch 6c, outlined at the end of the 6b plan). Add them to the table above with their commit hashes when they land. Infrastructure changes are backend-owned work and also require the gate before being marked complete.

## Reviewer output checklist

For each task: the finding table with stable IDs, an explicit "no actionable findings" when applicable, the checks actually run with their results, limitations (for example, checks that could not run), and a clear statement of anything that needs a user decision. Link the finished log from the tracker instead of copying findings into it.
