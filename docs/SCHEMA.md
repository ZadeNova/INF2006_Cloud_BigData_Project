# Schema contract

Initial foundation models/migrations live in src/accounts/, src/catalogue/, src/cart/, src/orders/ and src/reporting/. They establish persistence; application/import/aggregation behaviour is separate. PostgreSQL is required, including the versioned trigger migration reporting/0002_inventory_guards.py. [Data pipeline](DATA_PIPELINE.md) owns source mapping; [scope](../PROJECT_SCOPE_INF2006.md) owns features.

## Fields and constraints

All domain primary keys are BigAutoField unless stated. Foreign keys are NOT NULL unless stated. Source namespace strings are at most 160 characters; external IDs at most 100. Namespace/external ID pairs are nonempty and unique for customers/products/imported orders; PostgreSQL triggers prevent changing those identities. Product identities also scope order lines and inventory, preventing historical/demo mode mixing. Namespace strings are recorded manifest identities, not inferred from user input.

| Entity | Fields and constraints / deletion behaviour |
|---|---|
| Django User | Built-in auth.User selected before initial migrations; framework hashing/permissions/sessions; auth routes are implemented in `accounts`. Source profiles are optional for locally registered users. |
| CustomerProfile | One-to-one User (PROTECT); namespace/external ID; aware source_signup_at distinct from User.date_joined; channel/country up to 100 characters. |
| Product | namespace/external ID; name 200, category 100; price/cost decimal(12,2), finite and nonnegative; stock/lead_time_days nonnegative integers; active boolean. Retire via active rather than deleting historical references. Custom permission `catalogue.toggle_product_active` gates operator activate/deactivate; no other field is operator-writable. |
| Cart | One-to-one owner User (CASCADE); one persistent cart per user, emptied after later checkout rather than keeping multiple active carts. |
| CartItem | Cart (CASCADE), Product (PROTECT), quantity 1..999; unique cart/product. No stock reservation. |
| Order | Owner User (PROTECT); namespace, nullable external_id; status completed/cancelled/refunded; finite nonnegative decimal(14,2) total; aware placed_at; nullable UUID idempotency_key; request_fingerprint up to 64 characters. Indexed owner/date and namespace/status/date. |
| OrderItem | Order and Product (PROTECT); nullable nonempty external_id unique within order; positive quantity; finite nonnegative decimal(12,2) historical unit_price. Product namespace must match order namespace. |
| InventoryVersion | namespace/version (version up to 100), unique pair; aware cutoff; sealed boolean initially false. Append-only identity/cutoff; only false-to-true seal transition is allowed and requires at least one row. |
| InventorySnapshot | InventoryVersion and Product (PROTECT); nonnegative stock and lead_time_days; unique version/product. Product namespace must match version namespace. Rows are append-only, and inserts require an unsealed version. |
| AnalyticsRun | UUID primary key; InventoryVersion (PROTECT); aware window_start/cutoff, cutoff strictly later; status running/completed/failed; started_at, nullable finished_at; nonnegative processed_count; unique UUID summary_version. Running requires null finished_at; terminal status requires finished_at. Selection/window immutable; selected version must be sealed at the same cutoff. Custom permission `reporting.view_analytics` gates the dashboard; migration `0004_analyticsrun_permissions` changes model options only, with no table alteration. |
| DailyProductSales | AnalyticsRun (CASCADE), Product (PROTECT), business_date, nonnegative units, finite nonnegative decimal(18,2) sales_amount; unique run/date/product. Each reported product must have a row in the run's selected inventory version. |

Daily uniqueness is scoped to the run so independently published versions cannot overwrite one another. The later publisher must expose only one completed version per selected reporting context; it must never sum across versions. App business validation must enforce date-window membership and publication completeness; these are not claimed as implemented by the foundation schema.

Demo display currency: SGD as an explicit simulation convention, not a claim about the source's currency or an exchange-rate conversion. Decimal import policy is ROUND_HALF_UP to two places per unit value before summing quantity times historical unit price; retain source values/checksums and reconcile conversion. Enforce precision/range before persistence. Source acceptance must document whether this convention is suitable. Datetimes are aware; PostgreSQL stores instants, and reporting uses Asia/Singapore business dates. Source timezone/actual historical cutoff remains dataset-acceptance work, not an inferred source fact.

Historical Order rows have an external ID and no idempotency key/fingerprint. Live simulated orders have no external ID, require a user-scoped UUID key plus a 64-character lowercase SHA-256 fingerprint, and are completed only. Database uniqueness permits the same key for different users but never two orders for the same user/key. The later checkout service owns canonical fingerprint generation and replay handling.

## Reporting SQL view

`reporting_completed_sale_lines` is created by `reporting/0003_completed_sale_lines_view.py`
(`RunSQL`, reversed by dropping the view). It joins `orders_order` to `orders_orderitem`
and exposes completed lines only: namespace, order_id, placed_at, product_id, quantity,
historical unit_price, quantity-times-unit_price line_total, and the Asia/Singapore
business_date. Refresh uses placed_at for an indexable window bound and business_date
for complete-date membership. Formulas and sparse publication are owned by
[the analytics contract](ANALYTICS.md#processing-and-validation).

## Foundation decisions: DOC-001 and DOC-002

Imported accounts have unusable passwords and are never matched by email/name. CustomerProfile explicitly maps source identity to User. The dataset importer uses a full SHA-256 namespaced username and preserves authentication state on replay. Its accepted-input fingerprint is held in the immutable `InventoryVersion.version` identity (`import-v1-` plus SHA-256), allowing original product inputs to be verified independently of mutable Product fields. One accepted manifest per namespace; changed source revisions require new namespaces. No schema migration was required. Mapping details are in [data dictionary](../data/DATA_DICTIONARY.md); implementation passed independent round-2 review ([record](reviews/analytics-data-import.md)).

Persist immutable dated inventory separately from Product's mutable live stock AND lead time. Build an InventoryVersion and its rows in a transaction, verify all expected products, then seal. Row inserts lock the version to serialize with sealing; update/delete of snapshot rows and changes/unsealing of sealed versions fail at the database level. Corrections use a new version. Historical runs select an explicit namespace/version/cutoff and reject incomplete/mismatched snapshots; there is no fallback to Product values. A run cannot refer to an unsealed or differently dated version.

Reimport and field ownership follow [data pipeline](DATA_PIPELINE.md#safe-reimport-and-fixture-ownership). Mode/source revision/fixture version are part of namespace identity. Default imports and supplemental seeds are create-only, verifying existing rows and preserving live state. Import (`import_dataset`), checkout, snapshot and aggregation (`refresh_analytics`) are implemented and covered by `tests/test_import.py`, `test_orders.py` and the analytics tests; a controlled reset command is not implemented. Foundation tests separately demonstrate immutable snapshot persistence and separation from live Product updates.

## Checkout transaction

1. Authenticate, validate positive bounded quantities and derive owner/prices on server.
2. Resolve user-scoped idempotency key and stable request fingerprint. Equivalent retry returns the original order; changed contents conflict. Clearing the cart must not break equivalent retries. The review page submits the fingerprint of the lines it displayed; it must equal the fingerprint of the locked cart lines to place an order, and the stored fingerprint of an existing order on replay.
3. Lock cart/product state in a consistent order, or use correctly bounded conditional updates; recheck stock and atomically create order/items and deduct stock.
4. Enforce unique non-null user/idempotency key at DB level; handle concurrent uniqueness conflicts so only one order persists.
5. Clear purchased cart state transactionally; confirm only after commit. Never use cached stock/prices to authorise checkout.

Historical import bypasses live checkout and stock deductions. Include migrations with model changes and validate concurrency against PostgreSQL, not SQLite. The checkout service is `orders/services.py`; its concurrency tests use real PostgreSQL connections.
