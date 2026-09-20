# Astra review brief

Purpose: the single entry point for the independent Astra Medium reviewer. It lists every backend task that is implemented but has **not** passed the mandatory review gate, with the exact commits, owned paths, specifications, tests, decisions already made, and the specific things worth scrutinising. Procedure, logging format, finding table and the stop-and-escalate rule are in [DEVELOPMENT.md](../DEVELOPMENT.md#backend-review-gate) and [AGENTS.md](../../AGENTS.md); this file does not replace them.

Rules that matter for the reviewer:
- Read-only. No edits, staging, commits or deployment. Focused non-mutating checks (for example running a test file) are allowed; report anything you could not run as a limitation, not a pass.
- Independent: the reviewer must not have authored the implementation. All tasks below were implemented by the user with Claude Code (per the session-role note in `CLAUDE.md`), not by Astra Low.
- Log each task in its own `docs/reviews/<task-id>.md` (one file per task, all rounds, stable finding IDs). The coordinator writes the log.
- Do not turn style preferences or legacy issues in other tasks into blockers. Do flag mistakes, spec gaps, security issues, unhandled failure paths, duplicated logic, dead code and missing or weak tests.
- Do not re-litigate the recorded decisions below unless you can show a defect. A genuine spec ambiguity goes to the user.

Verification recorded by the author: at `a11247b` (end of the ecommerce tasks) the full suite was 135 passed; at `788f545` (analytics through the read queries) it was 301 passed. `manage.py check` was clean and `makemigrations --check --dry-run` reported no changes at both, run through Docker Compose (`docker compose run --rm web pytest -q`). After changing anything under `src/`, run `docker compose build web` first: the image copies `src/` at build time and only `tests/` is mounted. The reviewer should rerun what it can rather than trusting these.

Frontend and visual work (templates, CSS) is outside this backend gate. The checkout, receipt and order-history pages are functional-only by design; a design pass is deferred and is not a finding.

## Review queue

| Task ID | Scope | Reviewed snapshot | Base |
|---|---|---|---|
| `auth-registration` | Register, login, logout | `cafe528` | `4795f9f` |
| `catalogue-operator` | Catalogue listing, `store_operator` role, `seed_demo`, follow-up fixes | `c0c1bfb` (includes `962d751`, `6ca93b8`, `9cee9d2`) | `cafe528` |
| `cart` | Persistent cart | `0c13334` | `c0c1bfb` |
| `checkout` | Cart to order, atomic and idempotent (highest risk) | `ce174af` | `0c13334` |
| `order-history` | Owner order list | `a11247b` | `ce174af` |
| `analytics-refresh` | SQL view, date ranges, `refresh_analytics` (batch 6b, parts 1 and 2) | `470becd` (includes `41ea463`) | `91ba04e` (docs only) |
| `analytics-queries` | `snapshot_inventory` and the dashboard read queries (batch 6b, part 3) | `788f545` | `470becd` |
| `security-gap-check` | Cross-cutting check against `docs/SECURITY.md` | branch tip at the time of review | n/a |

Suggested order: checkout first (most complexity and risk), then analytics-refresh and analytics-queries, then cart, catalogue-operator, auth-registration, order-history, then the cross-cutting security check. For a snapshot use `git diff <base>..<snapshot> -- <owned paths>`; all reviewed code is committed, so nothing untracked is missed. Ignore the documentation-only and `CLAUDE.md` commits between them.

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

## `analytics-refresh`

- **Owned paths:** `src/reporting/migrations/0003_completed_sale_lines_view.py`, `src/reporting/ranges.py`, the refresh half of `src/reporting/services.py`, `src/reporting/management/commands/refresh_analytics.py` and `_args.py`; tests `tests/test_analytics_ranges.py`, `test_analytics_view.py`, `test_analytics_refresh.py` and the shared `tests/analytics_helpers.py`.
- **Specs:** [ANALYTICS.md](../ANALYTICS.md) (Definitions, Reporting range, Calendar correctness, Processing and validation), [SCHEMA.md](../SCHEMA.md) (AnalyticsRun, DailyProductSales, inventory versions and DOC-001), plan [batch-06b-analytics-refresh.md](batch-06b-analytics-refresh.md). SCHEMA.md does not yet describe the view; that is a known documentation gap, not a finding to report as new.
- **Decisions already made:** `--as-of D` sets the cutoff to 00:00 Asia/Singapore, so the last complete date L is D minus one; every run is a full recompute of a 366-date window ending at L; daily rows are stored sparsely (absent means zero); a Postgres advisory lock guards the command and a concurrent invocation skips with exit 0; the run row is created and committed first, the rows and the completion are written in one transaction, and a failure marks the run failed; any run left `running` is marked failed once the lock is held; retention keeps the newest N completed runs per namespace (minimum 2, never the new one) and deletes older ones after commit; the statement timeout is transaction-local; aggregation is SQL, never the ORM; every product in the namespace must have a row in the sealed inventory.
- **Scrutinise:**
  - The view: `placed_at AT TIME ZONE 'Asia/Singapore'` on a `timestamptz`, the completed-only filter, and the join.
  - `PUBLISH_SQL`: do the counts and the inserted rows really come from one snapshot, and are the `placed_at` range and the `business_date` bounds equivalent for a midnight cutoff?
  - The lock lifecycle: released on every path, session-level locks with pooled or reused connections, and what happens if the connection dies.
  - Failure handling: a mid-publish error, `_mark_failed`, and the orphan cleanup, which is global and only safe because the lock is global.
  - Retention: the ordering, the per-namespace scope, and the race with a reader who has just selected a run (the design relies on always keeping at least two).
  - Date arithmetic in `ranges.py` around leap years and month ends, bucket clipping, and shifted comparison buckets; the `zoneinfo` dependency in the slim image.
  - Test strength: would the lock, boundary, rollback and retention tests fail if the guarded behaviour were removed?
- **Not defects:** no incremental refresh (deliberate), no scheduler design yet (infrastructure phase), not yet run on real data (the dataset is gated).

## `analytics-queries`

- **Owned paths:** `src/reporting/queries.py`, the snapshot half of `src/reporting/services.py`, `src/reporting/management/commands/snapshot_inventory.py`; tests `tests/test_analytics_queries.py`, `test_analytics_snapshot.py`.
- **Specs:** [ANALYTICS.md](../ANALYTICS.md) (Metrics, Partial history, Compare, Range independence), [SCHEMA.md](../SCHEMA.md) inventory sections, plan [batch-06b-analytics-refresh.md](batch-06b-analytics-refresh.md).
- **Decisions already made:** coverage and flags use the sealed inventory snapshot, never live stock, over the seven complete dates ending at L regardless of the dashboard range; the flag is exact integer arithmetic (`stock * 7 <= lead_time * units`); states are flagged, ok, unavailable and insufficient_history; results are ordered by urgency in SQL; top sellers break ties on the lower product ID; category totals use each product's current category; the comparison series reuses the selected buckets shifted back by the span length; `snapshot_inventory` is create-only and its option is `--name` because Django reserves `--version`.
- **KO-1 (owner decided; mitigated with disclosure, awaiting re-review):** `snapshot_inventory` now accepts only today's Singapore date, and ANALYTICS.md discloses that live stock is captured at run time (conservative bias while nothing can raise stock). Findings AQRY-001 and AQRY-002 were fixed in the same change. See [analytics-queries.md](../reviews/analytics-queries.md).
- **Scrutinise:**
  - `COVERAGE_SQL`: the NULL behaviour of `flagged` (it must never be NULL), the boolean and integer parameters, rounding for display versus the exact threshold, and ordering with `NULLS LAST`.
  - The sufficiency rule for history (`earliest <= first`) at the six and seven date boundary.
  - `bucket_sales`: the dynamically built `VALUES` list (placeholders only, no interpolated values), the left join and zero-filling, and behaviour for an empty bucket list.
  - `top_sellers`: the window function combined with `GROUP BY`, and ordering stability.
  - `snapshot_inventory`: the nested atomic and `IntegrityError` handling, `_verify_existing`, and how it interacts with the append-only database guards.
  - Query budgets: each function should use a fixed number of statements regardless of product count.
  - Test strength around the exact threshold, the leap-day window and snapshot immutability.

## `security-gap-check`

A cross-cutting review of the implemented code against [SECURITY.md](../SECURITY.md); findings only, fixes need user approval. Items the author already suspects are gaps (verify, do not assume):

- (Fixed after round 1 as SEC-001: request logging now exists; see [security-gap-check.md](../reviews/security-gap-check.md).) Originally: no application logging configuration existed, so the request ID, duration and sanitised-error requirement was unimplemented.
- No login throttling or lockout was added. It is not required by the contract but is a common expectation; classify severity accordingly.
- Expired-session cleanup is required by the contract ("plan expired-session cleanup") and has no mechanism yet.
- Session lifetime is 14 days (`SESSION_COOKIE_AGE`); confirm this is intended.
- Confirm debug is off and allowed hosts are enforced outside local, and that `SECURE_PROXY_SSL_HEADER` is only set under the intended condition.
- Sessions use the database backend (`SESSION_ENGINE = "django.contrib.sessions.backends.db"`), which matches the shared-state rule. Cross-instance behaviour cannot be verified until a multi-instance deployment exists; record that as a limitation.
- Negative tests required by the contract: unauthenticated checkout, foreign cart or order access, non-operator analytics (not built yet), missing or invalid CSRF, quantity or price manipulation, duplicate checkout, anonymous S3 access (cloud, not yet). Map each to an existing test or record it as missing.

## Upcoming review queue (not implemented or not yet committed)

`analytics-refresh` and `analytics-queries` are already in the queue above. Still to come, each needing the same gate: `analytics-data-import` (batch 6a, [plan](batch-06a-data-import.md)) with the optional dataset generator ([plan](batch-06a-dataset-generator.md)), and the backend part of the analytics dashboard (batch 6c, [plan](batch-06c-dashboard.md)). Add them to the table above with their commit hashes when they land; current status is in [analytics-status.md](analytics-status.md). Infrastructure changes are backend-owned work and also require the gate before being marked complete.

## Reviewer output checklist

For each task: the finding table with stable IDs, an explicit "no actionable findings" when applicable, the checks actually run with their results, limitations (for example, checks that could not run), and a clear statement of anything that needs a user decision. Link the finished log from the tracker instead of copying findings into it.
