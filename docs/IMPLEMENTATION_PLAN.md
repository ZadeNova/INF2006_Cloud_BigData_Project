# Implementation plan

Status checked: 1 October 2026 (current state rewritten; the AWS and security entries were verified that day, other status lines are as last recorded). This file owns implementation status; [scope](../PROJECT_SCOPE_INF2006.md) owns requirements and dates.

## Current state (1 October 2026)

- **Backend freeze (user decision, 1 October 2026).** The backend is frozen unless the user confirms an emergency; remaining work is AWS infrastructure, testing and evidence. Rules, the emergency process and the pinned-image consequence are in [AGENTS.md](../AGENTS.md#current-phase-backend-freeze-decided-by-the-user-1-october-2026). Next: review the [EC2 / Fargate comparison plan](plans/aws-ecs-comparison.md) (written 1 October 2026), then the state migration, stage 2 apply in the new layout, the load and recovery runs, and evidence.

- **AWS: two variants, one sprint.** The AWS plan is [aws-ecs-comparison.md](plans/aws-ecs-comparison.md): compare EC2 + Auto Scaling group (A) with ECS on Fargate (B) for a small Singapore SME shop, under a `base/` + `ec2/` + `fargate/` Terraform layout. Terraform stages 0 and 1 are applied; stage 2 is written and reviewed but **not applied**, and must not be applied from the old single folder. A separate session writes the Terraform; the reviewing session reviews it read-only. Records: [runbook](../evidence/aws-build-runbook.md) (procedures, lab capability record, as-built log), [review log](reviews/aws-terraform.md), [contract](AWS_INFRASTRUCTURE.md).

- **Security evidence.** A separate session is running scans and recording evidence (started 1 October 2026): [plan](plans/security-evidence-20-percent.md), raw output in `evidence/raw/SCAN-*`, CI scanning being added.

- **Application, analytics and ML: complete locally** on the shoe catalogue baseline (registration to order history, the operator analytics page, descriptive RFM segmentation). Local functional, security and data/AI evidence was recorded in September (`evidence/test-functional.md`, `test-security.md`, `test-data-ai.md`). The backend review gate for `0442665..HEAD` is still open (see the Phases table). Every earlier batch and phase entry is in the [status history](archive/status-history.md).

- **Still needs AWS:** the ALB and HTTPS, the database jobs, the S3 import, scaling and recovery runs, monitoring evidence, the architecture diagram and the cost record.

- **Documentation consolidated (1 October 2026).** 43 finished plans and the retired AWS guides moved to [docs/archive/](archive/README.md); the AWS documents are now three files (the plan, the contract and the runbook).

## Phases

| Phase | Dates in 2026 | Status | Exit condition |
|---|---|---|---|
| 1. Foundation and feasibility | 11-17 Sep | Local foundation and dataset complete; lab permissions verified (read-only probe 25 Sep, active checks 29 Sep); Terraform stages 0 and 1 applied; the first smoke deployment (RDS and instance) follows the AWS plan, after the `base/` split | Verify account, HTTPS and dataset; scaffold local app and first AWS smoke deployment |
| 2. Ecommerce and analytics | 18-24 Sep | Complete locally, including the shoe catalogue baseline, the dashboard and descriptive ML; local functional, security and data/AI evidence recorded 26 Sep; backend review gate open for `0442665..HEAD`; AWS workflow and S3 import still open | AWS workflow/S3 import work; correctness/security/analytics tests pass |
| 3. Scaling and recovery | 25 Sep-1 Oct | Window ended with the 1 October feature freeze; the AWS sprint ([plan](plans/aws-ecs-comparison.md)) now carries this phase: no ALB, load test, scaling, recovery or monitoring evidence yet | Dated scaling, recovery and monitoring evidence; freeze features |
| 4. Reproduction and packaging | 2-8 Oct | Not started | Clean-machine rehearsal (offline and cloud reproduction, see the Phase 4 checklist), report, manifest and declarations complete |
| 5. Submission and preservation | 9-11 Oct | Not started | Submit by 11 Oct 23:59 SGT; archive ZIP and tag exact commit |

## Phase checklists

These are parallel work tracks, not extra staffing assumptions: the user leads backend/frontend, both developers share infrastructure, and three members support testing/reporting/admin. At each phase start, break only that phase into bounded tasks tied to its exit condition or a required rubric outcome. Keep future phases at checklist level. Agents check an item only after linking actual verification; do not turn this file into a transcript.

### Phase 1: foundation and feasibility

**Application**
- [x] Scaffold Django modules, pinned dependencies, Docker/Compose PostgreSQL, environment settings, initial migrations and health endpoint; local database connectivity verified. [Review and check summary](reviews/foundation-batch-4.md).
- [x] Render a base Django template with shared styling and HTMX through HTTP; record actual run/test commands. Implementation and browser evidence are recorded in [frontend foundation](reviews/frontend-foundation.md); independent Astra Medium review is clean in [frontend review](reviews/frontend-foundation.md).

**Infrastructure**
- [ ] Verify lab permissions, balance, region, Terraform state ownership and HTTPS arrangement; follow the [infrastructure setup order](AWS_INFRASTRUCTURE.md#setup-order-and-verification). Progress 30 September 2026: permissions verified ([runbook](../evidence/aws-build-runbook.md); the lab capability record stays local until redacted), balance USD 0.20 of 50 used, region `us-east-1`, state on one apply device, domain bought; **open:** the ACM certificate and DNS validation (stage 3).
- [ ] Deploy a minimal application through ALB/EC2 and demonstrate RDS connectivity. A placeholder page is an intermediate smoke check, not completion of the Phase 1 database requirement. Stage 2 (RDS and the first instance) is written and reviewed; the ALB is stage 3.

**Data and evidence**
- [x] Resolve relevant planning-review prerequisites before dependent implementation: DOC-001/002 contract/persistence corrections accepted in [batch 3 review](reviews/foundation-batch-3.md); DOC-003 already corrected. Workflow regressions remain follow-ups.
- [x] Download/pin the dataset, validate fields/relationships and record provenance/checksums; manual acceptance for descriptive use recorded. [Profile](../data/PROFILE.md), [provenance](../data/README.md), [round-2 review](reviews/analytics-data-import.md).
- [x] Define and implement source mapping, dated inventory and safe reimport rules. Full-source import/replay, inventory completeness and live-state preservation verified; [round-2 review](reviews/analytics-data-import.md).

### Phase 2: ecommerce and analytics

- [ ] Application: registration/login/logout, catalogue, persistent cart, atomic/idempotent checkout and owner-only history work end to end. All implemented on branch `erfan/backend-auth`; independent Astra Medium review gate cleared at `7eea9b7` on 22 Sep 2026 (logs linked in the entries below). Left unchecked because the end-to-end walkthrough on real data and the frontend integration are still open, not because review is pending.
- [ ] Frontend: remaining application route/form/validation integration using DESIGN. The protected analytics dashboard is complete locally; [round-3 review CLEAR](reviews/analytics-dashboard.md).
- [ ] Infrastructure: real app image, private S3 import, secure config, logs and cross-instance sessions work with no stickiness; HTTPS precedes credential-bearing traffic.
- [x] Data import: create-only replay preserves live state; generated inventory is complete and sealed. Dataset roadmap Phases 1–2 cleared; [review](reviews/analytics-data-import.md).
- [x] Data analytics: imported-data refresh independently reconciled with pandas and dashboard dates/freshness integrated (roadmap Phases 3–4). [Phase 3 review](reviews/analytics-phase3.md), [Phase 4 round-3 review CLEAR](reviews/analytics-dashboard.md).
- [ ] Verification: independent backend review gates and relevant functional/security/data tests pass; supporting members record results and report notes.

### Phase 3: scaling and recovery

- [ ] Measure fixed-capacity baseline then request-count autoscaling; capture latency, throughput, errors, healthy capacity and delay.
- [ ] With two healthy instances, demonstrate failure/session continuity and safe retry of uncertain checkout.
- [ ] Exercise analytics scheduler-host loss in a controlled test and verify restart/re-run without duplicate or partial summaries; record interruption and recovery.
- [ ] Complete security/storage/analytics tests and an actual monitoring query/alert; diagnose failures honestly.
- [ ] Validate included descriptive ML after core correctness; offline segmentation exists locally but its remediation/review and saved-model scheduled Lambda inference remain open. Cache remains conditional. Preserve ML isolation and freeze features by 1 October.

### Phase 4: reproduction and packaging

- [ ] Fix defects and have a teammate reproduce the app/analytics from README on a clean setup.
- [ ] **Reproducibility (rubric-wide; recorded 30 September 2026).** Two levels. *Offline:* a marker runs the app, tests and analytics with Docker only; the brief forbids requiring a cloud login (section 9). *Cloud:* the stack is reproducible from `src/infrastructure/` with documented prerequisites, expected cost and command order, and is shown to the marker through dated, redacted evidence. To do:
  - after each remaining Terraform stage, ask whether someone could repeat it from the docs alone;
  - write `docs/REPRODUCE_CLOUD.md`: prerequisites, expected cost, command order, the CLI-created S3 bucket, the `release-<sha>` tag step, `terraform.tfvars.example`;
  - build the ZIP from git (`git archive`), not by copying the folder, so `terraform.tfstate` and `terraform.tfvars` in `src/infrastructure/` cannot enter it, and check the ZIP for them;
  - a teammate who did not write the code follows only the README on a fresh clone (the brief's Appendix A);
  - run the manifest's `run.prerequisites` and `run.commands` literally from that clone;
  - rewrite the README's AWS status once the cloud evidence exists; state the AMI drift ("latest Amazon Linux 2023") in the write-up.
- [ ] Complete the report's required headings, manifest links, contribution/AI declarations and traceable evidence; check every claim against actual output.

### Phase 5: submission and preservation

- [ ] Validate ZIP structure, required artefacts, links and absence of secrets/personal data.
- [ ] Submit by the deadline; preserve the exact ZIP and tag the INF2006 baseline for later INF2003 work.

## Next work

1. Backend foundation is complete. Use [Docker quickstart](../src/README.md); local verification used the web/db services and the PostgreSQL volume is retained. Remaining Phase 1 work follows below.
2. Frontend foundation is complete at implementation checkpoint `c59b162` plus review/evidence checkpoint `6e94aec`; continue with the separate backend authentication task. Evidence: [frontend foundation](reviews/frontend-foundation.md); review: [frontend review](reviews/frontend-foundation.md).
3. Backend authentication task: registration/login/logout and session security implemented and pushed on branch `erfan/backend-auth` (see 13 Sep 2026 entry below for scope/verification). Status: implemented; independent review round 1 found no actionable findings ([log](reviews/auth-registration.md)); backend gate cleared at `7eea9b7` on 22 Sep 2026.
4. Backend catalogue, `store_operator`, cart, checkout and order history tasks: all implemented locally on branch `erfan/backend-auth` (see 14/15/19 Sep 2026 entries below). Status: implemented and independently reviewed; findings and re-reviews are in [catalogue-operator](reviews/catalogue-operator.md), [cart](reviews/cart.md), [checkout](reviews/checkout.md) and [order-history](reviews/order-history.md); backend gate cleared at `7eea9b7` on 22 Sep 2026.
5. Data track: dataset roadmap Phases 1–4 complete locally with independent review CLEAR; Phase 4 is cleared for the user-authorized local commit. Next: remaining evidence/packaging and separately scoped deterministic correctness/load fixtures; AWS remains on the infrastructure track. [Dashboard review and limitations](reviews/analytics-dashboard.md), [roadmap](archive/plans/backend-completion-roadmap.md).
6. Infrastructure track: follow [the AWS plan](plans/aws-ecs-comparison.md): state migration into `base/`, then `base/`, `ec2/`, the database jobs, `fargate/`, the load runs and evidence.

Planning DOC-001/002 are resolved at the contract/persistence boundary; future importer/checkout/aggregation regressions remain required. DOC-003 remains corrected. See [planning review](reviews/planning-suite-review.md).
## Open items

| Item | Required decision/evidence |
|---|---|
| Integration account, region, permissions, balance | Permissions and region verified (29 September 2026); the Learner Lab page shows USD 50 for the integration account, against the scope's USD 40 planning figure and the USD 30 cap with USD 10 reserve. Keep the measured cost per cloud session in the runbook; credits do not pool |
| HTTPS | Domain `fourtytwofactors.me` bought (Namecheap, 29 September 2026); the shop is `shop.fourtytwofactors.me`. Open: the Route 53 zone and the certificate in `base/` (see the AWS plan) |
| Dataset | Integrity passes: Analytics Engineering v1.0.0 (CC BY 4.0), raw download `b95905a` unchanged, exact counts and zero integrity rejects. **User accepted descriptive use on 22 Sep 2026 (DATA-003)**; weak weekly variation and 31.67–39.75% without recent sales do not rule out flat noise. [Review log](reviews/analytics-data-import.md), [profile](../data/PROFILE.md). Round-2 independent review cleared all findings and repeated full-source import/replay in reviewer-only scratch. Deployed demo namespace/date anchor remains to be selected. |
| ElastiCache | Conditional; requires explicit selection, lab support, budget and measured value |
| Included ML | Implemented locally as an additive RFM K-means panel (offline train + load command + dashboard), evaluated on the shoe dataset including the hold-out and subsample checks (`evidence/test-data-ai.md`). The earlier "publish only after required work/AWS evidence" gate was removed by the user on 27 September 2026. Keep it removable and descriptive-only on synthetic data. |
| Submission group ID | Fill in for submission packaging; member-name assignment is not a development task |
| INF2003 reuse | Confirm lecturer policy and contribution attribution |
| Dataset generation/alteration permission | **Resolved 22 Sep 2026:** confirmed permitted by the user. Generating/altering dataset fields (synthetic stock/lead-time supplementation per `docs/DATA_PIPELINE.md`) may proceed for the real-dataset import task |
| Shoe-shop remap of the dataset | **Approved by the professor (24 Sep 2026)**, covering replacing product identities, names, prices and categories (the 22 Sep permission above covered only generated stock and lead times). Plan: [shoe-dataset-remap.md](archive/plans/shoe-dataset-remap.md). A teammate owns the build: the shoe catalogue file, `analytics/build_shoe_dataset.py`, and the namespace switch, and decides the product count (the user's estimate is 20 to 40). Handoff for the teammate and their Claude Code session: [shoe-dataset-handoff.md](archive/plans/shoe-dataset-handoff.md). Not yet adopted, recorded as evidence or described in the report — that follows once the derived dataset passes `config.dataset.validate` with zero rejects |
