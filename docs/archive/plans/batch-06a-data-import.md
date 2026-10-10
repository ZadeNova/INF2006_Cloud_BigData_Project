# Batch 6a — dataset acceptance, import and seed

Written before implementation, per `CLAUDE.md`'s "Discuss / Plan" step. First of three analytics sub-batches: **6a data** (this file), **6b refresh and read queries** ([batch-06b-analytics-refresh.md](../../plans/batch-06b-analytics-refresh.md)), **6c dashboard page** (outlined at the end of 6b). Optional ML (K-means) is a later, gated batch 6d. Contracts: [ANALYTICS.md](../../ANALYTICS.md), [DATA_PIPELINE.md](../../DATA_PIPELINE.md), [SCHEMA.md](../../SCHEMA.md).

## Context

The application has no real data yet: the catalogue holds 14 hand-written demo products from `seed_demo`, and no historical orders exist. The analytics batches need a credible history to aggregate. The original chosen source, [LaelaZ/synthetic-ecommerce](https://huggingface.co/datasets/LaelaZ/synthetic-ecommerce) on Hugging Face, was **gated**: access was requested by the user on 20 September 2026 and never granted by the team's 22 September decision deadline. **Switched 22 September 2026** to the [Ecommerce Sales Dataset from Analytics Engineering](https://www.analyticsengineering.com/datasets/ecommerce-sales) — not gated, CC BY 4.0. **Downloaded 22 September 2026**: the CSV source-tables release (not Parquet; the site also offers Parquet, Excel and SQLite, but the CSV source tables are what the team took), saved to `data/raw/` with its own `DATA_DICTIONARY.md`, `LICENSE.txt`, `README.md` and `starter/` examples, checksummed in `data/raw/checksums.txt`. Its data dictionary states: 20,000 customers, 1,200 products, 100,000 orders, 237,537 order items, 105,388 payments (not imported), 7,910 refunds (not imported), coverage January 2023-December 2025 — row counts confirmed exact by direct count against the downloaded files. Full integrity validation (uniqueness, orphan keys, status mapping, per-order monetary reconciliation) still awaits the `profile_dataset.py` step below. See `PROJECT_SCOPE_INF2006.md` §5 for the full column mapping, including the `partially_refunded` status collapse and the discarded tax/shipping/discount columns. The deterministic generator ([batch-06a-dataset-generator.md](batch-06a-dataset-generator.md)) is no longer the historical-import fallback for this reason, but remains needed for the tiny hand-checkable correctness fixture and the isolated load-test fixture (`PROJECT_SCOPE_INF2006.md`'s "maintain three fixtures" rule); it would still serve as a second-line fallback if this dataset fails validation once profiled.

This batch does four things: profile and accept (or reject) the dataset, import it create-only and idempotently, generate the fields the source lacks (stock, lead times, inventory snapshot), and document provenance. It does not touch checkout, cart or any analytics code.

## Decisions to confirm before implementation

Each has a recommendation; none is settled until the user agrees.

1. **Namespace.** Import into `settings.DEMO_NAMESPACE` (`synthetic/revision-a/demo/v1`, the shifted-demo mode of DOC-002), **recommended**. Storefront, cart and checkout are hardwired to that namespace, and the `order_item_namespace_guard` trigger requires an order and its products to share one. Importing into a separate historical namespace would mean the store sells different product rows from the ones that carry the history, and live orders could never appear in analytics.
2. **Date shift.** Shift all imported dates forward by one recorded constant number of whole days so the last source order date lands on a chosen anchor date just before the demo cutoff, **recommended, but smaller than originally planned**. Unshifted data (coverage January 2023-December 2025) leaves roughly a 9-10 month gap between the last imported order and a live demo cutoff around October 2026 — much smaller than the 20-month gap the original, since-superseded LaelaZ selection (2024-only) would have left, but still worth closing so live checkout activity doesn't look disconnected from the imported history. Because the real range already covers the scope's suggested historical reporting cutoff (1 January 2025, `PROJECT_SCOPE_INF2006.md` §5), the *unshifted* data can be used directly for historical analytics validation; only the *live-demo* fixture needs the shift. Shift by days, never by adding a year (29 February). Record the offset and anchor in the manifest. Consequence: after a shift, the source's 29 February 2024 may no longer land on 29 February in the shifted fixture, so leap-day coverage there comes from explicit-date test fixtures; the unshifted historical fixture keeps its real leap day, so this only needs checking against `ANALYTICS.md`'s leap-day wording if that file is touched.
3. **Source timezone.** Naive source timestamps are assumed to be `Asia/Singapore`, **recommended**, and recorded as an assumption, not a claim about the source. It makes source dates equal business dates and keeps hand-checking simple.
4. **Rejects.** If validation rejects any row, the command reports counts and reasons and aborts by default; `--allow-rejects` imports the valid rows and writes a rejects file, **recommended**. Rejected parents reject their children. Nothing is silently repaired.
5. **`seed_demo` coexistence.** Leave the command unchanged. The 14 hand-written products can coexist in the namespace (different external IDs), but the cloud demo should not run it for products. `seed_demo` also creates the `demo-operator` account, so add a small `--no-products` flag rather than splitting the command. Skip if the user prefers to leave it alone.
6. **Dependency.** **Revised 22 September 2026 after download:** the actual source is CSV, not Parquet, so no new dependency is needed at all. `load_source(path)` uses Python's standard-library `csv.DictReader`; `validate()` does the same manual type coercion (Decimal, int, date parsing) it needed regardless of file format. `pyarrow` is dropped from this batch entirely — one fewer dependency than planned. pandas remains `analytics/requirements.txt`-only, so the web image stays exactly as light as originally intended.
7. **Raw files in git.** **Decided 22 September 2026: commit them.** The four imported tables total ~20.0 MB (customers 0.84 MB, products 0.07 MB, orders 7.8 MB, order_items 11.3 MB) — right at the original threshold; all six tables plus `DATA_DICTIONARY.md`, `LICENSE.txt`, `README.md` and the `starter/` reference examples total ~27 MB, trivial for git. Reasoning: no PII (synthetic), CC BY 4.0 explicitly permits redistribution with attribution, and committing removes an external-download dependency that the submission's own reproducibility checklist (a marker running on a clean machine, without paid or account-gated access) would otherwise penalise. SHA-256 checksums for all six tables are already recorded in `data/raw/checksums.txt`.

## Step 1: acquire and profile (the acceptance gate)

- **Done 22 September 2026:** the six CSV source tables (customers, products, orders, order_items, payments, refunds) plus the publisher's `DATA_DICTIONARY.md`, `LICENSE.txt`, `README.md` and `starter/` examples, downloaded unchanged into `data/raw/`; SHA-256 checksums recorded in `data/raw/checksums.txt`. Record the download date and licence text in `data/README.md` when that file is written. Payments and refunds are kept raw, not imported.
- `analytics/profile_dataset.py` (pandas; own `analytics/requirements.txt`; `--source DIR`, default `data/raw`) reads the files and writes `data/PROFILE.md`:
  - Verified counts and date range against the published figures.
  - Integrity: unique IDs, orphan foreign keys, statuses and how they map to completed/cancelled/refunded, nonnegative money, positive quantities, per-order sum of lines against the order total.
  - **Signal for analytics:** daily order volume over time, per-product unit variance, weekly pattern strength, status mix, price stability per product.
  - **Signal for K-means:** orders per customer distribution, recency spread.
- **Gate:** if integrity fails or the sales turn out to be flat noise once profiled, choose the fallback: the deterministic generator planned in [batch-06a-dataset-generator.md](batch-06a-dataset-generator.md), writing the same four-table schema to `data/generated/`, so the importer below is unchanged. Record the substitution. The gate outcome is reported to the user before step 2. Unlike the superseded LaelaZ card, this dataset's own documentation makes no seasonality/flat-sales disclosure either way; `profile_dataset.py` (not yet run) is what will actually show the sales signal and the customer-order skew relevant to K-means.

## Step 2: mapping and validation (pure code, no database)

- The importer touches accounts, catalogue and orders, so it lives with the other cross-app command in `src/config/`: reader and validator in one module, `src/config/dataset.py` (no package, no repository layer), and the command in `src/config/management/commands/import_dataset.py` beside `check_database`. (`src/tools/` holds standalone bootstrap scripts and is not used.) The module exposes `load_source(path)` (`csv.DictReader` to plain dicts), `validate(source)` returning valid rows plus a rejects list (row, reason), and the field mapping.
- Record the actual source fields and transformations in `data/DATA_DICTIONARY.md` (one row per field used, from the real files).
- Money: `ROUND_HALF_UP` to two places per unit value before quantity multiplication ([SCHEMA.md](../../SCHEMA.md)). SGD is a simulation convention.
- Source values map: customer to `User` + `CustomerProfile`; product to `Product`; order to `Order` (status mapped, `external_id` set, no idempotency key, empty fingerprint per `order_origin_valid`); line item to `OrderItem` (`unit_price` is the historical price).

## Step 3: `import_dataset` management command

`python manage.py import_dataset --source data/raw --namespace <ns> [--shift-anchor YYYY-MM-DD] [--allow-rejects] [--seed 42]`

- Reads a local directory only. The image copies only `src/` and `src/compose.yaml` mounts only `tests/`, so add a read-only `../data:/app/data:ro` mount to the `web` service; the command then reads `/app/data/raw` (or `/app/data/generated`) inside the container. Cloud demo: sync the checksummed S3 files to a local directory first (`aws s3 sync`); the command never talks to S3, so the local fallback rule holds and no AWS code enters the app.
- One transaction. Creates in this order: users, profiles, products, orders, order items, each with `bulk_create` in chunks. Users get `set_unusable_password()`; usernames are stable and namespaced (for example `cust-<external_id>`); never matched to existing accounts by name or email. If a user with that username exists without the matching profile, abort as a conflict.
- Create-only, DOC-002 semantics: loads existing namespace rows into memory (sizes are small) and compares; identical rows count as unchanged, a differing source-owned value aborts the whole transaction with a conflict summary. Product live fields (price, cost, name, active, stock, lead time) belong to the application after creation and are never overwritten or used for comparison; compare against the accepted source values only.
- Applies the date shift to `placed_at` and `source_signup_at`, refuses any result after the anchor cutoff, and prints the offset.
- Prints a reconciliation: rows read, valid, rejected, created, unchanged; decimal total of lines against source order totals per status.

## Step 4: generated supplements (same command, deterministic)

Not in the source: `Product.stock`, `Product.lead_time_days` (and `cost` if the source lacks it). Generated with `random.Random(f"{seed}:{external_id}")` per product, so results do not depend on iteration order.

- `lead_time_days`: 3 to 14, seeded.
- `stock`: derived from the product's average daily units over the seven complete dates before the cutoff, times a seeded factor of 2 to 20 days. This spreads coverage around the lead times so the replenishment flag has both flagged and unflagged products. Products with no recent sales get a seeded 20 to 200. This is stated as a limitation: stock is synthetic and correlated with sales by construction, so the flags demonstrate the mechanism, not real inventory behaviour.
- Live `Product` stock and lead time are set once at creation from these values. An `InventoryVersion` (`version` derived from the seed and fixture version) at the import cutoff is built with one row per product from the same generator values, then sealed. Replay compares against the generator's expected values, not live `Product` stock (which checkout may have changed), and conflicts if an existing version differs.
- Never reset existing stock, carts, orders, passwords or sessions.

## Tests (`tests/test_import.py`, new)

Tiny hand-checkable CSV fixtures written directly as plain text in `tmp_path` (about 3 customers, 2 products, 5 orders including one cancelled and one refunded, 8 lines). PostgreSQL only.

- Counts and field mapping; unusable passwords; profile-to-user mapping; decimal `ROUND_HALF_UP` behaviour.
- Idempotent re-import: no duplicates, all rows reported unchanged.
- Conflict: change one source price in the fixture, re-import, expect a full rollback and a conflict summary.
- Required regression from DATA_PIPELINE: import, change live stock and a password, add a live order and cart, re-import; stock, credentials, carts and live orders survive unchanged, no duplicates.
- Validation: negative price, zero quantity, orphan product, unknown status, duplicate ID are reported, not repaired; default aborts, `--allow-rejects` imports the rest; rejected parent rejects children.
- Date shift: fixed-day offset applied to every timestamp, relative intervals preserved, no result after the anchor, a shifted 29 February lands on a valid date.
- Namespace isolation: a second namespace imports the same source without colliding.
- Generator: same seed gives identical stock and lead times; snapshot is sealed, complete for every product and equals the generator values; live stock change does not change the sealed snapshot.

## Verification

`docker compose up --build -d --wait`; run `profile_dataset.py`, review `data/PROFILE.md` with the user, then the import against a scratch database; import twice and confirm the second reports everything unchanged; `docker compose run --rm web pytest -q tests/test_import.py` then the full suite (no regressions; existing 135 tests); `manage.py check`; `makemigrations --check --dry-run` (expect no changes: no model changes this batch); spot-check the storefront shows the imported products and one imported order appears on a customer's history page (using a password reset in the shell, since passwords are unusable). Then a Claude self-review (labelled as such), fix approved findings, update `docs/IMPLEMENTATION_PLAN.md`, `docs/DATA_PIPELINE.md` (status and verified commands), `data/README.md`, `data/DATA_DICTIONARY.md`, `project_manifest.yaml` (`data_ai` fields) and `docs/ANALYTICS.md` if the date shift is adopted. The mandatory independent backend review gate in AGENTS.md applies before this is marked complete. Commit only when asked; the user pushes.

## Out of scope

Analytics code (6b), the dashboard (6c), ML (6d), S3 access and Terraform (cloud phase), a data reset command.
