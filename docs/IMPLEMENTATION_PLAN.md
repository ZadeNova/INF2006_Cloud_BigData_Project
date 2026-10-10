# Implementation plan

> Final architecture: variant B (ECS on Fargate), ADR-018. Variant A (EC2) = evaluated alternative.

Status checked: 9 October 2026 (AWS bullets and the phase 3 row updated from the 8 October session; other entries as of 3 October). This file owns implementation status; [scope](../PROJECT_SCOPE_INF2006.md) owns requirements and dates. Everything finished before 1 October (every batch, review and phase entry) is in the [status history](archive/status-history.md); review logs are in [docs/reviews/](reviews/).

## Current state (9 October 2026)

- **Backend freeze (user decision, 1 October 2026).** The backend is frozen unless the user confirms an emergency; remaining work is AWS infrastructure, testing and evidence. Rules, the emergency process and the pinned-image consequence are in [AGENTS.md](../AGENTS.md#current-phase-backend-freeze-decided-by-the-user-1-october-2026).

- **AWS: two architectures were compared and load-tested; variant B (ECS on Fargate) was chosen (ADR-018, 9 October 2026), and variant A (EC2) is the evaluated alternative.** Variant A (EC2 + Auto Scaling group) and variant B (ECS on Fargate) run the same image digest against the same RDS, under a `base/` + `ec2/` + `fargate/` Terraform layout. Each was load-tested (one repeat per condition, indicative, n = 1) and the final architecture was chosen with criteria and weights fixed before the first comparison run, with a sensitivity analysis in ADR-018. Plan: [aws-ecs-comparison.md](plans/aws-ecs-comparison.md). Decisions: [docs/decisions/](decisions/) (ADR-001 to ADR-019).
  - **Done:** `base/` (network, RDS PostgreSQL 17, Route 53 zone, ACM certificate, ECR, S3 settings, secrets, alarm topic) and variant A (`ec2/`: ALB with HTTPS, ASG of 1 to 2 instances, request-count scaling, alarms, WAF) were applied and verified on 1 October: `https://shop-ec2.fourtytwofactors.me` served the shop, the dataset was imported, the operator account created, analytics refreshed, `smoke.sh` passed 8 of 8. **On 8 October variant A was applied again on the shared `modules/web-entry` and measured** (scale-out, replacement, saturation, alarms, logs, deployed security checks; one repeat each, n = 1): index [evidence/README.md](../evidence/README.md), generated tables [evidence/load-summary.md](../evidence/load-summary.md). The `ec2` stack is torn down between sessions; `base/` stays up. Record: [runbook](../evidence/aws-build-runbook.md). How to run it: [src/infrastructure/README.md](../src/infrastructure/README.md).
  - **Done, with open items:** variant B (`fargate/`) was applied and **measured on 9 October 2026** (results side by side with A in [evidence/README.md](../evidence/README.md); the 8 October preflight recorded that `LabRole` trusts `ecs-tasks.amazonaws.com` and that the Fargate quota cannot be read in the lab: `evidence/raw/PRE_2026-10-08_*.txt`). The load harness ([tests/load/](../tests/load/README.md); plan and locked decisions in [load-harness.md](plans/load-harness.md)) ran against variant A on 8 October and variant B on 9 October from a load-generator instance. Open items from those sessions: scale-in was not observed on A; RES-04 (session continuity) analysed on 10 October 2026 and held, on a small sample; `up.sh` stops at `db_bootstrap` on an existing database (work-around used); one saved Logs Insights query is malformed (`modules/web-entry/alarms.tf`); the WAF block test (SEC-17) was run on B only; FUNC-03 browser steps have no screenshots; MON-03 has one email leg per variant on record (ALARM on A, OK on B).
  - Contract: [AWS_INFRASTRUCTURE.md](AWS_INFRASTRUCTURE.md) (describes both variants; the final one is B, [ADR-018](decisions/ADR-018-final-architecture-ecs-fargate.md)).

- **Security evidence.** A separate session is running scans and recording evidence: [plan](plans/security-evidence-20-percent.md), raw output in `evidence/raw/SCAN-*`, CI scanning added.
  - **9 October CI secret-scan fix verified locally; independent review cleared; hosted rerun pending.** Five historical false positives have commit-and-path suppressions; the pinned history scan passes over 197 commits. The tracked-tree scan still reports four reviewed raw-evidence matches because commit-scoped suppressions do not apply there. [Triage](../evidence/security-scan-triage.md#scan-01-follow-up-9-october-2026); [review](reviews/gitleaks-ci-false-positives.md).

- **Application, analytics and ML: complete locally** on the shoe catalogue baseline (registration to order history, the operator analytics page, descriptive RFM segmentation). Local functional, security and data/AI evidence was recorded in September (`evidence/test-functional.md`, `test-security.md`, `test-data-ai.md`). The backend review gate for `0442665..HEAD` is still open.

- **Machine learning stays an offline batch job** (train, then the load command). Lambda and saved-model inference are not part of the plan (user decision, 3 October 2026).

- **Submission is in progress.** The report, manifest, README and functional evidence have been reconciled with the recorded A/B results; the contribution and AI declarations are final. Final architecture-diagram approval and report insertion, the remaining review gates and ZIP preflight are still open. Plan: [submissions-plans.md](plans/submissions-plans.md). Deadline 11 October 2026, 23:59 SGT.
  - **10 October documentation sync:** stale statements corrected across the README, evidence index, threat map, architecture notes, contributions and manifest ([plan](plans/doc-sync-final-submission.md)); no claim was added that the evidence does not support. Still open: team sign-off of the diagram, the AI-use confirmation paragraph in the declaration, `report.pdf`.
  - **9 October report audit follow-up:** the previously unknown Dior model source is now attributed in `src/static/models/CREDITS.md` to its Sketchfab author under CC BY 4.0; Section 2 now distinguishes the offline Fargate import path from the recorded variant-A import; Section 6 compares the recorded A/B scaling and replacement values side by side; Section 7 uses the task-only per-request figure; and Section 9 is reduced to a pointer to the final declaration. A PDF export rendered cleanly at 11 pages total, with the assessed body ending on page 10 before the references and appendix; this is within the 8-12-page limit excluding those end sections. The architecture image still needs insertion by a signed-in Google Docs editor because anonymous editing disables image insertion.

## Phases

| Phase                          | Dates in 2026 | Status                                                                                                                                                                                                                                                             | Exit condition                                                                                                                  |
| ------------------------------ | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| 1. Foundation and feasibility  | 11-17 Sep     | Complete: local foundation and dataset; lab permissions verified; variant A deployed behind HTTPS with RDS on 1 October                                                                                                                                            | Verify account, HTTPS and dataset; scaffold local app and first AWS smoke deployment                                            |
| 2. Ecommerce and analytics     | 18-24 Sep     | Complete locally with functional, security and data/AI evidence (26 Sep); on AWS the S3 import and the workflow ran on variant A; the backend review gate for `0442665..HEAD` is open                                                                              | AWS workflow/S3 import work; correctness/security/analytics tests pass                                                          |
| 3. Scaling and recovery        | 25 Sep-1 Oct  | Window ended with the 1 October feature freeze; the AWS comparison sprint ([plan](plans/aws-ecs-comparison.md)) now carries this phase: variant A load, scaling, recovery and monitoring evidence recorded on 8 October 2026; variant B measured on 9 October 2026 | Dated scaling, recovery and monitoring evidence; freeze features                                                                |
| 4. Reproduction and packaging  | 2-8 Oct       | In progress: clean-clone rehearsal recorded; report, manifest and evidence reconciliation underway; final diagram and ZIP preflight remain                                                                                                                         | Clean-machine rehearsal (offline and cloud reproduction, see the Phase 4 checklist), report, manifest and declarations complete |
| 5. Submission and preservation | 9-11 Oct      | Not started                                                                                                                                                                                                                                                        | Submit by 11 Oct 23:59 SGT; archive ZIP and tag exact commit                                                                    |

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
- [x] `fargate/`, the shared module and the script front door written (6 October, [fargate-variant.md](plans/fargate-variant.md), ADR-014 to 017). [ ] Apply `ec2/` (module refactor and ADR-013 settings), then `fargate/`, on the same image digest; record both in the runbook; independent review.
- [ ] RDS pilot: confirm the database is not the bottleneck, or state the limit.
- [ ] Load ladder of 1, 10, 100 and 1,000 virtual users, at least three repeats per level, on each variant, with raw outputs saved. Fixed capacity first, then request-count autoscaling.
- [ ] Per variant: scale-out time, replacement time and error window after killing an instance or task, new-image rollout time, p50 and p95 latency, throughput, error rate, cost per 1,000 requests and operational burden.
- [ ] With two healthy instances or tasks: failure and session continuity, and safe retry of uncertain checkout.
- [ ] Multi-AZ RDS failover with the app running: error window and recovery.
- [ ] Analytics refresh host loss in a controlled test: restart and re-run with no duplicate or partial summaries.
- [ ] Monitoring: exercise an actual alarm and a logs query, and record dated output (`evidence/monitoring.md`).
- [x] Choose the final architecture from the numbers (variant B, 9 October, [ADR-018](decisions/ADR-018-final-architecture-ecs-fargate.md)); record the decision, the weights used and the evidence in an ADR, and state the limits (lab region, one operator, synthetic load).
- [ ] Cache: ElastiCache stays unselected unless the data shows a measured need.

### Phase 4: reproduction and packaging

- [ ] Fix defects and have a teammate reproduce the app/analytics from README on a clean setup.
- [ ] **Reproducibility (rubric-wide).** Two levels. _Offline:_ a marker runs the app, tests and analytics with Docker only; the brief forbids requiring a cloud login (scope section 9). _Cloud:_ the stack is reproducible from `src/infrastructure/` with documented prerequisites, expected cost and command order, and is shown to the marker through dated, redacted evidence. To do:
  - write `docs/REPRODUCE_CLOUD.md`: prerequisites, expected cost, command order, the CLI-created S3 bucket, the `release-<sha>` tag step, the `terraform.tfvars.example` files in `base/` and `ec2/` (and `fargate/`);
  - build the ZIP from git (`git archive`), not by copying the folder, so the state and variable files in `base/` and `ec2/` cannot enter it, and check the ZIP for them;
  - a teammate who did not write the code follows only the README on a fresh clone (the brief's Appendix A);
  - run the manifest's `run.prerequisites` and `run.commands` literally from that clone;
  - rewrite the README's AWS status once the comparison evidence exists; state the AMI drift ("latest Amazon Linux 2023") in the write-up.
- [ ] Complete the report's required headings, the architecture diagram (`evidence/architecture.png`), manifest links, contribution/AI declarations and traceable evidence; check every claim against actual output.
- [x] Reconcile FUNC-03 Part 2 as not evidenced, remove its blank placeholders, and align the manifest, README and problem-framing roadmap with the draft-diagram/final-approval state (9 October 2026).
- [ ] Post-sprint documentation sync: make AWS_INFRASTRUCTURE.md, ARCHITECTURE.md and the README describe the chosen architecture, and archive the comparison plan.

### Phase 5: submission and preservation

- [ ] Validate ZIP structure, required artefacts, links and absence of secrets/personal data.
- [ ] Submit by the deadline; preserve the exact ZIP and tag the INF2006 baseline for later INF2003 work.

## Open items

| Item                            | Required decision/evidence                                                                                                                                                                                                                          |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Lab account, balance, cost      | Region `us-east-1` and permissions verified. The Learner Lab page showed USD 50 per member; the integration account retained a USD 30 working cap and roughly USD 20 reserve. Credits do not pool; measured session cost is recorded in the runbook |
| Comparison criteria and weights | The user fixes them before the first comparison run, so the result cannot be bent to a preferred answer                                                                                                                                             |
| Load-harness decisions          | Locked by the user on 3 October 2026 ([load-harness.md](plans/load-harness.md) section 2)                                                                                                                                                           |
| ElastiCache                     | Conditional; requires explicit selection, lab support, budget and measured value                                                                                                                                                                    |
| Dataset                         | The user accepted descriptive use of the synthetic dataset on 22 September 2026 (DATA-003); weak weekly variation does not rule out flat noise. See the [profile](../data/PROFILE.md) and [review log](reviews/analytics-data-import.md)            |
| Submission group ID             | `G021` is recorded in the manifest; the ZIP filename must be `Group_G021_INF2006_Project.zip`                                                                                                                                                       |
| INF2003 reuse                   | Confirm lecturer policy and contribution attribution                                                                                                                                                                                                |
