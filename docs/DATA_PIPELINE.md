# Dataset and import contract

Status: source selected, download/validation pending. The publisher describes [LaelaZ/synthetic-ecommerce](https://huggingface.co/datasets/LaelaZ/synthetic-ecommerce) as fully synthetic with MIT licensing. This is not an independent generator audit.

Download original Parquet files from the [Files tab](https://huggingface.co/datasets/LaelaZ/synthetic-ecommerce/tree/main): customers, products, orders and order_items. Events optional. Verify published counts/date ranges in the scope against downloaded files.

## Reproducible processing

1. Pin source revision; record licence/card, download date and SHA-256 checksums in data/README.md. Never hand-edit downloaded raw files; preserve source bytes and implement transformations as repeatable code with separate outputs. Preserve raw inputs under data/raw/; choose a suitable submission sample with reproduction instructions.
2. Validate unique IDs, relationships, finite/nonnegative money, positive quantities, statuses and chronology. Report rejected rows/counts/reasons, never silently repair or discard them.
3. Map namespaced source identities to [application schema](SCHEMA.md). Record actual source fields and transformations in data/DATA_DICTIONARY.md.
4. Import idempotently, reconcile row counts/decimal totals and test repeated import. Historical import bypasses checkout stock deduction.
5. Generate missing stock snapshots, lead times, display names and demo account/cart fixtures with a fixed seed. Imported users have unusable passwords; generated contacts use reserved example domains and send no mail.
6. Use identical checksummed inputs from private S3 for the cloud demo; retain local input support. Record authorised-read and anonymous-denial evidence.

## Safe reimport and fixture ownership

DOC-002: identities use source/revision + mode + fixture version as a namespace, together with the external ID. Historical, shifted-demo and load namespaces never reuse identities. Load fixtures run in a separate disposable database; shared production/demo state is never a reset target. Namespace strings and date shifts are recorded in the manifest before importing.

Default import is create-only: identical existing source rows are verified and counted as unchanged; conflicting source-owned values abort the transaction with a conflict summary rather than overwrite them. Customer source attributes and historical order/items belong to the source. Product source identity is immutable; live price, cost, name, active flag, stock and lead time belong to application state after initial creation and are not overwritten by reimport. Compare original source values against the accepted input manifest, not mutable live product values. New source revisions use a new namespace, not implicit reconciliation.

Supplemental stock/lead-time seeding is create-only. Never reset existing Product stock, carts, live orders, account password hashes, staff/permission flags or sessions during import. Create imported users with unusable passwords only at creation; use explicit profile source mappings, never email/name matching. Immutable dated inventory is defined in [schema](SCHEMA.md#foundation-decisions-doc-001-and-doc-002); replay verifies snapshot equality and conflicts on changed values.

Any future reset command must explicitly name a disposable database and namespace, reject the shared database, verify no cross-namespace references, and require a deliberate reset flag. It is outside foundation work. Required importer regression: import, change live stock through checkout and account credentials, reimport, then verify stock, credentials, carts and live orders survive unchanged with no duplicates. Record conflict/rollback and mode-isolation tests too.

## Dates and fixtures

Preserve source history by default with an explicit historical cutoff paired with stock generated for that date. Document assumed source timezone. Any demo date shift moves related timestamps by one recorded constant offset and avoids future events relative to the cutoff.

Separate tiny hand-checkable fixtures, imported history, shifted demo data and resettable load data. Live checkouts must not contaminate historical validation. Do not combine current stock with old sales and label coverage current.

Only synthetic data, not anonymised real data. If source acceptance fails, use a documented synthetic generator and record the substitution. More rows do not establish analytical quality. Exact seed/import commands are pending; add verified commands to data/README and the manifest when implemented.
