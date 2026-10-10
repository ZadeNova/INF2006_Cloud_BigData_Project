# Source and application data dictionary

Actual Analytics Engineering v1.0.0 CSV headers; see [provenance](README.md) and
the unchanged [publisher dictionary](raw/DATA_DICTIONARY.md). Identities are namespaced.

| Source field | Source type | Application treatment |
|---|---|---|
| customers.customer_id | text | CustomerProfile.external_id; stable namespaced User identity |
| customers.created_at | date | CustomerProfile.source_signup_at; initial User.date_joined; naive midnight assumed Singapore |
| customers.country_code | text | CustomerProfile.country, at most 100 characters |
| customers.acquisition_channel | text | CustomerProfile.channel, at most 100 characters |
| customers.customer_segment | text | Raw/fingerprint only; no model field |
| products.product_id | text | Product.external_id |
| products.sku | text | Raw/fingerprint only; no SKU model column or identity matching |
| products.product_name | text | Initial Product.name, at most 200 characters; no generated replacement |
| products.category | text | Source-owned Product.category, at most 100 characters; database drift conflicts on replay |
| products.unit_cost | decimal USD | Initial Product.cost, rounded to two places; present throughout this release |
| products.list_price | decimal USD | Initial Product.price, rounded to two places |
| orders.order_id | text | Order.external_id |
| orders.customer_id | text | Namespaced CustomerProfile lookup to Order.owner |
| orders.ordered_at | UTC datetime with Z | Order.placed_at, preserving the instant unless explicitly shifted |
| orders.order_status | enum | completed → completed; cancelled → cancelled; refunded and partially_refunded → refunded |
| orders.currency | text (USD) | Raw/fingerprint only; no exchange conversion; SGD is simulation display convention |
| orders.subtotal | decimal | Validate sum of source line_total; not persisted |
| orders.tax_amount | decimal | Validate finite/nonnegative and source arithmetic; discarded |
| orders.shipping_amount | decimal | Same treatment as tax_amount |
| orders.order_total | decimal | Validate subtotal + tax + shipping; not copied to Order.total |
| order_items.order_item_id | text | OrderItem.external_id; unique across the source table |
| order_items.order_id | text | Namespaced Order lookup |
| order_items.product_id | text | Namespaced Product lookup |
| order_items.quantity | integer | OrderItem.quantity, 1..2,147,483,647 |
| order_items.unit_price | decimal USD | Historical OrderItem.unit_price; ROUND_HALF_UP to two places before multiplication |
| order_items.discount_amount | decimal | Validate quantity × rounded price − discount = line_total; discarded |
| order_items.line_total | decimal | Validate net line/order amounts; application line amount is quantity × rounded price |

| Retained, non-imported table | Actual fields | Profile checks |
|---|---|---|
| payments | payment_id, order_id, paid_at, payment_method, payment_status, amount | Unique IDs, order relationship, timestamps, finite/nonnegative amounts |
| refunds | refund_id, payment_id, order_id, refunded_at, refund_reason, amount | Unique IDs, payment/order relationships, timestamps, finite/nonnegative amounts |

The supported-status gate concerns orders, the only imported status. This batch does
not implement payments or refund accounting.

## Generated fields and transformations

| Application field | Rule / lifecycle |
|---|---|
| namespace | Explicit nonblank argument, at most 160 characters; separate source/mode/revisions |
| User.username | `import-` + full SHA-256 of canonical JSON `[namespace, customer_id]`; checked against profile user, never email/name adoption |
| User.password | Django unusable password at creation only; never reset passwords or permissions |
| User.email/first_name/last_name | Empty defaults; no contacts fabricated or mail sent |
| User.date_joined | Imported signup instant at creation only |
| Product.active | True on creation only |
| Product.shoe_model / size | From optional `products.csv` columns `shoe_id` and `size` (both empty for size-less products). One ShoeModel per distinct `shoe_id` (name and category must agree across its sizes); `size` a half size 1..20, unique per shoe. Only the derived shoe dataset uses them |
| Product.lead_time_days | First draw from `random.Random(f"{seed}:{external_product_id}")`, integer 3..14 |
| Product.stock | Second draw gives 2..20 day factor; ROUND_HALF_UP(recent completed units × factor / 7) to integer; seven complete Singapore dates before cutoff |
| Product.stock with no recent sales | After lead-time/factor draws, draw integer 20..200 |
| Product.cost if absent/empty | 60% of rounded price, ROUND_HALF_UP to two places; fixed simulation assumption, unused for this real release; invalid cost is rejected, not replaced |
| Order.total | Sum rounded historical unit_price × quantity; maximum 999,999,999,999.99 |
| Order.idempotency_key/request_fingerprint | NULL / empty string for history |
| InventoryVersion.cutoff | Next Singapore midnight after latest accepted order, or explicit shift-anchor midnight |
| Shifted timestamps | Integer day offset = target cutoff − original cutoff, applied to all imported signup/order instants; reject any at/after cutoff |
| InventoryVersion.version | `import-v1-` + SHA-256 of accepted raw row dictionaries sorted by external ID, seed, day offset and ISO cutoff; stable JSON keys/separators |
| InventorySnapshot | One per accepted product with original generated stock/lead time; verify completeness then seal; live changes cannot alter snapshots |

Seed defaults to 42. Unit prices/costs must be finite, nonnegative and fit decimal(12,2);
order totals fit decimal(14,2). Explicit timestamp offsets are preserved; naive ones
assume Singapore. Existing source customer/order/item mappings are verified on replay;
original product inputs are checked via the sealed fingerprint, not mutable products.
Changed seed, row set/value or dates conflict in the same namespace. No incremental
extension of an accepted namespace is supported; use a new revision namespace.

Rejected parents reject children; rejected lines invalidate their entire order. All
creation (users, profiles, products, orders, lines, inventory/snapshots) shares one
transaction. Historical import never deducts stock. Existing inventory triggers make
the accepted fingerprint immutable; no migration/additional manifest table is needed.


## Derived shoe dataset (`data/derived/shoes/`)

Built from the unchanged `data/raw/` files by `analytics/build_shoe_dataset.py` (seed 42). Only `checksums.txt` and
`product_map.csv` are committed; the other derived files (`customers.csv`, `products.csv`, `orders.csv`,
`order_items.csv`) are regenerated and verified against `checksums.txt`. Their columns follow the source tables
described above, with product identities, prices and line totals recomputed.

`product_map.csv` (1,200 rows, one per source product; 20 distinct shoes; 6 source categories):

| Column | Meaning |
|---|---|
| `source_product_id` | `product_id` of the source product in `data/raw/products.csv` (for example `P00001`) |
| `source_category` | `category` of that source product; the shoe is chosen by a seeded weighted choice within this category |
| `shoe_id` | Identifier of the shoe model it is re-pointed to (`S01` to `S20`, from `src/catalogue/shoes.py`) |
| `shoe_name` | Display name of that shoe model |

The size of each order line is assigned separately by a seeded weighted choice and is synthetic.
