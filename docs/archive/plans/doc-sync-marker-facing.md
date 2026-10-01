# Doc sync: marker-facing README, manifest, ML reproduction and test counts

Written 27 September 2026, branch `syah&hermann/ML`. Approved by the user from the docs sync audit
(items 1, 2, 5 and 7). Documentation only; no code changes. Remaining audit items (API context
table, review-gate wording, scope, ML status, threat map, attribution, naming, hygiene) are later passes.

## 1. README.md

Replace claims contradicted by the repository:

- Status paragraph (24 September): functional/security evidence and the storefront browser
  walkthrough now exist (`evidence/README.md`, FUNC-01/02, SEC-01..08, 26 September); the shoe
  catalogue is the baseline; the latest changes await their logged independent review.
- Features: shoe catalogue (20 models x 10 US sizes, 3D previews), product detail page, operator
  filters.
- Dataset paragraph: the application imports the derived shoe dataset built from unchanged `data/raw/`.
- Testing paragraph and limitations: remove "evidence files record no run yet" and "no recorded
  walkthrough"; replace the 1,200-product "32–40% without recent sales" with the shoe run's
  9 of 200 while keeping the weak-weekly-pattern caveat; cite the suite count from tests/README.md.
- Layout: `analytics/` also builds the shoe dataset and holds the ML scripts.

## 2. project_manifest.yaml

- `verified_scratch_namespace` / `verified_inventory_version`: the shoe DATA-01 values
  (`synthetic/shoes/data-check/v1`, `import-v1-3e9692…`). The fingerprint in
  `config/dataset.py` excludes the namespace, so the dashboard namespace has the same version.
- `security.secrets_handling`: local generated `src/.env` (git-ignored) and production Secrets
  Manager startup loading, linking the canonical contracts.
- `local_release.status`: say the changes after the recorded Phase 6 review await review.

## 5. analytics/README.md reproduction block

Import `data/derived/shoes` (built by `analytics/build_shoe_dataset.py`) into
`settings.DEMO_NAMESPACE`, refresh with the importer-reported inventory version instead of a
hard-coded 1,200-product hash, and keep the raw-revision commands identified as historical.

## 7. Test count

Run the full suite once at HEAD in Docker and record the count in `tests/README.md` only;
README.md and docs/TESTING.md link to it instead of repeating a number.
