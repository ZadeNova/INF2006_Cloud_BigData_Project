# Review: readiness of the 8 October 2026 evidence session (variant A and variant B)

- **Reviewer:** Claude Opus 5.5 (`claude-opus-5-5`), **fresh session**, with no access to the implementing or earlier reviewing
  conversations. Read-only: no `terraform`, no `aws`, no edits. The only file written is this one.
- **Scope:** whether the planned cloud session will produce **dated, redacted, verifiable** evidence for the brief's four tests
  (functional, security, data/AI, scalability and resilience) and monitoring, on variant A (EC2 + ASG) and variant B (ECS
  Fargate). Code quality is not re-reviewed (that is [infra-fargate-and-load-harness.md](infra-fargate-and-load-harness.md)).
- **Read:** AGENTS.md; the review log above; `docs/plans/load-harness.md`, `fargate-variant.md`, `aws-ecs-comparison.md` §7,
  `submissions-plans.md` §A; `tests/load/README.md`, `aws_capture.py`, and parts of `run.py`, `common.py`, `analyze.py`;
  `src/infrastructure/README.md`, `scripts/{up,down,smoke,tf,status}.sh`, parts of `jobs.sh`; `modules/web-entry/{logs,alarms,waf}.tf`,
  `ec2/{compute,scaling,web_entry}.tf`, `fargate/{ecs,scaling,web_entry}.tf`, `base/{monitoring,storage}.tf`;
  `evidence/{test-resilience,monitoring,test-performance,test-functional,test-security,README,aws-build-runbook}.md`.
- **Severity:** P1 = without the fix the session loses evidence a marker would credit, or cannot finish; P2 = weakens or biases
  evidence; P3 = small, or a traceability nicety.
- **Statements about AWS behaviour** that I could not check offline are marked *(unverified)*.

## Verdict

**GO for variant A, once the four P1 fixes below are done offline (about 45 minutes, no lab time, no code change).
Conditional GO for variant B,** decided by five read-only checks at the start of the lab window (section 5). The full plan
(about 13 to 15 hours of lab time) does not fit in today's session. Run the trimmed order in section 4.

**Blockers, in order:**

1. **EVD-003.** Write the case skeletons and the *expected* results now, before anything runs: FUNC-03, SEC-09 to SEC-11,
   SEC-17 (WAF block), MON-01 to MON-03, and the RES-03 rows in `test-resilience.md`.
2. **EVD-001 and EVD-012.** Agree one capture-and-redact helper and one file-naming rule for everything the harness does not
   capture (section 1.2). Nothing goes into `evidence/raw/` without passing through `common.redact`.
3. **EVD-002.** Export the logs and the two saved Logs Insights queries before every `down.sh` (commands in section 1.2).
   Nothing in the repository does this today.
4. **EVD-004.** Adopt the trimmed order and the timer rule in section 4. The default plan runs out of credentials partway
   through the ladder, with no resilience, monitoring or security evidence collected.
5. **EVD-005.** In the first ten minutes, check that `release-c19d547` is still in ECR and that LabRole trusts
   `ecs-tasks.amazonaws.com`. Both are read-only, and both decide what the rest of the session can do.

## 1. Coverage: what produces each artefact, and where it lands

### 1.1 What exists

| Brief test / case | Producer | Artefact path | Expected vs actual recorded in | Status today |
|---|---|---|---|---|
| Scalability: scale-out (RES-03a) | `run.py scaleout` (generator), `aws_capture.py watch` and `export` (laptop) | `evidence/raw/RES-03-<v>-scaleout-r<n>_<date>/` | `evidence/test-performance.md` RES-03a | **Ready.** Not yet linked from `test-resilience.md` (EVD-003) |
| Resilience: replacement (RES-03b) | `run.py replace`, `aws_capture.py watch`, `kill`, `export` | `evidence/raw/RES-03-<v>-replace-r<n>_<date>/` | `test-performance.md` RES-03b | **Ready.** Same linking gap |
| Performance and comparison (LOAD-01 to 04) | `run.py pilot\|ladder\|saturation\|singapore`, `export`, `analyze.py` | `evidence/raw/LOAD-<v>-<type>-r<n>_<date>/`, `evidence/load-summary.md` | `test-performance.md` | **Ready** |
| Functional on the live shop (FUNC-03) | **None.** `smoke.sh` runs inside `up.sh` (`up.sh:136`, `:148`) and prints to the terminal only. `run.py smoke` would work against the live host but is documented for local use only | **None** | **No FUNC-03 entry** (`test-functional.md:5-8` lists FUNC-01 and FUNC-02 only) | **Gap** (EVD-001, EVD-003) |
| Security on deployed resources (SEC-09, 10, 11) | **None** | **None** | `test-security.md:23-25`, `:325-327`: "PLANNED", with no objective, command or expected result | **Gap** |
| WAF block mode (part of section A item 6) | **None.** It needs a tfvars change, an apply, a burst and a revert | **None** | **No case** | **Gap**, and a design trap (EVD-007) |
| Monitoring: alarm to SNS (MON) | **None.** `export` collects alarm history only inside a run window and only `StateUpdate` items (`aws_capture.py:306`) | `alarm_history.json` inside run folders only | `evidence/monitoring.md:1-7` is an all-TODO template | **Gap** (EVD-008) |
| Monitoring: Logs Insights and log sample | **None** (EVD-002) | **None** | Same template | **Gap** |
| Data/AI on AWS | `jobs.sh ec2 refresh` runs inside `up.sh ec2` (`jobs.sh:236`), but its output is not saved | **None** | `test-data-ai.md` holds local evidence only | Optional. Local DATA-01 and DATA-02 already pass. Save the refresh output if it is free (it is, see below) |
| First-apply facts (runbook) | `up.sh`, `tf.sh` (terminal) | `evidence/aws-build-runbook.md`, written by hand | runbook tables | Manual, acceptable. Needs redaction (EVD-012) |

The **submission plan's C1 script** ("evidence-session script … written beforehand", `submissions-plans.md:28`, `:49`) does not
exist. Nothing under `src/infrastructure/scripts/` or `tests/` writes to `evidence/raw/` except `aws_capture.py export`.

### 1.2 Minimal fix: a capture helper and one command per gap (no repository code change)

Set this up once, in the laptop terminal:

```bash
cd <repo root>
S="$HOME/evidence-scratch"; mkdir -p "$S"; chmod 700 "$S"      # unredacted copies stay outside the repository
D="$(date -u +%F)"                                              # UTC date, the same date run.py uses in run ids
redact() { python3 -c 'import sys; sys.path.insert(0, "tests/load"); import common; sys.stdout.write(common.redact(sys.stdin.read()))'; }
# rec <CASE_date_variant_step> <command...>: header, live output (prompts still work), exit code and end time,
# then a redacted copy into evidence/raw/. Run it from the repository root.
rec() { local f="$1" rc; shift
  { echo "# date_utc: $(date -u +%FT%TZ)"; echo "# commit: $(git rev-parse --short HEAD)"; echo "# command: $*"; } > "$S/$f.txt"
  "$@" 2>&1 | tee -a "$S/$f.txt"; rc=${PIPESTATUS[0]}
  echo "# exit: $rc  end_utc: $(date -u +%FT%TZ)" >> "$S/$f.txt"
  redact < "$S/$f.txt" > "evidence/raw/$f.txt"; }
```

Run commands that contain pipes as `rec NAME bash -c '...'`. `rec` also works around the interactive scripts
(`rec RUNBOOK_${D}_ec2_up src/infrastructure/scripts/up.sh ec2`): the plan and the `yes` prompt still show. File names
follow the existing convention (`SEC-01_2026-09-26_rerun.txt`): `<CASE>_<date>_<variant>[_<step>].txt`.

The commands are in the code block after this table, labelled by case. They show variant A; for B, replace `ec2` with
`fargate`.

| Case | What it captures | Expected (write it into the evidence file **before** running) |
|---|---|---|
| SEC-10 and smoke | `smoke.sh` and the listener settings | 8 of 8 PASS; port 80 redirects; port 443 is HTTPS with `ELBSecurityPolicy-TLS13-1-2-2021-06` |
| FUNC-03 (automated) | `run.py smoke` against the live host from the laptop, then `export` | Buyer, abandoner and shopper visits complete; at least 1 order; 0 unexpected errors in `requests-*.csv` |
| FUNC-03 (human) | FUNC-02 steps 1 to 5 and 7 to 8 in a browser on the live host. Save the screenshots as files this time (FUNC-02 did not) | As FUNC-02 |
| SEC-09 | RDS public flag, S3 public-access block and policy status, anonymous S3 request, RDS port from the laptop | `public: false`; all four blocks true; `IsPublic: false`; 403; `no connection` |
| SEC-11 | Launch template (A) or task definition (B) environment, `secrets.sh check`, `jobs.sh check`; CloudTrail optional *(may be denied in the lab)* | Only `AWS_SECRET_ID` names, no values; every field `match`; `{"database": "ok", "migrations": "applied"}` as the runtime login |
| SEC-17 WAF block | See EVD-007 | See EVD-007 |
| MON-01 log sample, SEC-08 on AWS | 20 log lines; counts of `password`, `csrftoken`, `sessionid` in the log group | JSON lines with `ts, level, logger, message, status, request_id`; 0 for each word |
| MON-02 Logs Insights | Both saved queries, run by the CLI over the session window | `status: Complete` and a table of rows. An empty result is valid if no warnings occurred; say so |
| MON-03 alarm to email | Forced alarm state, full alarm history, the email | `StateUpdate` OK to ALARM; `Action` "Successfully executed action arn:aws:sns:…"; ALARM to OK at the next evaluation; one ALARM and one OK email |
| DATA on AWS (optional, free) | The analytics refresh `up.sh ec2` already runs | A refresh run id with 41,345 daily rows from 71,079 lines, as in the 1 October runbook |

```bash
# --- SEC-10 and smoke
rec SEC-10_${D}_ec2_smoke src/infrastructure/scripts/smoke.sh ec2
ALB=$(aws elbv2 describe-load-balancers --names inf2006-grp21-ec2-alb --query 'LoadBalancers[0].LoadBalancerArn' --output text)
rec SEC-10_${D}_ec2_listeners aws elbv2 describe-listeners --load-balancer-arn "$ALB" \
  --query 'Listeners[].{port:Port,proto:Protocol,policy:SslPolicy,action:DefaultActions[0].Type}'

# --- FUNC-03 (from tests/load/, laptop; .env loaded; the run id is printed first)
python accounts.py create --base-url https://shop-ec2.fourtytwofactors.me --count 4
python run.py smoke --variant ec2 --base-url https://shop-ec2.fourtytwofactors.me --yes --location laptop
python aws_capture.py export --variant ec2 --run-id <RUN-ID> --run-dir out/<RUN-ID>

# --- SEC-09 (back at the repository root)
rec SEC-09_${D}_rds aws rds describe-db-instances \
  --query 'DBInstances[?starts_with(DBInstanceIdentifier, `inf2006-grp21`)].{id:DBInstanceIdentifier,public:PubliclyAccessible,encrypted:StorageEncrypted}'
B=$(terraform -chdir=src/infrastructure/base output -raw s3_bucket_name)
rec SEC-09_${D}_s3_block aws s3api get-public-access-block --bucket "$B"
rec SEC-09_${D}_s3_policy aws s3api get-bucket-policy-status --bucket "$B"
rec SEC-09_${D}_s3_anon curl -s -o /dev/null -w '%{http_code}\n' "https://$B.s3.amazonaws.com/anything"
DBH=$(terraform -chdir=src/infrastructure/base output -raw db_host)
rec SEC-09_${D}_rds_port bash -c "timeout 5 bash -c '</dev/tcp/$DBH/5432' && echo OPEN || echo 'no connection'"

# --- SEC-11
rec SEC-11_${D}_ec2_userdata bash -c 'aws ec2 describe-launch-template-versions --launch-template-name inf2006-grp21-ec2-lt \
  --versions "\$Latest" --query "LaunchTemplateVersions[0].LaunchTemplateData.UserData" --output text | base64 -d | grep -nE "SECRET|PASSWORD"'
# B instead: rec SEC-11_${D}_fargate_taskdef aws ecs describe-task-definition --task-definition inf2006-grp21-fargate-app \
#              --query 'taskDefinition.containerDefinitions[0].environment'
rec SEC-11_${D}_secrets src/infrastructure/scripts/secrets.sh check
rec SEC-11_${D}_ec2_check src/infrastructure/scripts/jobs.sh ec2 check

# --- MON-01 and SEC-08 on AWS (before down.sh)
LG=/inf2006-grp21-ec2/app; T0=$(( $(date -d '-3 hours' +%s) * 1000 ))
rec MON-01_${D}_ec2_sample aws logs filter-log-events --log-group-name "$LG" --start-time "$T0" --max-items 20
for w in password csrftoken sessionid; do
  rec SEC-08_${D}_ec2_cloudwatch_$w aws logs filter-log-events --log-group-name "$LG" --start-time "$T0" \
    --filter-pattern "\"$w\"" --query 'length(events)'
done

# --- MON-02 Logs Insights (before down.sh), once per saved query
for q in recent-errors-and-security-warnings errors-and-warnings-per-minute; do
  Q=$(aws logs describe-query-definitions --query-definition-name-prefix "inf2006-grp21-ec2/$q" \
        --query 'queryDefinitions[0].queryString' --output text)
  QID=$(aws logs start-query --log-group-name "$LG" --start-time $(date -d '-3 hours' +%s) --end-time $(date +%s) \
        --query-string "$Q" --query queryId --output text)
  sleep 15
  rec MON-02_${D}_ec2_$q aws logs get-query-results --query-id "$QID"
done

# --- MON-03 alarm to email
T0ISO=$(date -u +%FT%TZ)
rec MON-03_${D}_ec2_force aws cloudwatch set-alarm-state --alarm-name inf2006-grp21-ec2-target-5xx \
  --state-value ALARM --state-reason "evidence session: notification-path test (forced)"
# wait for the ALARM and OK emails, then (no type filter, so the Action items that prove the SNS publish are included):
rec MON-03_${D}_ec2_history aws cloudwatch describe-alarm-history --alarm-name inf2006-grp21-ec2-target-5xx --start-date "$T0ISO"

# --- DATA on AWS (optional)
rec DATA-01_${D}_aws_refresh src/infrastructure/scripts/jobs.sh ec2 refresh
```

## 2. What `down.sh` destroys, and whether anything exports it first

`down.sh` runs `terraform destroy` on the stack (`down.sh:15`). Everything in `modules/web-entry` goes with it.

| Item | Where it lives | Lost on `down.sh`? | Exported today? |
|---|---|---|---|
| App log group `/inf2006-grp21-<v>/app`: request logs, job logs, Fargate stdout including probe errors, the `cpu` task's log | `modules/web-entry/logs.tf:3-8` (7-day retention) | **Yes, deleted** | **No.** `aws_capture.py` reads logs only inside `run_in_task` (`:204`) for the CPU line. **Your belief is correct: `export` pulls no application log events.** |
| Two saved Logs Insights queries | `alarms.tf:71-90` | **Yes.** The query text survives in Terraform; the results do not | **No** |
| Three stack alarms and their history | `alarms.tf:19-67` | Alarms deleted. Whether their history stays queryable after deletion is *(unverified)*; treat it as lost | Partly: `export` pulls `StateUpdate` items only, only within each run's window ±300 s (`aws_capture.py:298-316`, `:397`). No `Action` items |
| Target-tracking alarms (`TargetTracking-…`) | Created by ASG / Application Auto Scaling | Yes, with the policy | Same as above. Note this is real detection evidence for monitoring |
| ECS service events | The service (last 100 events) | **Yes** | Within each run window only (`aws_capture.py:407-411`). The first deployment, circuit-breaker events and anything between runs are lost |
| ASG scaling activities | The group | **Yes** (a deleted group's activities cannot be described) | Within each run window only, latest 100, unpaginated (`:400-405`). Enough for one run |
| CloudWatch 1-minute metrics | CloudWatch | **No.** Metrics outlive the resource (1-minute data for about 15 days, so until about 23 October) | Per run window. **But a re-export after teardown fetches nothing:** `export` finds the load balancer through `describe_target_groups` on the live target group (`:387`), and `if lb:` skips every metric when that fails (`:390`). The ALB and target-group suffixes are not recorded in `stack.json` (EVD-009) |
| WAF sampled requests | The web ACL (`waf.tf:161`) | **Yes**, and AWS keeps them only about 3 hours anyway *(retention unverified)* | **No** |
| WAF metrics (`CountedRequests`, `BlockedRequests`) | CloudWatch | No | Per run window only (`aws_capture.py:262-266`). A block test outside a run window is not exported |
| SNS emails | Mailbox (topic is in `base/`, `monitoring.tf:3`) | No | Must be saved by hand, redacted |
| Target-health history | Not kept by AWS | n/a | Only `watch` records it, and only while it runs on the laptop |
| `kill.json`, `targets.jsonl`, `cpu-<v>.json` | Laptop `tests/load/aws-out/` (git-ignored) | No | Copied into the run folder by `export`, then redacted (`:371-376`, `:415`) |
| Run folders on the generator | Generator disk | **Yes**, on `down.sh loadgen` | Only if copied to S3 after each run (README "After every run"). S3 write from the generator is unproven (README `:102`) |
| Terraform output, apply timings | Terminal | n/a | No (EVD-012, EVD-015) |

## 3. Sameness: everything that differs between A and B in the session

**Inherent** (the thing being compared, or forced by the platform; record it, do not "fix" it):

| Difference | Where | Note |
|---|---|---|
| Kill mechanism: ASG `terminate_instance_in_auto_scaling_group` vs ECS `stop_task` | `aws_capture.py:136-141` | Both are meant to be graceful (INF-002). Whether the ASG drains first is unproven (section 5) |
| Boot path: instance boot, Docker install and image pull vs Fargate image pull | `ec2/user_data.sh.tftpl`, `fargate/ecs.tf` | This is what replacement and scale-out measure |
| Health-check grace 300 s vs 120 s; ASG warm-up 240 s vs ECS cooldowns 300/300 | `ec2/compute.tf:221`, `ec2/scaling.tf:11`, `fargate/ecs.tf:90`, `fargate/scaling.tf:52-53` | Recorded pairing in ADR-017. Affects scale-in and the 2-to-1 return between runs |
| Database jobs: `up.sh ec2` runs `secrets.sh fill` and all 7 jobs (including `import`, `restart`); `up.sh fargate` runs only `check` | `up.sh:131-149`, `jobs.sh:236` | Inherent to the frozen image. The procedural consequence is in the avoidable table |
| CPU-model capture: SSM on the serving instance vs a one-off task | `aws_capture.py:209-220` | INF-021 limitation, already stated |
| Metrics: `AWS/AutoScaling` + `AWS/EC2` vs `AWS/ECS` service CPU and memory | `aws_capture.py:240-252` | Different series, not compared directly |
| Target type `instance` vs `ip`; container stop timeout (Docker default vs `stopTimeout` 30) | module input, `ecs.tf:65` | Draining happens first on both, so the effect should be negligible |

**Avoidable** (each would bias the comparison; fix by procedure, identically on both):

| Difference | Why it biases | Procedure |
|---|---|---|
| Re-running `up.sh ec2` to change pinning | Re-runs `bootstrap`, `restart` and `import` against the shared RDS right before an A run only | Pin with `tf.sh <v> plan` / `apply` on both variants, never `up.sh` |
| RDS state carried from A to B: warm buffer cache, lower CPU credit balance, surplus credits, lower stock | B runs on a warmer but more credit-drained database, with more stock conflicts | Record `CPUCreditBalance` at each variant's first run (`export` captures it). Use the same order of run types on both. Report orders and stock conflicts per run. A then B in each window, never B's repeats after a long A block |
| Settle time after a pin or apply | Different time since the second unit became healthy (DB connections, Python warm-up) | Fixed rule: start `run.py` 3 minutes after `watch` shows the intended healthy count, on both |
| WAF mode | Block mode left on rejects the ladder's logins on one variant | Run the block test **last** on each variant. Revert `waf_login_action` in that stack's `terraform.tfvars` before that stack's next apply. `stack.json` records the mode |
| `--users-high` for scale-out | Default 200 is meant to be "set from the pilot", and the pilot runs on A only | Fix it at 200 now (about 670 requests per target per minute against a target of 300, so it triggers) and use it on both |
| `watch` start time and credential expiry | A missing `targets.jsonl` turns a run into "not verified" on one variant only | Start `watch` before `run.py` on both. Refresh credentials before every scale-out or replace run (EVD-006) |
| `cpu` one-off task timing | On B it takes 2 vCPU of quota and could collide with a 2-task pin | Run `cpu` once per variant, before pinning to 2, never during a run |
| Kill reaction time | The user types `kill` when prompted | `kill.json` measures from the actual call, so this is fine. Have the command ready with `--yes` to keep the kill near 300 s on both |
| Generator | A new generator for B would change the client host | Keep one `loadgen` up across both variants and both windows |
| Time of day and session | A in window 1, B in window 2 | Inherent to D5. State it. Keep windows close together |
| Number of repeats | If A gets r2 and B does not, the min-max tie rule treats them differently | Equal repeats per condition, or report only r1 for both |

## 4. Time and credentials

### 4.1 The full plan does not fit

`load-harness.md:142` estimates 5 to 6 hours per variant for load runs alone. Add, per variant, about 25 minutes for
`up.sh ec2` (7 jobs, including `import`) or 15 for `up.sh fargate`, 20 for the generator, harness and 2,200 registrations
(A only), about 45 for functional, security, monitoring and logs, and 5 (A) to 20 (B, ENI release) for teardown. **That is
about 13 to 15 hours of lab time, against windows of about 4 hours.** The submission plan's "about 2 to 3 hours" for
section A covered A only, with one scale-out and one kill.

### 4.2 Trimmed scope and order (strongest valid evidence first)

Principles: the brief's tests before the comparison; the two highest-weighted comparison criteria (replacement 25,
latency 20) before the rest; the fewest applies (defaults 1/2/1 are already the scale-out configuration). Drop the 1,000-user
pilot: ladder u100 confirms the metric dimensions and RDS headroom at the load the 2-unit runs use. The RDS gate becomes a
stated limitation unless window 3 happens.

**Window 1, variant A (about 2 h 50 min of a 4 h window, 70 min slack):**

| Clock | Step | Evidence |
|---|---|---|
| 0:00 | Start Lab, `labcreds`, `status.sh`; section 5 preflight checks (including B's) | runbook, `PRE_${D}` file |
| 0:10 | Terminal 1: `up.sh ec2`. Terminal 2: `up.sh loadgen` | runbook |
| 0:35 | SEC-10 smoke. Generator: harness via git bundle (EVD-013), venv, then `accounts.py create` (about 10 min). Laptop meanwhile: FUNC-03 smoke run and export, SEC-09, SEC-11, `cpu --variant ec2` | FUNC-03, SEC-09/10/11 |
| 0:55 | **RES-03a scale-out r1** (defaults 1/2/1; `watch` first); export | RES-03a |
| 1:20 | Pin 2/2/2 (`tf.sh ec2 plan`/`apply`); settle | |
| 1:28 | **RES-03b replace r1**; kill at the prompt. In the 15 idle minutes after the kill: MON-03 forced alarm | RES-03b, MON-03 |
| 1:50 | Export; pin 1/1/1; settle | |
| 1:57 | **Ladder u100 r1**; export; check `alb_healthy_hosts.csv` reads 1.0 and RDS CPU | LOAD-02 |
| 2:10 | **Ladder u10 r1**; export | LOAD-02 |
| 2:25 | SEC-17 WAF block: apply `block`, burst, export, revert the tfvars text | SEC-17 |
| 2:38 | MON-01, MON-02, SEC-08 on AWS (logs). **Then** `down.sh ec2` | MON-01/02 |
| 2:50 | Done. If more than 60 minutes remain on the timer, add replace r2 before the WAF step | |

**Window 2, variant B (about 2 h 30 min):** preflight, then `up.sh fargate` (stop rule below), SEC-10 smoke for B,
`cpu --variant fargate` (before pinning to 2), then the **same sequence as A**: scale-out r1, pin 2, replace r1, pin 1,
ladder u100 r1, ladder u10 r1, then MON-01/02 logs, then `down.sh fargate` with a 20-minute budget.

**Window 3, only if time allows (Fri 9 October):** replace r2 and ladder u10/u100 r2 on A then B, then saturation r1 on each
(it gives the cost criterion its knee), then Singapore. Same order on both.

### 4.3 Stop rules

**Every window:** never start a recorded run unless the session timer shows at least the run length plus 25 minutes
(export plus teardown). At 30 minutes left, start nothing new: export, save logs, tear down. A run marked invalid is rerun
at most once; a second failure is recorded with its diagnosis and the session moves on.

**Variant A:**

- `up.sh ec2` and smoke 8 of 8 not done within 45 minutes: no load runs. Capture the failure with `rec`, run `down.sh ec2`,
  and diagnose offline.
- Ladder u100 shows RDS CPU above 80% ("database-limited"): record it as a result. Do not resize RDS today (a `base/`
  change and about 9 minutes, and every earlier run would be superseded).
- The kill does not show `draining` in `watch`: record what happened and keep the run (section 5, ASG drain).

**Variant B:**

- Preflight shows that LabRole does not trust `ecs-tasks.amazonaws.com`: do not apply B. Save the check output as
  evidence that B is "designed, blocked by lab IAM", and spend window 2 on A repeats.
- No task RUNNING and healthy within 15 minutes of the apply starting, or `up.sh fargate` not finished within 30 minutes:
  capture service events, stopped reasons and the log group, run `down.sh fargate`, and record "B apply failed: <reason>".
- Fargate vCPU quota below 4, or an "unable to place" event: skip B's scale-out and replace (state why) and run the ladder
  only.

## 5. First-apply risks

| Assumption (review log tables) | Symptom if wrong | Fastest check | Fallback that still leaves evidence |
|---|---|---|---|
| `release-c19d547` still in ECR (lifecycle keeps 5 newest `release-*`, `base/storage.tf:120-135`) | `tf.sh ec2 plan` fails on the `aws_ecr_image` data source | `aws ecr describe-images --repository-name inf2006-grp21-app --image-ids imageTag=release-c19d547 --query 'imageDetails[0].imageDigest'` equals `sha256:fa72e949…cb481` | `push-image.sh` builds a new digest. Record it; the 1 October smoke evidence is then for another digest (AGENTS.md "image is pinned") |
| LabRole as ECS task and execution role | Tasks STOPPED with "unable to assume role", `CannotPullContainerError` or `ResourceInitializationError`; apply waits | `aws iam get-role --role-name LabRole --query 'Role.AssumeRolePolicyDocument.Statement[].Principal'` lists `ecs-tasks.amazonaws.com` | None in IaC (the lab cannot create roles). B "designed, blocked", with the check output and the stopped reason as evidence |
| ECS and Application Auto Scaling service-linked roles | Service creation fails with a service-linked-role error; `aws_appautoscaling_target` gets AccessDenied | `aws iam get-role --role-name AWSServiceRoleForECS`; `aws iam get-role --role-name AWSServiceRoleForApplicationAutoScaling_ECSService` | Try `aws iam create-service-linked-role --aws-service-name ecs.amazonaws.com` (or `ecs.application-autoscaling.amazonaws.com`) *(may be denied)*. If scaling alone fails, the stack has no switch to drop it (a code change), so record B scale-out as blocked and run the ladder and replace on a partial stack only if the service itself is up |
| Probe-host lookup (`ecs.tf:15`) | Task exits 1 immediately (`set -e`), or targets unhealthy with `Target.ResponseCodeMismatch` (400, DisallowedHost); circuit breaker | `aws logs tail /inf2006-grp21-fargate/app --since 10m`; `aws elbv2 describe-target-health --target-group-arn <tg>` | B unmeasured. Save the log lines and target-health reason (redacted) as the diagnosis |
| `wait_for_steady_state` ends on a failed rollout | `terraform apply` hangs for up to the provider's create timeout instead of failing | In a second terminal: `aws ecs describe-services --cluster inf2006-grp21-fargate-cluster --services inf2006-grp21-fargate-service --query 'services[0].{state:deployments[0].rolloutState,why:deployments[0].rolloutStateReason,events:events[:5].message}'` | Apply the 15-minute stop rule; Ctrl-C once (Terraform stops gracefully), capture, `down.sh fargate`. **Skip the planned "deliberate bad-image apply" today**: low value, high lab time |
| Fargate vCPU quota allows 2 tasks (4 vCPU; 6 while a one-off task runs) | Service event "unable to place a task … vCPU limit" | `aws service-quotas get-service-quota --service-code fargate --quota-code L-3032A538 --query Quota.Value` *(may be denied)*; otherwise the first pin to 2 | Skip B's scale-out and replace; ladder only; state the quota |
| ASG drains before terminating (INF-002 fix) | `targets.jsonl` jumps from `healthy` to gone with no `draining`; errors spike at the kill | `watch` output during the first A replace run | Keep the run and record the asymmetry in RES-03b and ADR-017's limitation (the A failure was then abrupt, B's graceful) |
| `HealthyHostCount` aggregates across zones (INF-020) | `alb_healthy_hosts.csv` reads 0.5, or 1 with two healthy targets | After ladder u100: the CSV reads 1.0. After replace: compare its 2-unit minutes with `targets.jsonl` | Two-unit runs already use `targets.jsonl`. For single-unit runs, also run `watch` and cite `targets.jsonl` in the evidence if the CSV disagrees |
| S3 write from the generator to `exports/load/` (README `:102`) | `AccessDenied` on `aws s3 cp` from the generator | Right after `up.sh loadgen`: `aws s3 cp /etc/hostname s3://$B/exports/load/probe.txt` on the generator | On the laptop, create a presigned PUT URL with boto3 (`generate_presigned_url('put_object', …)`); on the generator, `tar czf` the run folder and `curl -T` it |
| Learner Lab session end stops EC2 instances (generator and app) *(unverified, check the Learner Lab page)* | A run dies mid-way; the ASG replaces a stopped instance | Read the timer before every run | The timer rule in 4.3. Restart the lab before a long run if the lab allows the timer to be reset |
| SG / ENI release on `down.sh fargate` | Destroy waits on `sg-app` for many minutes | `aws ec2 describe-network-interfaces --filters Name=group-id,Values=<sg-app id> --query 'NetworkInterfaces[].Status'` | Budget 20 minutes; rerun `down.sh fargate`; record the time as an operational-burden data point |
| `mode=blocking` accepted (round 2 table) | Task definition registration error, or Docker refuses the log option | The apply itself | Code change needed; B unmeasured |

## 6. Redaction and traceability

**What `export` covers:** every `.csv/.json/.jsonl/.html/.txt/.md` file in a run folder passes through `common.redact`
(`aws_capture.py:351-357`, `:415`): 12-digit account IDs and public IPv4 addresses. Run files hold no passwords, cookies or
CSRF tokens (review log, "Checked and passed" F). Secret **names** (`inf2006-grp21/web`) appear and are fine; secret
**values** never reach these files.

**What leaks if captured outside `export`:**

| Source | Leaks | Fix |
|---|---|---|
| `labcreds` output, `aws sts get-caller-identity`, any `tf.sh` plan or apply output (ECR URL, ARNs), `status.sh` (last 4 digits only) | Account ID | Wrap in `rec` (section 1.2), or redact before saving. Never paste raw into the runbook |
| `aws secretsmanager get-secret-value --secret-id inf2006-grp21/operator` (README `:148`) | **The operator password** | Never run it inside `rec` or `tee`. Copy it straight to the clipboard |
| `aws sns list-subscriptions-by-topic`, the SNS email itself (recipient, "AWS Account: …", unsubscribe link ARN) | Email address, account ID | Redact the email by hand. `common.redact` does not cover email addresses |
| `aws wafv2 get-sampled-requests` | Laptop public IP (redacted) and **request headers including `Cookie` (session ID, CSRF cookie)** (not redacted) | Pipe through `jq 'del(.SampledRequests[].Request.Headers)'` before `redact` |
| CloudTrail `lookup-events` | Account IDs, public IPs (both redacted), access key IDs of the lab session *(not redacted)* | Save only `EventTime`, `EventName`, `Username` and the resource name (`--query`) |
| AWS console screenshots | Account ID in the top-right menu | Crop, or use the CLI |
| Copying `tests/load` to S3 for the generator | `.env` holds `LOADTEST_PASSWORD` | Use a git bundle (EVD-013); never upload `.env` |
| `tfstate` and `.bak` files | Account IDs, resource IDs | Already git-ignored. Never copy them into `evidence/` |

**Traceability:**

- Harness runs trace well: dated run ids, `run.json` (UTC times, command line), `stack.json` (digest, capacity, WAF mode,
  export time), and the case tables in `test-performance.md` give path patterns.
- **Non-harness steps do not**, until EVD-001 and EVD-003 are done: no file names, no recorded command, no expected value
  written beforehand. `rec` adds a date, commit, command and exit code to each file, as SEC-12 onward already do.
- `run.json` on the generator records an empty `git_commit` if the harness arrives without `.git` (`run.py:202`). Results
  then cannot be tied to the harness commit (EVD-013).
- `prices.json` is unverified, so every cost figure is flagged (EVD-011).

## 7. Findings

### EVD-001: P1, no capture path for the non-harness evidence

- **Where:** `docs/plans/submissions-plans.md:28`, `:49` (C1 script never written); `src/infrastructure/scripts/up.sh:136`,
  `:148` (smoke output only on the terminal); no script writes FUNC, SEC, MON or WAF files.
- **Impact:** FUNC-03, SEC-09/10/11, the WAF block test and MON would exist only as terminal scrollback. A marker credits
  none of it.
- **Fix:** use the `rec` helper and the command table in section 1.2. No repository code is needed today.

### EVD-002: P1, logs and Logs Insights results are destroyed and never exported

- **Where:** `modules/web-entry/logs.tf:3-8`, `alarms.tf:71-90`; `tests/load/aws_capture.py:360-417` (no `logs` call in
  `export`).
- **Impact:** the monitoring criterion's log and query evidence, and the cloud half of SEC-08, are lost on `down.sh`.
- **Fix:** run MON-01, MON-02 and SEC-08-on-AWS (section 1.2) as the last step before each `down.sh`. Optionally add an
  `aws_capture.py logs` subcommand later; it is not needed today.

### EVD-003: P1, no place written in advance for expected vs actual

- **Where:** `evidence/monitoring.md:1-7` and `evidence/test-resilience.md:3-9` (all TODO); `evidence/test-security.md:23-25`,
  `:325-327` (SEC-09 to 11 "PLANNED", no fields); `evidence/test-functional.md:5-8` (no FUNC-03); no SEC-17 or MON-0x cases.
- **Impact:** expected results written after the run are post-hoc. `test-security.md:231` already admits this for the local
  cases. The marker looks for objective, setup, command, expected, actual, date and artefact path.
- **Fix:** before Start Lab, add the skeletons with the "Expected" column of section 1.2. Add RES-03 rows to
  `test-resilience.md` linking `test-performance.md` RES-03a/b (plan D8). Leave "Actual" empty.

### EVD-004: P1, the planned scope does not fit the credential window

- **Where:** `docs/plans/load-harness.md:142` (5 to 6 h per variant); `submissions-plans.md:26` (2 to 3 h); credentials last
  about 4 h (`src/infrastructure/README.md:95`).
- **Impact:** following the plan's order (pilot, then the whole ladder) spends the first window on ladder repeats, with no
  resilience, monitoring or security evidence.
- **Fix:** section 4.2 order and section 4.3 stop rules.

### EVD-005: P2, cheap preflight checks are not part of the procedure

- **Where:** review log "Not verifiable offline" tables; `src/infrastructure/README.md:115-139`.
- **Impact:** discovering a missing image or an untrusted LabRole after 25 minutes of applying wastes a window.
- **Fix:** the first-row checks of section 5 (ECR image, LabRole trust, the two service-linked roles, Fargate quota, S3 write),
  saved with `rec PRE_${D}_<check>`. Listed as a blocker because it costs 10 minutes and decides the plan.

### EVD-006: P2, credential expiry and lab session end during a run

- **Where:** `tests/load/aws_capture.py:98-110` (`watch` has no exception handling, so an expired token ends it with a
  traceback); the generator is an EC2 instance (`loadgen/`).
- **Impact:** a partial `targets.jsonl` makes a 25-weight run "not verified". If the lab stops EC2 instances at session end
  *(unverified)*, the run dies.
- **Fix:** the timer rule in 4.3; refresh credentials before every scale-out or replace run. If `watch` dies, restart it with
  the same `--run-id`: it appends (`open(path, "a")`, `:100`).

### EVD-007: P2, the WAF block test is undefined and easy to get wrong

- **Where:** `modules/web-entry/waf.tf:103-162`; no case or script.
- **Impact:** a curl burst without a CSRF token gets Django's own 403, which looks like a WAF block. Sampled requests vanish
  with the ACL and carry cookies. The block metric falls outside any run window, so `export` misses it.
- **Fix (SEC-17):** set `waf_login_action = "block"` in `ec2/terraform.tfvars`, then `tf.sh ec2 plan`/`apply`. Run from
  the laptop:

  ```bash
  H=https://shop-ec2.fourtytwofactors.me; J=$(mktemp)
  for i in $(seq 1 40); do
    tok=$(curl -s -c "$J" -b "$J" "$H/login/" | sed -n 's/.*name="csrfmiddlewaretoken" value="\([^"]*\)".*/\1/p' | head -1)
    curl -s -o /dev/null -D - -b "$J" -c "$J" -e "$H/login/" -H "Origin: $H" \
      --data-urlencode "csrfmiddlewaretoken=$tok" --data-urlencode "username=waf-probe" --data-urlencode "password=wrong-$i" \
      "$H/login/" | awk -v i="$i" -v t="$(date -u +%FT%TZ)" 'NR==1{c=$2} tolower($1)=="server:"{s=$2} END{print t, i, c, s}'
    sleep 4
  done
  ```

  Save the loop as `$S/waf-burst.sh` and capture it with `rec SEC-17_${D}_ec2_burst bash "$S/waf-burst.sh"`. **Expected:** the first POSTs return 200 (Django re-shows the
  form after a failed login); after the 20th, within the rule's evaluation delay *(about a minute, unverified)*, 403 with
  `Server: awselb/2.0`. Then save `BlockedRequests` with `aws cloudwatch get-metric-statistics` (dimensions as in
  `aws_capture.py:264`) and the sampled requests with headers stripped (section 6). Restore `count` in the tfvars text
  before the next apply of that stack. Run this step last on the variant.

### EVD-008: P2, no alarm-to-email procedure; `export` drops `Action` history

- **Where:** `tests/load/aws_capture.py:306` (`HistoryItemType="StateUpdate"`); `alarms.tf:53-67`; `evidence/monitoring.md`.
- **Impact:** no proof that an alarm reached SNS. The natural replace run is graceful, so it probably does not trip
  `unhealthy-hosts`.
- **Fix:** MON-03 (section 1.2): `set-alarm-state`, then history with no type filter, then the redacted email. State honestly
  that this tests the notification path, not detection. For detection, cite the target-tracking `AlarmHigh` transition in
  the RES-03a `alarm_history.json`.

### EVD-009: P2, a re-export after teardown silently returns no metrics

- **Where:** `tests/load/aws_capture.py:386-394`; `describe_stack` (`:319-348`) records no ALB or target-group suffix.
- **Impact:** if one export is forgotten or fails before `down.sh`, its CloudWatch data still exists (about 15 days) but
  this tool cannot reach it.
- **Fix today (procedure):** export every run before any apply or `down.sh` (README already says so). Before each
  `down.sh`, note the ALB and target-group ARN suffixes in the session log (they are also in the tfstate `.bak`), so a manual
  `get-metric-data` stays possible until about 23 October.

### EVD-010: P2, avoidable A/B differences

- **Where:** section 3, "Avoidable" table.
- **Impact:** RDS carry-over, uneven settle time, WAF mode, `--users-high`, `watch` start time and `cpu` timing each move
  one variant's figures only.
- **Fix:** one per-run checklist used verbatim on both variants: tfvars values, settle 3 minutes, `watch` started,
  credentials fresh, carts reset, `--users-high 200`. Paste it into `test-performance.md` "Conditions common to every
  recorded run".

### EVD-011: P2, one repeat per condition makes the tie rule meaningless, and prices are unverified

- **Where:** `tests/load/analyze.py:338` (ties only when min-max ranges overlap; with n = 1 the ranges are points);
  `tests/load/prices.json` (`verified_by_user` false; README `:33`).
- **Impact:** any difference, however small, scores 10 against less than 10 on criteria weighted 25 and 20. The cost criterion
  is flagged unverified.
- **Fix:** in the report, label single-repeat comparisons "indicative, n = 1", and do not quote the weighted total as a
  decision without r2. Verify `prices.json` offline before the session (10 minutes, no lab time).

### EVD-012: P2, terminal output and manual exports can leak

- **Where:** section 6 table.
- **Impact:** account ID (tf output, `labcreds`), operator password (`get-secret-value`), email address (SNS), session
  cookies (WAF sampled requests) can reach `evidence/` or the runbook.
- **Fix:** `rec` and `redact` for everything; the specific exclusions in section 6. Before committing evidence, run
  `rg -n '\b[0-9]{12}\b|@|Cookie|sessionid|BEGIN' evidence/raw/*${D}*` and expect only redaction markers.

### EVD-013: P3, generator runs record no commit; the harness copy may carry `.env`

- **Where:** `tests/load/run.py:202` (`git rev-parse HEAD` on the generator); README "After every run" (S3 transfer).
- **Impact:** `run.json` cannot be tied to the harness commit; `LOADTEST_PASSWORD` could land in S3.
- **Fix:** on the laptop, `git bundle create "$S/repo.bundle" HEAD` and copy only that file through S3; on the generator,
  `git clone repo.bundle inf2006 && cd inf2006/tests/load`. Set `LOADTEST_PASSWORD` in the shell, not in a file.

### EVD-014: P3, the redaction regex can corrupt hex identifiers

- **Where:** `tests/load/common.py:105` (`(?<!\d)\d{12}(?!\d)`).
- **Impact:** a run of exactly 12 digits inside a task ID, instance ID or image digest becomes `<ACCOUNT>`, so the evidence ID
  no longer matches AWS or the runbook. The recorded digest `fa72e949…cb481` is safe (its longest digit run is 10).
- **Fix:** after the first export, check that `stack.json`'s `image_digest` equals the runbook's. If an ID is mangled, say so
  in the case. Do not change code today.

### EVD-015: P3, operational burden (weight 25) has no timed source in the session

- **Where:** `load-harness.md:74`; `up.sh` and `down.sh` print no timings.
- **Impact:** the boot-to-healthy, apply-time and teardown-time figures would be recollection.
- **Fix:** wrap `up.sh` and `down.sh` in `rec` (its header and last line give the start and end times), and take
  boot-to-healthy from the RES-03b timings. State that rollout time and patch steps were not measured.

### EVD-016: P3, session continuity across units is in the data but not reported

- **Where:** `evidence/test-resilience.md:11` (cross-instance session and cart named as not run); `analyze.py` has no such
  figure.
- **Impact:** a scope requirement is shown by the replace run's request log but never stated.
- **Fix (offline, after the session):** from `requests-*.csv` of RES-03b, count logged-in visits whose actions span the kill
  and completed without a re-login or an error. One paragraph in `test-resilience.md`.

## 8. Limitations of this review

- No AWS access. Every statement about Learner Lab limits, retention periods and rate-rule timing is from documentation
  memory and is marked *(unverified)* where it matters.
- The commands in section 1.2 and EVD-007 were written, not run. Read each `rec` output as it lands, and fix a typo
  there rather than trusting a non-zero `# exit:` line.
- Time estimates assume no failures and an `import` rerun of a few minutes (its rerun duration is not recorded in the
  runbook).

## 9. Response from the writing session (8 October 2026, Claude Opus 5.5)

The claims were checked against the code before acting: EVD-001, 002, 006, 008 and 009 were confirmed at the cited lines (`aws_capture.py:98-110`, `:306`, `:386-394`; `up.sh` runs `jobs.sh ec2 all`); the resource names, saved-query names, WAF limit (20 per 300 s) and base outputs in section 1.2 match the Terraform. Instead of the pasted `rec` helper, the commands of section 1.2 became one script, `src/infrastructure/scripts/evidence.sh`, so the steps cannot drift between variants (the user's requirement). Corrections to section 1.2:

- **SEC-09 `rds_port`:** dropped. `db_host` resolves to a private address, so a failed connection from a laptop proves only that 10.x is not routed. Replaced by the security-group rules of `sg-alb`, `sg-app` and `sg-db`.
- **SEC-08 on AWS:** became SEC-18, a Logs Insights search; the expected result allows a word without a value (a route name) and fails only on a value.
- **MON-02:** polls until `Complete` instead of `sleep 15`.
- **Missed:** nothing checked that the SNS email subscription is confirmed; added to the preflight.

| Finding | Disposition |
|---|---|
| EVD-001 | Fixed: `evidence.sh` (security, func, alarm, waf, logs, up, down, rec), redacting account IDs, public IPs and email addresses |
| EVD-002 | Fixed: `evidence.sh <v> logs` (MON-01, MON-02, SEC-18), a step before `down` in the runbook |
| EVD-003 | Fixed: expected results written before the run in `test-functional.md` (FUNC-03), `test-security.md` (SEC-09 to 11, 17, 18), `monitoring.md` (MON-01 to 04), `test-resilience.md` (RES-03a, RES-03b, RES-04 index) |
| EVD-004 | Accepted: section 4.2 order adopted as campaign 1 (`test-performance.md`, "Campaign 1 scope"; runbook [evidence-session.md](../plans/evidence-session.md)); both variants today |
| EVD-005 | Fixed: `evidence.sh preflight` (image, LabRole trust, service-linked roles, Fargate quota, SNS confirmation, leftover pin files); the generator's S3 write test is in the runbook |
| EVD-006 | Procedure: runbook stop rules and the per-run checklist |
| EVD-007 | Fixed: `evidence.sh <v> waf` (refuses unless the rule is in block mode; `Server: awselb/2.0` distinguishes a WAF block; GET still allowed; headers stripped from sampled requests); last test on each variant; `down` removes the pin file |
| EVD-008 | Fixed: `evidence.sh <v> alarm` saves the full history including `Action` items; MON-04 cites the target-tracking alarm for detection |
| EVD-009 | Fixed: `evidence.sh <v> security` saves the stack IDs (`SESSION_<date>_<v>_ids.txt`) |
| EVD-010 | Fixed: per-run checklist in `test-performance.md`; `pin` waits for the healthy count and prints the settle time; `watch` for every run type |
| EVD-011 | Accepted: "indicative, n = 1" stated in the campaign scope; `prices.json` check left to the user (runbook step 0.5) |
| EVD-012 | Fixed for the script's output; runbook section 6 holds the leak check and the screenshot rule |
| EVD-013 | Procedure: git bundle through S3; `LOADTEST_PASSWORD` typed into the generator's shell |
| EVD-014 | Procedure: digest check after the first export (runbook section 6) |
| EVD-015 | Fixed: `evidence.sh <v> up` and `down` record start and end times (`OPS_*`) |
| EVD-016 | After the session: RES-04 in `test-resilience.md` |

Not changed: `aws_capture.py` (no `logs` subcommand, `StateUpdate` filter kept, no suffixes in `stack.json`); `evidence.sh` covers these gaps without touching reviewed harness code. `evidence.sh` was tested offline against fake `aws` and `terraform` commands (preflight, rec and rerun naming, redaction, logs with a polled query, alarm, argument checks); none of its AWS calls has run against the lab.
