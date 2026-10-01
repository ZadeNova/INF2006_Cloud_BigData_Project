# ML quality and reproducible evaluation — Phase 3

Date: 25 September 2026. Status: implementation, accepted-data evaluation and independent review complete; local commit preparation. Hosted CI remains unrun.

## Baseline and ownership

Branch `erfan/analytics`, initial clean tree/index, baseline `529a0f9ee428af15524988dab2a2ccf74175b1b4`. Coordinator ran `git fetch origin` successfully: `origin/erfan/analytics` remains `89019b4bc10a22d7ce8d40769582652bd35030e7`; `git rev-list --left-right --count HEAD...origin/erfan/analytics` returned `3 0`. No incoming commits, rebase or semantic integration resolutions. Existing backup `CL/phase2-pre-rebase-20260925` remains at `eb914ef60160aa47479a48152702e3547d255369`. No new branch was necessary.

[Phase 1](ml-loader-safety.md) and [Phase 2](ml-segment-serving.md) were read as historical evidence, not newly executed checks. Their loader/extraction and safe balanced serving contracts remain required.

Implementer `/root/phase3_implementer`: explicit `gpt-6-astra`, reasoning `low`. Independent reviewer is explicit `gpt-6-astra`, reasoning `medium`, Independent (fresh session), read-only. Coordinator owns Git, this log, tracker, readiness dispositions and AI-use declaration. Subagents cannot stage, commit or push.

Agreed implementer scope: `analytics/segment_customers.py`, new `analytics/evaluate_segments.py`, focused `analytics/tests/test_segment_customers.py` and producer/loader integration test as needed, `.github/workflows/ci.yml`, ML sections of `analytics/README.md` and `docs/ANALYTICS.md`, analytics CI/descriptive demo portions of `docs/TESTING.md`, short-history clarification in scope section 6, aggregate `evidence/ml-quality-evaluation.json`, its entry in `evidence/test-data-ai.md`, and `project_manifest.yaml` evaluation links. No loader, frontend, model, migration, production dependency or teammate data edits.

Requirements: [analytics contract](../ANALYTICS.md), [data pipeline](../DATA_PIPELINE.md), [schema](../SCHEMA.md), [testing](../TESTING.md), [development gate](../DEVELOPMENT.md#backend-review-gate), [architecture](../ARCHITECTURE.md), [INF2003 isolation](../INF2003_BASELINE.md), scope sections 5–6; original M-01–07, M-12, READY-008/010 in [readiness dispositions](backend-aws-readiness.md) and [original Opus review](../latest-opus5.5-review.md).

## Dataset decision

Current accepted input is Analytics Engineering Ecommerce Sales & Returns v1.0.0, downloaded 22 September 2026, per `data/README.md` and `project_manifest.yaml`. Namespace `synthetic/revision-a/demo/v1`, seed 42, no shift, cutoff `2026-01-02T00:00:00+08:00`; expected inventory `import-v1-9884d29e2bf9a64778c63858230ebd71223569b293c28c8acb895b1920e10d0f`. Coordinator independently checked all four imported CSV SHA-256 hashes against the accepted record; implementer checked all six preserved source tables.

The [shoe remap](../archive/plans/shoe-dataset-remap.md) is explicitly plan-only; adoption requires a validated teammate build. `data/derived/shoes` is absent. Evaluation on the accepted release is not substitution for future shoe-data evaluation; READY-010 remains an adoption-time rerun requirement. Raw inputs are untouched, and source customer_segment labels are neither features nor ground truth.

## Verification and resources

Implementer inspected Docker state first. Task-only project `inf2006-phase3-20260925` uses container `inf2006-phase3-20260925-db-1`, matching default network, PostgreSQL loopback port 57704, and tmpfs storage with no named volume. Pre-existing stopped `inf2006-ml-loader-db-1` and existing volumes/networks remain outside task ownership. Temporary setup is under `$env:TEMP/inf2006-phase3-20260925`; source env.ps1 privately, never print it. Task credentials are excluded from records.

Actual import reported 20,000 customers, 1,200 products, 100,000 orders, 237,537 items, zero rejects and the expected inventory fingerprint. Run `bb3e4ce4-9485-47a3-94df-6d6e1cdac98c` completed 65,589 daily rows. Lifetime completed spend 55,821,834.61; eligible cohort 19,766, including 1,099 one-order customers. Full commands/runtime and final evaluation belong in the retained artifact and evidence record; these initial observations are not phase acceptance.

### Implementation checks and evidence

Astra Low reports an initial host Python 3.12.10 focused suite of 60 passed in 15.75s. Final source: pure ML in a genuinely Django-free, digest-pinned Python 3.13 container, 13 passed in 3.86s; separate pinned Python 3.13 container with Django/analytics dependencies against task PostgreSQL, 47 passed in 25.55s. Exact commands are retained in [test-data-ai](../../evidence/test-data-ai.md#ml-quality-evaluation-25-september-2026). Host Django system check: no issues; migration drift: no changes; whitespace check passed. All intended analytics modules collected, no silent skips.

Host full-cohort v2 producer plus unchanged strict loader succeeded with 19,766 assignments, k=2, silhouette 0.4347, seed ARI mean 0.9840/std 0.0111. Final host evaluation is in [aggregate JSON](../../evidence/ml-quality-evaluation.json), including working code hashes and runtime; this is distinct from Python 3.13 test execution. Two preprocessing candidates, k=2..4, were evaluated; all six fits valid. Log-frequency improved sampled silhouette from 0.3885 to 0.4347 with substantial groups and strong seed stability; selected by valid silhouette within the chosen preprocessing, ties preferring lower k. No resampling or predictive claim.

No failed tests/experiments reported. Initial sandbox Docker access denial was resolved by approved escalation. Hosted CI, production image build, full suite, browser and AWS unrun. Phase 2 serving source unchanged and existing arbitrary-label fallback coverage remains applicable; no redundant dashboard run or static collection. A current real-data loader execution establishes new-label persistence, not visual QA.

## Independent review

Completed through round 2 below; no unresolved actionable findings.

## Deferred scope

Explicit batch workflow only. No EventBridge Scheduler, Lambda, inference service, saved-model registry, snapshot orchestration, freshness lifecycle redesign, Terraform/AWS deployment, runtime TLS/secrets/bootstrap, frontend fixes or predictive tasks. M-04 presentation remains a later frontend dependency where lifetime values need clearer period copy. M-02 temporal predictive validation is unnecessary for the retained descriptive claim. Hosted CI remains unrun until publication; this task does not push or deploy.

### Frozen round 1 snapshot

Baseline-to-working-tree diff, including the new evaluator, aggregate JSON and this coordinator log. Reviewer must inspect untracked files too. All implementation/evidence files frozen; only coordinator review metadata may change while review runs. Working-byte hashes (CRLF working tree; Git normalizes text to LF):

| Path | SHA-256 |
|---|---|
| .github/workflows/ci.yml | a1d8a719af4639144287113c1b00596a36884bef1eedeb4d9ffcbd2eda75ee1e |
| AI_USE_DECLARATION.md | 8a98f49bb445b75f9d584dc46f41727f204bef6fec0df4d0317cd886c5f2f3cc |
| PROJECT_SCOPE_INF2006.md | efa8d943c8f9cf01229e306a445021fc28a5e590185ab28872057e86da46646a |
| analytics/README.md | 9edf4c731c712ea536d58a90b8329ceb6cc98ff5a6068214ce140118573f6cc9 |
| analytics/segment_customers.py | 099479e4c1eaa485ebbf869109dfc43ccb687e1448027730a42e3cd2dd0335df |
| analytics/evaluate_segments.py | 7bf11f414127447f9a458177acb8d664b60fd707f1692204902a326340b2d8c7 |
| analytics/tests/test_segment_customers.py | 1dcf3ea9ec71294dd5ffee95677030fbf5d80b2ede39b43a09f6a104d6af68c4 |
| docs/ANALYTICS.md | 89fbd4c81ca7c5463782897bcfbe0ba41820bb31664638854d89d22af1d1b40c |
| docs/IMPLEMENTATION_PLAN.md | 167e0762b81901c7e8f3bac5fcb4c623ee9a68be6d821dc06f069c3121cad4e7 |
| docs/TESTING.md | 9c1edaac68141de16c7180fbe657e843f0cccdc65ac244db78cb1c6d5a4ae31c |
| docs/reviews/backend-aws-readiness.md | 7a967535f012cced6e5071d7775ad62946eafbc087c6dcee5a2089879509a0d6 |
| evidence/ml-quality-evaluation.json | 91f4a7d6b94eed8646bf29e003dbd5cd8b00c9b9f87dda658d08a41f67ad58c6 |
| evidence/test-data-ai.md | 2fefae8bdaac5a6e8fa6b7d85956bc9dda87630bb3a7efcda4146b08b59e6047 |
| project_manifest.yaml | 472bce9ec70a5164ac981bf178c3a986a3bd8b20443b38c7bec6470108a4aa6b |

### Round 1 — Independent (fresh session)

Reviewer `/root/phase3_reviewer`, explicitly `gpt-6-astra` / `medium`, read-only. Reviewed the full frozen baseline-to-working-tree task diff including new files, original finding scope, contracts, evidence and CI. Independently ran the focused ML/PostgreSQL suite: **60 passed in 22.91s**. Initial sandbox attempt could not create temporary files; approved escalation enabled the successful run. Code hashes and artifact tracked-diff hash matched; candidate/profile cohort counts reconciled; whitespace check passed. No independent full-cohort evaluation, hosted CI, full suite, image build, browser or AWS rerun.

| ID | Severity | File/line | Required spec / evidence | Issue and expected correction | Low fix / verification | Re-review outcome |
|---|---|---|---|---|---|---|
| MLQ-001 | P2 | analytics/segment_customers.py:124–125; loader:70,130 | Preserve strict loader compatibility; reviewer mocked fitting/scoring and retained k=32768 | Producer permits k=32768 but loader caps k_clusters at 32767. Align bound/message to 32767 and change existing upper-bound regression from 32769 to 32768; no additional matrix | Corrected upper bound and existing regression; 56 tests passed; aggregate regenerated | Resolved in round 2 |

No other actionable findings. Gate remains open for MLQ-001. Same reviewer tier will inspect the revised complete diff. If this same requirement remains unresolved after the Low fix attempt, stop for user-selected implementation escalation per DEVELOPMENT; do not retry or auto-upgrade.
### Low remediation and frozen round 2 snapshot

MLQ-001: producer limit/error now 32767, existing upper-bound test now rejects 32768, matching the loader. No additional test cases. Astra Low reran the producer/loader focused suite: **56 passed in 18.98s**; exact command recorded in evidence/test-data-ai.md. Aggregate evaluation regenerated against the same accepted task dataset; metrics and selected configuration unchanged. Code/artifact identities verified and whitespace check passed. No unrelated implementation edits.

Updated working-byte hashes; other round 1 implementation files unchanged:

| Path | SHA-256 |
|---|---|
| analytics/segment_customers.py | 7ca159f71f905f255ba72e58ce1e8e759ee0a5092a7a03930c21e01eac7d6693 |
| analytics/tests/test_segment_customers.py | 1edbb6b45693321eea5ae0d6b0b376b3dda57df8ce3d27d43c163250d0d479e9 |
| evidence/ml-quality-evaluation.json | d65f7baf2ef099c983cae4e5591fd898903209e924a11fa4fe69e482e605a2d7 |
| evidence/test-data-ai.md | 78c91adc0c12fa9593246af80214b21b6f738244aefe721feeb7e6f5bf1ad9d3 |
### Round 2 — gate clear

Same Independent (fresh session) reviewer `/root/phase3_reviewer`, `gpt-6-astra` / `medium`, reviewed the revised complete diff against `529a0f9` with round 1 context. **MLQ-001 resolved; no unresolved actionable findings; backend gate clear.** All 14 frozen file hashes matched, regenerated artifact code/diff identity matched, and direct boundary probe rejected 32768. Independent boundary tests: **4 passed, 9 deselected in 6.82s**; whitespace check passed. Round 1 independent 60-test and Low post-fix 56-test results remain applicable. No independent full-cohort evaluation, hosted CI, full suite, image build, browser or AWS rerun.

Coordinator verified 15 scoped paths with no raw-data/application source changes. Added-text checks found no private-key, AWS access-key or credential-bearing PostgreSQL URL patterns. Local Markdown file-link inspection found no new missing links; one pre-existing scope link outside the changed section remains unrelated. Final staging/cleanup recorded below.
## Final staging and cleanup

Astra Low sourced the task-only environment privately and ran `docker compose -p inf2006-phase3-20260925 -f "$env:TEMP/inf2006-phase3-20260925/compose.yaml" down`. Only task container/network were removed; tmpfs storage disappeared with the container. Pre-existing stopped `inf2006-ml-loader-db-1`, its network and original volumes remain. Temporary configuration and ignored assignment export remain outside Git. No raw/source/application files changed during cleanup.

After the clear round-2 gate, coordinator updated only completion/review metadata in tracker, readiness dispositions and this log. Implementation/evaluation remains the frozen reviewed snapshot. Coordinator staged exactly the 15 scoped paths. All staged blobs match reviewed working content after CRLF-to-LF normalization; all artifact working-code hashes match. Staged whitespace and sensitive-pattern checks passed; aggregate JSON is 16,881 working bytes, with no assignment export or large dataset staged. The artifact tracked-diff hash records evaluation before the new evaluator was staged; its explicit working-file hash covers that then-untracked file. Only final coordinator completion metadata changed after review. Nothing pushed or deployed.
