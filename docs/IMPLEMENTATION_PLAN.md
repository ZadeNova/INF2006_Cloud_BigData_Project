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

## Next work

Outstanding documentation prerequisites: [independent planning review](reviews/planning-suite-review.md), findings DOC-001 through DOC-003. Resolve historical stock persistence, safe reimport rules and the autoscaling-policy inconsistency before dependent implementation. All three remain open; no remediation/re-review has occurred.

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
