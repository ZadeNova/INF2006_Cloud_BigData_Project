# AWS infrastructure in Terraform

Status (30 September 2026): **stages 0 and 1 are applied** to the user's Learner Lab account (38 resources managed; record in [evidence/aws-build-runbook.md](../../evidence/aws-build-runbook.md)). **Stage 2** (RDS and the first app instance) is written, has passed its independent review and is not applied ([stage 2 plan](aws-terraform-stage-2.md)). Stages 3 to 6 are not started. The application is not deployed. Review log: [reviews/aws-terraform.md](../reviews/aws-terraform.md).

Update 27 September 2026 (historical; the build began on 28 September 2026): The user decided on **public subnets for the app instances** (below), asked for **domain-purchase instructions** and added a **load-test tool** (Locust). The plan is complete for design and order but not yet buildable: each stage's missing decisions are listed under [Open items per stage](#open-items-per-stage-27-september-2026), and **agents must close or raise a stage's open items before writing or applying that stage**. Replaces the console-first order in [cloud-independent-prep.md](cloud-independent-prep.md) B7 and the "reproduce afterwards" framing of B5.

**How this is built.** The user has no Terraform experience and is learning it while building. Work goes one stage at a time, and **nothing starts until the user says so**. Each stage begins with a guide that explains the Terraform concepts that stage uses (starting from what Terraform is in stage 0), then lists explicit steps; the user runs `plan` and `apply` and approves every change.

Integration note (26 September 2026): Terraform-first sequencing and the teammate's lab observations are retained. The current scope and reviewed [runtime handoff](../AWS_INFRASTRUCTURE.md#image-and-infrastructure-owner-handoff) govern service selection and application startup: WAF remains selected; SSM, EventBridge Scheduler and Lambda are not selected. S3 media delivery was proposed and then dropped (29 September 2026; see the product images row below). Lab observations below are teammate-reported, not independently rerun during Git integration.

**Decisions revised by the user (26 September 2026), superseding the integration note where they differ:** Systems Manager Session Manager is reinstated for administration and one-off jobs; a scheduler is an optional side quest after stage 5; WAF stays, narrowed to one login rate rule; the user is the Terraform owner and the only person who runs `apply`. Details in the table below.

## Decisions recorded here

| Decision | Detail |
|---|---|
| **Build method (changed 25 September 2026)** | Terraform creates and owns every team resource. The console is for watching and learning (reading settings, logs, metrics, CloudTrail) and for the few steps Terraform cannot do: the ACM validation record at an external registrar, confirming the SNS email subscription, and reading the lab balance. Anything created by hand is imported into Terraform or deleted, so there is no drift. Replaces "console first, then reproduce in Terraform". |
| Region and account | `us-east-1`, AWS Academy Learner Lab (`voclabs` role); the lab offers no Singapore region. Two Availability Zones (the ALB requires at least two). **The user's own account is the one official account (confirmed 28 September 2026).** All evidence and the report describe this single deployment. **Documented lab constraint:** the story is a Singapore shop, so the report states the added latency for Singapore customers (measure it rather than assume), that production would use `ap-southeast-1` (a one-variable change in Terraform), and that the data is synthetic (PDPA's Transfer Limitation Obligation would otherwise apply to overseas storage). Analytics keeps Singapore business dates regardless. |
| Ownership | **The user writes the Terraform and is the single state owner and the only person who runs `apply`.** The application owner supplies the image and the runtime contract ([handoff](../AWS_INFRASTRUCTURE.md#image-and-infrastructure-owner-handoff)). |
| Groupmates' accounts (added 28 September 2026) | **Cold backups only, not concurrent capacity.** Each groupmate's own Learner Lab account is a fallback if the user's account runs out of budget mid-project. A fallback account starts a **fresh** `terraform apply` from the same versioned `.tf` code; it does not receive the user's `.tfstate` (a state file is meaningless in a different AWS account — different account ID, no matching resource IDs). No `.tfstate` is ever committed or transferred to a groupmate unless that handoff actually happens, and then only by direct private transfer, never through git. |
| IAM | **Role, user and policy creation is denied (verified 26 September 2026).** Terraform references `LabInstanceProfile` and `LabRole` through data sources and contains no `aws_iam_*` resources. Every instance and every job therefore runs as `LabRole`, so per-job IAM separation (web, migration, trainer, bootstrap) cannot be enforced at the IAM layer: any instance can read any team secret and the bucket. Least privilege is enforced where the lab allows it: separate database roles (runtime, migration, bootstrap), a separate secret per job so each container is only handed its own, security groups, S3 Block Public Access and TLS-only policy, no access keys anywhere. The intended per-job policies are written as reference JSON under `src/infrastructure/iam-reference/` (not applied) so the report can show the production design. Service roles needed by AWS itself (Auto Scaling's service-linked role, the scheduler's execution role) are checked in stage 1 and stage 'Optional'; RDS Enhanced Monitoring (needs its own role) is not used. |
| Database | RDS PostgreSQL pinned to **17.x** (the lab default is 18.3; the app, CI and all verification run on 17). Pick the newest 17 minor the lab offers. Single-AZ, private, encrypted, TLS forced. Master password managed by RDS in Secrets Manager (`manage_master_user_password`), so it never enters Terraform state. Stage 2 settings (29 September 2026): `db.t4g.micro` (fallback `db.t3.micro`), 20 GB gp3, no initial database, 7-day automated backups (free at this size; point-in-time restore, to be turned into evidence with a restore test in stage 5), `skip_final_snapshot`, PostgreSQL log exported to a 7-day log group. |
| Secrets | Terraform creates secret resources without values. Provision exact per-entrypoint schemas outside Terraform; the application startup loader retrieves its own secret using role credentials. Separate runtime, migration, trainer and bootstrap access as specified in the runtime handoff. Web instances must not read the master/bootstrap secret. Applied 29 September 2026 as four empty containers `inf2006-grp21/{web,migration,trainer,bootstrap}` with `recovery_window_in_days = 0`; values are set with the CLI, and generated passwords are never regenerated after `db_bootstrap`. |
| Object storage | **One S3 bucket**, prefixes `data/` (dataset) and `exports/` (analytics exports). Block Public Access, versioning, SSE-S3, a deny-non-TLS policy. Browsers never read from S3. **The bucket is created with the CLI and looked up as a data source (29 September 2026):** the Learner Lab's service control policy denies `s3:GetBucketObjectLockConfiguration`, which the `aws_s3_bucket` resource calls on every read; a probe of 16 bucket read calls showed it is the only one denied. Its settings stay Terraform resources; `terraform destroy` does not delete the bucket, so stage 6 empties and deletes it with the CLI. |
| Product images and 3D models (revised 29 September 2026) | **Static files in the app image, not S3; no CORS.** The `.glb` models (16 MB) and product images ship in `src/static/`, and WhiteNoise serves them with hashed file names and cache-forever headers, so each browser downloads a file once. Alternative considered: S3 with pre-signed URLs and a CORS rule. Not selected: for a small, fixed set of assets that change only with a release, it adds a service, per-request URL signing and a CORS policy with no benefit at this scale; the first request for each file still reaches the app instances, which is acceptable here. At catalogue scale, move them to S3 behind CloudFront. The CORS rule written in stage 1 was never created (it depended on `app_hostname`) and was removed before it could be. |
| Image registry | ECR, immutable tags (git SHA), scan on push. A deployed image also gets a `release-<git-sha>` tag (an extra tag on the same image) and `image_tag` points at it. The lifecycle policy keeps the 5 newest releases at the highest priority (a lower rule cannot expire an image matched by a higher one), deletes untagged images after 1 day and other builds after 30 days, so the running image is never deleted by count or age (stage 2 review, L8). |
| HTTPS | ACM certificate on a team-owned domain with DNS validation at the registrar. Certificate ARN is a variable, so everything else can be applied before the domain exists. A test certificate fallback requires confirmed import permission, hostname matching and explicit client trust; it is not guaranteed. |
| Audit | CloudTrail **event history** (on by default, 90 days, free). Nothing created; shown on the diagram and cited in the threat-control map. |
| Administration access | **Systems Manager Session Manager (reinstated 26 September 2026).** Admins and developers open a shell on an instance with no inbound ports, no SSH keys and no bastion; every session is recorded in CloudTrail. Used for debugging (container logs, connectivity) and for one-off jobs. Needs the SSM agent (preinstalled on Amazon Linux 2023) and SSM permissions on `LabInstanceProfile`, to be confirmed in stage 1. No port 22. |
| Batch operations | Explicitly triggered refresh, train, export, import and maintenance commands (`db_bootstrap`, `migrate`, S3 sync and `import_dataset`, `refresh_analytics`, `clearsessions`), run by hand through Session Manager on one designated instance, following the runbook and the role-separated secrets in the runtime handoff. |
| Scheduler | **Optional side quest, after stage 5.** EventBridge Scheduler invoking SSM Run Command on a tagged instance, if the lab accepts `LabRole` as the scheduler's role. Until then jobs are triggered by hand, which the scope allows. |
| WAF | **Selected, narrow.** One regional web ACL on the ALB with one rate-based rule on `POST /login/` (credential stuffing, threat T7), Count mode first, then Block. No managed rule sets. The Locust source is exempted or the limit raised during scaling runs, and that is recorded. Lab permission to be confirmed in stage 1. |
| Network placement (decided 27 September 2026) | **App instances run in the public subnets with public IPs**, so they reach ECR, Secrets Manager, SSM, S3 and CloudWatch Logs without a NAT gateway or paid interface endpoints. `sg-app` accepts only port 8000 from `sg-alb`; no other inbound rule, no port 22. RDS stays in the private subnets (`sg-db` accepts 5432 from `sg-app` only). A free S3 gateway endpoint is optional. The report states the trade-off: instances have public IPs but no reachable inbound port; production would use private subnets with NAT or endpoints. Record in threat rows T9/T11. |
| Not built | Lambda, CloudFront, NAT gateway, ElastiCache, EKS, a customer-managed KMS key (AWS-managed keys encrypt at rest), or a separate analytics service. EventBridge Scheduler only as the optional side quest above. |

## Layout

`src/infrastructure/` (decided 26 September 2026: the name already reserved by the runtime contract, excluded from the image by `src/.dockerignore` and checked by the ignore test in `tests/README.md`; it also holds the boot-script template and reference IAM policies, not only Terraform), one root module, one file per concern, no child modules (easier to read and learn):

```
versions.tf        provider and Terraform version pins
providers.tf       aws provider, locals.name_prefix = "inf2006-grp21", default_tags Project={name_prefix} Env=evidence ManagedBy=terraform
variables.tf       region, AZs, app hostname, alarm email, bucket name, image tag, instance type, DB class (later: certificate, scaling target)
data.tf            AL2023 AMI (public SSM parameter), LabInstanceProfile, ECR image digest, provider default tags
network.tf         VPC 10.0.0.0/16, 2 public + 2 private subnets, IGW, route tables
security_groups.tf sg-alb (443/80 from internet), sg-app (8000 from sg-alb), sg-db (5432 from sg-app)
storage.tf         S3 bucket (looked up) + settings + TLS policy, ECR repository + lifecycle
secrets.tf         Secrets Manager secret (value set outside Terraform)
database.tf        DB subnet group, parameter group (rds.force_ssl), RDS instance, 7-day PostgreSQL log group   (stage 2)
load_balancer.tf   ALB, target group (/health/), HTTPS listener, HTTP→HTTPS redirect   (stage 3)
compute.tf         launch template (IMDSv2 with hop limit 2, encrypted EBS), ASG: one instance in stage 2, ELB health in stage 3, target tracking in stage 4
user_data.sh.tftpl user data run at first boot (stage 2)
sql/               trainer login SQL, run once from the instance (stage 2)
terraform.tfvars.example   template for the git-ignored terraform.tfvars
monitoring.tf      log group (7-day retention), SNS topic + email, alarms, 5xx metric filter
waf.tf             regional WAF association and scoped rules, subject to plan review   (stage 4)
outputs.tf         ALB DNS name, ECR URL, bucket name, RDS endpoint
```

Names follow `inf2006-grp21-<component>` (`inf2006-grp21-alb`, `inf2006-grp21-db`, `inf2006-grp21-app-asg`), and the diagram uses the same names. The group number is a single `local.name_prefix` in `providers.tf`, not retyped per resource.

**State.** Local state, never committed (`.gitignore` gains `*.tfstate*`, `*.tfplan`, `.terraform.lock.hcl` is committed). The scope forbids submitting state with secrets, and the design above keeps secret values out of it anyway. **Remote state considered and not chosen (30 September 2026).** An S3 backend is the production practice (versioning, locking, no single laptop), but here a committed backend block would make `terraform init` fail for a reviewer or teammate without the team's account, which conflicts with the brief's requirement that the project be runnable without a cloud login, and the state bucket would have to outlive teardown. The custody rules below cover laptop loss; the report states the trade-off. Local state sits in `src/infrastructure/`, so the submission ZIP is built from git (`git archive`), never by copying the folder.

**One apply device (revised 28 September 2026, replaces moving state between devices).** The user's Fedora laptop is the only device that runs `plan`, `apply` and `destroy`, holds `terraform.tfstate` and has lab credentials exported. The user's other devices only write code (plus `fmt` and `validate` after `terraform init -backend=false`, which needs no AWS credentials). Code moves through git; state never leaves the laptop. Rules:
1. Apply only committed code: `git pull`, a clean working tree, `plan -out`, then `apply`. Record the commit SHA in the runbook entry.
2. After every apply, copy the state to a dated backup (`terraform.tfstate.<YYYY-MM-DD>.bak`) in a private location off the laptop, never git. If the state is lost, the `Project=inf2006-grp21` tags are the fallback for finding and deleting resources by hand.
3. Commit `.terraform.lock.hcl` so every device resolves the same provider versions.
4. If the laptop is unavailable, no other device applies. A groupmate's fallback account starts a fresh stack from the code (see above).

**Credentials.** The Learner Lab issues temporary credentials (from "AWS Details") that expire with the session. Export them before each `plan` or `apply`; an expired token mid-apply leaves a partial apply that the next run completes.

## User data (what every instance does at first boot)

Implemented in `src/infrastructure/user_data.sh.tftpl` (stage 2; independent review 29 September 2026). The launch template passes it as the instance's user data; cloud-init runs it once, as root. It holds only secret **names**, never values, because anyone who can read the launch template can read it.

1. Install Docker (with retries). Read the private IP and instance ID through **IMDSv2** (`curl -f`, retried).
2. Log in to ECR with the instance role and pull the image **by digest** (resolved from `image_tag` by `data.aws_ecr_image`), so every instance runs the same bytes.
3. Write the non-secret settings to `/etc/inf2006/app.env`: `DJANGO_ENV`, `AWS_REGION`, `APP_RELEASE_ID`, `DJANGO_ALLOWED_HOSTS` and the CSRF origin from `app_hostname`, `DJANGO_HEALTH_PROBE_HOST=<private-ip>:8000`, `DJANGO_TRUST_PROXY`, `DJANGO_HSTS_SECONDS`. The web container gets `AWS_SECRET_ID=inf2006-grp21/web`; the existing startup loader retrieves its own secret with the role. The RDS master secret is never read here.
4. Write the `/usr/local/bin/app-job` helper **before** starting the web container: `sudo /usr/local/bin/app-job web|migration|bootstrap <command>` runs a throwaway container that holds only that job's secret name.
5. Start the web container (retried) with `--restart unless-stopped` and the `awslogs` driver into `/inf2006-grp21/app`. Until the database is bootstrapped and migrated it fails at startup and restarts; that is expected in stage 2 (no ALB, so nothing replaces the instance).

`DJANGO_TRUST_PROXY` is `false` in stage 2 and becomes `true` in stage 3 behind the ALB; it is baked into the launch template, so running instances keep the old value until an **instance refresh**. The launch template requires IMDSv2 with **hop limit 2** so containers can reach the role credentials. Administration is through Systems Manager Session Manager; no SSH key and no port 22.

One-off operations run by hand through Session Manager on the ASG instance, not on every ASG boot: `db_bootstrap`, coordinated `migrate`, the trainer-login SQL (stage 2), then S3 dataset sync and `import_dataset` (stage 3). Use the separate secret schemas and commands in the [stage 2 plan](aws-terraform-stage-2.md) and the runtime handoff.

## Stages

Each stage: `fmt`, `validate`, `plan` saved to a file, the plan read aloud (creations, replacements, deletions, public exposure, IAM, NAT, Multi-AZ, cost), the user approves, `apply`, then an acceptance check and an entry in `evidence/aws-build-runbook.md` (settings, redacted `describe` output, time, cost). A successful apply is not evidence; the acceptance check is.

| Stage | Creates | Acceptance | Rough cost while up |
|---|---|---|---|
| 0 | Nothing: install Terraform, `init`, provider pins | `terraform version`, `validate` | none |
| 1 | Network, security groups, S3, ECR, secret, log group, SNS | Subnets in 2 AZs; S3 public access blocked; push the image to ECR | near zero |
| 2 | RDS, launch template, ASG (one instance, EC2 health checks) | RDS private, encrypted, 17.x, TLS forced, 7-day backups; the instance registers in Session Manager and runs the image by digest with logs in CloudWatch; `db_bootstrap`, `migrate` and the trainer SQL succeed; the runtime login cannot create tables and the trainer cannot write or read sessions. Plan: [aws-terraform-stage-2.md](aws-terraform-stage-2.md) | about USD 0.045/hour (RDS, t3.small, public IPv4) |
| 3 | ACM certificate, ALB, target group, listeners; ASG health check to ELB; `trust_proxy` true with an instance refresh | `https://shop.fourtytwofactors.me/health/` returns 200; HTTP redirects; dataset import from S3; the shop loads | about USD 0.10/hour total (adds the ALB and its IPv4 addresses) |
| 4 | Target tracking, max 2, alarms, WAF | Alarm email received; scoped WAF rules verified; explicit batch run verified | verify selected services against current pricing |
| 5 | Evidence runs: baseline, autoscaling, session continuity, batch failure/retry recovery | Evidence files per the scope | same |
| Optional | EventBridge Scheduler plus SSM Run Command for `refresh_analytics` and `clearsessions` | A scheduled run appears in the analytics run list | small |
| 6 | `terraform destroy` | Nothing tagged `Project=inf2006-grp21` remains; final balance recorded | none |

Costs are rough on-demand estimates; check them against the AWS pricing pages and the lab balance after each stage. Destroy between working sessions if the stack will sit idle for a day.

## Things this depends on

- **A domain** for stage 3. The user is buying one from an external registrar (cheaper than Route 53, and DNS stays outside the lab account, so it survives teardown). The purchase and DNS steps (buy, add ACM's validation CNAME, point `shop.<domain>` at the ALB) are explained in the stage 3 guide. Buying it before stage 3 is fine; nothing else needs it.
- **Application changes** before stage 3, backend-owned and through the review gate: configurable Gunicorn workers (`GUNICORN_WORKERS`, currently hardcoded 2 in the Dockerfile). The S3 media storage change (`django-storages`, pre-signed URLs) was dropped on 29 September 2026: images and models stay static files served by WhiteNoise.
- **Stage-1 lab checks:** secret creation and retrieval with `LabInstanceProfile`; Session Manager access to an instance; budget and WAF permissions. Record actual results; listing APIs does not establish creation permission.

## Reference IAM policies (planned 26 September 2026; written in stage 1, never applied)

**Why.** The lab denies IAM role, user and policy creation, so every job runs as `LabRole` and per-job least privilege cannot be enforced (see the IAM row above). The brief grades "least privilege" explicitly. Writing the policies we *would* attach in production shows the design was done and the limit is the platform's, not ours. About an hour; high return for the Security criterion.

**Where.** `src/infrastructure/iam-reference/`, one JSON file per role plus a short `README.md`. These files are documentation: Terraform does not read them, `terraform plan` must show no `aws_iam_*` resources, and the README says so in its first line.

| File | Production role for | Allows (scoped to named resources, no `*` actions) |
|---|---|---|
| `web-runtime.json` | Web instances in the Auto Scaling group | `secretsmanager:GetSecretValue` on the **web runtime secret only**; `ecr:GetAuthorizationToken` plus pull actions on the `inf2006-grp21-app` repository; `logs:CreateLogStream`/`PutLogEvents` on the app log group; the AWS-managed `AmazonSSMManagedInstanceCore` for Session Manager |
| `migration.json` | The one-off migration run | `GetSecretValue` on the **migration secret only**; ECR pull; logs. No S3 |
| `bootstrap.json` | The one-off `db_bootstrap` run | `GetSecretValue` on the **bootstrap secret only**; ECR pull; logs. Nothing else |
| `maintenance.json` | One-off Django commands: `import_dataset`, `refresh_analytics`, `load_customer_segments`, `clearsessions` | `GetSecretValue` on the **web runtime secret** (these are Django management commands, per the runtime handoff); `s3:GetObject` on `data/*` and `exports/*`; logs |
| `batch-trainer.json` | Standalone training and the refresh verifier | `GetSecretValue` on the **trainer/verifier secret only** (no Django signing key); `s3:GetObject` on `data/*`; `s3:GetObject`/`PutObject` on `exports/*`; logs |
| `scheduler.json` (optional side quest) | EventBridge Scheduler's execution role | `ssm:SendCommand` limited to the `AWS-RunShellScript` document and instances tagged `Project=inf2006-grp21` |

Each file also carries its trust policy (who may assume the role: `ec2.amazonaws.com`, or `scheduler.amazonaws.com` for the scheduler). Secret and bucket ARNs are written with placeholders (`<account>`, `<region>`), which also satisfies the redaction rule.

**How it is used as evidence.**
- Threat-control map: rows T8 and T9 (secrets, database and storage access) show status "Partial, lab constraint", citing these files as the intended control and listing what *is* enforced (separate database roles, a separate secret per job, security groups, S3 Block Public Access and TLS-only policy, no access keys).
- Report §4: one paragraph, "designed per-job roles; the lab permits only `LabRole`; here is what enforces least privilege instead".
- Validation (cheap and optional): run each file through IAM Access Analyzer's policy validation (`aws accessanalyzer validate-policy`) if the lab allows it, and record the output next to the files. A policy that validates cleanly is stronger evidence than one that only looks right.

**Acceptance.** Six JSON files that parse; a README stating they are not applied and why; no `aws_iam_*` resource in any plan; the threat-map rows cite them.

## Review

Terraform is team infrastructure configuration. Each stage's code is self-reviewed, and before the first apply of stages 1 to 3 the configuration goes to the review gate (fresh-session Opus 5.5 or Astra Medium), findings logged in `docs/reviews/aws-terraform.md`. No apply without the user's explicit approval.

## Diagram

Drawn from this plan's resource list before stage 1, with these names; renamed only if a name changes during the build. Source `evidence/architecture.drawio`, export `evidence/architecture.png`.

## Domain purchase (stage 3 prerequisite, instructions added 27 September 2026)

**Done 29 September 2026:** the team bought `fourtytwofactors.me` from Namecheap through the GitHub Student Developer Pack (first year free), rather than the Porkbun recommendation below; the shop is `shop.fourtytwofactors.me` and DNS stays at Namecheap. The steps below apply unchanged.

HTTPS on the ALB needs an ACM certificate, and ACM needs a domain you control. Buy it **before stage 3**; nothing earlier depends on it. Keep DNS at the registrar (not Route 53), so it survives `terraform destroy` and costs nothing extra.

**Where to buy.** Check prices on the day; first-year prices differ from renewal prices. **Recommendation (28 September 2026): Porkbun, a low-cost TLD (`.xyz`, `.site`, `.online`).** Instant registration (no verification wait), first-year price is the only price that matters for a two-week project, and its own DNS panel handles the CNAME records with no extra step.

| Option | Notes |
|---|---|
| **Porkbun or Namecheap (recommended)** | Cheap first-year TLDs (for example `.xyz`, `.site`, `.store`, often a few USD). Simple DNS editor with CNAME records, no nameserver migration needed. |
| GitHub Student Developer Pack | Has included a free first-year domain from a partner registrar (for example Namecheap `.me` or name.com). Only worth it if already verified for the pack from something else — new enrollment verification can take minutes to a couple of days, a risk not worth taking against the deadline just to save a few dollars. |
| Cloudflare Registrar (not recommended here) | At-cost pricing, but DNS must move to Cloudflare, and it is an easy footgun: a record left **proxied (orange cloud)** instead of **DNS only (grey cloud)** silently breaks ACM validation and the ALB CNAME. |

Pick a neutral name (not a real brand). Payment needs a card; decide who pays and record it in the cost section.

**Steps.**
1. Buy the domain; turn on the registrar's free WHOIS privacy.
2. Stage 3 (Terraform): request an ACM certificate for `shop.<domain>` with DNS validation. Terraform outputs the validation CNAME name and value.
3. At the registrar, add that CNAME exactly as given (some registrars append the domain automatically; do not add it twice). Wait for ACM status `Issued` (minutes to an hour).
4. After the ALB exists, add a CNAME `shop` pointing to the ALB DNS name. Use the subdomain, because the bare domain cannot be a CNAME at most registrars.
5. Check: `https://shop.<domain>/health/` returns 200 and `http://` redirects to `https://`.
6. After teardown, delete the `shop` CNAME; the validation CNAME can stay.

**Fallback if the domain is late:** build stages 0 to 2 and the ALB with only an HTTP listener, then add HTTPS when the certificate is issued. Do not claim HTTPS (SEC-10) until it works; a self-signed import is not assumed to be allowed.

## Load testing (added 27 September 2026)

**Tool: Locust** (Python, already named in [TESTING.md](../TESTING.md) and the scope; it handles Django login and CSRF in the same language as the app). k6 is the considered alternative (lower overhead per virtual user, JavaScript scripts); switch only if Locust cannot generate the needed load from one machine, and record the reason.

- **Location:** `tests/load/locustfile.py` plus a README with exact commands; pinned version in its own requirements file, not in the app image.
- **Workload (fixed before any cloud run, reused for every run):** anonymous browsing (catalogue and detail pages); a logged-in customer adds a size to the cart, views the cart and checks out with its own idempotency key; a small operator share on `/analytics/`. Synthetic accounts created by a setup command, never real data.
- **Run from outside the app instances:** the laptop (records Singapore to `us-east-1` latency) or a separate small instance; state which, and keep it the same for comparable runs.
- **Rehearse locally first** against Docker to find a supported load and fix script bugs for free.
- **Output:** Locust CSV stats and failures saved as `evidence/raw/RES-...` text files, summarised in `evidence/test-resilience.md`.

## Open items per stage (27 September 2026)

Missing decisions or artefacts. An agent working on a stage must resolve these (or ask the user) before writing or applying it, and tick them off here.

**Stage 0: tooling** (guide: [aws-terraform-stage-0.md](aws-terraform-stage-0.md))
- [x] Update the status line once Terraform is installed and `validate` passes (28 September 2026: Terraform 1.16.4, AWS provider 6.66.0 locked, `fmt` and `validate` pass; lock records `linux_amd64`, `windows_amd64`, `darwin_arm64` and `darwin_amd64` for the team's Fedora, Mint, Windows 11 and Mac devices).

**Stage 1: network, S3, ECR, secrets, logs, SNS**
- [x] Instance placement without NAT: public subnets (decided above).
- [x] Confirm each secret's exact field list against the runtime handoff (done; the migration secret also needs `DJANGO_SECRET_KEY`, found in stage 2 planning).
- [x] Write the image build, tag (git SHA) and push commands for ECR (done 29 September 2026: `inf2006-grp21-app:c19d547` pushed; commands in the runbook).
- [x] Run the lab checks (secret retrieval with `LabInstanceProfile`, Session Manager, WAF, budget) and record the results (29 September 2026: all allowed, see `evidence/aws-capability-record.md`).
- [ ] Write the reference IAM policies; then update threat rows T8/T9 in `evidence/threat-control-map.md` to "Partial, lab constraint", citing them.
- [ ] Draw `evidence/architecture.drawio` / `.png` with the `inf2006-grp21-*` names (the brief requires it; this plan says before stage 1).

**Stage 2: RDS and the first instance** (open items and decisions are in [aws-terraform-stage-2.md](aws-terraform-stage-2.md))
- [x] Parameter group `rds.force_ssl = 1`; backups 7 days; `skip_final_snapshot` (decided 29 September 2026).
- [x] Where `db_bootstrap` runs: the ASG instance, moved from stage 3 into stage 2.
- [ ] Apply, run the one-off jobs and record the acceptance checks in the runbook.

**Stage 3: HTTPS, ALB, launch template, ASG**
- [x] Domain bought (`fourtytwofactors.me`, Namecheap, GitHub Student Developer Pack, 29 September 2026); DNS stays at Namecheap. In Namecheap's Advanced DNS the **Host** field must not include the domain (enter `_abc123.shop`, not `_abc123.shop.fourtytwofactors.me`), or the certificate stays pending.
- [ ] Application change first, through the review gate: configurable `GUNICORN_WORKERS` (currently hard-coded to 2 in the Dockerfile).
- [x] User data written (`user_data.sh.tftpl`, stage 2): Docker, ECR login, image digest, environment file, `awslogs`, probe host from IMDSv2.
- [ ] Target-group health check values (path, interval, healthy/unhealthy thresholds, deregistration delay); they set the recovery times measured in stage 5.
- [ ] `trust_proxy` becomes `"true"` in `compute.tf` (from the stage 2 review). It is baked into the launch template, so running instances keep `false` until an **instance refresh**; behind the ALB, `false` with `SECURE_SSL_REDIRECT` sends every request into a redirect loop. Refresh the ASG as part of the stage 3 apply, and switch the ASG to ELB health checks in the same change.

**Stage 4: scaling, alarms, WAF**
- [ ] Target-tracking value (ALB requests per target) and cooldowns, chosen from the local Locust rehearsal.
- [ ] Alarm thresholds and periods (ALB 5xx, unhealthy hosts).
- [ ] One saved CloudWatch Logs Insights query and its exported result (the Operations "alert/query" evidence, MON-02).
- [ ] WAF rate limit value and how the Locust source is exempted during scaling runs.

**Stage 5: evidence runs**
- [ ] Locust workload written and rehearsed locally (section above).
- [ ] Success thresholds fixed before running (for example p95 latency and error rate at N users; time back to two healthy targets).
- [ ] Map each run to its evidence ID and file (RES-03 in `test-resilience.md`, MON-02 in `monitoring.md`, SEC-09..11 in `test-security.md`).
- [ ] Run the local RES-01/RES-02 and MON-01 cases as a safety net (no AWS needed).

**Stage 6: teardown**
- [ ] Pre-destroy export checklist: Terraform plan/outputs, redacted `describe` outputs, alarm history, CloudTrail events, Locust results, session costs.

**Across all stages**
- [ ] Reproducibility check after each stage: could someone repeat it from the docs alone? Cloud reproduction guide `docs/REPRODUCE_CLOUD.md` and the ZIP-from-git rule are tracked under Phase 4 in the [tracker](../IMPLEMENTATION_PLAN.md).
- [ ] Session budget: number of cloud sessions, total estimated cost against the lab balance, and what to cut if it runs low.
- [ ] Dates for each stage between now and the 11 October deadline (the scope's Phase 3 window ends 1 October).
