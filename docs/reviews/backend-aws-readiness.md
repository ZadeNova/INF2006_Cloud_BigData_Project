# Backend AWS readiness review

Date: 25 September 2026.
Snapshot: origin/erfan/analytics at f72a872590c5ebafe37e0385c07637b4a785fc8c.
Reference: [Opus review](../latest-opus5.5-review.md), which covered 91eba60 plus the then-uncommitted AWS probe.
Reviewer: Codex, primary planning session; model/reasoning not asserted. This is a findings reconciliation and static readiness review, not the independent implementation approval gate.
Owned changes: this document, the [remediation plan](../plans/backend-aws-readiness.md), and one tracker entry. No application, Terraform, dependencies, dataset or deployment changes.

## Evidence and limits

Inspected the review's affected functions/templates, their direct consumers and focused tests, CI, ML/analytics/security/schema/API contracts, current tracker, cloud-independent preparation and dataset handoff.
Read the fetched snapshot through an isolated worktree. After review, switched the clean primary checkout to erfan/analytics at the user's request and placed the three planning-document changes there; application files remain unchanged.
Executed with the bundled Python runtime, without AWS calls or database writes:
- Three focused checks of the actual probe module: sample assumed-role identity/email/account redaction; TimeoutExpired becomes error code 124; Markdown pipes/newlines remain within a table row. All passed.
- Extracted and executed the actual _segment_name_mapping function with pandas: a two-cluster profile with 387-day recency still receives core. Reproduced.
- Scoped caller search: coerce_range appears only in its definition and obsolete test.
No full pytest, Django/PostgreSQL suite, browser walkthrough, real-data model evaluation, Docker deployment or AWS test ran. Bundled Python lacks pytest, sklearn and psycopg. Opus's numerical scores and historical suite counts are attributed to that review, not reproduced here.
Frontend focus findings remain code-traced pending browser reproduction. This is not an exhaustive new audit of every backend path; scope is all Opus findings plus AWS integration seams.

## Opus finding dispositions

Original IDs and aliases are preserved. Open means a required remediation remains; experiment means evaluate before changing the model. Corrected does not imply independent review approval.

| IDs | Disposition | Evidence / corrective direction | Batch |
|---|---|---|---|
| M-01 / F-01 | Open; naming reproduced | analytics/segment_customers.py::_segment_name_mapping always calls the second of two clusters core. Use descriptive profile-supported labels; do not force k=3 only to produce at_risk. Existing choose-k-by-silhouette contract must change explicitly if a business-selected k is adopted. | B2 |
| M-02 | Optional enhancement, not a descriptive-ML blocker | Batch 06d says descriptive, not predictive. Temporal repurchase/spend evaluation becomes necessary support for predictive claims, not a mandatory change to the feature. Retain modest claims. | B2 |
| M-03 | Bounded experiment | Log monetary/raw recency/frequency confirmed; reported skew/correlation not remeasured. Compare a small number of preprocessing candidates; skew alone does not prove incorrectness. AOV changes the meaning of monetary and requires an explicit decision. | B2 |
| M-04 | Open presentation/definition gap | fetch_rfm sums all completed history before cutoff. Label lifetime-to-cutoff separately from selected dashboard range. Define eligibility/tenure treatment; a 366-day window is not inherently required or sufficient to remove tenure bias. | B1/B2 |
| M-05 | Evaluation enhancement | Seed-only ARI is implemented and satisfies seeds OR resamples in ANALYTICS. Resampling is a useful added robustness check, not proof the existing contract was violated. | B2 |
| M-06 | Open evidence gap | Loader stores serving assignments, not full evaluation; segments.json is ignored. Commit a concise evaluation artifact and link it from manifest/evidence. Do not duplicate all metadata per customer row. | B2/B5 |
| F-05 | Correction present | README, SCHEMA CustomerSegment row, test-count docs, manifest qualification and src README updated after review. Verify executable commands separately under F-06. Phase 0 reconciles the stale tracker claim against history; corrections are committed in the baseline. | B0/B5 |
| S-005 | Correction present | Statistics preview now links the protected analytics route. Preserve the invented-data disclosure. | B0 |
| W-01 | Correction present; focused check passed | Probe now redacts account/session/user/email and redacts before truncation. Full existing tests and required independent gate still need confirmation. | B0 |
| S-001 | Open | accounts/_form_fields.html emits -help/-error IDs, inconsistent with Django field references; repeated errors duplicate IDs. Align IDs and use one error container. | B4 |
| F-02 / M-09 | Open | Loader catches IntegrityError only; coercion and database range errors remain. Validate finite decimal/integer/string bounds and return sanitised CommandError without losing prior rows. | B1 |
| F-03 | Open | Loader accepts arbitrary auth.User references. Validate the same eligible population as feature extraction; simple CustomerProfile-only filtering would incorrectly exclude legitimate locally registered shoppers. | B1 |
| M-10 | Open | Feature query lacks staff exclusions; segment template displays login usernames. Define staff/operator eligibility explicitly and display safe references only. | B1/B4 |
| S-006 | Open lifecycle gap, partially documented | CustomerSegment run FK cascades; latest analytics run can lack segments. SCHEMA now explains this, but orchestration/freshness UX and failure handling remain. Never silently combine old assignments with a new run. | B3 |
| F-06 / M-12 | Open | CI runs /app/tests only. analytics test_verify_refresh imports Django; standalone instructions do not establish that environment. Dashboard assertion excludes demo-operator while fixture uses operator. Add the appropriate separate test jobs and meaningful assertions. | B1/B2/B5 |
| W-02 | Correction present; focused checks passed | Timeout handling and Markdown escaping present. Keep distinction between local fake-CLI checks and actual lab capabilities. | B0 |
| W-03 | Infrastructure-owned integration gate | Login throttling absent. User selected WAF; define scoped login rule and test through ALB, including shared-IP impact. No duplicate application throttle required by this plan. Existing CSRF/ownership tests already cover named threats; the rubric does not specifically mandate brute-force protection. | Handoff |
| F-04 | Code-traced, browser reproduction pending | analytics.js calls announcePanel for initial body htmx:load. Draw charts initially, move focus only for actual panel replacement. | B4 |
| S-002 | Code-traced, browser reproduction pending | Cart stepper/remove controls lack stable focus targets across outerHTML. Reproduce then implement minimal restoration including removed-row/empty-cart cases. | B4 |
| S-003 | Open | Header badge sits outside cart fragment and no relevant update exists. Preserve distinct-line counting semantics; quantity-only changes need not alter count. Verify remove/empty and subsequent navigation. | B4 |
| S-004 | Open low-priority consistency | Standalone 503 loads Inter/Manrope instead of current families. Align font reference without extending DB-dependent base template; self-hosting is optional. | B4 |
| S-007 | Correction present at e58e3a1 | coerce_range and its obsolete tests were removed upstream; no duplicate remediation. | B1 |
| S-008 | Open accessibility | Theme toggle lacks state announcement; initialise and update accessible state for stored/system preference and toggling. | B4 |
| M-07 | Open | fit_segments turns every negative silhouette into None. Keep valid negative scores; None only for undefined metric. | B2 |
| M-08 | Open | Default model version persists across differing parameters; loader can override it. Bind version to actual pipeline/artifact and source configuration. | B1/B3 |
| M-11 | Open reproducibility/security hygiene | README uses root with writable repository bind mount. Use a writable output directory under appropriate ownership; recommend environment/role-based credential delivery, not secret CLI URLs. | B3/B5 |
| W-04 | Open low-priority UX | Product toggle always redirects to page 1. Preserve a validated page number using a server-built URL, not arbitrary next URLs. | B4 |

## Additional findings and readiness gaps

P1 blocks the affected AWS integration or correctness path. P2 should be fixed in its bounded batch. Gaps are not claims that an undeployed system has been exploited.

| ID | Severity | Location / evidence | Required correction and acceptance | Batch |
|---|---|---|---|---|
| READY-001 | P2 | src/reporting/queries.py:284-303; up to 25 per segment ordered high_value/core/at_risk then overall 50 | First two populated groups exclude the third entirely. Use bounded balanced representation or an explicit segment filter. Test three populated groups; do not merely raise the cap for one k. | B1/B4 |
| READY-002 | P1 AWS | analytics/segment_customers.py:18-30 vs config/settings.py production TLS | Standalone connection only supplies sslmode/CA when present; DSN bypasses that logic. Require certificate/hostname verification for production DB tools, preserve explicit local mode, and apply the rule to supported DSN input too. Verify refusal of insecure/missing production config and document CA injection. | B3 |
| READY-003 | P1 | load_customer_segments.py:24,64; models/queries assume coherent metadata | Missing run_id accepted, version overridable, payload type unchecked, int coercion truncates fractional values/accepts bool, row k/scores need not agree, cluster_id need not be below k. Validate one coherent, eligible snapshot before atomic writes. Same identity+same payload is safe replay; conflicting payloads need explicit policy. Test prior rows survive rejection and concurrent retries are safe. | B1/B3 |
| READY-004 | P1 before image publication | src/Dockerfile COPY . .; src/.dockerignore; .gitignore | Planned Terraform beneath src can enter images, including ignored state. Exclude the agreed infrastructure directory AND sensitive state/plan files from build context. Ignore sensitive plans/vars in Git while retaining safe examples and provider lockfile. Inspect built image using harmless sentinels. | B3 |
| READY-005 | P1 AWS | src/tools/aws_capability_check.py:182 | Generated advice falls back to secrets in launch configuration. Replace with the user-selected Secrets Manager with least-privilege instance/Lambda role retrieval, never plaintext user data/launch-template secrets. If no compliant path exists, record blocked. | B0/B3 |
| READY-006 | P1 AWS ML | segment_customers.py::fit_segments/build_output | Current code refits scaler/KMeans, selects k, writes assignments; no saved model or inference handler exists. Proposed offline-train/scheduled-infer design requires a versioned pipeline plus fixed label mapping and validated feature/output contract. Keep offline CLI and web image isolation. | B3 |
| READY-007 | P1 AWS | settings.py, config/views.py::health, Dockerfile; prep B6 | RDS CA delivery, production startup config and ALB probe Host handling are unresolved. Define minimal environment/secret/mount contract, health Host solution with strict normal-host checks, trusted proxy boundary, one migration step and non-superuser runtime role. Do not disable host checks or TLS to pass smoke tests. | B3 |
| READY-008 | P2 evaluation | segment_customers.py::fetch_rfm/fit_segments | No deterministic SQL ordering; insufficient/distinct feature vectors can collapse clusters, while metric eligibility checks requested k rather than actual labels. Sort by stable customer identity, validate candidate bounds/actual labels, handle insufficient signal explicitly. Compare deterministic assignments excluding generated_at. | B2 |
| READY-009 | P1 plan alignment | cloud-independent-prep B4/B7 and implementation tracker | Current docs prescribe SSM (user omitted it), call self-signed fallback guaranteed, leave image route undecided, and do not reflect included ML/new services. Reconcile accepted decisions; imported test certificate still needs lab permission, matching hostname and explicit client trust. Region/account/budget remain actual capability gates. | B0/B3 |
| READY-010 | P2 dataset handoff | shoe-dataset-handoff; monetary derived from repriced orders | Shoe remap can change monetary features/model profiles. Train/evaluate on the actual accepted revision; retain source namespace/checksum and avoid using source customer_segment labels as inputs or unexamined ground truth. Coordinate dataset ownership without editing teammate files. | B2/B3 |

## Judgments to preserve

- M-02 is not mandatory predictive validation for a descriptive feature. No classification accuracy or proven churn/marketing claim.
- M-03/M-05 are measured alternatives, not automatic transformations or reason to add large test matrices.
- F-03's literal profile-only fix would break the documented optional-profile rule for local registrations. Define eligible owners of completed orders in the run namespace, excluding privileged/demo-only actors per an explicit policy; minimum history threshold must be recorded rather than invented.
- S-006 does not justify displaying stale results without their own cutoff/version.
- W-03 is assigned to WAF integration; do not claim deployment evidence from a local 403/CSRF test.
- Existing accepted CSP limitation CR-012 is not reopened. Historical cleared findings are not reopened without regression evidence.
- Corrected W-01/W-02 and F-05/S-005 need reconciliation, not duplicate fixes.
- Readiness means code/contracts/evidence prepared for deployment, not AWS verified or rubric points guaranteed.

Implementation sequence and teammate boundary: [backend AWS readiness plan](../plans/backend-aws-readiness.md).


## Upstream follow-up: e58e3a1 (25 September 2026)

Pulled 0f7e9d4, 7c5a10c and e58e3a1 into erfan/analytics and preserved the local planning documents. The tables above describe the original f72a872 review snapshot; these updates supersede affected status:

- S-007: coerce_range and its obsolete tests are now removed. No duplicate remediation needed.
- READY-007: the image now includes the documented RDS CA bundle and default POSTGRES_SSLROOTCERT path; configurable HSTS and db_bootstrap.py were added. This is partial implementation, not proof of real RDS/ALB readiness. Proxy/health Host handling and secure credential delivery still need integration verification.
- Test trim: upstream records 392 passing tests and mutation checks in docs/reviews/test-trim.md; deploy-readiness records focused settings/bootstrap checks. These are author-reported results, not rerun here. Independent backend gates remain open according to the incoming tracker.
- Review the new bootstrap tool before deployment, including production TLS override policy, inherited role privileges, existing database ownership and error redaction. The current script allows BOOTSTRAP_SSLMODE overrides and checks direct role attributes; do not equate that check with complete effective-privilege validation.
- No Terraform files were included in these three commits.

This follow-up is a targeted diff inspection, not a full independent review of the new implementation.

## Phase 0 reconciliation (25 September 2026)

HEAD and fetched `origin/erfan/analytics` both resolve to `e58e3a1c670bfad87c3cb9821cd3d95f25617057`; no incoming commits. F-05/S-005 and W-01/W-02 corrections are in the baseline, and S-007 was removed by `0f7e9d4`. The original review above remains a historical snapshot. Phase 0 updates the selected-service contracts and read-only probe advice for READY-005/009; it does not approve Phase 1 loader changes or resolve later runtime integration findings.

Phase 0 local verification: the existing `.venv` Python ran `PYTHONPATH=src python -m pytest -q -p no:cacheprovider -o addopts='' --confcutdir=tests tests/test_aws_capability_check.py`: **20 passed**, using fake CLI responses only. This covers selected-service calls, safe generated advice, AMI dependency, redaction, timeouts and Markdown escaping. Upstream suite/bootstrap claims remain author-reported, not rerun. No AWS calls, provisioning, database tests or bootstrap fixes occurred. Independent Phase 0 review remains pending; see [gate record](phase-0-baseline-alignment.md).

## Phase 3 ML quality/evaluation reconciliation (25 September 2026)

Current task baseline `529a0f9`; the original tables above remain historical findings. Phase 1 loader and Phase 2 serving dispositions are recorded in [ml-loader-safety](ml-loader-safety.md) and [ml-segment-serving](ml-segment-serving.md). This bounded Phase 3 follows [ml-quality-evaluation](ml-quality-evaluation.md); accepted-data evaluation and focused checks passed; independent Astra Medium round 2 cleared the gate after MLQ-001 remediation.

| IDs | Current bounded disposition | Residual ownership |
|---|---|---|
| M-01 / F-01, M-03, M-05, M-06, M-07, READY-008 | Resolved in Phase 3: correctness, profile naming, bounded comparison and retained accepted-data evidence; independent gate clear | Phase 3 |
| M-02 | Temporal prediction evaluation remains outside the descriptive claim; no churn or predictive accuracy claim introduced | Reconsider only if a predictive task is explicitly adopted |
| M-04 | Lifetime completed history and short-history/tenure limitations explicitly retained; feature period differs from dashboard date filters | B4/frontend: clarify lifetime-to-cutoff card copy; no frontend change in Phase 3 |
| F-06 / M-12 | Phase 1 extraction and Phase 2 meaningful privacy assertion preserved; dedicated analytics CI/environment coverage passed local equivalents and independent Phase 3 review | Hosted CI cannot be claimed from local checks |
| READY-010 | Current accepted raw v1.0.0 source verified against recorded hashes, namespace and cutoff; shoe remap remains plan-only | Dataset owner/B3: rerun evaluation after accepted derived revision is adopted |

Next bounded batch-workflow work is B3's run/cutoff/namespace/version handoff and recovery contract, with any lifecycle/snapshot publication decisions separately scoped. Saved-model inference remains optional; EventBridge Scheduler/Lambda are excluded. Runtime TLS/Secrets Manager/bootstrap, image publication and AWS integration are separate gates; this entry does not clear them.

## Phase 4 batch handoff/recovery reconciliation (25 September 2026)

Phase 4 baseline `d934859`; implementation/review status and actual checks are in [ml-batch-handoff](ml-batch-handoff.md). The original tables above describe historical findings; this entry records the bounded current disposition.

| IDs | Phase 4 scope | Remaining boundary |
|---|---|---|
| M-08 | Resolved locally: configuration-derived version and separate completed batch identity, explicit run/source provenance; independent Phase 4 gate clear | No saved-model artifact, authentication or immutable source proof |
| M-11 | Resolved for current batch runbook: isolated ordinary-user environments, dedicated output and environment/role credentials; independent Phase 4 gate clear | Production credential retrieval and TLS remain separate runtime-security work |
| READY-003 | Phase 1 validation/replacement preserved; completed batch/destination checks and retry verified; independent Phase 4 gate clear | Source orders/roles can change; metadata does not prove historical RFM values |
| READY-006 | Explicit retraining/export/import is the selected design; no saved-model inference or Scheduler/Lambda required | Local batch verification does not establish AWS execution readiness |
| S-006 | Bounded explicit batch recovery only; lifecycle gap remains open | Later task: pending/failed/stale presentation and lifetime-period copy; never silently use another run's assignments |

Immutable feature snapshots remain unimplemented and require a separately bounded decision. READY-002 and broader TLS/Secrets Manager/bootstrap/image/AWS gates are unchanged. Shoe-data adoption still requires separate reevaluation under READY-010.
