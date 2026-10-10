# ML batch handoff and recovery — Phase 4

Date: 25 September 2026. Status: implementation, local verification and independent round 2 review complete locally.

## Baseline and ownership

Branch `erfan/analytics`; initial HEAD and post-integration baseline `d9348597589c51bb19b16cedddae3babc7cece9d`. Initial working tree/index clean, no merge/rebase in progress. Fresh `git fetch origin` succeeded; upstream remains `89019b4bc10a22d7ce8d40769582652bd35030e7`. `git rev-list --left-right --count HEAD...origin/erfan/analytics` returned `4 0`. No incoming commits, backup/rebase, replay mappings or semantic conflict resolutions required.

Coordinator owns Git operations, review records, finding dispositions, tracker and attribution. Implementer `/root/phase4_implementer` explicitly assigned `gpt-6-astra` / `low`; separate `gpt-6-astra` / `medium` reviewer will receive a bounded fresh context and remain read-only. Subagents cannot stage, commit or push. Follow [development gate](../DEVELOPMENT.md#backend-review-gate), including stop on a repeated unresolved finding after its Low fix attempt.

Phase 3 evidence and prior Phase 1/2/3 reviews were inspected, not rerun as Phase 4 verification. Accepted evidence records 19,766 eligible customers and log-frequency preprocessing with best valid k over 2–4 (accepted cohort k=2). Phase 4 preserves this design and strict current-cohort atomic import semantics.

## Scope and contract

Explicit completed run selection, source/run association, configuration identity distinct from batch identity, validated atomic local export, exact-file import and retry/recovery. Relevant original findings: M-08, M-11, READY-003/006 and the bounded batch portion of S-006. Specifications: [analytics](../ANALYTICS.md), [schema](../SCHEMA.md), [data pipeline](../DATA_PIPELINE.md), [runbook](../../analytics/README.md), [testing](../TESTING.md), architecture and security contracts.

No scheduling, saved-model inference/registry, immutable feature snapshots, dashboard lifecycle/redesign, preprocessing experiment, shoe-data replacement, AWS provisioning/deployment or production TLS/Secrets Manager/bootstrap changes. Current eligible cohort validation does not establish immutable original RFM values. Preserve source/run ownership, no silent older-result fallback, no exactly-once claim.

## Verification

Implementation checks, isolated end-to-end commands/resources and independent review results will be recorded below when executed. No prior test result constitutes a new pass. Nothing pushed or deployed.

Coordinator baseline integrity check: current bytes match all three working-file SHA-256 entries in evidence/ml-quality-evaluation.json (segment_customers.py, evaluate_segments.py, analytics/requirements.txt) and all six referenced raw CSV hashes. This verifies preserved evidence/source bytes only; it does not rerun training or validate the database.

### Implementer verification in progress

Astra Low inspected Docker resources before creating project `inf2006-phase4-20260925`, PostgreSQL on loopback port 57705 with tmpfs storage. Configuration is under `$env:TEMP/inf2006-phase4-20260925`; credentials stay in task-only environment files and are not reproduced here. Shared databases, pre-existing stopped resources and accepted data are untouched. Database retained temporarily for the independent reviewer.

After sourcing the private task environment and setting `PYTHONPATH` to `$PWD/src;$PWD/tests`, host command:

```powershell
. "$env:TEMP/inf2006-phase4-20260925/env.ps1"
$env:PYTHONPATH = "$PWD/src;$PWD/tests"
.\.venv\Scripts\python.exe -m pytest -q -c src/pytest.ini -p no:cacheprovider analytics/tests/test_segment_customers.py analytics/tests/test_segment_loader_integration.py analytics/tests/test_verify_refresh.py tests/test_customer_segments_command.py
.\.venv\Scripts\python.exe src/manage.py check
.\.venv\Scripts\python.exe src/manage.py makemigrations --check --dry-run
```

Initial test collection lacked the `tests` helper path; corrected before the focused run. First complete run: **68 passed, 1 failed in 21.63s**, exposing producer float `0.0` versus loader lossless Decimal digest normalization. Low corrected shared numeric canonicalization; the existing real producer/loader integration covers the regression. Post-fix focused run: **69 passed in 21.60s**; system check: 0 issues; migration drift: no changes. Reported by the implementer; independent gate still pending. End-to-end and pinned Python checks are recorded separately once executed.

### Delivered identity and recovery contract

The runbook and analytics contract define two identities: `model_version=rfm-v3-<SHA256>` covers the training configuration and code/runtime/dependency provenance; `batch_id` covers canonical meaningful completed output, excluding only itself and generation time. Digests are consistency checks, not authentication or proof of original source RFM. Selected k and output metrics/assignments belong to batch identity, separately from the recipe. The producer derives namespace/cutoff/inventory/summary from the explicitly completed run, and import checks them against the explicitly selected destination.

The operator independently provisions `ML_SOURCE_ID` per intended deployment/database. Both endpoints check that association and PostgreSQL's actual database name; duplicated configuration plus cloned run identities cannot reliably distinguish a clone. No namespace-only source claim is made. Full provenance remains in the retained export; the database schema is unchanged.

The producer validates before writing a temporary sibling, flushing/fsyncing and atomically replacing the exact output. Same-run/version import remains a locked atomic replacement. Retry the same completed valid file after failure or uncertain acknowledgement; no retraining is needed while it remains valid. Current eligibility drift requires regeneration. Same-ID feature drift can be undetected; no immutable features, exactly-once execution or historical RFM proof is promised. Legacy pre-envelope exports require regeneration. No older-run fallback, lifecycle implementation or production security readiness claim.

### End-to-end and pinned checks

Implementer completed a real command-line workflow against a representative 18-customer/63-order fixture, producing 53 daily summary rows and completed run `a3bf439d-addd-431a-a5fe-13336cdf52f3`. SELECT-only trainer and scoped non-superuser loader both exited 0; 18 persisted assignments matched all normalized export fields. Invalid version assertion failed without changing the existing file; mismatched source import failed; correcting the independently provisioned configuration allowed the exact unchanged file to load without retraining. Raw file hash remained `907a996559a37d697afcc7eae1f435c8505eac0269fb9dc4ae8ee3ec8a2fa10a`. Small-fixture metrics establish execution only, not a new quality evaluation.

Exact commands, fixture recipe, roles, identities and setup failures: [Phase 4 evidence](../../evidence/test-data-ai.md#ml-explicit-batch-handoff---25-september-2026). Pinned Python 3.13, ordinary UID1000 and read-only checkout: **16 pure ML passed in 10.35s**, without Django; **53 PostgreSQL/verifier/strict-loader passed in 14.56s**. Containers exited 0. Host and pinned tests collected all intended modules. Coordinator `git diff --check` passed after Low removed a loader EOF blank line. No full suite, hosted Actions, production image build, browser, AWS or accepted full-dataset reevaluation run in Phase 4.

## Frozen round 1 snapshot

Review boundary: `d9348597589c51bb19b16cedddae3babc7cece9d` to the working tree, including the new `src/reporting/segment_contract.py` and this log. No staged changes or unrelated initial edits. All task implementation, tests, evidence and contract documentation frozen; only this coordinator review log may receive review metadata during review. No upstream semantic resolutions to inspect.

Working-file SHA-256 (Git may normalize CRLF at staging):

| Path | SHA-256 |
|---|---|
| AI_USE_DECLARATION.md | 974421034378e1e2189237aaf0384ba5fb90755f22a2830b064de6da420496f2 |
| analytics/README.md | 19ddcff4798a22062e6021d5c5a4d21e3bde3726753a2ef7c82386c27ede9f9e |
| analytics/evaluate_segments.py | 16bd35eb9a43aa5fcd90cbf21abf584847212b846184c936d4433036df477110 |
| analytics/segment_customers.py | 020b9806a4e1d4af231590fa604633438bd5a3a26c393089183f1912ab0b5fff |
| analytics/tests/test_segment_customers.py | 0460d19fd629aff9edc7fc891493ed5700a7aae212806f214c57b65057c40282 |
| analytics/tests/test_segment_loader_integration.py | 4aa93c5e37c93a50b479e2e3ca37b8fcac3bb7952471e4431c86adb88669713c |
| docs/ANALYTICS.md | d08635ff426d134afe18c9663093cd4611991d42df22633a4efba7f30204cc69 |
| docs/ARCHITECTURE.md | 074caf77adc5006bee3e296ff4baaf4a9e71e6998a8bfd8b0c81e629f3282bdb |
| docs/IMPLEMENTATION_PLAN.md | 9b9d56e0f040042aa442aae76dac44c20fe687916fcb6f35e9c0b32aacd0e100 |
| docs/SCHEMA.md | 49cc0cf050ebc388f6736cabede8b2469abdc3e031fa923cb2fc35f26e1882e2 |
| docs/reviews/backend-aws-readiness.md | 7ed2883dc36aa5271f4ee24e6b4061035e3517e56dc286ccd722f285e7ad8f73 |
| evidence/test-data-ai.md | 5aa5371b19b3537169272d1521e73fedbec032490676ebc1598d46cb2fb1636d |
| src/reporting/management/commands/load_customer_segments.py | 561c485c0f746cdd776e4d9fbd5caaeb4a3247a96f5fdb6fd452636a641761b6 |
| src/reporting/segment_contract.py | 6d9459640819adc1254c435fab97e007fff576db523ec39e31cb1c6d00fdc591 |
| tests/test_customer_segments_command.py | bf504f870685595ec99bc5b7aaebbbff3b2632cbbbccc0291e71a71a4aa0e2f0 |

Snapshot documentation correction during round 1: coordinator UTF-8/link check found one CP1252 em-dash byte in the newly appended evidence heading. Low replaced that byte with ASCII `-`, preserving prior evidence bytes; no implementation/test changes. Reviewer notified. Revised `evidence/test-data-ai.md` SHA-256: `a89d0284821c04a78204d66c83dbfa1abef38f09e25af5fd4cb7f64fc5d7d0e9` (supersedes that row above). All other frozen hashes unchanged. Local Markdown file-link scan: 144 checked, none missing. Added-text private-key/AWS access-key/credential-bearing database-URL pattern scan: zero matches; scope inspection also required before staging.

### Round 1 — Independent (fresh session), in progress

Reviewer `/root/phase4_reviewer`, explicitly `gpt-6-astra` / `medium`, read-only, separate from the implementer. Full baseline-to-working-tree task review including untracked files; focused checks use the dedicated test database. Initial read-only sandbox prevented environment/temp use; narrow escalation was requested for checks. Execution results are recorded only after completion.

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| MLH-001 | P2 | evidence/test-data-ai.md:242 | Readable UTF-8 operational evidence; coordinator decode failed at byte 17007 | Newly appended heading used CP1252 byte 0x97; replace with UTF-8 or ASCII without changing prior evidence | Low replaced only the new dash with ASCII; updated hash recorded above, full UTF-8 decode succeeds | Reviewer verification pending |

Independent round 1 verification: **69 focused tests passed in 23.90s**. All 15 frozen/revised working-file hashes matched. Reviewer confirmed full UTF-8 decoding and the corrected evidence hash: **MLH-001 resolved**.

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| MLH-002 | P3 | analytics/segment_customers.py:27–29 | AGENTS simplicity/dead-code rule; scoped callers in main, evaluator and tests use connect() | Removing the CLI URL option left unused connect(database_url=None) and its credential-URL branch. Remove the unused parameter/branch and keep the environment path | Pending Low remediation after round 1 freeze is released | Pending |

No other actionable findings identified in the reviewer's preliminary result; final round 1 report and revised complete-diff review remain required. Removing the producer branch changes its recorded code provenance, so subsequent exports intentionally receive a new recipe identity. Historical executed E2E identities remain attributed to their original snapshot.

Round 1 final: MLH-002 is the sole unresolved actionable finding; gate not clear. Reviewer otherwise found the bounded producer/loader, atomic publication/recovery, source limitations and dependency-isolation contracts satisfied. No independent full-cohort/full-suite/pinned-container/image/hosted/browser/AWS rerun. Low assigned the exact MLH-002 correction and affected checks plus refreshed representative CLI provenance; no implementation escalation authorised.

## Low remediation and frozen round 2

MLH-002: removed only the unused `connect(database_url=None)` argument/URL branch; `connect()` retains environment-based configuration. No change to fitting, validation, payload schema or tests. Low reran the 69-test focused suite: **69 passed in 24.53s**. New scoped-role CLI train/export/import and retry of the prior unchanged completed file all exited 0. Exact 18 stored fields/rows matched each export under its own derived version. The new recipe identity reflects the changed producer source hash, as intended; old completed exports remain retryable. Exact commands and identities appended to [evidence](../../evidence/test-data-ai.md#ml-explicit-batch-handoff---25-september-2026); earlier executed identities remain historical, not overwritten.

Only producer and append-only evidence changed from round 1; other 13 frozen paths unchanged. UTF-8 and whitespace checks passed. Pinned 16+53 checks were not repeated for the unused-branch removal; the final host suite and real CLI integration were rerun. No broader unrun check is newly claimed.

| Path | Revised working SHA-256 |
|---|---|
| analytics/segment_customers.py | b7ff4df579ac64e9172ce235d4a33647e3f3f70376623a440b34ca6df81dc91d |
| evidence/test-data-ai.md | ec6d750926d772546e2c5474190b07b9d780960753755aecc2ba1851d12ff8be |

Same independent reviewer assigned the revised complete diff with existing IDs; MLH-002 must be resolved or the task stops for user-selected implementation escalation.

## Round 2 — gate clear

Same Independent (fresh session) reviewer `/root/phase4_reviewer`, explicit `gpt-6-astra` / `medium`, reviewed the complete revised baseline-to-working-tree diff. **MLH-001 and MLH-002 resolved; no unresolved actionable findings; backend review gate clear.** All 15 frozen/revised hashes matched. Trainer/evaluator call sites remain compatible with environment-only `connect()`. Independent whitespace/UTF-8 checks passed. Round 1 independent 69-test pass remains applicable; reviewer inspected Low's final 69-test and refreshed CLI/retry evidence without a redundant suite rerun. Unrun checks remain as disclosed.

Coordinator updated only completion metadata after review: this record, the tracker and bounded current dispositions in backend-aws-readiness. No implementation/test/evidence change after the cleared snapshot. S-006 lifecycle, immutable snapshots, lifetime frontend copy, runtime TLS/Secrets Manager/bootstrap and broader AWS gates remain open. Next bounded task: own-run pending/failed/stale lifecycle and lifetime-period display, with explicit scope/model ownership before implementation. Shoe-data reevaluation waits for accepted adoption.

## Resource cleanup and commit preparation

After gate clearance, Low verified the resolved task directory was exactly `C:/Users/limch/AppData/Local/Temp/inf2006-phase4-20260925`, inside the resolved TEMP root with the expected leaf. With credentials sourced privately, `docker compose -p inf2006-phase4-20260925 -f <verified-task-directory>/compose.yaml down` exited 0. Native PowerShell `Remove-Item -LiteralPath <verified-task-directory> -Recurse -Force` then removed only task-created configuration, credentials, fixture scripts and both assignment exports; absence verified. Task database/container/network and tmpfs data are gone. Pre-existing stopped `inf2006-ml-loader-db-1`, its network, named/anonymous volumes and shared datasets were preserved. No task export or credential file is staged.

Local commit authorised only after the cleared gate and checks above. Coordinator stages the 16 explicit task paths, reviews staged scope/content and verifies the resulting commit subject/body and clean tree. Nothing pushed or deployed.

Final staged inspection: exactly 16 reviewed task paths; no generated customer exports, secrets, dependency/model/migration/frontend/AWS or raw-data changes. Staged text matches the working snapshot after Git newline normalization; implementation/test/evidence hashes match the cleared round 2 snapshot. Only completion metadata and heading spacing in coordinator-owned records changed afterward. All 16 paths decode as UTF-8; staged whitespace check passed, no unstaged changes, and added-text credential/private-key pattern scan found zero matches. This is a scoped inspection, not a claim of exhaustive secret detection. Commit includes a descriptive body with verification and unrun limits; final hash/tree verification is reported to the user after creation.

## Committed-snapshot verification on renewed request

25 September 2026: the requested Phase 4 work was already committed as `3c75f4d9ef03c88a49bfc3fb5196197a4ce73bbf` when this coordination pass started. Implementation baseline remains `d9348597589c51bb19b16cedddae3babc7cece9d`; this pass starts from `3c75f4d`. Tree/index were clean and no merge/rebase was in progress. Fresh `git fetch origin` succeeded; origin remains `89019b4bc10a22d7ce8d40769582652bd35030e7`, with five local and zero incoming commits. No backup, rebase or semantic resolution was required.

Separate explicitly assigned subagents: `/root/phase4_implementer`, `gpt-6-astra` / `low`, inspected the existing implementation and ran focused verification; `/root/phase4_reviewer`, `gpt-6-astra` / `medium`, Independent (fresh session), reviewed the frozen exact diff `d934859..3c75f4d` read-only. Neither changed files or performed Git mutations. Reviewer outcome: **no actionable findings**; MLH-001/002 remain resolved. This additional review is code/contract inspection, not a new test-suite pass.

Newly executed Low verification, host venv with `PYTHONDONTWRITEBYTECODE=1` and `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` all set to `1`:

```powershell
.venv\Scripts\python.exe -B -m pytest -q -c src/pytest.ini -p no:cacheprovider -p no:django analytics/tests/test_segment_customers.py
```

Result: **16 passed in 4.68s**, with one expected unknown `DJANGO_SETTINGS_MODULE` configuration warning because the Django plugin was disabled. Initial attempts failed before collection due to sandbox temporary-file restrictions, then missing Django settings; approved temporary-file access and the disabled Django plugin enabled the successful pure test run. No database or application resources were recreated.

Coordinator checks: all six current raw CSV SHA-256 values match the Phase 3 aggregate evidence; raw data and that evidence JSON have no changes in `d934859..3c75f4d`. An initial PowerShell result-formatting attempt failed under constrained language mode; rerunning with plain string output confirmed all six matches. `git diff d934859 HEAD --check` passed. The existing implementation commit has a descriptive body and remains intact.

The recorded 69-test suites, pinned 16+53 checks and scoped-role 18-customer CLI/E2E recovery remain historical execution evidence; none was rerun in this pass. No implementation change requires repeating them. Full suite, hosted CI, image build, browser, AWS and full-dataset reevaluation remain unrun here. Current-cohort validation, undetected same-ID feature drift and cloned configuration limitations remain unchanged. Lifecycle/lifetime copy, immutable snapshots, runtime security and broader S-006/ML-AWS readiness remain deferred. This pass adds only this review record and tracker verification metadata. Nothing pushed or deployed.
