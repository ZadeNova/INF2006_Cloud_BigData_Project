# Shoe catalogue with sizes

Written 25 September 2026, branch `quarantine`. Status: **approved by the user 26 September 2026 (option 1: derived dataset, `data/raw/` untouched); implemented and merged (26 September 2026, `0291b29`).**

Extends the approved [shoe dataset remap](../archive/plans/shoe-dataset-remap.md) with one scope change the user made on 25 September 2026: **every shoe has 10 sizes**. The remap's "Not in scope: sizes" line is superseded. The user takes over the build that the remap assigned to a teammate. The remap's other rules still apply unchanged: `data/raw/` is not modified, a reproducible script writes a derived dataset, all 100,000 orders and 237,537 lines are kept, the app moves to a new namespace, and the importer must report zero rejects.

## Decisions (user, 25 September 2026)

| Decision | Choice |
|---|---|
| Size model | **One `Product` row per shoe and size (SKU).** A new `catalogue_shoemodel` table groups the SKUs. |
| Sizes | US men's **7, 7.5, 8, 8.5, 9, 9.5, 10, 10.5, 11, 11.5** (10 sizes) |
| Names | Real names that match the 12 3D models, plus 8 colourway variants that reuse a model |
| Shoe count | **20** shoe models, so 200 SKUs |
| Branch | Work directly on `quarantine` |

## Why one product row per size

`Product` is the stock-keeping unit, and every table that references it needs stock at size level: cart lines, checkout stock locking, order lines, inventory snapshots, daily sales and coverage. Making each size its own `Product` keeps all those foreign keys, the checkout transaction and the refresh SQL unchanged. A separate size table would need a new foreign key in five tables and a rewrite of checkout locking, the importer and the coverage SQL.

## Schema

New table `catalogue_shoemodel`:

| Field | Type | Rule |
|---|---|---|
| `id` | auto PK | |
| `namespace` | char 160 | non-empty |
| `external_id` | char 100 | non-empty; unique with `namespace`; for example `S01` |
| `name` | char 200 | for example `Nike Air Max 90` |
| `category` | char 100 | |

Changes to `catalogue_product`:

| Field | Type | Rule |
|---|---|---|
| `shoe_model_id` | FK `catalogue_shoemodel`, `PROTECT`, nullable | |
| `size` | decimal(3,1), nullable | from 1.0 to 20.0, in steps of 0.5 |

- Constraints: `shoe_model` and `size` are both null or both set. `(shoe_model, size)` is unique.
- Why the new columns are nullable: the existing namespace `synthetic/revision-a/demo/v1` still holds 1,200 imported rows. Those rows are protected by sealed inventory and PROTECT foreign keys. A non-null migration has no value to give them. Test fixtures that do not need sizes also stay valid. In the new namespace every product has a model and a size.
- `Product.name` and `Product.category` keep the model's values. Templates, checkout error messages and analytics SQL then keep working without a join. The importer checks that each SKU's name and category match its model.
- New properties:
  - `size_label` returns `"US 9.5"`, or `""` when there is no size.
  - `display_name` returns `"Nike Air Max 90 · US 9.5"`.
- `model_asset` still looks up the `PRODUCT_MODELS` dictionary by `name`. The 8 colourway entries are added to that dictionary.

Migrations: `catalogue/0003` adds the model and the two fields. There is no data migration and no trigger change. The existing `product_source_guard` trigger does not cover the new columns. `docs/SCHEMA.md` is updated in the same change.

## Shoe catalogue: single source

`src/catalogue/shoes.py` is a standard-library module and the only definition of the shoe list. It holds:

- `SIZES`
- `SHOES` (id, name, category, list price, unit cost, 3D asset)
- the size weights
- the shoe weights

It replaces the planned `analytics/shoe_catalogue.csv`. The build script and `seed_demo` both import it, so the two paths cannot disagree. `PRODUCT_MODELS` in `catalogue/models.py` is built from `SHOES`.

Source category pairing is fixed and written into the derived README:

- apparel to Lifestyle
- beauty to Luxury
- electronics to Running
- home to Classics
- office to Basketball
- outdoors to Trail

| ID | Name | Category | Price S$ | Cost S$ | 3D model | Weight |
|---|---|---|---|---|---|---|
| S01 | Air Jordan 1 High | Basketball | 249.00 | 142.00 | air-jordan-1-high | 40 |
| S02 | Air Jordan 1 Classic | Basketball | 229.00 | 131.00 | air-jordan-1-classic | 30 |
| S03 | Air Jordan 1 High "Bred" | Basketball | 259.00 | 148.00 | air-jordan-1-high (reuse) | 20 |
| S04 | Air Jordan 1 Classic "Royal" | Basketball | 235.00 | 134.00 | air-jordan-1-classic (reuse) | 10 |
| S05 | Nike Air Max 90 | Running | 199.00 | 112.00 | nike-air-max-90 | 40 |
| S06 | Adidas Yellow & Black Runner | Running | 169.00 | 95.00 | adidas-yellow-black | 30 |
| S07 | Nike Air Max 90 "Infrared" | Running | 209.00 | 118.00 | nike-air-max-90 (reuse) | 20 |
| S08 | Adidas Runner "Core Black" | Running | 175.00 | 98.00 | adidas-yellow-black (reuse) | 10 |
| S09 | New Balance 574 Classic | Lifestyle | 139.00 | 78.00 | new-balance-574 | 50 |
| S10 | New Balance 997 | Lifestyle | 219.00 | 124.00 | new-balance-997 | 30 |
| S11 | New Balance 574 "Navy" | Lifestyle | 145.00 | 81.00 | new-balance-574 (reuse) | 20 |
| S12 | Converse Chuck High | Classics | 95.00 | 52.00 | converse-high | 50 |
| S13 | Classic Brown Sneaker | Classics | 119.00 | 66.00 | brown-sneaker | 30 |
| S14 | FILA Chunky Sneaker | Classics | 129.00 | 72.00 | fila-sneaker | 20 |
| S15 | Salomon XT-6 | Trail | 265.00 | 150.00 | salomon-xt6 | 50 |
| S16 | Salomon XT-6 "Black" | Trail | 269.00 | 152.00 | salomon-xt6 (reuse) | 30 |
| S17 | Salomon XT-6 "Lunar Grey" | Trail | 275.00 | 156.00 | salomon-xt6 (reuse) | 20 |
| S18 | Air Jordan 1 Low Dior | Luxury | 2990.00 | 1700.00 | air-jordan-1-low-dior | 50 |
| S19 | RTFKT Creator One | Luxury | 1450.00 | 820.00 | rtfkt-creator-one | 30 |
| S20 | RTFKT Creator One "Genesis" | Luxury | 1590.00 | 900.00 | rtfkt-creator-one (reuse) | 20 |

- Every price is distinct, and every cost is below its price.
- Size weights for US 7 to 11.5 are 3, 6, 10, 13, 15, 15, 13, 11, 8, 6. Mid sizes sell most, which gives the size chart a real shape.
- SKU external ID format: `S05-095` (model ID, then the size times 10, zero-padded).
- Price is the same for every size of a model.

## Derived dataset: `analytics/build_shoe_dataset.py`

The remap design applies unchanged except for these three points.

1. **Two-stage mapping.**
   - Each source product maps to one shoe by a seeded weighted choice inside its paired category (seed 42). This is the remap design.
   - Each order line then gets a size by a seeded weighted choice. The seed is `42:<order_item_id>`, so the result does not depend on row order.
   - The line's `product_id` becomes the SKU ID.
   - `product_map.csv` records source product to shoe model. The line-level size is reproducible from the seed, so it is not stored twice.
2. **`products.csv`** has 200 rows with these columns: `product_id sku product_name category list_price unit_cost shoe_id size`.
3. **Money** is computed exactly as the remap design says. Price does not depend on size, so the size step changes no amounts.

The output goes to `data/derived/shoes/`, which is gitignored except `checksums.txt` and `product_map.csv`. The output files are:

- `customers.csv`
- `products.csv`
- `orders.csv`
- `order_items.csv`
- `product_map.csv`
- `checksums.txt`
- `README.md`, which records the changes and the CC BY 4.0 attribution

Newlines are LF and row order is sorted, so output is byte-identical on every run. The script uses the standard library only and imports `src/catalogue/shoes.py` through `sys.path`.

## Importer

In `config/dataset.py` and `import_dataset.py`:

- `shoe_id` and `size` are **optional** product columns, handled like `unit_cost`. Raw data and existing tests still import unchanged.
- Validation when the columns are present:
  - `size` is a valid half size.
  - `(shoe_id, size)` is unique.
  - Every row of one `shoe_id` has the same name and category.
  - A mismatch rejects the product row.
- On persist, the importer first creates one `ShoeModel` per distinct `shoe_id`, then the SKUs with `shoe_model` and `size` set.
- Replay also checks `shoe_model` and `size`.
- The input fingerprint already covers the full source rows, so the new columns are covered with no extra work.
- Stock and lead time are still generated per SKU from its own recent sales. At about 217 lines a day spread over 200 SKUs, each SKU sells about 1 line a day, so the coverage flags stay meaningful.

## Storefront

- **Catalogue `/products/`** lists **shoe models**, 20 at 12 per page, so 2 pages:
  - It shows models in `DEMO_NAMESPACE` that have at least one active SKU.
  - The active SKUs are prefetched and ordered by size.
  - Each card shows name, category, price and the 3D model, as it does now.
  - Each card gets a **size `<select>`** whose option values are SKU primary keys. Out-of-stock sizes appear but are disabled.
  - The stock line summarises the model: in stock, low stock (some sizes low or out), or sold out (every size at 0).
  - The form still posts `product_id` to the unchanged `cart:add` view, so cart and checkout need no logic change.
- **Cart, checkout, order detail and order history** show `size_label` next to each line's category.
- **Operator list `/products/manage/`** stays per SKU, so a single sold-out size can be deactivated. It gains a size column and orders by name, then size, over 200 rows at 12 per page.
- **`seed_demo`** creates the 20 models and 200 SKUs from `shoes.py`, using the current deterministic stock and lead-time rule. It deactivates the old 12 size-less sneaker rows the same way it already retires `demo-` rows.
  - Current SKU external IDs cannot be reused as new identities: the source identity is immutable, and namespace plus external ID is unique.
  - `seed_demo --no-products` behaviour does not change.

Frontend-owned template and CSS edits follow [DESIGN.md](../../DESIGN.md) and add no new visual language: reuse the existing `select`, `stock` and `line__meta` styles.

## Analytics

Refresh (`reporting/services.py`), `DailyProductSales`, inventory snapshots, `verify_refresh.py`, `export_coverage.py` and `segment_customers.py` keep working per `product_id`, which is now the SKU. They need **no change**. The existing zero-mismatch cross-check still applies.

Dashboard query changes in `reporting/queries.py`:

| Query | Change |
|---|---|
| `top_sellers` | Group by **shoe model** (`LEFT JOIN catalogue_shoemodel`). A product without a model counts as its own group, so legacy and test rows still rank. Show the ten best shoes; ties break on the model's lowest product ID. |
| **new `size_sales`** | Units and sales value per size over the span, ordered by size. Products without a size are left out. Shown as a bar chart and an accessible table in the same style as the category section. The previous-period comparison uses the same pattern as categories. |
| `category_sales` | Unchanged: the category stays on `Product`. |
| `coverage` | Stays per SKU, because stock is per size. The row label becomes `display_name` (name and size). |

- `docs/ANALYTICS.md` gains the size-sales formula and the model-level top-seller rule.
- The panel's "Top ten sellers" copy changes from "product ID" to "shoe" wording.
- `analytics/profile_dataset.py` is **not changed** (decided during implementation): it hard-codes the raw row counts and requires payments/refunds, so `--output` alone could not profile the derived set. The numbers the remap wanted from it (no-recent-sales share, flagged share) come from `verify_refresh.py`.

## Namespace switch

`DEMO_NAMESPACE` becomes `synthetic/shoes/revision-a/demo/v1`. The same change goes into:

- `project_manifest.yaml`
- `src/README.md`, `analytics/README.md` and `data/README.md`, where they quote the import commands

The two literals in `tests/test_schema.py` are left unchanged, as the handoff says.

## Tests (targeted)

- **Schema:**
  - the both-or-neither constraint
  - the unique `(shoe_model, size)` constraint
  - an invalid size is rejected
- **Build script** (`analytics/tests/test_build_shoe_dataset.py`, small sample):
  - every source product maps to exactly one shoe
  - the three money identities hold
  - `validate` returns zero rejects
  - regenerating the output is byte-identical
- **Importer:**
  - sized products create models and SKUs
  - inconsistent name, category or duplicate size is rejected
  - replay is unchanged
- **Catalogue:**
  - the list shows one card per model with its sizes
  - out-of-stock sizes are disabled
  - adding a chosen size puts that SKU in the cart
- **Analytics:**
  - top sellers aggregate every size of a model
  - `size_sales` totals equal the summary totals for sized products
- **Existing suites:** run `test_cart`, `test_orders`, `test_catalogue`, `test_import` and the analytics tests. Then run the full suite once after the namespace switch, as the handoff requires.

## End-to-end verification

The environment is a disposable Compose project, `-p inf2006-shoes`, removed at the end. The dev database and `inf2006-foundation` are not touched.

1. Fast check: `validate` on `data/derived/shoes` prints 20,000 customers, 200 products, 100,000 orders, 237,537 order lines and `rejects: 0`.
2. `migrate`, `import_dataset`, replay, `seed_demo --no-products`, then `refresh_analytics --as-of 2026-01-02`.
3. `export_coverage.py` and `verify_refresh.py` report zero mismatches.
4. `segment_customers.py` and `load_customer_segments` run for the new run, and the panel appears.
5. HTTP checks:
   - the catalogue has 2 pages
   - add a size to the cart, then complete checkout
   - the order shows its size
   - the dashboard shows top shoes, the size chart and coverage by size

## Review gate and limits

- Everything under `src/` and `tests/` is backend-owned and needs the [review gate](../DEVELOPMENT.md#backend-review-gate): Astra Medium, or a **fresh-session** Opus 5.5. A self-review from this session is only an early check.
- The data is still synthetic. Sizes are assigned by seeded weights, not taken from real demand. Do not claim real size distributions, shoe demand or seasonality.
- Colourway names are invented variants of real shoes and reuse the base model's 3D asset.
- Do not commit or push unless the user asks.

## Documents to update

- `docs/SCHEMA.md`, `docs/ANALYTICS.md`, `docs/API.md` (the catalogue context now lists models) and `docs/DATA_PIPELINE.md`
- `data/README.md` and `DATA_DICTIONARY.md` (the derived dataset)
- `src/README.md` (add the build step to the demo recipe)
- the `.gitignore` entry for `data/derived/`
- the tracker's current-state and Open-items entries
- a supersede note in `shoe-dataset-remap.md` and `shoe-dataset-handoff.md`
- `AI_USE_DECLARATION.md`

The evidence entry in `evidence/test-data-ai.md` is added only after the end-to-end run passes.
