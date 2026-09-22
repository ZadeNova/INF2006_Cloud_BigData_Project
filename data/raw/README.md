# Ecommerce Sales & Returns Dataset v1.0.0

A deterministic synthetic commerce system built for source modeling, revenue reconciliation, cohort analysis, and data-quality practice.

This is synthetic educational data generated to model a fictional business. It does not represent a real company or establish industry benchmarks.

## Contents

- `customers`: 20,000 rows
- `products`: 1,200 rows
- `orders`: 100,000 rows
- `order_items`: 237,537 rows
- `payments`: 105,388 rows
- `refunds`: 7,910 rows

The source CSV ZIP preserves normalized source tables. SQLite contains the same
tables. XLSX and Parquet contain an analysis-ready denormalized view. Starter
examples demonstrate safe read-only exploration.

## Reproducibility

Built by `datasets/generate.py` with version `1.0.0` and seed
`2025090501`. See `manifest.json` for row profiles, reference outputs,
validation checks, file sizes, and SHA-256 checksums.

## License

See `LICENSE.txt`. Limitations from the catalog:
- This is synthetic educational data generated to model a fictional business. It does not represent a real company or establish industry benchmarks.
- All monetary values are USD.
- No PII is included.
