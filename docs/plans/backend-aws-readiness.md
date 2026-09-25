# Backend remediation and AWS integration preparation

Date: 25 September 2026. Planning baseline: erfan/analytics at f72a872. Phase 0 reconciliation baseline: e58e3a1 (HEAD and fetched origin aligned).
Status: original remediation plan retained. Phase 0 contract/probe reconciliation is implemented locally, pending its independent review gate; later batches remain separate.
Companion: [finding dispositions and evidence](../reviews/backend-aws-readiness.md). Preserve original Opus IDs and READY-001 through READY-010.

## Goal and boundaries

Resolve confirmed backend/ML issues, coordinate related frontend fixes, and prepare a reproducible application release and ML interface for the existing infrastructure plus ECR, SNS, CloudTrail, WAF and Secrets Manager.

The user owns application/ML remediation; their groupmate owns Terraform. This plan does not authorise a Terraform rewrite, AWS creation, dataset replacement, commit or push. The original planning task wrote planning documents only; Phase 0 now reconciles contracts and the read-only probe without AWS calls.
ML is included by the user's current decision; Phase 0 reconciles the active optional/deferred language. Offline training/loading use an explicitly triggered batch workflow. Saved-model inference is optional and unimplemented; EventBridge Scheduler and Lambda are not selected. Keep segmentation descriptive and removable, and preserve deterministic sales/inventory calculations. No forecasting replacement, SPA, queue architecture, dedicated model server or automatic marketing actions.
Secrets Manager is selected for database credentials and the shared Django signing key. Terraform provisions or references the permitted secrets and access policies; runtime retrieves them through roles, never baked-in values. Systems Manager is not selected. Agree a secure administration/diagnostic method with the Terraform owner.

The recorded console-first learning pass followed by Terraform reproduction remains the documented deployment method unless the team changes it. Terraform file development can proceed in parallel. Avoid duplicate resources/state ownership; validate/plan is not evidence of apply or successful deployment.

## B0 - Reconcile status, scope and security advice

Owner: backend/documentation coordinator. Before dependent implementation.

- Mark F-05/S-005 corrections as present on the baseline; W-01/W-02 code corrected with focused local checks, independent gate still pending. Remove stale not-yet-committed status only after checking history.
- Replace READY-005 unsafe launch-configuration secret advice in tooling/output and guide. Secrets Manager is explicitly selected by the user. Denial is a deployment blocker to resolve with the lab/instructor, not permission to expose credentials or silently substitute another store.
- Update scope/analytics/architecture/infrastructure documents narrowly for included descriptive ML, the agreed service additions, ECR image route and omission of SSM. Retain budget, local reproducibility and cloud evidence conditions.
- Correct READY-009: no guaranteed self-signed fallback; no creation-permission claim based on list APIs or a plan alone. Capability checks/record must cover the added services and relevant execution roles without provisioning resources.
- Keep original Opus review immutable as historical evidence; append dispositions to the new review record rather than erasing findings.

Acceptance: scoped document consistency checks; existing probe tests including security advice/redaction run; independent backend review for changed probe code. Actual lab access remains for the infrastructure owner.

## B1 - Safe ML input and serving behaviour

Depends on B0 decisions. Owner: backend.
Paths: analytics/segment_customers.py extraction boundary; src/reporting/management/commands/load_customer_segments.py; reporting models/migrations/queries; relevant tests and SCHEMA/ANALYTICS contracts.
IDs: F-02/M-09, F-03, M-10, READY-001/003; S-007; F-06 vacuous assertion.

- Define one eligibility rule: completed-order owners in the source namespace before cutoff; exclude privileged/demo-only actors according to documented policy. Local registered customers can lack CustomerProfile; do not require a profile blindly. Specify insufficient-history treatment and safe customer reference.
- Strictly validate JSON object/schema, explicit run identity, model identity, field types/ranges/finite money, distinct eligible customers, cluster_id < k, consistent metadata and allowed label mapping.
- Validate before replacement. Preserve prior assignments on invalid input. Define same-identity replay/conflict behaviour and serialise concurrent loads at the relevant run/version boundary.
- Derive expected eligibility/completeness from the declared feature snapshot; never silently publish a truncated assignment file as complete. Do not force contiguously populated clusters for later inference where a valid cluster may have no assigned customers.
- Remove unnecessary usernames. Fix balanced bounded list behaviour and replace the vacuous operator assertion with the correct fixture/eligibility assertion.
- Remove coerce_range and its obsolete tests after confirming callers.
- Add migrations only for actual model changes and update owned contracts in the same batch.

Verification: focused PostgreSQL loader/query tests for rejection preserving old data, cross-namespace/privileged rejection, valid local shopper, replay/concurrent publication, metadata conflict and three-group visibility. Cover each independently breakable behaviour once. Independent backend gate before completion.

## B2 - Credible descriptive ML and retained evaluation

Depends on eligibility from B1 and accepted dataset identity; coordinate READY-010 with the dataset owner.
Paths: analytics/segment_customers.py, analytics/tests, requirements only if needed, evaluation evidence, ANALYTICS and batch-06d plan.
IDs: M-01/03/04/05/06/07, READY-008/010; M-02 explicitly optional.

- Keep a small k candidate range. Select and explain k from separation, stability, cluster sizes and operator interpretation; do not force k=3 just to create desired labels.
- Compare current preprocessing against one justified alternative. Record feature window and tenure limitation. Default to retaining lifetime semantics with explicit labels unless evidence supports changing the business definition.
- Give clusters descriptive profile-supported names; avoid unvalidated churn labels. Fix missing negative silhouettes.
- Validate min/max k and actual distinct labels; handle insufficient signal with a clear non-success outcome. Stable customer ordering and fixed seeds support repeatability.
- Keep seed stability; add a bounded resampling comparison if it materially informs selection. Temporal repurchase validation is a stretch experiment only if making predictive usefulness claims.
- Produce a small committed evaluation record: source hash/namespace, cutoff/window, eligibility/excluded counts, preprocessing, candidate metrics, chosen k, profiles, limitations, exact command and runtime. Link it in evidence/test-data-ai.md and manifest. Full customer rows need not be committed.
- Compare outputs excluding intentionally changing timestamps; do not claim byte identity from random_seed alone.
- If shoe data is adopted, rerun feature/evaluation checks on that revision before promoting its model.

Verification: meaningful tiny-fixture RFM SQL/date/status tests, naming and degenerate-input tests, retained negative-score case, deterministic assignment comparison and one real-data evaluation. Keep score thresholds evidence-based; do not promise a silhouette/accuracy target. Independent gate.

## B3 - Production runtime and ML handoff

Can begin runtime packaging work alongside B2 after B1 interface decisions.
Owner: backend; coordinate inputs/outputs with Terraform owner.
IDs: M-08/11, S-006, READY-002/003/004/005/006/007/009.

Application runtime:
- Exclude infrastructure/state/plans/sensitive variables from Docker context before groupmate files are added under src. Keep harmless examples and Terraform provider lockfile versionable. Verify with harmless sentinel files in a disposable build context.
- Supply trusted RDS CA via a documented image asset or read-only mount; production web and standalone DB tools enforce verify-full with correct hostname. Keep explicit local mode.
- Specify container image digest, app port 8000, required settings/secrets, shared signing key, namespace, DB role and CA path; no credentials in ECR image/user data/Terraform evidence.
- Document trusted ALB proxy boundary, allowed-host/CSRF origins and a health probe Host solution; preserve DB-independent liveness. Run migrations once with appropriate separate privileges; don't race them on ASG boot.
- Test production-mode configuration locally with safe test credentials/certificates; fail on missing/insecure config. Real ALB/RDS checks belong to integration, not local readiness.
- Reuse existing stdout JSON logging. Add only bounded operational fields/metrics required for readiness (release identity, analytics/ML run status/duration/freshness); do not emit customer IDs as metric dimensions or secrets in logs.

ML contract, explicitly triggered batch workflow:
- Keep offline training/export and validated assignment loading as the selected workflow, isolated from the web image. EventBridge Scheduler and Lambda are not selected.
- Preserve run/cutoff, namespace and model-version coherence. Pending/failed/stale lifecycle handling and immutable feature snapshots remain deferred; the current-run panel must never silently fall back to another run.
- Saved-model inference is optional future work. If adopted, retain a versioned preprocessing pipeline, model and fixed label mapping with feature schema and artifact identity; load only trusted artifacts.
- The operator explicitly triggers a batch for an accepted source revision. Repeated imports retain the atomic replacement contract; no recurring cadence or cloud adapter is required.

Later verification covers batch reproducibility, invalid imports preserving prior assignments, refresh without assignments and recovery loading. Optional saved-artifact inference needs its own equivalence and schema checks if selected. Runtime packaging and actual AWS permissions remain separate gates, not Phase 2 deliverables.

## B4 - Related frontend and operator fixes

Owner: frontend (Luna Max per repository assignment); backend owns any routes/query/context changes. Do not edit the same files concurrently.
IDs: S-001/002/003/004/008, F-04, W-04; presentation portions of M-10, READY-001 and S-006.

- Correct form help/error IDs and single error container.
- Reproduce cart focus loss and analytics initial-focus jump in browser; fix only reproduced behaviour with stable targets and post-swap handling.
- Update cart header count on line removal/empty state while retaining distinct-line semantics.
- Align standalone 503 fonts without introducing database dependencies; announce theme state accessibly.
- Preserve validated operator pagination after toggles.
- Integrate safe customer references, balanced segment display and clear ML period/freshness labels.

Verification: HTTP-rendered contracts and a focused keyboard/HTMX/light-dark browser walkthrough. Frontend-only work needs visual verification; backend-owned changes still require independent review. These polish issues need not block an isolated routing smoke deployment, but stay open until verified.

## B5 - CI, reproducibility and release evidence

Depends on completed relevant batches; add the ML CI job early so it protects B2/B3.
IDs: F-06/M-12, M-06/11 and residual documentation/evidence issues.

- Run pure ML tests in a pinned analytics environment and Django-dependent verification tests with required dependencies, PostgreSQL, paths and settings. Do not silently skip broken collection to obtain a green build.
- Retain current application build/check/migration/test pipeline; do not add ML runtime libraries to the production web image.
- Fix README commands/test counts and run them on a clean disposable environment. Record hosted CI separately from local passes.
- Full final application suite, analytics tests, check, migration drift, image build and exact local import -> refresh -> train/infer -> load -> dashboard walkthrough on the release candidate.
- Record functional/security/data evidence from actual results, fill threat-control mapping, validate manifest paths and update attribution/contributions using real work. Do not invent members' contributions.
- Prepare bounded Locust workload/fixtures for the Terraform owner's later fixed-capacity/scaling experiments; dry-run locally and label results local.
- Independent backend review per coherent batch; final integration delta reviewed after merging fixes. Preserve finding identities and stop on repeated unresolved issues after the authorised Low fix attempt.

## Terraform owner handoff (no Terraform edits in these batches)

| Service / boundary | Backend supplies | Terraform/integration owner supplies and verifies |
|---|---|---|
| ECR / EC2 / ASG | Tested digest, port/start command, health contract, configuration schema | Registry pull permissions, launch config, no stickiness, capacity/draining, same release across instances |
| RDS / secrets | CA/config contract, runtime vs migration needs, one-off commands | Private endpoint/SG, forced TLS, Secrets Manager delivery and shared signing key |
| S3 | Dataset/model/input/output prefixes and artifact schemas; local fallback | Private policies, encryption/version/retention, role access and denied unauthorised operations |
| WAF (W-03) | Login route/method, expected legitimate traffic, test scenario | Count then enforce selected rule, observed impact and residual distributed/shared-IP limitations |
| CloudWatch / SNS | Sanitised stdout fields, run identifiers, freshness/error definitions | Log retention, metric/alarms and confirmed notification; no sensitive exports |
| CloudTrail | Named audit actions for evidence | Permitted management-event history/trail and redacted evidence; object-access auditing is separate |

The backend must not claim WAF protection, notifications, S3 denial or RDS isolation before these joint tests run. No AWS resources are created by this plan.

## Exit criteria and immediate next step

Backend ready for AWS integration means B0-B3 correctness/runtime contracts and B5 relevant checks are complete, with no unresolved actionable gate findings. Track B4 separately if only visual polish remains; complete it before final demonstration.
AWS ready is a later status: full HTTPS workflow, S3 dataset/import path, WAF test, logs/alert, audit trail, explicitly triggered batch assignment and evaluation evidence, scaling/session continuity and failure recovery verified with dated evidence. Saved-model inference evidence is required only if that optional path is selected.
Final report, architecture image and submission packaging remain tracked obligations, not hidden backend implementation blockers.

Current progress and the next bounded task are owned by [IMPLEMENTATION_PLAN](../IMPLEMENTATION_PLAN.md). Do not implement the entire list as one large unreviewable change.


## Upstream coordination update: e58e3a1

The 25 September pull includes test trimming, removal of coerce_range, the RDS CA bundle, configurable HSTS and the RDS bootstrap tool. Treat B1's dead-code removal as already implemented and B3's CA packaging as implemented pending verification/review. Reuse these changes; do not recreate them. Add the bootstrap tool to B3's credential/TLS/least-privilege review, preserving Secrets Manager as the selected delivery mechanism. Remaining original findings and the independent review gates stay open. See the review's upstream follow-up for exact limitations.
