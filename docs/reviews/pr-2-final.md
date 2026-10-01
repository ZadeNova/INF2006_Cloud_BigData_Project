# PR #2 final integration review

Date: 22 September 2026. Coordinator: Codex. Independent reviewer: `/root/final_review`, explicitly assigned `gpt-6-astra` / `medium`, read-only and independent of the implementation. Procedure: [backend review gate](../DEVELOPMENT.md#backend-review-gate).

## Scope and snapshot

- User request: final implementation/specification review of [PR #2](https://github.com/ZadeNova/INF2006_Cloud_BigData_Project/pull/2), with merge into main authorized only after the review and checks pass.
- Base: `4795f9f6ab469ebb131ee5a1cf8cfa9e84eaa8e2` (`main`). Round 1 head: `c8d26569896c3df8d8bd50c001b56b8aa9fa59f3` (`erfan/backend`); 36 commits, 110 changed paths. Working tree initially clean.
- Review covers implemented authentication, catalogue/operator permissions, persistent cart, checkout/order history, analytics refresh/read queries, security handling and associated migrations/tests, plus dataset/documentation additions. Prior feature reviews cleared at `7eea9b7` are reference evidence, not a substitute for this integration review.
- References: [review brief and feature logs](../archive/plans/astra-review.md), scope sections 4/5/8/9, architecture, API, schema, security, analytics, data pipeline and testing contracts, and associated batch plans. Deferred importer, dashboard, AWS and visual design are not claimed complete.
- This task owns the review log and concise tracker update; any remediation paths and snapshots are recorded below. No unrelated changes existed.

## Round 1 — changes requested

Independent review completed with one actionable finding, FINAL-001, and no additional implementation/specification blockers. Coverage included authentication/session routes, operator permissions/seeding, cart validation/ownership/concurrency, checkout fingerprints/replays/transactions/stock locking, order ownership/history, database failures and sanitized logs, analytics SQL/ranges/publication/retention/snapshots, relevant migrations/constraints/tests and functional template/HTMX boundaries. No concrete unnecessary complexity or dead-code blocker was found.

Dataset status mapping and discarded monetary-field treatment are consistent across the scope and import plan. Publisher attribution, source URL, license notice/link and dictionary are present; raw-file inclusion has a documented reproducibility rationale. Independently counted rows match the publisher: customers 20,000; products 1,200; orders 100,000; order items 237,537; payments 105,388; refunds 7,910. All six hashes match after CRLF-to-LF conversion in memory, isolating Git checkout normalization as the defect.

Nonblocking follow-up: the import plan's Singapore-time assumption applies only to genuinely naive inputs. Actual order timestamps have explicit UTC `Z` offsets, which the future importer must preserve. Existing snapshot approximation and insufficient-history presentation decisions remain accepted; no new findings were created for deferred work.

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| FINAL-001 | P2 | `data/raw/checksums.txt:1`; missing root `.gitattributes` | Raw source bytes must remain unchanged and checksums reproducible. Reviewer found all six CSVs checked out as CRLF (`i/lf w/crlf`) under Windows `core.autocrlf=true`; their working-file hashes differ from the recorded hashes. | Preserve raw CSV bytes across Git checkouts with scoped attributes, restore the working copies to committed bytes, and verify all six checksums. | `/root/raw_bytes_fix`, explicitly assigned Astra Low, added `data/raw/*.csv -text` to root `.gitattributes` and restored six working files directly from the existing committed blobs. All six hashes and row counts match; attributes report `text: unset`; checkout filters with `core.autocrlf=true` preserve all hashes. Checksums, source metadata and committed CSV content unchanged. | Resolved in independent round 2; no new actionable findings. |

## Round 2 — review gate clear

The same independent Astra Medium reviewer examined `c8d2656` plus the new root `.gitattributes` in the context of the original PR diff. It independently verified every working CSV checksum and every checkout-filter hash with `core.autocrlf=true`; Git reports `i/lf w/lf attr/-text` for all six. The attribute excludes application source and raw Markdown. There are no CSV, application, test or checksum content changes. FINAL-001 is resolved with no new actionable findings. Task-owned publication changes are `.gitattributes`, this log and the tracker entry; the two documentation files record the review rather than change implementation.

## Verification

- Hosted [CI job](https://github.com/ZadeNova/INF2006_Cloud_BigData_Project/actions/runs/35696235323/job/106643601213) at round-1 head completed successfully on 22 September 2026, 06:45:51 UTC. Coordinator read the actual job log: fresh migrations passed, Django system check reported no issues, `makemigrations --check --dry-run` reported no changes, and **381 tests passed in 15.92 seconds**.
- Local rerun attempted: initialized previously absent ignored `src/.env` without exposing secrets and started Docker Desktop. The engine returned HTTP 500 for `info` and `/_ping`; `docker compose -p inf2006-pr2-review build web` failed before building or starting a test database. This is an environment limitation, not a local test pass.
- `git diff --check origin/main...HEAD` reports three pre-existing Markdown trailing-space lines, including two in the preserved publisher dictionary. These are not runtime defects; raw publisher files are not edited for whitespace style.
- No new browser visual walkthrough, AWS deployment, S3 access, cross-instance recovery, load test or full dataset acceptance/import was performed.

## Merge decision

Independent final review passed after the single Low fix and Medium re-review. The implemented backend matches the reviewed contracts within the stated scope and limitations. The coordinator will publish the fix/log/tracker and require successful final-head GitHub checks and unchanged reviewed implementation before exercising the user's merge authorization. The exact published/merged commits and subsequent CI result are available in PR #2 history; this log does not pre-claim a future merge or test result.
