# Plan: EC2 + ASG (A) compared with ECS on Fargate (B)

Part of [aws-terraform.md](../archive/plans/aws-terraform.md), which this plan supersedes where they differ (layout, ownership, RDS size, stage order). Written and consolidated 1 October 2026.

**Status (3 October 2026):** plan agreed with the user and in execution. **Done on 1 October:** the state migration, `base/` (RDS, zone, certificate, ECR, secrets, alarm topic), the scripts, and variant A (`ec2/`) with its database jobs, scaling, alarms and WAF, verified (`smoke.sh` 8 of 8) and then torn down; `base/` stays up. See the [runbook](../../evidence/aws-build-runbook.md). **Not done:** `fargate/` (not written), the Fargate lab checks, the load harness ([load-harness.md](load-harness.md), draft), the comparison weights, and every load, scaling, recovery and monitoring run. The rules below were written before the build and still apply to the remaining work.

## 1. Read this first

**What the project does now.** The backend is frozen ([AGENTS.md](../../AGENTS.md#current-phase-backend-freeze-decided-by-the-user-1-october-2026)). The remaining work is AWS infrastructure, testing and evidence. The professor confirmed ECS and Fargate work in the lab and said a performance comparison between EC2 and Fargate would make the project stand out, and that every architectural decision, down to the small ones, must be justified. So the comparison is a deliverable and every setting traces to a recorded decision.

**Hard rules for every Claude session**
1. **Never apply from the retired single-folder layout.** It was removed after the state migration passed its gate on 1 October (section 5); `base/` and each stack are applied only through `scripts/tf.sh` from committed code.
2. **One writer per file.** The **writing session** (writes the Terraform and scripts) is the only one that edits `src/infrastructure/**`. The **reviewing session** (discusses the architecture, reviews diffs read-only, owns decision records, the load harness and evidence) never edits those files. If both must write, one uses a separate `git worktree` and branch and they merge through git. The independent-review rule in AGENTS.md forbids a session reviewing its own code.
3. **The user runs every `plan` and `apply`.** Sessions prepare; they do not apply.
4. **Nothing is committed or pushed unless the user asks** (CLAUDE.md).
5. **If a session finds code already written in the old layout** (for example an edited `compute.tf` or `database.tf`), it says so and stops, so the user decides where it goes.
6. **Read before writing:** this plan, AGENTS.md and the superseded parts of aws-terraform.md only as history.

**Who does what.** W = writing session, R = reviewing session, U = the user.

## 2. The shop and its scale

42Factors is treated as **a small Singapore startup or SME selling shoes online**: one operator, always open, steady browsing with bursts (a restock or sale), a small share of checkouts ([scope](../../PROJECT_SCOPE_INF2006.md)).

**Design target, not a finding:** a busy normal day of about 3,000 visits, about 5 dynamic pages per visit, 10% of the day's visits in the busiest hour. That is about 300 visits per hour, 0.4 dynamic pages per second and **about 15 concurrent visitors at the evening peak**.

Evidence and its limits (checked 1 October 2026):
- Typical small stores are far smaller: StoreCensus reports a median of 567 visits per month for 237 clothing Shopify stores (third-party estimates). Established stores reach tens of thousands: Koala Apps reports 26,101 (smallest) and 59,472 (median) modelled monthly visits for a busy, self-selected cohort. The target is deliberately at the established tier and the report says so.
- Pages per visit 4.4 to 4.9 (Contentsquare benchmark via Oberlo, Q4 2022). Singapore conversion about 2.8% (Statista via a Branch8 blog; weak), which supports a small checkout share.
- No public source gives per-store traffic for Singapore SMEs, and none supports a per-store burst multiple. Platform-wide Black Friday peaks are +17% to +77% over baseline (aggregates, not one store), so the burst is a **stress parameter**, not a claim.
- The 3-minute session length and the 10% peak-hour share are unsourced assumptions. Two claims from search summaries failed verification and are not used: a 10 pm Singapore peak and a 3 to 5 minute session benchmark.

The report must state honestly:
- At this scale **one small instance or task carries normal load.** Autoscaling gives burst headroom and replacement after a failure, not capacity the shop needs.
- The load tests push **far beyond** realistic SME traffic to make scaling visible. Results are reported as capacity per unit of compute and as a multiple of the assumed peak.
- The monthly cost gap between the variants is a few dollars. Operational effort (patching, boot scripts, scale-out time, recovery) is the larger difference.

### Load ladder

**1, 10, 100 and 1,000 virtual users**; one user is one concurrent visitor with realistic think time (about 36 s per page). By Little's law (concurrent users = visits per second times session length):

| Users | Visits per hour | Dynamic pages/s | Times the SME peak | Role in the story |
|---|---|---|---|---|
| 1 | 20 | 0.03 | 0.07 | Unloaded baseline: pure latency |
| 10 | 200 | 0.3 | 0.7 | A normal busy evening |
| 100 | 2,000 | 2.8 | 6.7 | A campaign or flash sale |
| 1,000 | 20,000 | 28 | 67 | Stress, far beyond the SME story: find the limit, trigger scaling |

The top level is outside the SME story by design. A separate **saturation run** (no think time) finds maximum throughput and is reported apart from the ladder. The figures change if the assumptions change.

## 3. Decisions (user, 1 October 2026 unless noted)

**Scope**

| Decision | Detail |
|---|---|
| Variants | **A: EC2 + ASG** and **B: ECS on Fargate** only. ECS on EC2 was dropped for time; whether a difference comes from ECS or from Fargate is answered in the report from the design and stated as unmeasured. App Runner, Lambda and others are not compared (Lambda would need an app rewrite). |
| Primary architecture | **Decided after the data comes in.** Diagram and threat map cover both variants. |
| Backend | Frozen. Both variants run **one recorded image digest**. |

**Network and DNS**

| Decision | Detail |
|---|---|
| Latency to the US | **Accepted** (lab is us-east-1 only; the professor was told). The report states the added latency for Singapore customers, measured by one run from outside the region, and that production would use `ap-southeast-1`. |
| Load generator | In-region by default, so the comparison measures the infrastructure, not the ocean. |
| ALB and WAF | **Required.** The ALB gives TLS termination, health checks, replacement and the request-count metric that scaling uses; the WAF rate rule on `POST /login/` answers threat T7. |
| DNS | **Route 53, tried first, time-boxed.** The hosted zone and the ACM validation records live in `base/`; each stack adds an alias for its own hostname (`shop-ec2.<domain>`, `shop-fargate.<domain>`), so a recreated ALB needs no manual DNS change. Order: (1) create the zone in `base/` and see whether the lab allows it; (2) only if it does, set the four Route 53 name servers at Namecheap and wait for delegation (`dig NS`); (3) validate the certificate in Terraform. If the zone is denied, or delegation is not working by the time the ALB is ready, fall back to manual ACM validation and one CNAME per ALB at Namecheap. **Do not change the Namecheap name servers before step 1 succeeds:** after delegation Namecheap's own records stop applying, so a fallback means switching back and waiting again. Keep the zone until final teardown, because a recreated zone gets new name servers. |

**Database**

| Decision | Detail |
|---|---|
| RDS size | **One size for every recorded run and for the final submission**, chosen from a measured pilot, not from the traffic assumption. Start `db.t4g.small` (2 vCPU, 2 GB; about USD 0.032 per hour, verify), replacing the stage 2 default `db.t4g.micro`. Why not larger: the database sees about 2 to 3 queries per second at peak and about 200 at the 1,000-user step, a few percent of one vCPU, and the dataset is a few hundred MB. Burstable with unlimited mode (the RDS default) suits low average load with sustained promotions: it does not throttle, it bills a small surcharge. Revisit trigger: promotions that are frequent or last many hours, then use a fixed-performance class. |
| Sizing rule | **Pilot gate:** one single-instance run at the 1,000-user step with RDS CPU, connections, free memory and credit balance captured. If CPU is not comfortably low, size up once (`db.t4g.medium`) before the recorded runs. A failure **inside a recorded run** is kept as a finding about small, then the affected runs are rerun on the new size and the old ones marked superseded, so no comparison mixes two sizes. A resize takes a Single-AZ database down for minutes, so do it only between runs. If the database still limits the saturation run, the report says so; scale-out, replacement, rollout, cost and operational burden do not depend on it. |
| Availability | Single-AZ by default (budget, stated). **One controlled Multi-AZ failover test:** enable Multi-AZ, force a failover, measure the error window and recovery (the app already returns a controlled 503 while the database is unavailable), record it, then decide whether to keep it. Whether the lab allows Multi-AZ is learned at plan and apply. |
| Not used | **Read replica:** it does not fail over by itself and the frozen app has one connection and no read routing, so it would sit idle. **Database autoscaling:** plain RDS has none; Aurora Serverless v2 would, but it is a different engine from the one the bootstrap and security checks were built and tested against, and at these loads there is nothing for it to react to. The report names it as the evolution path; verify its minimum-capacity price before quoting it. |

**Process**

| Decision | Detail |
|---|---|
| Mode | Implementation Mode; explanations on request. Pace: as fast as possible without lowering quality, so the order of value, review gates and decision records stay. |
| Data transfer cost | **Not measured; documented limitation.** Static files and 3D models are served by the app, so first-visit egress could cost more than compute. |

## 4. Layout

```
src/infrastructure/
  README.md     apply and destroy order, state custody, command cheat sheet
  base/         VPC, subnets, sg-db, Route 53 zone, certificate, RDS, ECR, S3, secrets, SNS (stays up between experiments)
  ec2/          ALB, sg-alb, sg-app, launch template, ASG, scaling, alarms, user_data, alias record, per-stack log group
  fargate/      ALB, sg-alb, sg-app, cluster, task definition, service, scaling, alias record, per-stack log group
  sql/          trainer role scripts, unchanged
  scripts/      see section 8
```

1. **One-way dependencies.** `ec2/` and `fargate/` read `base/` through `terraform_remote_state` (local backend path). `base/` never reads them. `base/outputs.tf` is the interface: VPC and subnet IDs, `sg-db`, DB host, secret names, ECR URL, bucket, zone ID, certificate ARN, SNS topic.
2. **One folder, one state.** No workspaces.
3. **Names and tags.** `inf2006-grp21-<stack>-<component>`; `base` has no stack part. Every resource carries `Stack = base | ec2 | fargate` besides the default tags.
4. **No child modules, no symlinks.** `versions.tf` and `providers.tf` are repeated per folder; each folder runs alone and survives `git archive`.
5. **State.** Local, one file per folder, gitignored, dated backup after every apply. `.terraform.lock.hcl` committed in each folder.
6. **Teardown order.** Stacks, then `base/`, then the S3 bucket by CLI. `base/` stays up through the sprint (RDS about USD 0.43 per day); destroying it means re-bootstrapping and re-importing.
7. **Every setting traces to a decision.** Code comments carry the decision ID (`# ADR-014`).

Writing order: `base/` first, then `ec2/`, then `fargate/`.

## 5. State migration (done 1 October 2026)

The 40 stage 1 resources move into `base/` with `terraform state mv`. `sg-alb`, `sg-app` and their rules move to the stacks; they are attached to nothing, so recreating them costs nothing. Procedure: dated state backup, move, then **gate: `terraform plan` in `base/` shows no changes.** Nothing else proceeds until it passes. Recreating stage 1 is the fallback, but it loses the secret values and the pushed image. The migration ran with `scripts/migrate-state.sh` (one-time, done); the result is in the runbook.

## 6. What differs between the variants

The A-versus-B table is recorded in the contract: [AWS_INFRASTRUCTURE.md, Variant B](../AWS_INFRASTRUCTURE.md#variant-b-ecs-on-fargate-built-and-measured-the-final-architecture). Summary: B runs an ECS task with no instance, scales with Application Auto Scaling on the same request-count metric, reads its probe host from the ECS metadata endpoint, runs jobs with `aws ecs run-task`, and uses the task role.

Both use LabRole (no IAM creation), the same ALB design and health check (`/health/`), no stickiness, the same Gunicorn settings and the same image digest. Fargate has its own vCPU quota that the lab will not let us read, so how far B can scale is learned at apply.

## 7. Experiment method

Fairness controls:
- **Same image digest**, same RDS, same Locust profile, one variant tested at a time. Both stacks may exist together, but only one takes load.
- **Match compute.** Default EC2 `c5.large` (2 vCPU, 4 GiB, non-burstable) against Fargate 2 vCPU / 4 GB. A burstable t3 would confound the result; if used, record `CPUCreditBalance`. If the lab refuses `c5.large`, use an equivalent and say so.
- **Pilot first** (RDS pilot gate above), then at least **3 repeats** per condition with warm-up and a fixed run length.
- Think times and the request mix are fixed before the first comparison run. About 1% of requests are checkout (2 to 3% conversion).

Measurements: scale-out time (trigger to first healthy target); replacement time and error window after killing an instance or task; new-image rollout time; cost per hour and per 1,000 requests at equal capacity; p50 and p95 latency, throughput and error rate; **operational burden** (Terraform lines and resources, boot-to-healthy time, steps to patch).

Criteria and weights are fixed by U **before the first comparison run**, so the result cannot be bent to a preferred answer. Expected, unproven: similar steady-state speed at matched size, with the differences in scale-out, operations and cost. The kill-and-replace and scaling runs double as the scaling, recovery and session-continuity evidence the scope requires.

**Decision records:** `docs/decisions/ADR-NNN-<title>.md`, one per decision: the decision, options considered, the driver traced to the shop scenario, the evidence that will back it, and when to revisit. W drafts each while writing the `.tf`; R reviews it. Only settings that plausibly move results are tuned (scaling target value, health-check interval, deregistration delay, grace period); everything else gets a stated default and reasoning. After each stack R gives U a short oral rehearsal (R asks, U answers without opening the files).

## 8. Manual steps and automation

Aim: one command per stack. Best practice is not zero manual steps but few, explicit, scripted, repeatable ones, with secrets never in code or state. [ci.yml](../../.github/workflows/ci.yml) runs tests only: it builds no image and touches neither AWS nor Terraform. The report presents this table with the production version of each step.

**Unavoidable manual steps:** lab credentials (they expire; every script runs `sts get-caller-identity` first and fails clearly), the one-time Namecheap name-server change, the SNS email click, the image push (the lab cannot create the IAM role or OIDC link for CI), and creating the S3 bucket by CLI (the lab denies a read the Terraform resource needs).

Scripts under `src/infrastructure/scripts/`, small and idempotent, written by W and reviewed by R. No framework; each script stops on its first failure; Terraform builds infrastructure and scripts run jobs (no provisioners, because the jobs must run inside the VPC).

| Script | Does | When |
|---|---|---|
| `tf.sh <folder>` | `fmt -check`, `validate`, `plan -out` with the commit SHA recorded; refuses a dirty tree | every plan and apply |
| `push-image.sh` | Build, tag by git SHA, push to ECR, record the digest; supplies `image_tag` to Terraform | per code change |
| `secrets.sh` | Create missing secret fields with random passwords and never regenerate an existing one; copy the RDS master credentials into the bootstrap secret immediately before bootstrap (frozen secrets contract, 7-day rotation); print only match or differ | once, safe to rerun |
| `up.sh <ec2\|fargate>` | Apply the stack, run database jobs still needed, then `smoke.sh` | per run |
| `jobs.sh <variant> <bootstrap\|migrate\|trainer-sql\|import>` | Run in order: EC2 through SSM Run Command or a non-interactive session calling `app-job`; Fargate through `aws ecs run-task`, waiting for the exit code | once per fresh database |
| `smoke.sh <hostname>` | `/health/`, the HTTPS certificate, the login page, a product page | per run |
| `evidence.sh <variant>` | Collect redacted outputs into `evidence/raw` | per run |
| `down.sh <variant>` | Destroy the stack and confirm nothing billing remains | per run |

To verify early: whether `LabRole` allows SSM `SendCommand` (fallback: a non-interactive session through the Session Manager plugin). Optional and not run: `scripts/probe-lab-comparison.sh` (since deleted; git history keeps it) (the professor confirmed Fargate, so `c5.large`, the RDS class and Multi-AZ are found out at plan and apply, with small fallbacks).

## 9. Schedule (about two working days)

Order of value: A fully working with its required evidence first, then B, then the comparison runs.

| # | Step | Owner | Gate | Status |
|---|---|---|---|---|
| 1 | State migration into `base/` | W prepares, U runs | zero-diff plan in `base/` | Done 1 Oct |
| 2 | `base/`: **the Route 53 zone first** (section 3, DNS), then stage 2's RDS and parameter group, the certificate and its validation, outputs | W writes, R reviews, U applies | applied; RDS reachable only from sg-app; certificate issued | Done 1 Oct |
| 3 | `scripts/`: `tf.sh`, `push-image.sh`, `secrets.sh` | W, R reviews | secrets match; image digest recorded | Done 1 Oct |
| 4 | `ec2/`: stage 2 compute plus the ALB, HTTPS and alias record | W, R, U | healthy through the ALB at its hostname | Done 1 Oct (stack torn down between sessions) |
| 5 | `jobs.sh`: `db_bootstrap`, `migrate`, trainer SQL, dataset import, once (shared by both variants) | W, U | `check_database` passes as the runtime login | Done 1 Oct |
| 6 | `fargate/` | W, R, U | healthy through its ALB on the same digest | Not started |
| 7 | Load harness (in-region), RDS pilot, then the ladder and saturation runs on each variant | R builds the harness; U runs | RDS is not the bottleneck, or the limit is stated | Harness is a draft ([load-harness.md](load-harness.md)); no runs yet |
| 8 | Multi-AZ failover test, with the app running | U, R records | error window and recovery recorded | Not started |
| 9 | Evidence, decision records, redacted configuration, teardown | R, U | evidence files written; destroy order followed | Partly: runbook entries written; ADR-001 to ADR-012 drafted for review |

## 10. Acceptance

- **`base/`:** RDS private, encrypted, engine 17.x, `rds.force_ssl = 1`, 7-day backups; zone delegated; certificate issued.
- **Each stack:** target healthy behind the ALB over HTTPS at its own hostname; no port 22; container (or task) running from the recorded digest; logs arriving in CloudWatch; (A) IMDSv2 required.
- **Database jobs:** bootstrap, migrate, trainer SQL and import succeed; `check_database` passes as the runtime login. Least privilege tested: the runtime login cannot `CREATE TABLE`, the trainer login cannot `INSERT`.
- **Comparison:** at least 3 repeats at each ladder level on each variant, with raw outputs saved; criteria weights recorded before the first run.
- **Teardown and record:** nothing billing remains; runbook entry with commits, redacted outputs and the lab balance.

## 11. Cost

A rough order of magnitude, to be verified against current pricing before each session: base about USD 0.04 per hour (RDS small plus the zone, which is about USD 0.50 per month); each stack (ALB, its public IPv4 addresses, one or two compute units) about USD 0.10 to 0.20 per hour while up. Two days should stay well under USD 10 if stacks are destroyed between runs. Read the lab balance at the start and end of every session.

## 12. Open items

- [ ] U confirms the SME scale assumption and the 3-minute session / 10% peak-hour parameters; find sources if possible.
- [ ] U fixes the comparison weights before the first run.
- [x] Lab permissions learned by apply (1 October): Route 53 zone creation, `c5.large`, `db.t4g.small`, SSM `SendCommand`, WAFv2 on an ALB, CloudWatch alarms and query definitions all allowed ([runbook](../../evidence/aws-build-runbook.md)).
- [ ] Lab permissions still unknown: Multi-AZ, `LabRole` as an ECS task and execution role, a Fargate task pulling the ECR image, the Fargate vCPU quota. `scripts/probe-lab-comparison.sh` (since deleted; git history keeps it) answers these but was written for the retired single folder and needs a small update first. Each has a stated fallback.
- [ ] Record a browser session (HAR) against the local build to count requests per visit, dynamic and static separately.
- [ ] Per-stack log groups: done for `ec2/` (its own log group); confirm the same while writing `fargate/`.

## 13. Carried forward from the retired Terraform plans

The old plan ([aws-terraform.md](../archive/plans/aws-terraform.md) and the stage 0 to 2 guides) is archived. What is still true and still needed is here, so the justification record is not lost.

**Decisions that still hold**

| Topic | Decision |
|---|---|
| Build method | Terraform creates and owns every team resource. The console is for watching, and for the few steps Terraform cannot do (section 8). Anything created by hand is imported into Terraform or deleted. |
| Region and account | `us-east-1` only (the lab has no Singapore region); two AZs (`us-east-1a`, `us-east-1b`, pinned). The user's own Learner Lab account is the one official account. Groupmates' accounts are **cold backups only**: a fallback starts a fresh `apply` from the same code and never receives the `.tfstate`. |
| IAM | Role, user and policy creation is denied (verified 26 September 2026). Terraform references `LabInstanceProfile` and `LabRole` as data sources and contains no `aws_iam_*` resource. Every instance and job therefore runs as `LabRole`, so per-job IAM separation cannot be enforced. Least privilege is enforced elsewhere: separate database roles (runtime, migration, bootstrap, trainer), a separate secret per job so each container is handed only its own, security groups, S3 Block Public Access with a TLS-only policy, and no access keys anywhere. The policies we would attach are written as **reference JSON, never applied** (below). |
| Secrets | Four secrets `inf2006-grp21/{web,migration,trainer,bootstrap}`, containers created by Terraform with `recovery_window_in_days = 0`, values set by CLI so they never enter state (runbook, Procedures). |
| Object storage | One S3 bucket, prefixes `data/` and `exports/`; Block Public Access, versioning, SSE-S3, a deny-non-TLS policy, a 7-day noncurrent-version lifecycle. Created by CLI and looked up as a data source (lab constraint). Browsers never read from S3. |
| Images and 3D models | Static files in the app image served by WhiteNoise with hashed, cache-forever names; no S3 media, no CORS. S3 with pre-signed URLs and CloudFront was considered and not selected: for a small, fixed asset set it adds services and a CORS policy for no benefit at this scale. |
| Image registry | ECR, immutable tags (git SHA), scan on push; stacks run the image by **digest**. A deployed image also gets a `release-<sha>` tag and the lifecycle policy never expires the running image. |
| HTTPS | ACM certificate on the team-owned domain `fourtytwofactors.me`; DNS validation (Route 53 per section 3). |
| Audit | CloudTrail event history only (on by default, 90 days, free); nothing created. |
| Administration | Systems Manager Session Manager: no SSH, no inbound admin port, every session recorded in CloudTrail. |
| Batch operations | Explicitly triggered, by hand or script, on one designated compute unit: `db_bootstrap`, `migrate`, S3 sync and `import_dataset`, `refresh_analytics`, `clearsessions`. Scheduler (EventBridge plus SSM Run Command) is an optional side quest after the evidence runs. |
| WAF | One regional web ACL on each ALB with one rate-based rule on `POST /login/` (threat T7), Count mode first, then Block; no managed rule sets; the Locust source is exempted or the limit raised during scaling runs and that is recorded. |
| Network placement | App compute runs in the **public subnets with public IPs** (no NAT gateway, no paid endpoints): `sg-app` accepts only port 8000 from `sg-alb`, no port 22. RDS stays in the private subnets (`sg-db` accepts 5432 from `sg-app` only). The report states the trade-off; production would use private subnets with NAT or endpoints. |
| Not built | Lambda, CloudFront, NAT gateway, ElastiCache, EKS, ECS on EC2, a customer-managed KMS key, a separate analytics service. |
| State and credentials | One apply device (the user's Fedora laptop) holds the state and the lab credentials; apply only committed code (record the SHA); dated state backup after every apply; lab credentials expire, so an expired token mid-apply leaves a partial apply the next run completes. Remote state was considered and rejected: a committed backend block would make `terraform init` fail for anyone without the team's account, and the state bucket would have to outlive teardown. |

**RDS settings (both variants share one database).** PostgreSQL 17 (major pinned, auto minor upgrade on; record the actual minor); gp3 20 GB, encrypted with the AWS-managed key, no storage autoscaling; private subnet group across both AZs; `publicly_accessible = false`; `sg-db` only; parameter group with `rds.force_ssl = 1`; **no initial database** (bootstrap creates it owned by the migration login); master password managed by RDS in Secrets Manager (`manage_master_user_password`, never in state); 7-day automated backups; `skip_final_snapshot`, no deletion protection, `delete_automated_backups`; `apply_immediately`; PostgreSQL log exported to a 7-day log group that is created **before** the instance; Enhanced Monitoring off (needs an IAM role the lab cannot create); Multi-AZ off by default.

**Container environment (both variants).** `DJANGO_ENV=production`; `AWS_SECRET_ID=inf2006-grp21/web` and `AWS_REGION`; `APP_RELEASE_ID` (the image git SHA); `DJANGO_HEALTH_PROBE_HOST=<private-ip>:8000`; `DJANGO_ALLOWED_HOSTS` (the stack's hostname, never `*`) and a matching `DJANGO_CSRF_TRUSTED_ORIGINS`; `DJANGO_TRUST_PROXY` (`false` before an ALB, `true` behind it; on A it is baked into the launch template, so running instances keep the old value until an **instance refresh**, and `false` behind the ALB with `SECURE_SSL_REDIRECT` causes a redirect loop); `DJANGO_HSTS_SECONDS=3600`. None is secret. Gunicorn stays at the image's 2 workers in both variants (the backend is frozen, so the old `GUNICORN_WORKERS` change is dropped).

**Variant A boot behaviour (user data, `user_data.sh.tftpl`).** Install Docker with retries; read the private IP and instance ID through IMDSv2 (hop limit 2 so containers reach role credentials); log in to ECR with the instance role and pull the image by digest; write the non-secret settings to `/etc/inf2006/app.env`; write the `app-job` helper **before** starting the web container; start it with `--restart unless-stopped` and the `awslogs` driver. User data holds only secret **names**, never values.

**Reference IAM policies (docs only, not yet written).** Six JSON files in `src/infrastructure/iam-reference/` plus a README stating they are not applied (`terraform plan` must show no `aws_iam_*`): `web-runtime` (GetSecretValue on the web secret only, ECR pull, logs, SSM core), `migration` and `bootstrap` (their own secret only, ECR pull, logs), `maintenance` (web secret, `s3:GetObject` on `data/*` and `exports/*`), `batch-trainer` (trainer secret only, S3 read and exports write), `scheduler` (optional: `ssm:SendCommand` limited to `AWS-RunShellScript` on tagged instances). Each carries its trust policy; ARNs use placeholders. Cited from threat rows T8 and T9 as "Partial, lab constraint". Optional: validate with IAM Access Analyzer.

**Load harness.** Locust (k6 only if Locust cannot generate the load from one machine). Files `tests/load/locustfile.py` and a README with exact commands, pinned in its own requirements file, outside the app image. Workload fixed before any cloud run: anonymous browsing, a logged-in customer adds a size to the cart and checks out with its own idempotency key, a small operator share on `/analytics/`; synthetic accounts only. Rehearse locally against Docker first. Output: Locust CSV and failure files saved as `evidence/raw/RES-...`, summarised in `evidence/test-resilience.md`.

**Open items per step, still unchecked**
- [ ] Target-group health-check values (path, interval, thresholds, deregistration delay): set in [ADR-008](../decisions/ADR-008-alb-and-health-check-settings.md) as starting values; tune from the replacement test, they set the recovery times measured.
- [ ] Target-tracking value and cooldowns, alarm thresholds, WAF rate limit: set in [ADR-011](../decisions/ADR-011-target-tracking-on-request-count.md) and [ADR-012](../decisions/ADR-012-alarms-and-login-rate-limit.md) as starting values; tune from the local Locust rehearsal and the failure tests, and record the Locust exemption.
- [ ] Logs Insights: the queries are saved on variant A (ADR-012); run one and export the result (MON-02).
- [ ] Success thresholds fixed before running; each run mapped to its evidence ID (RES-03, MON-02, SEC-09 to SEC-11); the local RES-01, RES-02 and MON-01 cases run as a safety net.
- [ ] The reference IAM policies and the threat-row update (above).
- [x] A labelled architecture diagram is present at `evidence/architecture.png`, with reproducible source at `evidence/architecture.src.py`; final team approval and report insertion remain.
- [ ] A pre-destroy export checklist: Terraform outputs, redacted `describe` outputs, alarm history, CloudTrail events, Locust results, session costs.
- [ ] A cloud reproduction guide (tracked in the implementation tracker, Phase 4).

## 14. Document map (consolidated 1 October 2026)

The AWS documents are now **three files**: this plan (decisions, design, schedule), [AWS_INFRASTRUCTURE.md](../AWS_INFRASTRUCTURE.md) (the app and infrastructure contract) and [evidence/aws-build-runbook.md](../../evidence/aws-build-runbook.md) (procedures, lab capability record, as-built log). The old Terraform plans, stage guides and capability-check guide are in [docs/archive/](../archive/README.md). The AWS review logs under `docs/reviews/` stay as evidence of the review process.

Until the data is in, the primary architecture is undecided, so the contract documents get a banner now and one coordinated rewrite after the runs (schedule step 9).

| Document | State | Action | When |
|---|---|---|---|
| This plan | Governs AWS decisions and the sprint | none | n/a |
| [AWS_INFRASTRUCTURE.md](../AWS_INFRASTRUCTURE.md) | The runtime contract (secrets, environment, TLS, health) is still valid; the baseline and setup-order text describe variant A only | Banner added; status line, setup order and integration checklist corrected 3 October 2026; later generalise "ASG instance" to "compute unit" | after data |
| [ARCHITECTURE.md](../ARCHITECTURE.md) | Describes variant A only | Banner added; status line and archived links corrected 3 October 2026; rewrite for the primary architecture | after data |
| [PROBLEM_FRAMING_AND_ARCHITECTURE.md](../PROBLEM_FRAMING_AND_ARCHITECTURE.md) | Fargate rejected on D5 by argument, not measurement | Banner added; rewrite that paragraph and the matrix from the data | after data |
| [PROJECT_SCOPE_INF2006.md](../../PROJECT_SCOPE_INF2006.md) sections 3 and 7 | Name EC2 and ASG as the baseline cloud stack; the runbook records the measured USD 50 allocation | **Resolved 9 October:** the scope now records USD 50 per member while retaining the conservative USD 30 integration-account cap | complete |
| [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) | Status owner; rewritten 3 October 2026 around this comparison | Update as each step completes | continuous |
| [load-harness.md](load-harness.md) | Draft harness plan for the load runs | Answer its section 3, then implement | before step 7 |
| [submissions-plans.md](submissions-plans.md) | Parked submission plan | Start only once engineering is done | after data |
| [TESTING.md](../TESTING.md) signature demos | "Instance lost" wording is EC2-specific | Make it "instance or task" | with the harness |
| README.md | Check run and deploy statements | Check at the final sync | after data |

Known dangling reference: a string in `src/tools/aws_capability_check.py` still names the archived `cloud-independent-prep.md`. It is left alone because the backend is frozen and the text is only printed by a finished probe.
