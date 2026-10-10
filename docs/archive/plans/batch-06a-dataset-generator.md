# Batch 6a (alternative) — deterministic dataset generator

Written before implementation, per `CLAUDE.md`'s "Discuss / Plan" step. Companion to [batch-06a-data-import.md](batch-06a-data-import.md). Contracts: [DATA_PIPELINE.md](../../DATA_PIPELINE.md), [SCHEMA.md](../../SCHEMA.md), [ANALYTICS.md](../../ANALYTICS.md).

## Context

**Role narrowed on 22 September 2026.** This plan was originally the fallback for a gated source dataset. That situation resolved differently: the team switched to the Analytics Engineering Ecommerce Sales Dataset, which is not gated and is already downloaded (see `PROJECT_SCOPE_INF2006.md` §5 and [batch-06a-data-import.md](batch-06a-data-import.md)). The generator is therefore **no longer the historical-import fallback**. Its remaining jobs:

- **Fixtures the real dataset cannot provide:** the isolated, resettable load-test fixture with sufficient stock and repeatable shoppers, kept separate from historical data per DOC-002 (`PROJECT_SCOPE_INF2006.md`'s "maintain three fixtures" rule). The tiny hand-checkable correctness fixture is written inline in the import tests and does not need this generator.
- **Better analytics story, if wanted:** patterns are planted and known, so the dashboard can be shown to recover them (weekly pattern, popular products, a price change). Whether the real dataset needs this supplement depends on what `analytics/profile_dataset.py` reports about its sales signal.
- **Second-line fallback:** if profiling rejects the real dataset on integrity grounds, this becomes the primary source again, and the substitution is recorded.

The generator writes the **same four-table CSV schema** as the source dataset, so `import_dataset` (6a) is unchanged and needs no second reader. Every planted parameter is documented, and results on it validate the method, not real demand (stated as a limitation in every place it is used).

## Decisions to confirm before implementation

1. **Location and runner.** Core code in `src/config/dataset_generator.py` and a `generate_dataset` management command, beside the importer, **recommended**. The container image copies only `src/` and mounts only `tests/`, so a generator under `data/` or `analytics/` could not be tested in the project's Docker test flow. Run on the host through Compose: `docker compose run --rm --user "$(id -u):$(id -g)" -v "$PWD/data:/app/data" web python manage.py generate_dataset --out /app/data/generated` (the `--user` avoids root-owned output files).
2. **Dependencies.** Python standard library only: `random.Random(seed)` for draws and `csv` for output. `pyarrow` is **not** needed — the source is CSV, so the importer reads CSV with `csv.DictReader` and the generator writes it the same way (the originally planned `pyarrow` dependency was dropped, see [batch-06a-data-import.md](batch-06a-data-import.md) decision 6). No numpy or pandas in the web image.
3. **Timeline and timestamps.** Defaults are sized for the generator's actual purpose rather than mirroring a source dataset: enough customers, products and orders for a repeatable load fixture, over a window that includes a leap day so date handling is exercised. Proposed: 2,000 customers, 200 products, 20,000 orders, 366 days from 2024-01-01, all overridable by flag. (The earlier defaults mirrored the superseded LaelaZ dataset's shape and no longer track anything.) Order and signup times are naive local timestamps in the same textual form as the source CSVs; the import's timezone assumption applies.
4. **Events table.** Not generated. It is not imported, so generating it would be unused code. Documented as a difference.
5. **Planted customer segments and truth file.** Customers are drawn from four latent segments; an optional `customer_segments.csv` (customer ID and segment, never imported) records the truth, **recommended**. It allows K-means (batch 6d, if it happens) to be evaluated against known structure, with the caveat that we planted it.
6. **Status mix.** 80% completed, 10% refunded, 10% cancelled (the source is about 67% completed). More completed sales give more analytics signal while still exercising exclusion.
7. **Committing output.** Commit the generator, its documented parameters and checksums of the default output; commit the default output itself only if it is small (under about 20 MB), so a marker has sample data without generating. Larger scale outputs are never committed.

## What the generator plants

Every parameter is a documented constant in the module and listed in `data/README.md`. Random draws use one seeded `random.Random`, and per-entity choices use derived seeds so output does not depend on iteration order.

| Structure | Definition | Why |
|---|---|---|
| Weekly pattern | Relative order weight by weekday: Mon 1.00, Tue 0.90, Wed 0.95, Thu 1.00, Fri 1.15, Sat 1.30, Sun 1.20 | Visible in the daily chart; testable |
| Trend | Linear growth, +30% from first to last day | A range comparison that means something |
| Promotion | One 14-day window with +40% weight for one category | An event the dashboard can show |
| Product popularity | Zipf-like weights, exponent about 0.9, across the generated product count and six categories | Meaningful top sellers and a long tail (some products with zero recent sales) |
| Prices | Log-normal base price, median about S$30, range roughly S$5 to S$200; cost is 40% to 70% of base; about 10% of products have one price change (10% to 25%) on a random date, and order lines carry the price in force on the order date | Exercises the "historical price" rule with real data |
| Hour of day | Evening-weighted (peak 19:00 to 22:00) | Realistic timestamps; exercises Singapore date boundaries near midnight |
| Basket | 1 to 5 distinct products per order (weights 35/30/20/10/5); quantity 1 to 4 (weights 55/25/12/8) | Matches the source's ranges |
| Customer segments | `champion` 10% (high order rate, recent, larger baskets), `regular` 40%, `occasional` 35%, `lapsed` 15% (active only until a random date within the first 60% of the timeline); each customer's rate also has Gamma-shaped variation | Skewed orders per customer and real recency structure for RFM |
| Signup | Before the customer's first possible order; no order predates signup | Chronology invariant |
| Channel and country | Weighted lists (Singapore-centred: SG about 60%, then MY, ID, PH, TH, VN, AU, US) | Plausible attributes; not used by analytics |
| Product names | Category-specific readable names, unique (the source uses `SKU-0001` placeholders) | Storefront-friendly; DATA_PIPELINE already expects generated display names |

Orders are allocated to days by weighted sampling with the day weight (weekday x trend x promotion), then to eligible customers (signed up and not lapsed) by segment-rate weight. Currency is SGD by simulation convention. Money is stored as doubles rounded to two decimals, like the source, so the importer's `ROUND_HALF_UP` conversion is exercised.

## Implementation

- **`src/config/dataset_generator.py`:** pure functions returning table data (lists of dicts or column lists) for customers, products, orders, order items and the optional truth table, plus `write_csv(tables, out_dir)` using the standard-library `csv` module, with the source's exact column names and textual formats (matching `data/raw/DATA_DICTIONARY.md` and the schema recorded in `data/DATA_DICTIONARY.md`). Parameters live in one documented constants block.
- **`src/config/management/commands/generate_dataset.py`:** `--out DIR`, `--seed 42`, `--customers`, `--products`, `--orders`, `--start YYYY-MM-DD`, `--days 366`, `--with-truth`. Refuses to overwrite an existing output directory unless `--force`. Prints row counts, date range and the SHA-256 of each file.
- **Scale option:** `--orders 1000000` streams rows straight to `csv.writer` day by day, so memory stays bounded without any chunking machinery. Measure and record the actual run time; do not quote a figure before measuring. Scale outputs are for load fixtures.
- **Compose:** a read-only `../data:/app/data:ro` mount on the `web` service so the importer can read `/app/data/...` in the container (also required by the import plan); the generator run overrides it read-write as shown above.
- **Docs:** `data/README.md` (generator section: purpose, parameters table, how to run, checksums, "planted structure, not real behaviour"), `data/DATA_DICTIONARY.md` (fields of the generated tables), DATA_PIPELINE.md (record the substitution or the fixture role), `project_manifest.yaml` (`data_ai.dataset`, `reproducible_command`), `AI_USE_DECLARATION.md` (generator code is AI-assisted and verified by tests).
- **Profile compatibility:** `analytics/profile_dataset.py` accepts `--source DIR` so the same profile runs on generated data and reports whether the planted structure is detectable.

## Tests (`tests/test_dataset_generator.py`, no database unless noted)

Small parameters, fixed seeds. Because the seed is fixed, threshold checks are deterministic (checked once against the seeded output, not statistical flakes).

- **Schema:** column names and dtypes equal the documented source schema; the truth table is separate and optional.
- **Integrity:** unique IDs; every foreign key resolves; all prices and costs positive; quantity in 1 to 4; only the three statuses; no order before its customer's signup; no lapsed customer orders after their lapse date.
- **Determinism:** two runs with one seed produce equal tables and equal checksums; a different seed differs. CSV output is plain text written by the standard library, so byte-for-byte identity across runs is a reasonable assertion here (unlike Parquet, where it would have depended on the writer version).
- **Planted structure detectable:** weekend mean daily orders at least 1.15 times the weekday-Tuesday mean; the promotion window lifts its category; the top 10% of customers place at least 30% of orders; top products dominate as Zipf implies; at least one product's order lines show both its old and new price; status shares within a few points of 80/10/10 at default size.
- **Output safety:** refuses to overwrite without `--force`; scale mode produces the requested order count with bounded memory (small-scale proxy test).
- **Import compatibility (PostgreSQL, added when 6a's importer exists):** the default generated dataset passes the importer's validation with zero rejects and imports with reconciled counts.

## Verification

Run `generate_dataset` through Compose with the default seed; record row counts, file sizes and checksums; run `analytics/profile_dataset.py --source data/generated` and confirm the planted structure shows up (weekly pattern, skew, price changes); `docker compose run --rm web pytest -q tests/test_dataset_generator.py` then the full suite; `manage.py check`; `makemigrations --check --dry-run` (no model changes). After 6a's importer exists, import the generated data twice and confirm idempotence. Then a Claude self-review (labelled), fix approved findings, update the tracker. The independent backend review gate applies (import/analytics-owned code). Commit only when asked; the user pushes.

## Out of scope

Clickstream events, real-world realism claims, ML on the data (batch 6d), load user accounts (separate disposable load fixture).
