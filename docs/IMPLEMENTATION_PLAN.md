# Implementation plan

Status checked: 3 October 2026. This file owns implementation status; [scope](../PROJECT_SCOPE_INF2006.md) owns requirements and dates. Everything finished before 1 October (every batch, review and phase entry) is in the [status history](archive/status-history.md); review logs are in [docs/reviews/](reviews/).

## Current state (3 October 2026)

- **Backend freeze (user decision, 1 October 2026).** The backend is frozen unless the user confirms an emergency; remaining work is AWS infrastructure, testing and evidence. Rules, the emergency process and the pinned-image consequence are in [AGENTS.md](../AGENTS.md#current-phase-backend-freeze-decided-by-the-user-1-october-2026).

- **AWS: compare two architectures, load-test each, then choose.** Variant A (EC2 + Auto Scaling group) and variant B (ECS on Fargate) run the same image digest against the same RDS, under a `base/` + `ec2/` + `fargate/` Terraform layout. Each is load-tested and the primary architecture is chosen from the measured numbers, against criteria and weights fixed before the first comparison run. Plan: [aws-ecs-comparison.md](plans/aws-ecs-comparison.md). Decisions: [docs/decisions/](decisions/) (ADR-001 to ADR-012).
  - **Done:** `base/` (network, RDS PostgreSQL 17, Route 53 zone, ACM certificate, ECR, S3 settings, secrets, alarm topic) and variant A (`ec2/`: ALB with HTTPS, ASG of 1 to 2 instances, request-count scaling, alarms, WAF) were applied and verified on 1 October: `https://shop-ec2.fourtytwofactors.me` served the shop, the dataset was imported, the operator account created, analytics refreshed, `smoke.sh` passed 8 of 8. The `ec2` stack is then torn down between sessions; `base/` stays up. Record: [runbook](../evidence/aws-build-runbook.md). How to run it: [src/infrastructure/README.md](../src/infrastructure/README.md).
  - **Not done:** variant B (`fargate/`) is not written; the Fargate lab checks in `scripts/probe-lab-comparison.sh` have not been run. The load harness is built and verified locally ([tests/load/](../tests/load/README.md); plan and locked decisions in [load-harness.md](plans/load-harness.md)) but has not run against AWS. No load, scaling, recovery or monitoring evidence exists yet.
  - Contract: [AWS_INFRASTRUCTURE.md](AWS_INFRASTRUCTURE.md) (describes variant A; the plan governs where they differ until the post-sprint documentation sync).

- **Security evidence.** A separate session is running scans and recording evidence: [plan](plans/security-evidence-20-percent.md), raw output in `evidence/raw/SCAN-*`, CI scanning added.

- **Application, analytics and ML: complete locally** on the shoe catalogue baseline (registration to order history, the operator analytics page, descriptive RFM segmentation). Local functional, security and data/AI evidence was recorded in September (`evidence/test-functional.md`, `test-security.md`, `test-data-ai.md`). The backend review gate for `0442665..HEAD` is still open.

- **Machine learning stays an offline batch job** (train, then the load command). Lambda and saved-model inference are not part of the plan (user decision, 3 October 2026).

- **Submission** is parked until engineering is done: [submissions-plans.md](plans/submissions-plans.md). Deadline 11 October 2026, 23:59 SGT.

## Phases

| Phase | Dates in 2026 | Status | Exit condition |
|---|---|---|---|
| 1. Foundation and feasibility | 11-17 Sep | Complete: local foundation and dataset; lab permissions verified; variant A deployed behind HTTPS with RDS on 1 October | Verify account, HTTPS and dataset; scaffold local app and first AWS smoke deployment |
| 2. Ecommerce and analytics | 18-24 Sep | Complete locally with functional, security and data/AI evidence (26 Sep); on AWS the S3 import and the workflow ran on variant A; the backend review gate for `0442665..HEAD` is open | AWS workflow/S3 import work; correctness/security/analytics tests pass |
| 3. Scaling and recovery | 25 Sep-1 Oct | Window ended with the 1 October feature freeze; the AWS comparison sprint ([plan](plans/aws-ecs-comparison.md)) now carries this phase: variant B and all load, scaling, recovery and monitoring evidence outstanding | Dated scaling, recovery and monitoring evidence; freeze features |
| 4. Reproduction and packaging | 2-8 Oct | Not started | Clean-machine rehearsal (offline and cloud reproduction, see the Phase 4 checklist), report, manifest and declarations complete |
| 5. Submission and preservation | 9-11 Oct | Not started | Submit by 11 Oct 23:59 SGT; archive ZIP and tag exact commit |

## Phase checklists

These are parallel work tracks, not extra staffing assumptions: the user leads backend/frontend, both developers share infrastructure, and three members support testing/reporting/admin. Only unfinished work is listed. Agents check an item only after linking actual verification; do not turn this file into a transcript.

### Phase 1 and 2: carry-overs

- [ ] Backend review gate: independent review of `0442665..HEAD` (shoe catalogue from the merge onward) logged under `docs/reviews/`, or a recorded user decision to accept it unreviewed.
- [ ] Independent review of `ec2/` and the scripts (`eb9fd70..c4ae7c4`): the log [reviews/aws-terraform.md](reviews/aws-terraform.md) covers only the retired single-folder stages 1 and 2. Run the gate or record why it was skipped.
- [ ] Cross-instance session and cart continuity with no stickiness, shown with two healthy instances (also in Phase 3).

### Phase 3: scaling, recovery and the architecture comparison

Method, fairness controls and measurements are in [aws-ecs-comparison.md](plans/aws-ecs-comparison.md) section 7; the harness is in [load-harness.md](plans/load-harness.md).

- [ ] Confirm the SME scale assumption (about 15 concurrent visitors at peak). The comparison weights were locked on 3 October 2026 ([load-harness.md](plans/load-harness.md) section 3).
- [x] Harness decisions locked, harness implemented and verified locally on 3 October 2026 ([tests/load/README.md](../tests/load/README.md)). Still needed before any AWS run: the load-generator instance, ASG detailed monitoring and capacity-pinning variables ([load-harness.md](plans/load-harness.md) section 10, for the Terraform session), and the user's check of `tests/load/prices.json`.
- [ ] Run the Fargate lab checks (`scripts/probe-lab-comparison.sh`, updated for the `base/` layout), then write, review and apply `fargate/` on the same image digest.
- [ ] RDS pilot: confirm the database is not the bottleneck, or state the limit.
- [ ] Load ladder of 1, 10, 100 and 1,000 virtual users, at least three repeats per level, on each variant, with raw outputs saved. Fixed capacity first, then request-count autoscaling.
- [ ] Per variant: scale-out time, replacement time and error window after killing an instance or task, new-image rollout time, p50 and p95 latency, throughput, error rate, cost per 1,000 requests and operational burden.
- [ ] With two healthy instances or tasks: failure and session continuity, and safe retry of uncertain checkout.
- [ ] Multi-AZ RDS failover with the app running: error window and recovery.
- [ ] Analytics refresh host loss in a controlled test: restart and re-run with no duplicate or partial summaries.
- [ ] Monitoring: exercise an actual alarm and a logs query, and record dated output (`evidence/monitoring.md`).
- [ ] Choose the primary architecture from the numbers; record the decision, the weights used and the evidence in an ADR, and state the limits (lab region, one operator, synthetic load).
- [ ] Cache: ElastiCache stays unselected unless the data shows a measured need.

### Phase 4: reproduction and packaging

- [ ] Fix defects and have a teammate reproduce the app/analytics from README on a clean setup.
- [ ] **Reproducibility (rubric-wide).** Two levels. *Offline:* a marker runs the app, tests and analytics with Docker only; the brief forbids requiring a cloud login (scope section 9). *Cloud:* the stack is reproducible from `src/infrastructure/` with documented prerequisites, expected cost and command order, and is shown to the marker through dated, redacted evidence. To do:
  - write `docs/REPRODUCE_CLOUD.md`: prerequisites, expected cost, command order, the CLI-created S3 bucket, the `release-<sha>` tag step, the `terraform.tfvars.example` files in `base/` and `ec2/` (and `fargate/`);
  - build the ZIP from git (`git archive`), not by copying the folder, so the state and variable files in `base/` and `ec2/` cannot enter it, and check the ZIP for them;
  - a teammate who did not write the code follows only the README on a fresh clone (the brief's Appendix A);
  - run the manifest's `run.prerequisites` and `run.commands` literally from that clone;
  - rewrite the README's AWS status once the comparison evidence exists; state the AMI drift ("latest Amazon Linux 2023") in the write-up.
- [ ] Complete the report's required headings, the architecture diagram (`evidence/architecture.png`), manifest links, contribution/AI declarations and traceable evidence; check every claim against actual output.
- [ ] Post-sprint documentation sync: make AWS_INFRASTRUCTURE.md, ARCHITECTURE.md and the README describe the chosen architecture, and archive the comparison plan.

### Phase 5: submission and preservation

- [ ] Validate ZIP structure, required artefacts, links and absence of secrets/personal data.
- [ ] Submit by the deadline; preserve the exact ZIP and tag the INF2006 baseline for later INF2003 work.

## Open items

| Item | Required decision/evidence |
|---|---|
| Lab account, balance, cost | Region `us-east-1` and permissions verified. The Learner Lab page showed USD 50 on 29 September, against the scope's USD 40 planning figure and USD 30 cap with USD 10 reserve. Credits do not pool; record the measured cost of each cloud session in the runbook |
| Comparison criteria and weights | The user fixes them before the first comparison run, so the result cannot be bent to a preferred answer |
| Load-harness decisions | Locked by the user on 3 October 2026 ([load-harness.md](plans/load-harness.md) section 2) |
| ElastiCache | Conditional; requires explicit selection, lab support, budget and measured value |
| Dataset | The user accepted descriptive use of the synthetic dataset on 22 September 2026 (DATA-003); weak weekly variation does not rule out flat noise. See the [profile](../data/PROFILE.md) and [review log](reviews/analytics-data-import.md) |
| Submission group ID | Fill in for submission packaging; member-name assignment is not a development task |
| INF2003 reuse | Confirm lecturer policy and contribution attribution |
