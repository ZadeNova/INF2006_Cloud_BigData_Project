# Shoe dataset remap

> **26 September 2026:** extended and built by [shoe-sizes-catalogue.md](shoe-sizes-catalogue.md). The user took over the build, added 10 sizes per shoe (superseding "Not in scope: sizes" below), fixed the count at 20 shoes and moved the catalogue from `analytics/shoe_catalogue.csv` to `src/catalogue/shoes.py`. Where they differ, that plan wins.

Written 24 September 2026, branch `erfan/analytics`. Status: **approved, plan only, nothing built.** How to start and what not to break: [shoe-dataset-handoff.md](shoe-dataset-handoff.md). Goal: turn the imported catalogue of 1,200 mixed products into a shoe shop of a few dozen products (the teammate decides the count; the user's estimate is 20 to 40) without touching the downloaded raw files, keeping the sales history, the analytics numbers and every integrity check meaningful. Agreed with the user: raw data stays unchanged and a reproducible script makes a separate derived dataset ([AGENTS.md](../../AGENTS.md), [data pipeline](../DATA_PIPELINE.md)); the remap approach was chosen over a subset.

## Why a remap and not a subset

Measured on the raw data (24 September 2026):

- Product demand is nearly uniform: **148 to 247 order lines per product, median 197**, spread 7% of the mean. A subset of 40 products would keep that per-product rate (about 0.18 lines a day), so roughly a third of products would still show "no recent sales", and total sales would fall to about 7 lines a day.
- Historical prices track list prices tightly: `unit_price / list_price` is **0.96 to 1.04**, and 38% of lines carry a discount.

Mapping every source product onto one of the shoes keeps all 100,000 orders and 237,537 lines. That is about 217 lines a day across the catalogue, so each shoe sells about 5 lines a day at 40 shoes and about 11 at 20; the coverage and replenishment flags become meaningful and the charts have a signal.

## Approval gate

**Approved by the professor, 24 September 2026.** The tracker's Open items row is updated accordingly. Adoption is still gated on the script itself: the app is not switched to the derived data, nothing is recorded as evidence, and the report does not describe it, until the derived dataset passes `config.dataset.validate` with zero rejects (see step 4 in the build order below) and a teammate has built and checked it in.

**Ownership: a teammate builds this**, per the user's 24 September decision. They own the shoe catalogue file (`analytics/shoe_catalogue.csv`), `analytics/build_shoe_dataset.py`, and the namespace switch and its tests/docs/evidence (step 4 below). This plan remains the agreed design; check with them before changing it.

## Decisions (24 September 2026)

1. Approval: **granted by the professor, 24 September 2026** (above).
2. Derived CSVs are **generated on demand**, not committed. The script, the shoe catalogue, the product map and `checksums.txt` are committed.
3. Shoe categories and names: **another group member decides**. They supply `analytics/shoe_catalogue.csv` (spec below).
4. Price range: **the same member decides**.
5. Number of shoes: **the teammate decides**, expected 20 to 40 (25 September 2026).

## Design

**Input:** `data/raw/*.csv` (unchanged). **Output:** `data/derived/shoes/` with `customers.csv`, `products.csv`, `orders.csv`, `order_items.csv`, `product_map.csv` (source product to shoe, the audit trail), `checksums.txt` and a README. `payments.csv` and `refunds.csv` are not imported and their amounts would no longer match, so they are omitted.

**Shoe catalogue (supplied by a group member):** a small hand-authored input, `analytics/shoe_catalogue.csv`. It is committed, so the shop's contents are reviewable and not generated. The script reads it and does not care what the shoes are called; it only needs the structure below.

| Column | Rule |
|---|---|
| `shoe_id` | Unique, at most 100 characters, for example `S001` |
| `sku` | Unique text |
| `name` | 1 to 200 characters; fictional brands are safest for licensing |
| `category` | 1 to 100 characters; **exactly 6 distinct categories** (one per source category) |
| `list_price` | Decimal with at most 2 places, greater than 0 |
| `unit_cost` | Decimal with at most 2 places, greater than 0 and below `list_price` |

The teammate decides the total (the user's estimate is **20 to 40**; the original proposal was 6 categories x 7 = 42). The hard rule is **at least 3 shoes in every category**, so at least 18 in total. Each shoe should have a distinct price so the price column in the dashboard is not flat. Until the member delivers the file the script is tested against a clearly labelled placeholder catalogue that is not committed as the real one.

**Category-preserving mapping:** the six source categories map one-to-one onto the six shoe categories, so per-category sales totals and shares are unchanged and the category chart keeps its shape. The pairing of a source category to a shoe category is arbitrary and is decided together with the catalogue. Within a category the 200 source products are assigned to that category's shoes by a **seeded weighted choice** (seed 42, weights declared in the script), so some shoes become bestsellers. A uniform assignment would make all shoes nearly identical (with k shoes in a category each would average about 200/k source products of similar demand) and leave the top-sellers table flat.

**Same shoe on two lines of one order.** Several source products map to each shoe, so some multi-line orders will contain the same shoe twice. A rough uniform estimate on the 72,221 multi-line orders is 7% to 16% (3 to 7 shoes per category), and weighted assignment raises it. The schema allows this (`OrderItem` is unique on order and line ID, not on product) and analytics sums are unaffected. Recommended: accept and document it, which keeps 237,537 lines; merging duplicates would change the line count and need a weighted price. Recorded as a decision for the teammate in the handoff.

**Rewriting rows:** only the columns that carry product identity or money change.

| Table | Changed | How |
|---|---|---|
| `order_items` | `product_id`, `unit_price`, `discount_amount`, `line_total` | `product_id` from the map; `unit_price = shoe list_price x (source unit_price / source list_price)`, which keeps the 0.96 to 1.04 drift; `discount_amount` keeps the source discount rate; `line_total = unit_price x quantity - discount_amount` |
| `orders` | `subtotal`, `tax_amount`, `order_total` | `subtotal` = sum of the new `line_total`; `tax_amount` keeps the source rate on `subtotal`; `shipping_amount` unchanged; `order_total = subtotal + tax + shipping` |
| `customers`, order ids, dates, statuses, quantities | none | unchanged |

Everything is Decimal, rounded ROUND_HALF_UP to cents. The importer rejects any row where `unit_price x quantity - discount != line_total`, any order where the line sum `!= subtotal`, and any order where `subtotal + tax + shipping != order_total`, so the script must satisfy all three exactly, and the acceptance check is that `config.dataset.validate` returns **zero rejects** on the output.

**Determinism:** same inputs and seed give byte-identical output (LF newlines, fixed column order, sorted rows), so `checksums.txt` is stable across machines.

## Where things live and what changes

| Item | Decision |
|---|---|
| Script | `analytics/build_shoe_dataset.py`, standard library only, run with host Python 3 like `init_env.py` |
| Derived files | Generated on demand, not committed (about the size of `data/raw`); the map, catalogue and `checksums.txt` are committed. The Demo data recipe gains one step (run the script), and `data/derived/` is gitignored. |
| Namespace | A new one, for example `synthetic/shoes/revision-a/demo/v1`, because changed source data needs a new namespace. `DEMO_NAMESPACE` in `settings.py` changes to it, along with `project_manifest.yaml` and the docs and recipes that quote the old value. The tests need no edit: they read `settings.DEMO_NAMESPACE`, and the two literals in `tests/test_schema.py` are fixture strings that must stay different from that file's own `NAMESPACE`. |
| Importer, refresh, dashboard | No code change expected: same tables, same rules, same cutoff (`2026-01-02`). |
| `analytics/profile_dataset.py` | Needs an `--output` option, because it always overwrites `data/PROFILE.md`. Profile the derived set to `data/derived/shoes/PROFILE.md`. |
| `analytics/verify_refresh.py` | Recomputes from the imported tables, so it should run unchanged; confirm when running it. |

## Verification (in a disposable Compose project, removed afterwards)

1. Script tests: mapping covers every source product exactly once; each shoe gets at least one source product; per-category totals are preserved; the three arithmetic rules hold on a sample and on the full output; regeneration is byte-identical.
2. `validate` gives zero rejects; `import_dataset` creates 20,000 users, the chosen number of products, 100,000 orders and 237,537 lines, and replay reports everything unchanged.
3. Profile the derived set and read the numbers: share of shoes with no recent sales (expected about zero), top-seller spread, flagged share.
4. `refresh_analytics --as-of 2026-01-02`, then `export_coverage.py` and `verify_refresh.py`: zero mismatches, as for the raw import.
5. Storefront and dashboard over HTTP: the catalogue has 2 to 4 pages at 12 per page, the dashboard shows categories and top sellers with distinct values.
6. Customer segments: segments are stored per analytics run and the panel appears only when the selected run has assignments, so after the refresh run `analytics/segment_customers.py` and `load_customer_segments` for the new run and check the panel. Prices change in the remap, so the clusters will differ from the current ones.

## Documents and evidence to update after approval

`data/README.md` and `DATA_DICTIONARY.md` (a derived dataset, its mapping and every changed field), `evidence/test-data-ai.md` (a new run; the September 22 results stay as history), `project_manifest.yaml` `data_ai`, `docs/DATA_PIPELINE.md`, `docs/ANALYTICS.md` figures, `src/README.md` Demo data recipe, the Open items row in the tracker, and the report.

## Honesty and licence

- The result is a **synthetic derived dataset**: product identities, names, prices and categories are replaced. The sales timing and volume patterns are the source's, and they are weak (see [PROFILE.md](../../data/PROFILE.md)). Do not claim shoe demand, seasonality or real product performance; say what was changed and why.
- CC BY 4.0 requires attribution and an indication that changes were made. Keep the attribution and record the changes in the derived README.
- Imported customers keep unusable passwords.

## Steps and sizes

| Step | Size |
|---|---|
| 1. Group member delivers `shoe_catalogue.csv` (not our work) | S, theirs |
| 2. `build_shoe_dataset.py`, weights and mapping, with tests, against a placeholder catalogue | M |
| 3. `--output` for the profiler; scratch import, profile, refresh, cross-check | S to M |
| 4. On professor approval: namespace switch, tests, docs, evidence, tracker | M |

About one working day of our work in total. The cross-check tooling already exists, so this is a re-run, not new verification code.

## Still open

The catalogue file and the product count, both from the teammate or the group member they agree it with. Nothing else blocks steps 2 and 3.

## Not in scope

Product images, sizes or colour variants (one row per model), new schema fields, and any change to the raw files.
