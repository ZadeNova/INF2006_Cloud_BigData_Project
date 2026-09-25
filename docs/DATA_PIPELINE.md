# Dataset and import contract

Status: source integrity passed on 22 September 2026; the user explicitly accepted the checksummed dataset for descriptive sales/inventory use despite flat-noise risk (DATA-003). Import complete locally; independent round-2 review resolved DATA-001–003 with no new actionable findings. **Gate CLEAR.** [Review log](reviews/analytics-data-import.md), [reproduction](../analytics/README.md), [profile](../data/PROFILE.md). **Switched 22 September 2026**: the original LaelaZ selection was gated and access never granted by the decision deadline. Analytics Engineering describes the replacement as synthetic educational data under CC BY 4.0; this is not an independent generator audit.

The CSV source tables from https://www.analyticsengineering.com/datasets/ecommerce-sales are pinned under data/raw/. Published counts and UTC order coverage match; payments/refunds are retained and profiled but not imported. [Actual fields, dates, checksums and attribution](../data/README.md).

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

Only synthetic data, not anonymised real data. More rows do not establish analytical quality. No fallback generator was needed or implemented in this batch.

## Implemented importer conventions

`config.dataset` reads CSV using the standard library, validates all four tables and
returns valid rows plus row-numbered rejects. `import_dataset --source DIR --namespace NS
[--shift-anchor YYYY-MM-DD] [--allow-rejects] [--seed 42]` creates users, profiles,
products, orders, lines and sealed inventory in one transaction. A namespace advisory
lock serializes importers. Historical import never invokes checkout. The web service
mounts `../data:/app/data:ro`; pandas stays in analytics requirements.

One accepted manifest per namespace is fingerprinted in immutable
`InventoryVersion.version` (`import-v1-` plus SHA-256). Canonical accepted input rows,
seed, offset and cutoff determine it; row order does not. A revision/addition/removal
conflicts rather than extending the namespace. This verifies original product inputs
without overwriting/comparing mutable live fields or introducing a manifest table.
Existing customer/order/item mappings and generated snapshot values are verified on
replay. Product category remains source-owned and is checked against input on replay.
The namespace must contain no products outside the accepted source, because reporting
requires every namespace product in the historical snapshot. Import/replay rejects
such extras before creating rows. Use an empty product namespace and
`seed_demo --no-products` for the operator. That flag does not remove existing demo
products: use a separate namespace/database rather than resetting shared state.

Explicit UTC offsets are preserved; naive inputs assume Asia/Singapore. Default
cutoff is next Singapore midnight after the latest accepted order (2026-01-02 for
the pinned release). Shift-anchor means exclusive midnight cutoff, with all imported
signup/order timestamps shifted by the same whole-day offset and required to precede
it. No year arithmetic. Source USD numerics are used under a disclosed SGD simulation
convention. Source discounts/tax/shipping are validated but excluded from application
totals. Full mappings/generation rules, including missing-cost fallback at 60% of
rounded price, are owned by [data dictionary](../data/DATA_DICTIONARY.md).

Rejects abort by default. With allow-rejects, rejected parents reject children and
any invalid line rejects its entire order, avoiding partial historical orders. Audit
JSON contains table, CSV row, external ID and reasons and is also printed to stdout.
`--rejects-file` selects a writable destination outside source; default temporary files
vanish with a disposable container, so capture stdout or use a mounted output path.

Full scratch import/replay and decimal reconciliation passed. The profile found weak
weekly variation and 31.67–39.75% of products without recent completed sales; these
are documented limitations, not commercial demand evidence. The import review gate is
CLEAR ([log](reviews/analytics-data-import.md)); see the tracker for test counts.
