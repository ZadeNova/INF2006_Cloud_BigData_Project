# Shoe dataset handoff

> **26 September 2026:** no longer needed for a teammate: the user built it with sizes; see [shoe-sizes-catalogue.md](../../plans/shoe-sizes-catalogue.md).

Written 25 September 2026 for the teammate who builds the shoe dataset, and for the Claude Code session they work with. Companion to the design, [shoe-dataset-remap.md](shoe-dataset-remap.md): that file says **what** and **why**; this one says how to start, how to check your work in seconds, and what not to break. If the two disagree, the design wins; tell the user so it can be fixed.

## The job

1. Turn the imported dataset (1,200 mixed products) into a **shoe shop**, without touching `data/raw/`. A script reads the raw CSVs and writes a separate derived dataset.
2. **You decide the number of shoes**, plus their names, categories and prices (or agree them with the group member who supplies the catalogue). The user's estimate is 20 to 40. The design needs at least 3 shoes in each of the 6 categories, so at least 18.
3. Keep all **100,000 orders and 237,537 order lines**. Only the columns that carry product identity or money change.
4. The derived dataset must pass the importer's own validation with **zero rejects**.
5. Then switch the app to a new namespace and re-check analytics, the dashboard and the customer segments.

The professor approved modifying the dataset on 24 September 2026. The result is a **synthetic derived dataset**: never claim real shoe demand or seasonality (see [Honesty](shoe-dataset-remap.md#honesty-and-licence)).

## Before you start

- **Branch from `origin/erfan/analytics`** while its pull request into `main` is still under review: `git fetch`, then `git switch -c <yourname>/shoe-dataset origin/erfan/analytics`. That branch already contains everything you need (the importer, dashboard, segments and these docs); do not branch from an older commit or from `main`, which lacks them until the pull request merges. Never push to `erfan/analytics` itself; only the user does.
- **Keeping up.** Review fixes may land on `erfan/analytics` while you work: `git fetch`, then **merge** `origin/erfan/analytics` into your branch (do not rebase; other people's commits are shared). After the pull request merges, merge `origin/main` the same way; it will be clean because it contains the same commits, and from then on `main` is your base and your pull request's target.
- **Your session has no memory of this project.** It reads `CLAUDE.md` and `AGENTS.md` on its own. Also have it read, in this order: the [design](shoe-dataset-remap.md), this file, [DATA_PIPELINE.md](../../DATA_PIPELINE.md), [batch-06a-data-import.md](batch-06a-data-import.md) (the importer's rules), [data/README.md](../../../data/README.md).
- **Plan first.** `CLAUDE.md` requires your own plan in `docs/plans/` before implementation. Do not just paste this file back.
- **Verify by running.** Numbers in these docs were true on 25 September 2026; re-check anything you depend on.
- **Do not commit or push** unless you tell the session to.
- You need Docker and Python 3 on the host. The script uses the standard library only.

## What is yours, and what needs review

| Yours | Needs the review gate |
|---|---|
| `analytics/shoe_catalogue.csv`, `analytics/build_shoe_dataset.py` and its tests, the `--output` option for the profiler, `data/derived/` docs, the evidence and report text about the derived set | Anything under `src/` or `tests/`, including the one-line `DEMO_NAMESPACE` change. Import tooling counts as backend-owned work: see [the gate](../../DEVELOPMENT.md#backend-review-gate) (Astra Medium, or Opus 5.5 in a **fresh** session). Ask the user to run it before anything is merged. |

## Fast check loop: seconds, no Docker

`config/dataset.py` uses only the standard library, so the importer's real validation runs on your laptop against any folder of CSVs. Run this from the repository root (save it anywhere, for example `analytics/check_dataset.py`):

```python
import sys
sys.path.insert(0, "src")
from collections import Counter
from config.dataset import load_source, validate

valid, rejects = validate(load_source(sys.argv[1]))
print({table: len(rows) for table, rows in valid.items()}, "rejects:", len(rejects))
for reason, count in Counter(r for entry in rejects for r in entry["reasons"]).most_common():
    print(count, reason)
```

`python3 analytics/check_dataset.py data/derived/shoes`. On the raw data it prints `{'customers': 20000, 'products': 1200, 'orders': 100000, 'order_items': 237537} rejects: 0` in about 2.4 seconds (checked 25 September). Your target is the same line with your product count and `rejects: 0`.

Reading the output: **one bad line rejects its whole order**, so a single wrong `line_total` also shows "missing/rejected order items" and "missing/rejected order". Fix the arithmetic reasons first; the cascade disappears with them.

## What the importer requires

- **Four files with these exact column names** (extra columns are ignored; missing ones fail immediately): `customers.csv` (`customer_id created_at country_code acquisition_channel customer_segment`), `products.csv` (`product_id sku product_name category list_price`), `orders.csv` (`order_id customer_id ordered_at order_status currency subtotal tax_amount shipping_amount order_total`), `order_items.csv` (`order_item_id order_id product_id quantity unit_price discount_amount line_total`). `products.csv` may also carry `unit_cost`; without it the importer derives cost as 60% of price.
- **Three exact identities, in cents:** `unit_price x quantity - discount_amount = line_total`; the order's line totals sum to `subtotal`; `subtotal + tax_amount + shipping_amount = order_total`. Use `Decimal` with `ROUND_HALF_UP`, never floats, and compute in that order.
- **Every `order_items.product_id` must exist in `products.csv`**, and every order needs at least one valid line.
- **Stock and lead times are generated by the importer** (seeded, from recent sales), not by your script.

## Steps

1. **Catalogue.** `analytics/shoe_catalogue.csv` with the columns in the design (`shoe_id, sku, name, category, list_price, unit_cost`). Exactly 6 categories, at least 3 shoes each, distinct prices. Until the real one exists, test against a clearly labelled placeholder that is **not** committed as the real catalogue.
2. **Script.** `analytics/build_shoe_dataset.py`: reads `data/raw/`, writes `data/derived/shoes/` (`customers`, `products`, `orders`, `order_items`, `product_map`, `checksums.txt`, a README). Deterministic: same input and seed give byte-identical output (**LF newlines**, fixed column order, sorted rows). Write tests against a small sample.
3. **Check.** Run the fast loop until `rejects: 0`.
4. **Profiler.** `analytics/profile_dataset.py` always writes `data/PROFILE.md` (line 142 hardcodes it), which is the committed profile of the **real** dataset. Add an `--output` option first, then profile the derived set to `data/derived/shoes/PROFILE.md`.
5. **Verify in a disposable project** (see below), then read the numbers: share of shoes with no recent sales (expected about zero), top-seller spread, flagged share.
6. **Namespace switch** (below).
7. **Segments** (below).
8. **Docs and evidence** listed in the design, including `AI_USE_DECLARATION.md` (your Claude use belongs there; it is already stale) and the CC BY 4.0 note that changes were made.

## Verifying in a disposable project

Use `docker compose -p inf2006-shoes ...` so nothing touches your dev database: **sealed inventory versions cannot be deleted**, so an import into the dev database is permanent until you wipe the volume. The exact build, `migrate`, import and cleanup sequence is in [analytics/README.md](../../../analytics/README.md) (replace the project name and use `--source /app/data/derived/shoes` and your new namespace); the Compose file already mounts `data/` read-only at `/app/data`, so derived files are visible without changes. `docker compose ... down --volumes` at the end removes it.

Two gotchas: the image **copies `src/` at build time**, so run `docker compose -p inf2006-shoes build web` after editing `settings.py`; and `refresh_analytics` and the dashboard read `DEMO_NAMESPACE`, so either switch it before the check or pass `--namespace` explicitly.

Then: `import_dataset` (zero rejects, replay reports everything unchanged), `seed_demo --no-products`, `refresh_analytics --as-of 2026-01-02`, `analytics/export_coverage.py` and `analytics/verify_refresh.py` (zero mismatches), and an HTTP look at the catalogue and `/analytics/`.

## The namespace switch

A namespace is a text label on rows; the app shows only rows whose label equals `settings.DEMO_NAMESPACE`. Changed data needs a **new** label (the importer refuses to load into a namespace that already holds different products), for example `synthetic/shoes/revision-a/demo/v1`. Change it in:

- `src/config/settings.py:105` (`DEMO_NAMESPACE`), a backend change: review gate.
- `project_manifest.yaml` (`verified_scratch_namespace`).
- The commands quoted in `src/README.md` (Demo data), `analytics/README.md` and `data/README.md`.

Tests need **no** namespace edits: they read `settings.DEMO_NAMESPACE`, and the two literals in `tests/test_schema.py` are fixture strings that must differ from that file's own `NAMESPACE`, so leave them. Run the full suite after the switch to confirm.

## Customer segments after the switch

Segments (optional ML) are stored per **analytics run**, and the dashboard shows the segment panel only when the selected run has assignments. Every new `refresh_analytics` creates a new run, so after the shoe import and refresh, get the run id, then run `analytics/segment_customers.py --run-id <id>` and `load_customer_segments` (commands in [analytics/README.md](../../../analytics/README.md#optional-ml-offline-rfm-k-means)). Without this the panel is simply absent. Segmentation reads customer order totals, and the remap rewrites prices, so the clusters will differ from the current ones.

## Decisions to make and record

- **How many shoes.** Lines per shoe per day is about 217 lines a day divided by your count: roughly 11 at 20 shoes, 5 at 40. More shoes means a longer tail and more "no recent sales".
- **Same shoe twice in one order.** Several source products of one category map to each shoe, so some multi-line orders get two lines with the same shoe. A rough estimate on 72,221 multi-line orders is 7% to 16% at 3 to 7 shoes per category, and weighted (bestseller) assignment makes it more likely. The schema allows it (uniqueness is on order and line ID, not product) and analytics sums are unaffected. **Recommended: accept and document it**, which keeps the 237,537 lines. Merging duplicate lines would change the line count and needs a weighted price.
- **Category pairing.** The 6 source categories (`apparel`, `beauty`, `electronics`, `home`, `office`, `outdoors`, 200 products each) map one-to-one onto your 6 shoe categories; the pairing is arbitrary but must be written down in `product_map.csv`'s README.
- **Weights** for the seeded assignment (some shoes must become bestsellers or the top-sellers table is flat).

## Do not

- Edit, delete or reformat anything in `data/raw/`.
- Overwrite `data/PROFILE.md` (add `--output` first).
- Commit `data/derived/`: add it to `.gitignore` first. Commit the script, catalogue, `product_map` and `checksums.txt`.
- Import into the dev database or the `inf2006-foundation` project.
- Use floats for money, or write CRLF newlines.
- Change application code beyond the one-line namespace setting without the review gate.
- Write shoe demand, seasonality or "real" performance into the report; say what was changed and why.

## Numbers to expect

| Item | Expected |
|---|---|
| customers, orders, order lines | 20,000 / 100,000 / 237,537 (unchanged) |
| products | your count, decided above |
| validation rejects | 0 |
| cutoff | `2026-01-02T00:00:00+08:00` (unshifted) |
| refresh daily rows | **will differ** from the current 65,589 (that is for 1,200 products); do not compare |
| products with no recent sales | about zero (currently 31.67% to 39.75% of the 1,200) |
| catalogue pages | 2 to 4 at 12 per page (for 20 to 40 shoes) |

## Done when

- [ ] Fast check: your product count, `rejects: 0`, and regeneration is byte-identical (`checksums.txt` stable).
- [ ] Script tests pass; full test suite passes after the namespace switch.
- [ ] Disposable-project import, replay-unchanged, refresh, `verify_refresh` (zero mismatches) and the HTTP look at the shop and dashboard are recorded.
- [ ] Profile of the derived set written to its own file, and the raw profile untouched.
- [ ] Segments re-run for the new run and the panel appears.
- [ ] Docs and evidence updated as listed in the design, the tracker's Open items row updated, `AI_USE_DECLARATION.md` updated.
- [ ] Review gate run on the analytics and `src/` changes (fresh-session reviewer), findings logged in `docs/reviews/`.
