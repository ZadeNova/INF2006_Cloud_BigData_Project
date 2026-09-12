# Dataset and import contract

Status: source selected, download/validation pending. The publisher describes [LaelaZ/synthetic-ecommerce](https://huggingface.co/datasets/LaelaZ/synthetic-ecommerce) as fully synthetic with MIT licensing. This is not an independent generator audit.

Download original Parquet files from the [Files tab](https://huggingface.co/datasets/LaelaZ/synthetic-ecommerce/tree/main): customers, products, orders and order_items. Events optional. Verify published counts/date ranges in the scope against downloaded files.

## Reproducible processing

1. Pin source revision; record licence/card, download date and SHA-256 checksums in data/README.md. Preserve raw inputs under data/raw/; choose a suitable submission sample with reproduction instructions.
2. Validate unique IDs, relationships, finite/nonnegative money, positive quantities, statuses and chronology. Report rejected rows/counts/reasons, never silently repair or discard them.
3. Map namespaced source identities to [application schema](SCHEMA.md). Record actual source fields and transformations in data/DATA_DICTIONARY.md.
4. Import idempotently, reconcile row counts/decimal totals and test repeated import. Historical import bypasses checkout stock deduction.
5. Generate missing stock snapshots, lead times, display names and demo account/cart fixtures with a fixed seed. Imported users have unusable passwords; generated contacts use reserved example domains and send no mail.
6. Use identical checksummed inputs from private S3 for the cloud demo; retain local input support. Record authorised-read and anonymous-denial evidence.

## Dates and fixtures

Preserve source history by default with an explicit historical cutoff paired with stock generated for that date. Document assumed source timezone. Any demo date shift moves related timestamps by one recorded constant offset and avoids future events relative to the cutoff.

Separate tiny hand-checkable fixtures, imported history, shifted demo data and resettable load data. Live checkouts must not contaminate historical validation. Do not combine current stock with old sales and label coverage current.

Only synthetic data, not anonymised real data. If source acceptance fails, use a documented synthetic generator and record the substitution. More rows do not establish analytical quality. Exact seed/import commands are pending; add verified commands to data/README and the manifest when implemented.
