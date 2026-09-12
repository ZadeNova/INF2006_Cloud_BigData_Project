# Implementation plan

Status checked: 12 September 2026. This file owns implementation status; [scope](../PROJECT_SCOPE_INF2006.md) owns requirements and dates.

## Current state

- Documentation cleanup: removed nine separate foundation verification/output files at the user's request. Existing reviews in `docs/reviews/` are retained; supporting historical records remain in Git history. Required submission evidence templates remain in `evidence/`.

- Complete locally: added [GitHub Actions CI](../.github/workflows/ci.yml) for pull requests and main pushes, reusing pinned Docker/PostgreSQL. Image build, fresh isolated migrations, Django checks, missing-migration check and all 53 tests passed on 12 September; validation resources cleaned up. Hosted Ubuntu execution remains to be confirmed in Actions after push; Linux initializer ownership is configured but not reproduced locally. User explicitly waived independent review for this CI-only task; the general backend review rule remains unchanged.

- Pre-push follow-up: FP-001 mobile anchor offset and FP-002 stale status text corrected locally; focused independent Medium re-review found no new actionable findings. Original mobile reproduction verified; full cross-viewport settled-scroll matrix has a hidden-browser tooling limitation. [Review rounds and evidence](reviews/foundation-pre-push.md). Fixes and review record are included with this handover change; consult Git history for commit/publication state.

- Complete: removed the uncommitted dev.py launcher; root Docker Compose now supports up --build/up/down with a single local migration gate. Fresh-clone secret initialization remains explicit. Independent Medium review clean; live build/start, repeat startup and 53 tests passed. [Review and verification](reviews/root-compose-workflow.md).

- Complete: scope, design reference and submission scaffolding exist. Scope/design were pushed in commit `c7ed9d1`.
- Complete: agent entry point and focused planning documents drafted. This is documentation, not application delivery.
- Complete: all four backend foundation batches passed independent review and local verification (48 tests). See the bounded batch table below for evidence and review records. Dataset download/validation, business workflows, analytics and AWS deployment remain unimplemented/unverified; the frontend foundation is complete locally after its independent Astra Medium review.
- Complete: frontend foundation batches 1-3 plus review remediation serve the shared shell, representative presentation page, reusable states, responsive navigation, HTMX success/failure preview and branded 404/message states through Django HTTP. Overall Phase 1 remains in progress for dataset and AWS requirements.
- Backend authentication (registration/login/logout, session security) is implemented locally on branch `erfan/backend-auth`, not yet pushed or independently reviewed; see the 13 Sep 2026 entry under Update protocol and decisions for scope and verification.
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
- [x] Scaffold Django modules, pinned dependencies, Docker/Compose PostgreSQL, environment settings, initial migrations and health endpoint; local database connectivity verified. [Review and check summary](reviews/foundation-batch-4.md).
- [x] Render a base Django template with shared styling and HTMX through HTTP; record actual run/test commands. Implementation and browser evidence are recorded in [frontend foundation](reviews/frontend-foundation.md); independent Astra Medium review is clean in [frontend review](reviews/frontend-foundation.md).

**Infrastructure**
- [ ] Verify lab permissions, balance, region, shared Terraform state ownership and HTTPS arrangement; follow the [infrastructure setup order](AWS_INFRASTRUCTURE.md#setup-order-and-verification).
- [ ] Deploy a minimal application through ALB/EC2 and demonstrate RDS connectivity. A placeholder page is an intermediate smoke check, not completion of the Phase 1 database requirement.

**Data and evidence**
- [x] Resolve relevant planning-review prerequisites before dependent implementation: DOC-001/002 contract/persistence corrections accepted in [batch 3 review](reviews/foundation-batch-3.md); DOC-003 already corrected. Workflow regressions remain follow-ups.
- [ ] Download/pin the dataset, validate fields/relationships and record provenance/checksums; accept it or document the synthetic fallback.
- [ ] Define source mapping, dated inventory and safe reimport rules; capture evidence and review links as work completes.

### Phase 2: ecommerce and analytics

- [ ] Application: registration/login/logout, catalogue, persistent cart, atomic/idempotent checkout and owner-only history work end to end. Registration/login/logout implemented locally on branch `erfan/backend-auth` (implemented, Astra review pending); catalogue, cart, checkout and history remain.
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

1. Backend foundation is complete. Use [Docker quickstart](../src/README.md); local verification used the web/db services and the PostgreSQL volume is retained. Remaining Phase 1 work follows below.
2. Frontend foundation is complete at implementation checkpoint `c59b162` plus review/evidence checkpoint `6e94aec`; continue with the separate backend authentication task. Evidence: [frontend foundation](reviews/frontend-foundation.md); review: [frontend review](reviews/frontend-foundation.md).
3. Backend authentication task: registration/login/logout and session security implemented locally on branch `erfan/backend-auth` (see 13 Sep 2026 entry below for scope/verification). Status: implemented, Astra Medium review pending on push/PR per `CLAUDE.md`'s session-role note — not yet complete; independent review still required before this task can close.
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
- 12 Sep 2026: frontend foundation batch 3 added shared informational/error message presentation and `404.html`; focused tests passed 4/4, the full suite passed 52/52, and browser/HTTP evidence was recorded in [frontend-foundation.md](reviews/frontend-foundation.md). Round 1 Astra Medium review identified F-001 through F-005; `c59b162` remediated them with the validation sample, 503/retry preview, visible swap focus, 44px mobile controls and corrected evidence baseline. Focused tests passed 5/5, the full suite passed 53/53, and Round 2 independent Astra Medium review through `6e94aec` was clean with no new actionable findings. The frontend foundation is complete; dataset and AWS gates remain open.

- 13 Sep 2026: backend authentication (registration/login/logout, session security) implemented on branch `erfan/backend-auth` by the user working directly with Claude Code, per the session-role note added to `CLAUDE.md` (a separate learning-focused implementation track, not the standard Astra Low implementer assignment). Scope: `accounts` app registration via `UserCreationForm` (no `CustomerProfile` created, per `docs/SCHEMA.md`'s "profiles optional for locally registered users"); Django's built-in `LoginView`/`LogoutView` reused directly with safe-`next` handling and `redirect_authenticated_user`/`dispatch`-guard redirects for already-authenticated users; a `LOGOUT_REDIRECT_URL` fix (missing setting caused a 500 via Django's default `registration/logged_out.html` lookup); minimal templates reusing existing `site.css` patterns (`.form-field`, `.error-page`-style `.auth-page` card); and a fixed `Dockerfile` Gunicorn `--no-control-socket` flag (unrelated pre-existing local-dev-only log noise, non-fatal, found while verifying this task). Verification: `tests/test_accounts.py` (16 tests covering registration validation, login success/failure/safe-next, logout CSRF/405, already-authenticated guards) plus full suite 69/69 passed, `manage.py check` clean, `makemigrations --check --dry-run` reports no changes — all run locally via Docker Compose. Status: implemented, Astra Medium review pending on push/PR; do not mark this task complete until that independent review runs. A Claude self-review (not the Astra gate) additionally found and fixed two real issues before push: registration/login success messages rendered with an unstyled bare tag class instead of the site's `.message`/`.message--*` convention (fixed: `message message--{tag}` markup plus a `.message--success` CSS rule and `.messages` wrapper), and the field-rendering loop was duplicated between `register.html`/`login.html` (fixed: extracted to `accounts/_form_fields.html`, included by both). Full suite re-verified at 69/69 after these fixes.
- 12 Sep 2026: retain the complete technical scope with two primary developers and three testing/report/admin members. The user leads backend/frontend and both developers share infrastructure; remaining data/analytics and test-script ownership must be assigned. Contribution records must reflect actual work.

- Role-based ownership only: do not ask for or invent member names. Keep this tracker concise with task-specific file paths and check references; agents use targeted reads rather than routine repository-wide scans.

- Backend completion gate: independent Astra Medium reviews each backend task diff; Astra Low fixes logged findings. A repeated issue after its Low fix attempt stops the task for user-controlled Medium implementation escalation. Procedure: [development review gate](DEVELOPMENT.md#backend-review-gate). Foundation reviews are linked in the batch table below.

- Adopted from teammate reference: phase checklists split application/infrastructure/data work, task-to-exit-condition traceability and progressive infrastructure verification. Preserve Phase 1 RDS/HTTPS gates and current model/review rules.

## Active backend foundation batches

User-authorised local-only scope, base f719c67. Four sequential reviewed checkpoints; no AWS provisioning or push. No unfinished implementation drafts remain.

| Batch | Status | Verification / review |
|---|---|---|
| 1. Skeleton and dependencies (fca20e7) | Complete; review round 2 passed, B1-001 resolved | [Review and check summary](reviews/foundation-batch-1.md) |
| 2. Docker/PostgreSQL and environment (b137d63) | Complete; review round 1 passed, no findings | [Review and check summary](reviews/foundation-batch-2.md); base fca20e7 |
| 3. Schema and migrations (dd10f3a) | Complete; review round 1 passed; DOC-001/002 resolved at contract/persistence boundary | [Review and check summary](reviews/foundation-batch-3.md); base b137d63 |
| 4. Health and foundation verification | Complete; 48 tests; review round 1 passed, no findings | [Review and check summary](reviews/foundation-batch-4.md); base dd10f3a |

Follow-up tasks remain separate: authentication; catalogue/cart; data acceptance/import/analytics; AWS feasibility/deployment. The frontend foundation is completed in the frontend checkpoints and review record above; none of these remaining tasks is completed by the backend foundation.
