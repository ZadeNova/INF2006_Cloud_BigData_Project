# Analytics Engineering dataset

Attribution: Analytics Engineering, "Ecommerce Sales & Returns Dataset v1.0.0".
Source: <https://www.analyticsengineering.com/datasets/ecommerce-sales>.
Downloaded **22 September 2026**, CSV source-table release. Licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); the publisher's notice
is preserved in [raw/LICENSE.txt](raw/LICENSE.txt). Redistribution/adaptation requires attribution.

The publisher describes fictional, synthetic educational data with no real people
or organisations. Its README identifies generator version 1.0.0 and seed 2025090501;
we have not audited that generator. Original CSVs, documentation and starter examples
remain unchanged under `raw/`. Payments and refunds are retained but not imported.

## Acceptance on 22 September 2026

[PROFILE.md](PROFILE.md) is deterministic output from the independent pandas profiler.
All six published row counts matched. Zero rows were rejected by the ID, relationship,
status, finite/nonnegative money, positive quantity, chronology and exact decimal
reconciliation checks. **Manual acceptance recorded on 22 September 2026:** the user explicitly accepted
this checksummed dataset for descriptive sales/inventory demonstrations despite
weak patterns and flat-noise risk. This resolves the scope decision for DATA-003;
independent round-2 review cleared its implementation; DATA-001–003 are resolved. The earlier automatic overall PASS was insufficient and is superseded:
positive variance can be flat random noise. Integrity passes, but that alone does
not accept the dataset. Independent review found DATA-001–003; see the
[review log](../docs/reviews/analytics-data-import.md).

The accepted limited use is descriptive sales totals, rankings and an illustrative
inventory mechanism, with no demand/seasonality/forecast validation claim. Evidence:
daily mean 91.158 and variance 87.549, weekday mean ratio 1.025, varying historical
unit prices, and 31.67–39.75% of products without completed sales in sampled weeks.
These metrics describe the limitation; they are not a statistical rejection of flat
noise. The user's acceptance is a scope decision, not statistical evidence of useful
trend, seasonality or forecasting quality. Integrity failure still blocks import.
No fallback dataset/generator is substituted.

| File | Rows | SHA-256 |
|---|---:|---|
| customers.csv | 20,000 | `aa564464d95a344e055c95dc96380dbdb4d3055112d56385a829b9863d499f98` |
| products.csv | 1,200 | `45bccbc014c318d1902f50b94fe952e1d7a753638f6994a406d632e65b10c6f3` |
| orders.csv | 100,000 | `7c244862a063c8313c73679d96d0b95cc21adc890bef5df4595ec3fcc4a5f03c` |
| order_items.csv | 237,537 | `da2213afac3dedf2af1be7cffbfaa16518dad97d5bd611c54c05451d2261b646` |
| payments.csv | 105,388 | `3490bcfefca40133229bc446b834a2685d3268df65995f55e85530f607aed05a` |
| refunds.csv | 7,910 | `d4a030e15e3069f8df8620470ecb64b594ec1cf51e4c8766f4b9ce136a1b0005` |

These match [raw/checksums.txt](raw/checksums.txt). Actual fields and transformations
are documented in [DATA_DICTIONARY.md](DATA_DICTIONARY.md). No raw file is rewritten.

## Dates and currency

The source explicitly labels order timestamps UTC and supplies `Z` offsets.
Preserving those instants gives **2023-01-01 08:27:20 through 2026-01-01 07:59:03
Asia/Singapore**, matching published UTC coverage 2023-01-01..2025-12-31.
Naive signup dates (and any naive timestamp inputs) assume Asia/Singapore; this is
an application assumption. Signup dates span 2023-01-01..2023-04-01.

The unshifted cutoff is **2026-01-02 00:00:00+08:00**, the next Singapore midnight
after the latest accepted order. `--shift-anchor YYYY-MM-DD` selects an exclusive
midnight cutoff; one whole-day offset moves every imported signup/order date so
the last order falls on the preceding date. Every imported event must precede the
cutoff. This preserves intervals and handles leap days without adding calendar
years. Use a separate namespace for shifted fixtures. Full verification used no shift;
the deployed demo anchor has not been selected.

Source money is **USD**, according to the publisher. The application retains the
numeric values and labels its simulation **SGD**; this is neither a source-currency
claim nor a currency conversion. Unit values use Decimal ROUND_HALF_UP to two places
before multiplication. Source net lines reconcile to subtotal; subtotal plus tax and
shipping reconciles to order_total. Application orders sum historical unit price ×
quantity, discarding discount/tax/shipping. `partially_refunded` maps to `refunded`;
both are excluded from completed sales.

## Reproduce

See [analytics/README.md](../analytics/README.md) for profiling and verification.
The Compose web service mounts raw files read-only at `/app/data/raw`:

```powershell
docker compose -p inf2006-dataset-review run --rm --no-deps web python manage.py import_dataset --source /app/data/raw --namespace synthetic/revision-a/demo/v1
```

This ran twice in a newly created scratch project, not a shared database. First run
created 20,000 users/profiles, 1,200 products, 100,000 orders, 237,537 items, one sealed
inventory and 1,200 snapshots. Replay reported all unchanged. Independent SQL found
zero per-order total mismatches. Application lines total **62,484,389.20**; completed
lines total **55,821,834.61**. Inventory identity:
`import-v1-9884d29e2bf9a64778c63858230ebd71223569b293c28c8acb895b1920e10d0f`.

One namespace accepts one canonical input manifest, seed and date convention.
Before first import it must have no products; on replay it must contain only accepted
source products. Existing demo products cause a conflict, because historical reporting
requires a snapshot for every namespace product. Use `seed_demo --no-products` before
inserting demo products; it does not delete existing ones. Use a separate namespace or
scratch database instead of resetting shared state. Category is source-owned and
category drift in the database conflicts on replay.
Changed inputs conflict; use a new namespace for revisions. Replay preserves live
products, passwords, staff flags, carts, sessions and checkout orders/stock. The
accepted fingerprint lives in the sealed inventory identity, independently of mutable
Product fields. CSV row ordering does not affect it or generated inventory; only
accepted rows enter the fingerprint.

Rejects abort before database writes by default. `--allow-rejects` imports complete
valid orders only. Rejected parents reject children; a rejected line also rejects its
whole order. Every rejected row number/ID/reason is printed and written as JSON.
Default audit files are in the container temporary directory and disappear with
`--rm`; capture stdout or set `--rejects-file` on a writable bind mount to retain them.
Audit files are forbidden inside the source directory.

## Limitations

Daily orders vary (32..120, mean 91.158), but weekday max/min mean is only 1.025:
there is little weekly pattern and no evidence of real seasonality. Between 31.67%
and 39.75% of products have no completed sales in sampled seven-day windows (35.92%
at the historical cutoff). Their coverage is unavailable. Historical prices vary;
current list prices must not replace them.

Generated inventory demonstrates the mechanism, not real supply conditions; stock
is deliberately correlated with recent sales. The UTC source end gives a partial
final Singapore sales date: complete calendar dates cannot supply missing source
hours. Synthetic sales do not establish demand, elasticity or forecast accuracy.
Analytics refresh against this data, dashboard, ML, S3/cloud remain outside this batch.
Imported users cannot log in until a password is deliberately set.
