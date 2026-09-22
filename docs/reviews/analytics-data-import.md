# Analytics dataset Phases 1–2 review

Base/HEAD: `3deed85024e841bd9dccc99c1860ca379d5012bc`, branch `CL/Analytics`.
Scope: full uncommitted dataset batch, including untracked files; owned paths are
listed in the [tracker handoff](../IMPLEMENTATION_PLAN.md#dataset-phases-12-review-handoff-22-september-2026).
Reviewed implementation paths: `analytics/profile_dataset.py`, `analytics/requirements.txt`,
`analytics/README.md`, `data/PROFILE.md`, `data/README.md`, `data/DATA_DICTIONARY.md`,
`src/config/dataset.py`, `src/config/management/commands/import_dataset.py`,
`src/catalogue/management/commands/seed_demo.py`, `src/compose.yaml`, `tests/test_import.py`,
`docs/IMPLEMENTATION_PLAN.md`, `docs/DATA_PIPELINE.md`, `docs/SCHEMA.md`,
`docs/ANALYTICS.md`, this review record, and `project_manifest.yaml`.
Commit preparation additionally updates the status checklist in
`docs/plans/backend-completion-roadmap.md`; no implementation change.
No unrelated changes were present. References: [batch 6a](../plans/batch-06a-data-import.md),
[roadmap Phases 1–2](../plans/backend-completion-roadmap.md), [data pipeline](../DATA_PIPELINE.md),
[schema](../SCHEMA.md), [analytics](../ANALYTICS.md), [review gate](../DEVELOPMENT.md#backend-review-gate).

## Round 1 — user-supplied independent review

Received 22 September 2026. Reviewer identity/model was not included in the pasted
report; do not infer it. Report states read-only inspection and unchanged SHA-256
of its sorted path-to-file-hash manifest:
`997fd39d5fd4cc5d929cbe7f5be9500e99bc4c62c3781dbcf06c9e8e1e751c9a`.
Boundary: 10 tracked modifications and six untracked task files. Outcome: **NOT CLEAR**.

| ID | Severity | File/line at round 1 | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| DATA-001 | P2 | src/config/management/commands/import_dataset.py:162 | Reporting `_require_every_product` requires every namespace product in inventory | Supported coexistence with 14 demo products seals incomplete historical inventory. Reject incompatible namespace products before writes; do not use live stock as historical inventory. | Import/replay now checks for products outside accepted input before any creation. Regression seeds demo products, verifies refusal/no partial writes, then validates a clean namespace inventory through the reporting completeness function. Verification pending below. | Pending |
| DATA-002 | P2 | src/config/management/commands/import_dataset.py:118 | DATA_PIPELINE application-owned product field list excludes category | Input fingerprint cannot detect database category drift. Verify source-owned category on replay without overwriting it. | Added category comparison; focused regression changes category, expects conflict and proves changed value remains untouched. Existing live-field preservation regression retained. Verification pending below. | Pending |
| DATA-003 | P2 | analytics/profile_dataset.py:131 | Phase 1 flat-noise gate requires rejection or explicit decision | Positive variance plus any completed sales does not establish meaningful signal. Separate integrity from manual acceptance; document evidence and explicit scope decision. | Removed automated sales-signal/overall PASS. Profiler now reports integrity only and directs to a checksummed-release manual decision. User explicitly accepted descriptive use despite flat-noise risk on 22 September 2026; recorded in data/README.md. No invented statistical threshold or automated noise classifier. | Pending independent re-review |

Round-1 reviewer independently reproduced the profile in memory (SHA-256
`9bfb9c8168f112581ce87bba7ec1057eb7ec301dd1ae3967729475f89e2a9835`), four-table
validation counts with zero rejects, cutoff/offset/fingerprint and per-status totals.
They verified six source checksums, no raw diff, rejection for negative prices and
duplicate product IDs, whitespace checks, pinned Django 5.2.17 system check and no
model changes detected.

Limitations: reviewer did not start PostgreSQL or mutate data. The original 23-test
focused run, 404-test suite, full persisted import/replay, reconciliation and HTTP
checks were implementer-reported; reviewer did not reproduce them. Migration-history
consistency was unverified without PostgreSQL.

Non-blocking observations: customer-order distribution and recency diagnostics are
explicitly deferred with optional ML, as the user excluded ML from this batch.
Bulk-create batching does not bound total memory: source dictionaries, typed rows,
canonical manifest and ORM objects coexist. No peak-memory/cloud-instance suitability
claim is made; measure against the eventual selected instance before cloud import.

## Remediation verification

Fresh isolated Compose project `inf2006-dataset-review`, using repository build and
migration workflow; no shared database touched. Commands:

```powershell
docker compose -p inf2006-dataset-review build web
docker compose -p inf2006-dataset-review up --wait --wait-timeout 90 db
docker compose -p inf2006-dataset-review run --rm --no-deps migrate
docker compose -p inf2006-dataset-review run --rm --no-deps web pytest -q -p no:cacheprovider /app/tests/test_import.py
docker compose -p inf2006-dataset-review run --rm --no-deps web pytest -q -p no:cacheprovider /app/tests
python analytics/profile_dataset.py --source data/raw
```

Focused tests: **25 passed in 1.79s**. Full suite: **406 passed in 13.68s**.
Profile reports integrity PASS, no automated overall/signal acceptance. Generated
Markdown SHA-256: `367fd85353565c1f86366464d8b5c091b138e0d7386957c0140205da114d5d5b`.
DATA-003 user decision: on 22 September 2026 the user said, 'accept this dataset,
generate the review prompt'. The accepted use is descriptive sales/inventory
demonstration despite disclosed flat-noise risk, not validated trend/seasonality or
forecasting. This supersedes the earlier pending-decision state. No new full-source
import, independent re-review or gate clearance is claimed. This is the first Low
remediation attempt; the repeat-after-fix stop rule has not been triggered.

Additional checks passed using `docker compose -p inf2006-dataset-review run --rm
--no-deps web python manage.py` followed by `check`, `makemigrations --check --dry-run`
and `check_database`: zero issues, no model changes, database OK/migrations applied.
`git diff --check` passed; all six raw SHA-256 checksums still match. Cleanup succeeded
with `docker compose -p inf2006-dataset-review down --volumes --remove-orphans`, removing
only this newly created scratch project's containers/network/volume. No commits/pushes.

Preserve finding IDs across rounds. If any DATA-001–003 remains unresolved
after this fix attempt in independent re-review, stop for the user's manual Astra
Medium escalation under DEVELOPMENT; do not silently retry or declare the gate clear.


## Round 2 — independent Astra Medium review, 22 September 2026

**Gate CLEAR. No unresolved actionable findings and no new actionable findings.**
Reviewer: independent OpenAI Codex / gpt-6-astra, medium, in the review task;
not the implementer. No delegation, code edits, staging or publication during review.
The user subsequently authorized coordination, documentation updates and committing.

Reviewed all 17 task files (10 tracked modifications and seven untracked files) against
base `3deed85024e841bd9dccc99c1860ca379d5012bc` on `CL/Analytics`. No unrelated changes.
Before/after SHA-256 of the sorted path-to-file-SHA-256 JSON manifest:
`1585de4c5e79cfc353832d3d4464d002690dc0d5b631cf0935730db39b8e5ac6`.
Subsequent commit preparation changes only status/review documentation and manifest wording;
reviewed application code, tests, dependencies, Compose and generated profile remain unchanged.

| ID | Round-2 outcome | Evidence |
|---|---|---|
| DATA-001 | Resolved | import_dataset.py:87-89 rejects extra namespace products before creation on first import/replay. First-import regression passed; separate full-source replay probe refused an added product without altering records. Accepted inventory passes reporting._require_every_product(). No deletion or fabricated historical stock. |
| DATA-002 | Resolved | import_dataset.py:123 verifies category. Category drift conflicts without overwrite; existing checkout/live-field/password/cart/session preservation regression passed. |
| DATA-003 | Resolved | profile_dataset.py:131-134 reports integrity only. data/README.md:19 records explicit limited descriptive-use acceptance despite flat-noise risk; no meaningful-trend/seasonality/forecast claim. |

### Independently reproduced verification

Used pinned existing application image
`sha256:1bc434f4cb281c491934be824da7f509cdfdd7f27dd51af3e2a1bc57a4833f65`
after verifying hashes of dataset.py, import_dataset.py and seed_demo.py against the
working tree. Django 5.2.17; pinned PostgreSQL 17 image from Compose. Disposable
`inf2006-review-r2-db` had memory-backed storage, no exposed ports, and the existing
initializer created a non-superuser application role with CREATEDB for pytest.
App checks used read-only tests/data mounts, a read-only root and temporary /tmp;
no shared database or image tag was changed.

- Applied migrations in scratch, then `check`, `makemigrations --check --dry-run`
  and `check_database`: zero issues, no changes, database OK/migrations applied.
- `pytest -q -p no:cacheprovider /app/tests`: **406 passed in 12.87s**, including
  all 25 import tests and existing analytics/schema/security tests.
- Called `profile_dataset.profile(Path('data/raw'))` in memory, without overwriting
  the report: integrity PASS, byte-identical SHA-256
  `367fd85353565c1f86366464d8b5c091b138e0d7386957c0140205da114d5d5b`.
- All six raw CSV checksums matched; pure validation found zero rejected rows.
- `import_dataset --source /app/data/raw --namespace reviewer/history/v1` twice:
  20,000 users/profiles, 1,200 products, 100,000 orders, 237,537 items, one sealed
  inventory and 1,200 snapshots; replay created nothing and reported all unchanged.
  All imported passwords were unusable; reporting inventory completeness passed.
- SQL grouped each order's lines and compared their sum with Order.total:
  **zero mismatches**. Per-status line totals: cancelled 1,818,915.27;
  completed 55,821,834.61; refunded 4,843,639.32, matching documented results.
- Added an extra product only inside a scratch transaction, verified replay refused
  it and preserved records, then rolled back the probe.
- `git diff --check` and separate untracked-file whitespace checks: no errors.
  Final file hashes, raw checksums and Git state matched review start.
- Stopped only the reviewer-created database container; --rm removed its resources.
  No reviewer containers remained; shared application image tag was unchanged.

### Limitations and next work

Actual HTTP/browser checks, real-data analytics refresh, AWS and load testing were not
repeated. Earlier HTTP results remain implementer-reported. Importer process peak RSS
was 828,696 KiB after first import (22.87s), then 981,416 KiB after replay in the same
process (10.33s). These are local measurements, not cloud sizing evidence; retain the
deployment memory check. Customer-order/recency diagnostics remain deferred with ML.
Next: roadmap Phase 3's independent pandas verification of real-data analytics refresh.
Clearance covers this dataset batch, not overall project phases or deployment.
