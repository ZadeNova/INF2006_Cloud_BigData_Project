# AWS infrastructure: how to run it

Terraform and scripts that deploy 42Factors to AWS (Learner Lab, `us-east-1`). Decisions are in [docs/decisions/](../../docs/decisions/) (ADR-001 to ADR-012), the plan in [aws-ecs-comparison.md](../../docs/plans/aws-ecs-comparison.md), and what was actually applied, with dates and results, in [evidence/aws-build-runbook.md](../../evidence/aws-build-runbook.md).

**Status (1 October 2026).** `base/` is applied. **Variant A (`ec2/`) is applied and verified**: `https://shop-ec2.fourtytwofactors.me` serves the shop over HTTPS, with the dataset imported, the operator account created, the analytics refreshed, scaling, alarms and the WAF in place, and `smoke.sh` passing 8 of 8. Variant B (`fargate/`) is not written yet. Between work sessions the `ec2` stack is torn down to save money; `base/` stays up.

## Contents

1. [Layout](#layout)
2. [Rules](#rules)
3. [Tools and credentials](#tools-and-credentials)
4. [Bring variant A up (the usual case)](#bring-variant-a-up-the-usual-case)
5. [Take variant A down](#take-variant-a-down)
6. [If you are not on the apply laptop](#if-you-are-not-on-the-apply-laptop)
7. [Build everything from nothing in a new account](#build-everything-from-nothing-in-a-new-account)
8. [Command reference](#command-reference)
9. [Cost](#cost)
10. [Troubleshooting](#troubleshooting)
11. [Final teardown](#final-teardown)
12. [What comes next](#what-comes-next)

## Layout

| Folder | What it owns | State |
|---|---|---|
| `base/` | VPC, subnets, `sg-db`, Route 53 zone, ACM certificate, RDS PostgreSQL 17, ECR, S3 bucket settings, the five secrets, SNS alarm topic. Stays up between experiments | `base/terraform.tfstate` |
| `ec2/` | Variant A: its own `sg-alb` and `sg-app`, ALB with HTTPS, launch template, Auto Scaling group (1 to 2 instances), scaling policy, alarms, saved log queries, WAF, alias record `shop-ec2.fourtytwofactors.me`, log group | `ec2/terraform.tfstate` |
| `fargate/` | Variant B (not written yet) | |
| `scripts/` | The commands below | |
| `sql/` | The trainer login's two SQL files (run by `jobs.sh trainer-sql`) | |

`ec2/` reads `base/` through `terraform_remote_state` (`../base/terraform.tfstate`); `base/` never reads a stack, so a stack can be destroyed without touching the database.

**Do not run Terraform in `src/infrastructure/` itself.** The `.tf` files directly in this folder are the superseded single-folder version from stages 1 and 2; their resources were moved into `base/` on 1 October 2026 (`scripts/migrate-state.sh`, one-time, done). They are kept until a cleanup commit removes them.

## Rules

1. **One apply device.** The owner's Fedora laptop holds the state files and is the only machine that runs `plan`, `apply` or `destroy`. Other devices write and review code through git. Never create a second state for the same resources.
2. **Apply only committed code.** `scripts/tf.sh` refuses a dirty tree and refuses a plan made from another commit.
3. **Never commit** `*.tfstate*`, `*.tfvars` (except `*.tfvars.example`), `*.tfplan` or secret values. They are git-ignored; keep it that way.
4. **Back up state after every apply.** `tf.sh apply` writes `terraform.tfstate.<date>.<commit>.bak`; copy it off the laptop (USB or a private drive, never git).
5. **Read every plan before applying it.** Anything replaced or destroyed that you did not expect: stop.
6. **Tear the stack down when you stop for the day** ([cost](#cost)).

## Tools and credentials

Installed on the apply laptop (versions used):

| Tool | Version | Used for |
|---|---|---|
| Terraform | 1.16.4 (needs 1.10 or newer) | everything in `base/` and `ec2/` |
| AWS CLI v2 | 2.37 | every script |
| Session Manager plugin | 1.2 | `aws ssm start-session` (manual debugging only) |
| `jq`, `openssl`, `curl`, `git`, `python3` | any recent | scripts |
| Docker | any recent | building the app image (`push-image.sh`) |

**Lab credentials** expire after about 4 hours and every script checks them first. In the Learner Lab: Start Lab, then AWS Details, then Show next to AWS CLI. Add this function to `~/.bashrc` once, then run `labcreds` in each new terminal and paste the block, followed by an empty line:

```bash
labcreds() {
  echo "Paste the AWS Details 'aws_access_key_id=...' block, then press Enter on an empty line:"
  local line
  while IFS= read -r line && [ -n "$line" ]; do
    case "$line" in
      aws_access_key_id=*)     export AWS_ACCESS_KEY_ID="${line#aws_access_key_id=}" ;;
      aws_secret_access_key=*) export AWS_SECRET_ACCESS_KEY="${line#aws_secret_access_key=}" ;;
      aws_session_token=*)     export AWS_SESSION_TOKEN="${line#aws_session_token=}" ;;
    esac
  done
  export AWS_DEFAULT_REGION=us-east-1
  aws sts get-caller-identity
}
```

It prints your account and an `assumed-role/voclabs/...` ARN when it worked. Do not screenshot or paste these credentials anywhere.

All commands below run from the **repository root**.

## Bring variant A up (the usual case)

On the apply laptop, with `base/` already applied (it is):

```bash
labcreds
src/infrastructure/scripts/up.sh ec2
```

What happens:

1. `tf.sh ec2 plan` prints the plan. **Read it.** After a teardown it should be 25 to add, 0 to change, 0 to destroy (security groups, ALB, listeners, target group, launch template, ASG, scaling policy, 3 alarms, 2 queries, WAF and its association, alias record, log group). Type `yes`.
2. `tf.sh ec2 apply` builds it (about 3 to 5 minutes, mostly the ALB) and backs up the state.
3. `secrets.sh fill` adds any missing secret field; it never changes an existing password.
4. `jobs.sh ec2 all` runs every database job in order on the new instance through SSM. On the existing database each one finds its work already done and changes nothing (the import reports `created=0 unchanged=...`). This takes a few minutes; it waits for the instance to register with Systems Manager first.
5. `smoke.sh ec2` checks the site from outside. Expect `All checks passed.` (8 of 8).

The shop is then at **https://shop-ec2.fourtytwofactors.me**. The hostname follows the new load balancer automatically.

Faster, when you know the database is intact (skips step 4): `scripts/tf.sh ec2 plan`, `scripts/tf.sh ec2 apply`, `scripts/smoke.sh ec2`.

**Operator login** (`demo-operator`, for `/analytics/`):

```bash
aws secretsmanager get-secret-value --secret-id inf2006-grp21/operator --query SecretString --output text
```

**Prerequisites `up.sh` checks:** `base/` applied; `src/infrastructure/ec2/image.auto.tfvars` present (written by `push-image.sh`; it stays on the laptop between sessions, currently `image_tag = "release-c19d547"`); a clean committed tree; working credentials.

## Take variant A down

```bash
labcreds
src/infrastructure/scripts/down.sh ec2
```

Terraform lists everything it will destroy; type `yes`. The script then prints leftover load balancers, instances and NAT gateways; all three lists must be empty. The database, its data, the zone, the certificate, the image and the secrets stay ([cost](#cost)).

## If you are not on the apply laptop

You cannot plan or apply against the team's stack: the state is on the owner's laptop, and a second state would fight over the same resources. You can:

- **Write and check code:** `terraform -chdir=src/infrastructure/ec2 init -backend=false` then `terraform -chdir=src/infrastructure/ec2 validate` (no credentials needed), commit, and ask the owner to plan and apply.
- **Check the live site** (no credentials needed): `src/infrastructure/scripts/smoke.sh shop-ec2.fourtytwofactors.me`.
- **Read the record:** [evidence/aws-build-runbook.md](../../evidence/aws-build-runbook.md).

If the apply laptop is lost or unavailable, use the next section in your own Learner Lab account; never copy the owner's state to another machine.

## Build everything from nothing in a new account

For a teammate's cold-backup account, or to reproduce the build. About 45 minutes, most of it waiting. Everything is created fresh; nothing is shared with the team's account.

**Domain caveat.** `fourtytwofactors.me` can be delegated to only one Route 53 zone at a time. A new account creates a new zone with different name servers; pointing Namecheap at it moves the domain away from the team's account. Agree this with the domain owner first, or set `domain_name` in `base/terraform.tfvars` to another domain you control.

1. **Credentials and a clean clone**
   ```bash
   labcreds
   git clone <repo-url> && cd <repo> && git checkout <branch>
   ```

2. **Create the S3 bucket with the CLI** (the lab denies one read the Terraform bucket resource needs; Terraform then manages all its settings):
   ```bash
   B="inf2006-grp21-data-$(openssl rand -hex 8)"
   aws s3api create-bucket --bucket "$B" --region us-east-1
   aws s3api put-bucket-tagging --bucket "$B" --tagging \
     'TagSet=[{Key=Name,Value=inf2006-grp21-data},{Key=Project,Value=inf2006-grp21},{Key=Env,Value=evidence},{Key=ManagedBy,Value=cli}]'
   ```

3. **Fill in `base/terraform.tfvars`** (git-ignored):
   ```bash
   cp src/infrastructure/base/terraform.tfvars.example src/infrastructure/base/terraform.tfvars
   ```
   Set `alarm_email` (you will get a confirmation email) and `s3_bucket_name = "<the $B from step 2>"`. Add `domain_name = "..."` only if not using `fourtytwofactors.me`.

4. **Apply `base/`** (RDS takes about 9 minutes; the certificate waits for DNS):
   ```bash
   src/infrastructure/scripts/tf.sh base plan      # expect 38 to add, 0 to change, 0 to destroy
   src/infrastructure/scripts/tf.sh base apply
   ```
   While it waits on `aws_acm_certificate_validation.shop`, get the zone's name servers in a second terminal and set them at the registrar (Namecheap: Domain List, Manage, Nameservers, Custom DNS, enter the four, click the green tick):
   ```bash
   aws route53 get-hosted-zone --id "$(aws route53 list-hosted-zones-by-name --dns-name <domain> --query 'HostedZones[0].Id' --output text)" \
     --query 'DelegationSet.NameServers' --output text
   ```
   Check delegation with `dig NS <domain> @a0.nic.me +norec | grep -A8 'AUTHORITY SECTION'`. Once it shows the AWS servers, the certificate issues within minutes and the apply finishes. **Click the SNS confirmation link** in the email (check spam).

5. **Build and push the image, and choose it for the stack:**
   ```bash
   src/infrastructure/scripts/push-image.sh
   ```
   It builds `src/Dockerfile` at the current commit, pushes it, adds the protected `release-<sha>` tag, prints the digest and writes `ec2/image.auto.tfvars`. The recorded evidence used `c19d547` (digest `sha256:fa72e949...cb481`); the application code is unchanged since then, but a rebuild has a different digest, so record yours.

6. **Fill the secrets** (random passwords, generated once, never printed):
   ```bash
   src/infrastructure/scripts/secrets.sh fill       # expect four "match" lines
   ```

7. **Bring variant A up**, which also bootstraps the database, migrates, creates the trainer login, imports the dataset (built from `data/raw/` and checked against `data/derived/shoes/checksums.txt`), creates the operator and refreshes the analytics:
   ```bash
   src/infrastructure/scripts/up.sh ec2
   ```

## Command reference

| Command | Does | When |
|---|---|---|
| `scripts/tf.sh <base\|ec2> plan` | fmt check, validate, saved plan, records the commit | before every apply |
| `scripts/tf.sh <base\|ec2> apply` | applies that saved plan only, then backs up the state | after reading the plan |
| `scripts/up.sh ec2` | plan, confirm, apply, secrets, all jobs, smoke | start of a session |
| `scripts/down.sh ec2` | destroy the stack, list leftovers | end of a session |
| `scripts/smoke.sh ec2` (or a hostname) | 8 outside-in checks, no credentials needed | after any change |
| `scripts/jobs.sh ec2 <job>` | one job on the instance through SSM: `bootstrap`, `migrate`, `trainer-sql`, `restart`, `check`, `import`, `operator`, `refresh`, `all` | fresh database; `check` any time |
| `scripts/secrets.sh fill\|check` | complete or check the secrets (prints key names and match/DIFFER only) | once; `check` any time |
| `scripts/secrets.sh master-in\|master-out` | used by `jobs.sh bootstrap`; do not run by hand | |
| `scripts/push-image.sh [sha]` | build (only if the tag is missing), push, release-tag, record the digest | per image change |

All scripts are under `src/infrastructure/scripts/`, stop at the first error, and need `labcreds` except `smoke.sh`.

**Manual access to the instance** (debugging only; no SSH, no port 22):
```bash
INSTANCE=$(aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names inf2006-grp21-ec2-asg \
  --query "AutoScalingGroups[0].Instances[0].InstanceId" --output text)
aws ssm start-session --target "$INSTANCE"
sudo docker logs --tail 50 web          # the app
sudo cat /var/log/cloud-init-output.log # the boot script
```

## Cost

US East list prices, rounded; verify before relying on them. Read the lab balance (Learner Lab page) at the start and end of each session.

| Running | About |
|---|---|
| `base/` only (RDS `db.t4g.small` and storage, secrets, zone) | USD 1.2 per day |
| plus the `ec2` stack (one `c5.large`, ALB, 3 public IPv4 addresses, WAF) | plus USD 0.13 per hour, about USD 3 per day |
| a second instance while scaled out | plus USD 0.085 per hour |

Everything running continuously is about USD 4 per day; the lab budget is USD 50. **Tear the stack down when you stop** and keep `base/` up: rebuilding the stack takes about 5 minutes, rebuilding `base/` means re-bootstrapping and re-importing.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `no working lab credentials`, `ExpiredToken`, `InvalidToken` | Credentials expired. `labcreds` again |
| `uncommitted changes in src/infrastructure; commit first` | `tf.sh` only applies committed code. Commit (or stash), then plan again |
| `the plan was made from commit X, HEAD is Y` | You committed after planning. Plan again |
| A plan shows a replace (`-/+`) or destroy you did not expect | Stop and ask; do not apply |
| `jobs.sh`: `is not Online in Systems Manager` | The instance is still booting (about 3 to 4 minutes after launch). Rerun |
| Target unhealthy, site returns 502/503 | Start a session (above) and read `docker logs web` and the cloud-init log |
| `smoke.sh`: `/products/ lists 0 product links` | The database has no data. `scripts/jobs.sh ec2 import` |
| `app-job: usage: ...` | Job name mistyped; it is `bootstrap`, not `boostrap` |
| A security group rule fails with `Invalid rule description` | AWS rejects some characters (an apostrophe, for one) in descriptions |

More history: the "Problems met" lists in the [build runbook](../../evidence/aws-build-runbook.md).

## Final teardown

Only after all evidence is exported (plan section 13: pre-destroy export checklist). In this order:

```bash
src/infrastructure/scripts/down.sh ec2
terraform -chdir=src/infrastructure/base destroy        # database, zone, certificate, registry, secrets
# The bucket is not Terraform's: empty every object version, then delete it.
B=<bucket name>
aws s3api list-object-versions --bucket "$B" --output json \
  | jq '{Objects: ([.Versions[]?, .DeleteMarkers[]?] | map({Key, VersionId}))}' > /tmp/v.json
jq -e '.Objects | length > 0' /tmp/v.json >/dev/null && aws s3api delete-objects --bucket "$B" --delete file:///tmp/v.json
aws s3api delete-bucket --bucket "$B"
```

`delete-objects` takes at most 1,000 entries per call; this bucket holds far fewer. Then set the Namecheap name servers back to Namecheap BasicDNS if the domain is reused.

## What comes next

In order (plan: [aws-ecs-comparison.md](../../docs/plans/aws-ecs-comparison.md), sections 7 and 9):

1. **Load-testing method and harness.** Locust under `tests/load/` with its own pinned requirements, outside the app image; workload fixed before any cloud run (anonymous browsing, a logged-in customer adding a size to the cart and checking out with its own idempotency key, a small operator share on `/analytics/`, about 1% checkouts); rehearsed locally against Docker first. The load generator runs in-region (`us-east-1`) so results measure the infrastructure, not the distance. The WAF login limit is raised or the generator's IP exempted during these runs, and that is recorded.
2. **Benchmark variant A.**
   - **RDS pilot:** one run at the 1,000-user step with RDS CPU, connections, memory and credits captured; size up once (`db.t4g.medium`) only if the database is the limit.
   - **The ladder:** 1, 10, 100 and 1,000 users, at least 3 repeats each, plus a separate saturation run.
   - **Scale-out:** time from the scaling trigger to a healthy second instance.
   - **Recovery:** kill an instance, then record the alarm, the replacement time and the error window.
   - **Rollout:** time for an instance refresh to a new image.
   - **The rest:** WAF block-mode test, Logs Insights export, Multi-AZ failover test.

   Results go to `evidence/raw/` and `evidence/test-resilience.md`.
3. **Variant B (`fargate/`).** Same `base/`, same image digest, same ALB design and health check: ECS cluster, task definition (2 vCPU / 4 GB, matched to `c5.large`), service, Application Auto Scaling on requests per target, alarms, WAF, alias record `shop-fargate.fourtytwofactors.me`. `jobs.sh`, `up.sh` and `down.sh` gain a `fargate` branch (`aws ecs run-task` instead of SSM). The database jobs are not rerun: both variants share the database.
4. **Benchmark variant B** with the identical harness, ladder and repeats, one variant taking load at a time; then the comparison (criteria and weights fixed before the first comparison run): scale-out time, recovery, rollout, latency and throughput, cost per hour and per 1,000 requests, and operational burden.
5. **Write-up pieces:** `docs/REPRODUCE_CLOUD.md` (based on this file), the architecture diagram check, the threat-control map update, reference IAM policies, then final teardown.
