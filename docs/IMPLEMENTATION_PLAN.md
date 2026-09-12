# Implementation plan

Status checked: 12 September 2026. This file owns implementation status; [scope](../PROJECT_SCOPE_INF2006.md) owns requirements and dates.

## Current state

- Complete: scope, design reference and submission scaffolding exist. Scope/design were pushed in commit `c7ed9d1`.
- Complete: agent entry point and focused planning documents drafted. This is documentation, not application delivery.
- Not implemented/verified: Django app, dependency environment, migrations, dataset download/validation, analytics, AWS deployment and automated tests. Existing README/evidence placeholders do not prove completion.
- No cloud resources are established by creating these documents.

## Phases

| Phase | Dates in 2026 | Status | Exit condition |
|---|---|---|---|
| 1. Foundation and feasibility | 11-17 Sep | Pending implementation | Verify account, HTTPS and dataset; scaffold local app and first AWS smoke deployment |
| 2. Ecommerce and analytics | 18-24 Sep | Not started | AWS workflow/S3 import work; correctness/security/analytics tests pass |
| 3. Scaling and recovery | 25 Sep-1 Oct | Not started | Dated scaling, recovery and monitoring evidence; freeze features |
| 4. Reproduction and packaging | 2-8 Oct | Not started | Clean-machine rehearsal, report, manifest and declarations complete |
| 5. Submission and preservation | 9-11 Oct | Not started | Submit by 11 Oct 23:59 SGT; archive ZIP and tag exact commit |

## Phase checklists

These are parallel work tracks, not extra staffing assumptions: the user leads backend/frontend, both developers share infrastructure, and three members support testing/reporting/admin. At each phase start, break only that phase into bounded tasks tied to its exit condition or a required rubric outcome. Keep future phases at checklist level. Agents check an item only after linking actual verification; do not turn this file into a transcript.

### Phase 1: foundation and feasibility

**Application**
- [ ] Scaffold Django modules, pinned dependencies, Docker/Compose PostgreSQL, environment settings and health endpoint; verify local database connectivity.
- [ ] Render a base Django template with shared styling and HTMX through HTTP; record actual run/test commands.

**Infrastructure**
- [ ] Verify lab permissions, balance, region, shared Terraform state ownership and HTTPS arrangement; follow the [infrastructure setup order](AWS_INFRASTRUCTURE.md#setup-order-and-verification).
- [ ] Deploy a minimal application through ALB/EC2 and demonstrate RDS connectivity. A placeholder page is an intermediate smoke check, not completion of the Phase 1 database requirement.

**Data and evidence**
- [ ] Resolve relevant planning-review prerequisites before dependent implementation.
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

Outstanding documentation prerequisites: [independent planning review](reviews/planning-suite-review.md), findings DOC-001 through DOC-003. Resolve historical stock persistence, safe reimport rules and the autoscaling-policy inconsistency before dependent implementation. DOC-001 and DOC-002 remain open. DOC-003 has been corrected in the infrastructure contract; see the review record for the documentation check.

1. Use role-based ownership; verify actual AWS permissions, region, credits and HTTPS arrangement. Do not block development on member names.
2. Pin supported dependencies/runtime and scaffold Django with Docker PostgreSQL. Add verified commands to README.
3. Download/accept the synthetic dataset and reconcile actual fields with schema/date policy.
4. Implement migrations, authentication and a small workflow; deploy early before broad feature work.
5. Complete checkout and analytics with tests, then proceed through phase gates.

Local setup can proceed during AWS checks. Do not proceed with dependent deployment until its prerequisites are resolved.

## Open items

| Item | Required decision/evidence |
|---|---|
| Integration account, region, permissions, balance | Actual capability record and cost estimate; credits do not pool |
| HTTPS | Supported hostname/certificate and validation arrangement |
| Dataset | Revision, provenance and validation; selected but not audited |
| Dependencies | Pin versions and choose workflow during scaffolding |
| ElastiCache | Conditional; requires explicit selection, lab support, budget and measured value |
| Optional ML | Deferred; omit if it delays required work |
| Submission group ID | Fill in for submission packaging; member-name assignment is not a development task |
| INF2003 reuse | Confirm lecturer policy and contribution attribution |

## Update protocol and decisions

Update this file with substantive changes: status, evidence/commit references, blockers and next steps. Never mark a phase complete from code existence alone. For backend tasks, link the review log and record review status/round, unresolved finding IDs and next action. A repeated unresolved finding after Low remediation sets the task to Awaiting user manual Astra Medium escalation; do not mark it complete. Reserve proposal time for INF2003 before 4 October 23:30 without implementing its expansion here.

- 12 Sep 2026: one tracker combines active work, blockers and completed-history references.
- 12 Sep 2026: backend Astra Low, frontend Luna Max; user controls backend Medium escalation.

- 12 Sep 2026: retain the complete technical scope with two primary developers and three testing/report/admin members. The user leads backend/frontend and both developers share infrastructure; remaining data/analytics and test-script ownership must be assigned. Contribution records must reflect actual work.

- Role-based ownership only: do not ask for or invent member names. Keep this tracker concise with task-specific file paths and check references; agents use targeted reads rather than routine repository-wide scans.

- Backend completion gate: independent Astra Medium reviews each backend task diff; Astra Low fixes logged findings. A repeated issue after its Low fix attempt stops the task for user-controlled Medium implementation escalation. Procedure: [development review gate](DEVELOPMENT.md#backend-review-gate). No implementation reviews have run yet.

- Adopted from teammate reference: phase checklists split application/infrastructure/data work, task-to-exit-condition traceability and progressive infrastructure verification. Preserve Phase 1 RDS/HTTPS gates and current model/review rules.

## Active backend foundation batches

User-authorised local-only scope, base f719c67. No AWS provisioning or push. Preserve later drafts outside each staged review snapshot.

| Batch | Status | Verification / review |
|---|---|---|
| 1. Skeleton and dependencies | Complete; review round 2 passed, B1-001 resolved | [Checks](../evidence/foundation-batch-1.md), [review](reviews/foundation-batch-1.md) |
| 2. Docker/PostgreSQL and environment | Draft only; not verified | Starts after batch 1 passes |
| 3. Schema and migrations | Contract/model drafts only; DOC-001/002 correction pending review | Starts after batch 2 passes |
| 4. Health and foundation verification | Draft only; not verified | Starts after batch 3 passes |

Follow-up tasks remain separate: authentication; catalogue/cart; frontend styling/HTMX in the user's Luna Max chat; data acceptance/import/analytics; AWS feasibility/deployment. None of those is completed by the backend foundation.
