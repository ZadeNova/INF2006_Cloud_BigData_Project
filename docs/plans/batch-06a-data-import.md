# Batch 6a — dataset acceptance, import and seed

Written before implementation, per `CLAUDE.md`'s "Discuss / Plan" step. First of three analytics sub-batches: **6a data** (this file), **6b refresh and read queries** ([batch-06b-analytics-refresh.md](batch-06b-analytics-refresh.md)), **6c dashboard page** (outlined at the end of 6b). Optional ML (K-means) is a later, gated batch 6d. Contracts: [ANALYTICS.md](../ANALYTICS.md), [DATA_PIPELINE.md](../DATA_PIPELINE.md), [SCHEMA.md](../SCHEMA.md), [INF2003_BASELINE.md](../INF2003_BASELINE.md).

## Context

The application has no real data yet: the catalogue holds 14 hand-written demo products from `seed_demo`, and no historical orders exist. The analytics batches need a credible history to aggregate. The chosen source is [LaelaZorana/synthetic-ecommerce](https://huggingface.co/datasets/LaelaZorana/synthetic-ecommerce) (renamed from `LaelaZ`; pinned revision `04ba3b7ad88904d27169e2e998b7b22c44b3029d`). The files are **gated**: access was requested by the user on 20 September 2026 and the Parquet files cannot be downloaded until it is granted. Its dataset card (saved as `data/raw/DATASET_CARD.md`) states: 2,000 customers, 120 products, 12,000 orders, 30,120 line items, 59,599 events, 2024, Parquet, MIT licence, with no seasonality and deliberately simple relationships. Those figures are unverified until step 1 runs. If access does not arrive by about 22 September, the fallback is [batch-06a-dataset-generator.md](batch-06a-dataset-generator.md), which produces the same table schema so the importer below is unchanged.

This batch does four things: profile and accept (or reject) the dataset, import it create-only and idempotently, generate the fields the source lacks (stock, lead times, inventory snapshot), and document provenance. It does not touch checkout, cart or any analytics code.

## Decisions to confirm before implementation

Each has a recommendation; none is settled until the user agrees.

1. **Namespace.** Import into `settings.DEMO_NAMESPACE` (`synthetic/revision-a/demo/v1`, the shifted-demo mode of DOC-002), **recommended**. Storefront, cart and checkout are hardwired to that namespace, and the `order_item_namespace_guard` trigger requires an order and its products to share one. Importing into a separate historical namespace would mean the store sells different product rows from the ones that carry the history, and live orders could never appear in analytics.
2. **Date shift.** Shift all imported dates forward by one recorded constant number of whole days so the last source order date lands on a chosen anchor date just before the demo cutoff, **recommended**. Unshifted 2024 data would leave a 20-month gap before live demo orders. Shift by days, never by adding a year (29 February). Record the offset and anchor in the manifest. Consequence: after a shift, 29 February 2024 no longer appears in the data, so leap-day coverage comes from explicit-date test fixtures, and the sentence in ANALYTICS.md ("The dataset includes 29 February 2024") must be amended to say so.
3. **Source timezone.** Naive source timestamps are assumed to be `Asia/Singapore`, **recommended**, and recorded as an assumption, not a claim about the source. It makes source dates equal business dates and keeps hand-checking simple.
4. **Rejects.** If validation rejects any row, the command reports counts and reasons and aborts by default; `--allow-rejects` imports the valid rows and writes a rejects file, **recommended**. Rejected parents reject their children. Nothing is silently repaired.
5. **`seed_demo` coexistence.** Leave the command unchanged. The 14 hand-written products can coexist in the namespace (different external IDs), but the cloud demo should not run it for products. `seed_demo` also creates the `demo-operator` account, so add a small `--no-products` flag rather than splitting the command. Skip if the user prefers to leave it alone.
6. **Dependency.** Add `pyarrow` (Parquet reader, not an ML library) to `src/requirements.in` and regenerate `requirements.txt` the way the repo already does; pandas stays in `analytics/requirements.txt` only, so the web image stays light.
7. **Raw files in git.** Commit `data/raw/` only if the four tables are small (roughly under 20 MB total); otherwise ignore them and commit SHA-256 checksums plus download instructions. Decide after the download.

## Step 1: acquire and profile (the acceptance gate)

- Download the four required Parquet files (customers, products, orders, order_items) at a pinned revision into `data/raw/`, unchanged. Record source revision, licence text, download date and SHA-256 checksums in `data/README.md`. Events are optional, kept raw, not imported (INF2003 baseline rule 5).
- `analytics/profile_dataset.py` (pandas; own `analytics/requirements.txt`; `--source DIR`, default `data/raw`) reads the files and writes `data/PROFILE.md`:
  - Verified counts and date range against the published figures.
  - Integrity: unique IDs, orphan foreign keys, statuses and how they map to completed/cancelled/refunded, nonnegative money, positive quantities, per-order sum of lines against the order total.
  - **Signal for analytics:** daily order volume over time, per-product unit variance, weekly pattern strength, status mix, price stability per product.
  - **Signal for K-means:** orders per customer distribution, recency spread.
- **Gate:** if integrity fails, the sales are flat noise, or access is not granted in time, choose the fallback: the deterministic generator planned in [batch-06a-dataset-generator.md](batch-06a-dataset-generator.md), writing the same four-table Parquet schema to `data/generated/`, so the importer below is unchanged. Record the substitution. The gate outcome is reported to the user before step 2. Note the card already warns of flat sales, so expect the profile to show weak sales signal even if the data is valid; the customer-order skew it describes may still support K-means.

## Step 2: mapping and validation (pure code, no database)

- The importer touches accounts, catalogue and orders, so it lives with the other cross-app command in `src/config/`: reader and validator in one module, `src/config/dataset.py` (no package, no repository layer), and the command in `src/config/management/commands/import_dataset.py` beside `check_database`. (`src/tools/` holds standalone bootstrap scripts and is not used.) The module exposes `load_source(path)` (pyarrow to plain dicts), `validate(source)` returning valid rows plus a rejects list (row, reason), and the field mapping.
- Record the actual source fields and transformations in `data/DATA_DICTIONARY.md` (one row per field used, from the real files).
- Money: `ROUND_HALF_UP` to two places per unit value before quantity multiplication ([SCHEMA.md](../SCHEMA.md)). SGD is a simulation convention.
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

Tiny hand-checkable Parquet fixtures written with pyarrow in `tmp_path` (about 3 customers, 2 products, 5 orders including one cancelled and one refunded, 8 lines). PostgreSQL only.

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

Analytics code (6b), the dashboard (6c), ML (6d), S3 access and Terraform (cloud phase), a data reset command, and any INF2003 schema (variants, merchants, reviews).
