# Schema contract

Status: proposed logical schema, no migrations implemented. [Data pipeline](DATA_PIPELINE.md) owns source mapping; [scope](../PROJECT_SCOPE_INF2006.md) owns features.

| Entity | Fields and constraints |
|---|---|
| Django User | Framework authentication; choose user-model strategy before first migration |
| CustomerProfile | User link, namespaced external ID, source signup date, channel, country; unique source identity when present |
| Product | Source identity, name, category, decimal price/cost, nonnegative stock and lead-time days, active flag |
| Cart | Authenticated owner; one active cart per user |
| CartItem | Cart/product foreign keys, positive quantity; unique cart/product |
| Order | Owner, optional source identity, status, decimal total, aware timestamp, optional live idempotency key and request fingerprint |
| OrderItem | Order/product foreign keys, positive quantity and historical decimal unit price |
| DailyProductSales | Business date/product, units and sales amount; unique date/product |
| AnalyticsRun | Run ID, window/cutoff, status, timestamps, counts and summary version |

Specify lengths, precision, choices and deletion behaviour alongside initial models. Use one documented demo currency; do not infer source currency as SGD fact. Protect historical references and retire products with an active flag. Imported source IDs are not globally unique application IDs. Imported users have unusable passwords by default; source signup date differs from app account creation time.

Initial historical statuses: completed, cancelled, refunded. Live simulated checkout creates completed orders only after commit. Additional states require API/data/analytics updates. No refund UI required.

## Checkout transaction

1. Authenticate, validate positive bounded quantities and derive owner/prices on server.
2. Resolve user-scoped idempotency key and stable request fingerprint. Equivalent retry returns the original order; changed contents conflict. Clearing the cart must not break equivalent retries.
3. Lock cart/product state in a consistent order, or use correctly bounded conditional updates; recheck stock and atomically create order/items and deduct stock.
4. Enforce unique non-null user/idempotency key at DB level; handle concurrent uniqueness conflicts so only one order persists.
5. Clear purchased cart state transactionally; confirm only after commit. Never use cached stock/prices to authorise checkout.

Historical import bypasses live checkout and stock deductions. Include foreign-key/check constraints and indexes for owner history, timestamps/status and summaries. Justify additional indexes with query patterns. Include migrations with model changes and validate concurrency against PostgreSQL, not SQLite.
