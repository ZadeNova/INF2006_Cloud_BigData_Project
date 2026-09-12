# Implementation plan

Status checked: 12 September 2026. This file owns implementation status; [scope](../PROJECT_SCOPE_INF2006.md) owns requirements and dates.

## Current state

- Complete: scope, design reference and submission scaffolding exist. Scope/design were pushed in commit `c7ed9d1`.
- Complete: agent entry point and focused planning documents drafted. This is documentation, not application delivery.
- Complete: all four backend foundation batches passed independent review and local verification (48 tests). See the bounded batch table below for evidence and review records. Dataset download/validation, business workflows, analytics and AWS deployment remain unimplemented/unverified; the frontend foundation is implemented locally and its independent review remediation is ready for the required Astra Medium re-review.
- Complete locally: frontend foundation batches 1-3 serve the shared shell, representative presentation page, reusable states, responsive navigation, HTMX success/failure preview and branded 404/message states through Django HTTP. Final independent Astra Medium re-review is pending.
- No cloud resources are established by creating these documents.

## Phases

| Phase | Dates in 2026 | Status | Exit condition |
|---|---|---|---|
| 1. Foundation and feasibility | 11-17 Sep | In progress; local backend foundation reviewed in batches | Verify account, HTTPS and dataset; scaffold local app and first AWS smoke deployment |
| 2. Ecommerce and analytics | 18-24 Sep | Not started | AWS workflow/S3 import work; correctness/security/analytics tests pass |
| 3. Scaling and recovery | 25 Sep-1 Oct | Not started | Dated scaling, recovery and monitoring evidence; freeze features |
| 4. Reproduction and packaging | 2-8 Oct | Not started | Clean-machine rehearsal, report, manifest and declarations complete |
| 5. Submission and preservation | 9-11 Oct | Not started | Submit by 11 Oct 23:59 SGT; archive ZIP and tag exact commit |

## Phase checklists

These are parallel work tracks, not extra staffing assumptions: the user leads backend/frontend, both developers share infrastructure, and three members support testing/reporting/admin. At each phase start, break only that phase into bounded tasks tied to its exit condition or a required rubric outcome. Keep future phases at checklist level. Agents check an item only after linking actual verification; do not turn this file into a transcript.

### Phase 1: foundation and feasibility

**Application**
- [x] Scaffold Django modules, pinned dependencies, Docker/Compose PostgreSQL, environment settings, initial migrations and health endpoint; local database connectivity verified. [Final evidence](../evidence/foundation-batch-4.md), [review](reviews/foundation-batch-4.md).
- [ ] Render a base Django template with shared styling and HTMX through HTTP; record actual run/test commands. Implementation and browser evidence are recorded in [frontend foundation](../evidence/frontend-foundation.md); final independent review is pending.

**Infrastructure**
- [ ] Verify lab permissions, balance, region, shared Terraform state ownership and HTTPS arrangement; follow the [infrastructure setup order](AWS_INFRASTRUCTURE.md#setup-order-and-verification).
- [ ] Deploy a minimal application through ALB/EC2 and demonstrate RDS connectivity. A placeholder page is an intermediate smoke check, not completion of the Phase 1 database requirement.

**Data and evidence**
- [x] Resolve relevant planning-review prerequisites before dependent implementation: DOC-001/002 contract/persistence corrections accepted in [batch 3 review](reviews/foundation-batch-3.md); DOC-003 already corrected. Workflow regressions remain follow-ups.
- [ ] Download/pin the dataset, validate fields/relationships and record provenance/checksums; accept it or document the synthetic fallback.
- [ ] Define source mapping, dated inventory and safe reimport rules; capture evidence and review links as work completes.

### Phase 2: ecommerce and analytics

- [ ] Application: registration/login/logout, catalogue, persistent cart, atomic/idempotent checkout and owner-only history work end to end.
- [ ] Frontend: integrate routes, forms, validation/retry states and the protected analytics dashboard using DESIGN.
- [ ] Infrastructure: real app image, private S3 import, secure config, logs and cross-instance sessions work with no stickiness; HTTPS precedes credential-bearing traffic.
- [ ] Data: idempotent import preserves live state; analytics matches hand-checkable fixtures and shows reporting dates/freshness.
- [ ] Verification: independent backend review gates and relevant functional/security/data tests pass; supporting members record results and report notes.

### Phase 3: scaling and recovery

- [ ] Measure fixed-capacity baseline then request-count autoscaling; capture latency, throughput, errors, healthy capacity and delay.
- [ ] With two healthy instances, demonstrate failure/session continuity and safe retry of uncertain checkout.
- [ ] Exercise analytics scheduler-host loss in a controlled test and verify restart/re-run without duplicate or partial summaries; record interruption and recovery.
- [ ] Complete security/storage/analytics tests and an actual monitoring query/alert; diagnose failures honestly.
- [ ] Evaluate optional cache/ML only after core work is solid; preserve the existing conditional scope and freeze features by 1 October.

### Phase 4: reproduction and packaging

- [ ] Fix defects and have a teammate reproduce the app/analytics from README on a clean setup.
- [ ] Complete the report's required headings, manifest links, contribution/AI declarations and traceable evidence; check every claim against actual output.

### Phase 5: submission and preservation

- [ ] Validate ZIP structure, required artefacts, links and absence of secrets/personal data.
- [ ] Submit by the deadline; preserve the exact ZIP and tag the INF2006 baseline for later INF2003 work.

## Next work

1. Backend foundation is complete. Use [Docker quickstart](../src/README.md); services are stopped and the local PostgreSQL volume is retained. Remaining Phase 1 work follows below.
2. Frontend foundation implementation is checkpointed through the review-remediation batch after `ffbe975`; complete the same Astra Medium re-review before marking the Phase 1 application item complete. Evidence: [frontend foundation](../evidence/frontend-foundation.md); review: [frontend review](reviews/frontend-foundation.md).
3. Separate backend authentication task: registration/login/logout and session security; independent review required.
4. Separate catalogue/cart task: active product pagination, persistent owner-scoped mutations and validation; independent review required. Checkout/history follow afterwards.
5. Data track: accept/pin dataset, verify actual mapping/date policy, implement create-only import and regression tests per DOC-001/002 contracts; then analytics.
6. Infrastructure track (outside this task): actual lab permissions/balance/region, shared-state ownership and HTTPS/ALB health Host arrangement before a smoke deployment with RDS. No AWS resources were provisioned here.

Planning DOC-001/002 are resolved at the contract/persistence boundary; future importer/checkout/aggregation regressions remain required. DOC-003 remains corrected. See [planning review](reviews/planning-suite-review.md).
## Open items

| Item | Required decision/evidence |
|---|---|
| Integration account, region, permissions, balance | Actual capability record and cost estimate; credits do not pool |
| HTTPS | Supported hostname/certificate and validation arrangement |
| Dataset | Revision, provenance and validation; selected but not audited |
| ElastiCache | Conditional; requires explicit selection, lab support, budget and measured value |
| Optional ML | Deferred; omit if it delays required work |
| Submission group ID | Fill in for submission packaging; member-name assignment is not a development task |
| INF2003 reuse | Confirm lecturer policy and contribution attribution |

## Update protocol and decisions

Update this file with substantive changes: status, evidence/commit references, blockers and next steps. Never mark a phase complete from code existence alone. For backend tasks, link the review log and record review status/round, unresolved finding IDs and next action. A repeated unresolved finding after Low remediation sets the task to Awaiting user manual Astra Medium escalation; do not mark it complete. Reserve proposal time for INF2003 before 4 October 23:30 without implementing its expansion here.

- 12 Sep 2026: one tracker combines active work, blockers and completed-history references.
- 12 Sep 2026: backend Astra Low, frontend Luna Max; user controls backend Medium escalation.
- 12 Sep 2026: frontend foundation batch 1 added the live presentation shell and representative page; Django checks passed and HTTP verification returned 200 for `/` and `/health/`. Component states, responsive navigation and HTMX remain open for the next batches.
- 12 Sep 2026: frontend foundation batch 2 added shared state components, responsive navigation and `GET /foundation/design-notes/`; focused tests passed, fragment HTTP returned 200, and browser verification confirmed the HTMX swap/focus handoff with no console errors at desktop and mobile viewports.
- 12 Sep 2026: frontend foundation batch 3 added shared informational/error message presentation and `404.html`; focused tests passed 4/4, the full suite passed 52/52, and browser/HTTP evidence was recorded in [frontend-foundation.md](../evidence/frontend-foundation.md). Round 1 Astra Medium review then identified F-001 through F-005; remediation adds the validation sample, 503/retry preview, visible swap focus, 44px mobile controls and corrected evidence baseline. Focused tests passed 5/5 and the full suite passed 53/53; Round 2 review is pending.

- 12 Sep 2026: retain the complete technical scope with two primary developers and three testing/report/admin members. The user leads backend/frontend and both developers share infrastructure; remaining data/analytics and test-script ownership must be assigned. Contribution records must reflect actual work.

- Role-based ownership only: do not ask for or invent member names. Keep this tracker concise with task-specific file paths and check references; agents use targeted reads rather than routine repository-wide scans.

- Backend completion gate: independent Astra Medium reviews each backend task diff; Astra Low fixes logged findings. A repeated issue after its Low fix attempt stops the task for user-controlled Medium implementation escalation. Procedure: [development review gate](DEVELOPMENT.md#backend-review-gate). Foundation reviews are linked in the batch table below.

- Adopted from teammate reference: phase checklists split application/infrastructure/data work, task-to-exit-condition traceability and progressive infrastructure verification. Preserve Phase 1 RDS/HTTPS gates and current model/review rules.

## Active backend foundation batches

User-authorised local-only scope, base f719c67. Four sequential reviewed checkpoints; no AWS provisioning or push. No unfinished implementation drafts remain.

| Batch | Status | Verification / review |
|---|---|---|
| 1. Skeleton and dependencies (fca20e7) | Complete; review round 2 passed, B1-001 resolved | [Checks](../evidence/foundation-batch-1.md), [review](reviews/foundation-batch-1.md) |
| 2. Docker/PostgreSQL and environment (b137d63) | Complete; review round 1 passed, no findings | [Checks](../evidence/foundation-batch-2.md), [review](reviews/foundation-batch-2.md); base fca20e7 |
| 3. Schema and migrations (dd10f3a) | Complete; review round 1 passed; DOC-001/002 resolved at contract/persistence boundary | [Checks](../evidence/foundation-batch-3.md), [review](reviews/foundation-batch-3.md); base b137d63 |
| 4. Health and foundation verification | Complete; 48 tests; review round 1 passed, no findings | [Checks](../evidence/foundation-batch-4.md), [review](reviews/foundation-batch-4.md); base dd10f3a |

Follow-up tasks remain separate: authentication; catalogue/cart; frontend styling/HTMX in the user's Luna Max chat; data acceptance/import/analytics; AWS feasibility/deployment. None of those is completed by the backend foundation.
