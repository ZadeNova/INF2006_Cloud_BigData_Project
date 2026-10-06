# Review: web-entry module, ec2 refactor, fargate, loadgen, scripts and load harness

One file per review task (docs/DEVELOPMENT.md, "Review handoff"). Rounds are appended below; finding IDs are stable
across rounds and must not be renumbered or reworded to reset the repeat-after-fix rule.

## Task and scope

- **Branch / commit reviewed:** `erfan/aws` at `f36c663` (clean tree).
- **Owned paths:** `src/infrastructure/modules/web-entry/`, `src/infrastructure/ec2/` (changes since `c4ae7c4`, the last
  applied and verified version), `src/infrastructure/fargate/`, `src/infrastructure/loadgen/`,
  `src/infrastructure/base/outputs.tf` (one added output), `src/infrastructure/scripts/` (status, up, down, jobs, tf,
  secrets, push-image, smoke), `tests/load/` (commits ac91995, 9518d8e, 84d2a52, 17db3d6), and the docs that make claims
  about them: ADR-013 to ADR-017 (ADR-001, 008, 011, 012 where relevant), `docs/plans/fargate-variant.md`,
  `docs/plans/load-harness.md`, `src/infrastructure/README.md`, `src/infrastructure/modules/web-entry/README.md`.
- **State of the work at review time:** nothing since `c4ae7c4` has been applied. Every AWS-behaviour assumption is
  unproven; scripts were tested only against stub `aws`/`terraform`.
- **Backend, Dockerfile and requirements.txt are frozen** (AGENTS.md). No finding below needs a backend change.

## Round 1 (6 October 2026)

- **Reviewer:** Claude Opus 5.5 (`claude-opus-5-5`), **fresh session** with no access to the implementing conversation.
  Read-only: no edits, no `terraform plan/apply`, no `aws`, no `docker`, no AWS credentials.
- **Effort:** full scope (areas A to G of the review brief).

### Checks run

| Check | Result |
|---|---|
| `terraform -chdir=<folder> init -backend=false`, `validate`, `fmt -check -recursive` for `base`, `ec2`, `fargate`, `loadgen`, `modules/web-entry` | All pass. `base/` prints two "undeclared variable" warnings from the local, git-ignored `base/terraform.tfvars` (not the code). The `init` of `modules/web-entry` created an untracked `.terraform.lock.hcl` and `.terraform/`; the reviewer deleted both, tree clean afterwards |
| `bash -n` on all 8 scripts | Pass |
| shellcheck | **Not run** (not installed). Recorded as a limitation, not a pass |
| `python3 tests/load/selftest.py` | 10 of 10 PASS (boto3/botocore present; Locust not installed and not needed by the self-test) |
| Local bash test of a subshell `trap … EXIT` under INT, TERM, HUP sent to the process group (scratch dir) | Trap runs for all three (relevant to `jobs.sh` bootstrap master-out) |
| Diffs read | `git diff c4ae7c4..HEAD -- src/infrastructure/ec2 src/infrastructure/modules src/infrastructure/base`; `user_data.sh.tftpl` at `c4ae7c4` |

### Verdict

**Ready after fixes below.**

- **Blocks `up.sh fargate`:** INF-001 (documented order of operations yields two different image digests).
- **Block the recorded load campaign (not the applies):** INF-002, INF-003, INF-004.
- Everything else is non-blocking.

### Findings

Status of every finding at the end of round 1: **open**.

Severity scale: Critical / High / Medium / Low / Info. "Will fail" = deterministic from the code; "might fail" = depends
on AWS or timing; "style" = no behavioural effect.

#### INF-001 — High, will fail — area E, C — `up.sh fargate` builds a new image, so A and B run different digests

- **Location:** `src/infrastructure/scripts/up.sh:102-109` (`need_image`), `src/infrastructure/scripts/push-image.sh:49-51`.
- **Evidence:** `need_image fargate` runs `push-image.sh` with no argument whenever `fargate/image.auto.tfvars` is
  missing. That builds the current HEAD (a new tag) and writes `image.auto.tfvars` into **both** `ec2/` and `fargate/`.
  On the apply laptop today `ec2/image.auto.tfvars` is `release-c19d547` and `fargate/image.auto.tfvars` does not exist.
- **Impact:** following the documented order (`up.sh ec2`, then `up.sh fargate`), fargate gets a freshly built image (or
  the script stops if Docker is absent). A rebuild has a different digest (the infrastructure README says so), so A and
  B run different digests, contradicting ADR-015/ADR-017 and the comparison plan. ec2's selection is also silently
  overwritten, so the next ec2 plan rolls a new image onto A.
- **Direction:** when one stack already has an image selected, reuse that release for the other instead of building;
  and have `up.sh fargate` (or `tf.sh fargate plan`) stop if the fargate digest differs from the ec2 one.

#### INF-002 — High, will bias the comparison — area C, F — replacement test kills A abruptly but stops B gracefully

- **Location:** `tests/load/aws_capture.py:131-134` (`kill`).
- **Evidence:** A uses `ec2.terminate_instances`; B uses `ecs.stop_task`.
- **Impact:** StopTask on a service task behind an ALB first deregisters the target (30 s drain), then sends SIGTERM
  (`stopTimeout` 30 s): a graceful stop. A direct EC2 terminate has no drain first; requests keep going to the dying
  target until three health checks fail. The criterion "replacement time and error window" (weight 25) would compare a
  graceful stop on B against an abrupt failure on A, and nothing records this difference.
- **Direction:** make the two failure modes equivalent (for example the Auto Scaling terminate-instance API for A,
  which drains through the target group), or record the asymmetry explicitly in ADR-017 and the report.

#### INF-003 — High — area F — analyze.py does not enforce most run-validity rules

- **Location:** `tests/load/analyze.py:52-77` (`load_run`), `131-168` (`analyse_run`).
- **Evidence:** `stack.json` is never read. Of the plan section 3 validity rules, only generator CPU (≤70% over 30 s)
  and clock offset (<50 ms) are checked. Not checked: same image digest, RDS class and WAF mode as the campaign;
  capacity pinned as D3 requires (1 unit; 2 for `replace`; 1 to 2 for `scaleout`); healthy targets as intended at
  measurement start; one variant under load.
- **Impact:** non-comparable runs are counted as valid without a warning, e.g. the digest mismatch of INF-001, a ladder
  run with pinning forgotten (min 1, max 2), the WAF left in block mode after the security test, or a run started before
  the second target was healthy.
- **Direction:** read `stack.json`; mark a run invalid when digest, RDS class or WAF action differ from the campaign, or
  min/max/desired don't match the run type; use `alb_healthy_hosts` at the window start for the healthy-target rule.

#### INF-004 — Medium — area F — replacement "error window" is unbounded

- **Location:** `tests/load/analyze.py:208-211` (`replace_timings`).
- **Evidence:** `error_window_s = last error − first error` over every error after the kill, up to the end of the run
  (about 900 s later); `errors_after_kill` counts the same set.
- **Impact:** one unrelated late error (stock-related, a WAF event) stretches the window to many minutes and moves a
  criterion weighted 25.
- **Direction:** bound it to errors between the kill and recovery (plus a small margin); report errors outside that
  window separately.

#### INF-005 — Medium, might fail — area E, D — `secrets.sh get()` swallows every read error

- **Location:** `src/infrastructure/scripts/secrets.sh:31`.
- **Evidence:** `get()` returns `'{}'` on **any** failure of `get-secret-value`, not only "no value yet"
  (ResourceNotFound).
- **Impact:** `fill` runs on every `up.sh ec2`. A transient read failure followed by a successful write generates and
  stores new web, migration and trainer passwords and a new `DJANGO_SECRET_KEY`, contradicting "never regenerates".
  `master-in`/`master-out` after a failed read would write a bootstrap secret holding only the `BOOTSTRAP_*` keys,
  dropping `POSTGRES_HOST`, `POSTGRES_DB` and the copied logins.
- **Direction:** treat only ResourceNotFound as `{}`; fail loudly on any other error.

#### INF-006 — Medium, might bias, unverified — area C — awslogs `mode` not set on either variant

- **Location:** `src/infrastructure/fargate/ecs.tf:67-74`, `src/infrastructure/ec2/user_data.sh.tftpl:82-85`.
- **Evidence:** neither side sets the awslogs `mode` option. Docker defaults to blocking. ECS takes its default from the
  account setting `defaultLogDriverMode`, which (reviewer's recollection, unverified) AWS changed to non-blocking for
  new accounts in 2025.
- **Impact:** every request writes one JSON log line; blocking versus non-blocking logging behave differently under load
  (latency versus dropped lines). An unrecorded A/B difference in the latency criteria.
- **Direction:** set `mode` explicitly and identically on both variants and record it in ADR-017. Confirm the ECS
  default with the observable in "Not verifiable offline".

#### INF-007 — Low, might hang — area E — name-server prompt skipped when any `awsdns` server is delegated

- **Location:** `src/infrastructure/scripts/up.sh:81`.
- **Evidence:** the prompt is skipped if `dig +short NS <domain>` contains any `awsdns` name.
- **Impact:** a rebuild in a new account, or after final teardown, while the registrar still points at an old zone:
  no prompt is shown and the base apply waits for ACM validation until it times out, with no hint why.
- **Direction:** compare the delegated NS set with the new zone's `DelegationSet.NameServers`, not any `awsdns` match.

#### INF-008 — Low — area E — polling loop can kill `up.sh base` while the apply keeps running

- **Location:** `src/infrastructure/scripts/up.sh:82`.
- **Evidence:** `ns="$(aws route53 get-hosted-zone …)"` inside the polling loop has no fallback, under `set -e`.
- **Impact:** a transient API error ends `up.sh` while the background `tf.sh base apply` keeps running on its own; a
  re-run then meets the state lock and the output is confusing.
- **Direction:** tolerate that failure (as line 78 already does), or wait for / stop the apply before exiting.

#### INF-009 — Low — area E — two silent failure paths in `jobs.sh`

- **Location:** `src/infrastructure/scripts/jobs.sh:120`, `138-140`.
- **Evidence:** (a) `read -r exit_code reason < <(aws ecs describe-tasks …)`: if the AWS call fails (expired
  credentials), `read` hits EOF and the script exits under `set -e` with no STOP message. (b) If the `master-out` trap
  fails (credentials expired during bootstrap), the only message is the generic "no working lab credentials".
- **Impact:** (a) an unexplained stop. (b) the RDS master login stays in the bootstrap secret without the operator
  being told (low exposure: LabRole can read the master secret anyway).
- **Direction:** check the describe-tasks result explicitly; when master-out fails, print the exact command to run once
  credentials are refreshed.

#### INF-010 — Low, dead code — area G — unused outputs and an always-empty metric query

- **Location:** `src/infrastructure/modules/web-entry/outputs.tf:47` (`https_listener_arn`);
  `src/infrastructure/base/outputs.tf:89` (`db_instance_identifier`); `alb_arn_suffix`, `target_group_arn_suffix` in
  `ec2/outputs.tf` and `fargate/outputs.tf`, `alb_arn` in `fargate/outputs.tf`; `tests/load/aws_capture.py:170`.
- **Evidence:** both stacks use `depends_on = [module.web_entry]`, so nothing reads `https_listener_arn`. aws_capture
  derives the LB and TG dimensions itself and finds RDS through `describe_db_instances` with a name prefix, so the suffix
  outputs and `db_instance_identifier` are unread. `ECS/ContainerInsights RunningTaskCount` is always empty because
  Container Insights is disabled (ADR-015).
- **Impact:** dead outputs and an always-empty CSV in every Fargate run. ADR-015's statement that the capture "falls
  back" to other metrics is only half true: no fallback code exists (HealthyHostCount is collected anyway).
- **Direction:** either have aws_capture use the outputs and drop its own lookups, or remove the outputs; drop the
  Container Insights query (or use the ECS service events); align ADR-013 and ADR-015 with the result.

#### INF-011 — Low — area G — docs that contradict the code

- **Location:** `docs/AWS_INFRASTRUCTURE.md:34-36`, `:54`; `src/infrastructure/scripts/smoke.sh:8`;
  `tests/load/common.py:13`.
- **Evidence:** (a) AWS_INFRASTRUCTURE.md still says "`fargate/` does not exist" and links
  `scripts/probe-lab-comparison.sh`, deleted in `f36c663`. (b) smoke.sh says it "needs only curl and openssl"; the
  `ec2|fargate` form also needs terraform, jq and the base state file. (c) The harness hard-codes the
  `fourtytwofactors.me` hostnames, while fargate-variant.md section 8 names `domain_name` as the only non-portable input.
- **Impact:** readers are sent to a deleted file; a newcomer in another account finds the harness refuses their domain.
- **Direction:** sync AWS_INFRASTRUCTURE.md (already planned), fix the smoke.sh header, and either derive the
  allow-list from base `shop_hostnames` or the environment, or record the domain as a harness limit.

#### INF-012 — Low — area F — no tests for the timing functions

- **Location:** `tests/load/selftest.py:167` (near `test_analysis`).
- **Evidence:** no test covers `scaleout_timings` or `replace_timings`.
- **Impact:** these feed criteria weighted 10 and 25; INF-004 would have been caught.
- **Direction:** one focused check for each function.

#### INF-013 — Low — area D — operator password in argv on the instance

- **Location:** `src/infrastructure/scripts/jobs.sh:185-186` (`job_operator`).
- **Evidence:** `jq --arg p "$DEMO_OPERATOR_PASSWORD"` and `--secret-string "$(…)"` put the password into process
  argv on the instance (visible in `/proc` while they run).
- **Impact:** brief argv exposure against the "never in argv" rule; low practical risk on a single-user instance.
- **Direction:** write it through a private temp file with `file://`, as `secrets.sh put` already does.

#### INF-014 — Low — area F — saturation table repeats run-wide RDS figures on every step

- **Location:** `tests/load/analyze.py:332-333`.
- **Evidence:** each step row shows the run's overall RDS CPU max and credit minimum.
- **Impact:** reads as a per-step value; could mislead the RDS pilot-gate reading.
- **Direction:** compute per step window, or show once per run.

#### INF-015 — Info, might — area B — probe-host lookup depends on list order

- **Location:** `src/infrastructure/fargate/ecs.tf:15`.
- **Evidence:** the IP is read from `/task` → `Containers[0]`. The container's own endpoint
  (`$ECS_CONTAINER_METADATA_URI_V4`, no path) returns that container's `Networks` directly.
- **Impact:** fine with one container; depends on list order otherwise.
- **Direction:** optionally read the container endpoint instead.

#### INF-016 — Info — area C — CPU model not recorded

- **Location:** `tests/load/aws_capture.py:237` (`describe_stack`).
- **Evidence:** no run records the CPU model of the Fargate task or the c5.large host; Fargate does not guarantee a
  processor generation.
- **Impact:** a possible unrecorded hardware difference behind "matched compute".
- **Direction:** record the CPU model once per session (for example from a one-off task's log) and state it in the
  report.

### Checked and passed (do not re-review unless the code changes)

**A. Module and ec2 refactor**

- The module holds the same resources and settings as the verified `c4ae7c4` files: 7 security-group rules, ALB, target
  group (port 8000, `/health/`, interval 10, timeout 5, healthy 2, unhealthy 3, 30 s deregistration, no stickiness),
  both listeners, TLS policy `ELBSecurityPolicy-TLS13-1-2-2021-06`, WAF rule and association, 3 alarms, 2 saved queries,
  log group, alias record.
- Names unchanged (module `name` = `stack_prefix`). Only two descriptions changed: `sg-app` now says "App compute" (a
  security-group description forces replacement, harmless while ec2 is torn down), and the `sg-db` rule description now
  uses `${stack}`.
- The rendered `/etc/inf2006/app.env` has the same 8 keys and values as at `c4ae7c4`; only the order changed.
- No dependency cycles; provider inherited correctly (the module only declares `required_providers`).
- Resource-count claims match the code: ec2 25 resources, fargate 27.

**B. fargate**

- Probe-host command: the Dockerfile has no ENTRYPOINT; `python` and `sh` exist in the image; `exec` makes gunicorn
  PID 1; under dash `set -e`, a failed command substitution in the `IP=` assignment stops the task; Django accepts
  `private-IPv4:8000` (`src/config/settings.py:42-50`, `src/config/middleware.py` HealthProbeMiddleware); the `tf.sh`
  drift check matches today's `CMD` exactly.
- `awsvpc` with public IP, LabRole as task and execution role, task CPU/memory, the `service/<cluster>/<service>`
  resource ID and the `alb/tg` scaling resource label are correct.
- Destroy order: the service depends on the module (listener exists before the service; service destroyed first).
- Log stream `web/web/<task-id>` in `jobs.sh` matches the awslogs prefix format.
- `jobs.sh ecs_task`: the NUL-separated `jq --argjson` handling of option-like words is correct; the container override
  of `AWS_SECRET_ID` wins over the task definition value.

**C. Fairness**

- Matched by construction: module, Gunicorn workers, health check, deregistration delay, scaling metric and target 300,
  min/max/desired variable names, WAF, alarms, environment.
- The documented pairings (ASG warm-up 240 s vs ECS cooldowns 300 s; grace 300 s vs 120 s) are recorded in ADR-017.

**D. Security**

- No port 22. The loadgen has no inbound rules and requires IMDSv2.
- Task definition and user data hold only the secret name, never a value; `secrets.sh` writes values through a 0600
  temp file, never argv.
- The bootstrap master-in/out trap runs on error and on INT, TERM and HUP (tested).
- Provider lock files are committed with 4 h1 hashes per folder, so `init` on another platform should not dirty the tree.

**E. Scripts**

- `tf.sh` clean-tree check and plan-commit guard work; `.plan-commit` and `*.tfplan` are git-ignored.
- `status.sh` is read-only; its state count is 0 after a destroy (empty `resources`).
- `down.sh` leftover filters match the names and tags used.

**F. Load harness**

- Determinism: inputs sorted; output byte-identical (self-test).
- Statistics: nearest-rank percentiles; p95 only from 100 samples, p99 only from 1,000.
- Windows match plan section 6; abort rule matches section 3; pacing never catches up in bursts; user IDs unique across
  Locust processes.
- Cleanup requests excluded from statistics and the abort count; redaction covers 12-digit account IDs (including in
  ARNs) and public IPv4; no password logged or passed in argv by `run.py`, `accounts.py` or `locustfile.py`.
- The WAF `Rule` dimension (`<name>-login-rate`) matches the module's rule metric name; target-tracking alarm prefixes
  match both variants.

### Not verifiable offline (the first apply must confirm)

**Fargate apply and roles**

| Assumption | Observable that confirms it |
|---|---|
| LabRole can be assumed by `ecs-tasks.amazonaws.com` | `aws iam get-role --role-name LabRole --query Role.AssumeRolePolicyDocument` lists `ecs-tasks`; the first task reaches RUNNING |
| ECS and Application Auto Scaling service-linked roles exist or can be created in the lab | `aws iam get-role --role-name AWSServiceRoleForECS` and `--role-name AWSServiceRoleForApplicationAutoScaling_ECSService`; the scalable target registers without AccessDenied |
| The metadata path returns the task's private IP | First task's log lines; `aws elbv2 describe-target-health` shows the task `healthy` |
| `wait_for_steady_state` fails the apply after a circuit-breaker rollback instead of reporting success | Deliberate bad-image apply: apply exit code, and `rolloutState` in `aws ecs describe-services` |
| Fargate vCPU quota allows 2 tasks | Scale-out run's ECS events show "has started 1 tasks" with no capacity error |
| ECS default log driver mode (INF-006) | `aws ecs list-account-settings --name defaultLogDriverMode --effective-settings` |
| A second plan right after apply shows no task-definition diff (environment order normalised) | `scripts/tf.sh fargate plan` right after the apply shows "No changes" |
| Security-group / ENI release delay on destroy is short | How long `scripts/down.sh fargate` takes |

**Harness and loadgen metrics**

| Assumption | Observable that confirms it |
|---|---|
| CloudWatch series exist under the dimensions used: EC2 `AutoScalingGroupName` at 1-minute granularity; `AWS/ECS` with ClusterName + ServiceName; `RequestCountPerTarget` and `HealthyHostCount` with TargetGroup + LoadBalancer; `AWS/WAFV2` with WebACL + Rule + Region | `aws cloudwatch list-metrics --namespace <ns> --dimensions …` during the pilot; non-empty CSVs under the run's `cloudwatch/` folder |
| The loadgen installs `python3.12`, and chrony reaches the Amazon Time Sync Service with only HTTPS allowed out | `/var/lib/loadgen-ready` exists; `chronyc tracking` reports an offset |

**Other**

| Assumption | Observable that confirms it |
|---|---|
| `release-c19d547` (the recorded digest) is still in ECR | `aws ecr describe-images --repository-name inf2006-grp21-app --image-ids imageTag=release-c19d547` |

### Limitations of this round

- shellcheck not installed; only `bash -n` was run.
- No AWS access: every AWS-behaviour statement above is from documentation knowledge, not observation. INF-006's
  claim about the ECS default log mode is from the reviewer's memory and must be checked.
- Locust is not installed locally, so `locustfile.py` was reviewed by reading only (the self-test does not import it).

### Next step

Hand the findings the user approves to the fixer (per DEVELOPMENT.md), then a round 2 review of the revised diff by
the same reviewer tier, keeping these IDs. Record fixes and round 2 results below this line; do not edit round 1.

## Fixes applied after round 1 (6 October 2026, before round 2)

Fixer: the writing session (Claude Sonnet 5.5), at the user's request and with their decisions recorded below. Not committed at the time of writing; round 2 reviews the resulting diff. Offline checks after the fixes: `terraform fmt -check` and `validate` for all five folders, `bash -n` on every script, stub tests of the changed scripts, `tests/load/selftest.py` 14 of 14 (was 10).

| ID | Disposition |
|---|---|
| INF-001 | Fixed. `up.sh` copies the image another stack already runs and builds only when neither has one; `tf.sh ec2\|fargate plan` stops when the two image tags differ (`ALLOW_IMAGE_MISMATCH=1` overrides, for a deliberate rollout test). Tested with scratch copies. |
| INF-002 | **User decision: graceful on both variants.** `aws_capture.py kill` on A now calls the Auto Scaling `terminate_instance_in_auto_scaling_group` (ShouldDecrementDesiredCapacity false); B keeps `stop_task`. `kill.json` records `mode: graceful`. ADR-017, the harness README and plan section 15 say the test measures a planned replacement, not a crash. |
| INF-003 | Fixed. `analyze.py` reads `stack.json`: campaign reference (most common digest, RDS class, WAF mode), pinned capacity per run type, variant label, and healthy targets at the start from `alb_healthy_hosts`. Missing data is flagged "not verified", not invalid. "One variant under load" stays a procedure. |
| INF-004 | Fixed. The error window runs from the kill to healthy again plus 30 s; later errors are counted apart (`errors_later`). |
| INF-005 | Fixed. `secrets.sh get()` treats only ResourceNotFoundException as an empty secret and stops on any other error. Tested with a stub `aws`. |
| INF-006 | Fixed by setting the awslogs `mode` to `blocking` explicitly on both variants (so the question of the ECS default no longer matters); recorded in ADR-017. The ECS default itself is still to be confirmed with the observable in "Not verifiable offline". |
| INF-007 | Fixed. The name-server prompt is skipped only if the registrar's delegation equals this zone's four servers. |
| INF-008 | Fixed. The lookup inside the polling loop tolerates a transient failure and retries. |
| INF-009 | Fixed. `describe-tasks` failure stops with a message; a failed `master-out` prints the exact command to run after `labcreds`. |
| INF-010 | Fixed by removal: `https_listener_arn`, `alb_arn`, `db_instance_identifier` and the stack-level suffix outputs are gone; the empty Container Insights query is gone. ADR-013 and ADR-015 corrected. |
| INF-011 | Fixed. AWS_INFRASTRUCTURE.md no longer says `fargate/` does not exist or links the deleted probe; the `smoke.sh` header lists its real needs; the harness takes `LOAD_DOMAIN` for another domain. |
| INF-012 | Partly disagreed: `test_analysis` already asserted the scale-out and replacement timings, but never a late error. Added tests for the bounded window (late error, never recovered), stack validity (11 cases), per-step database figures and the CPU record. |
| INF-013 | Fixed. The operator password reaches `put-secret-value` through a 0600 temp file (`jq` reads it from the environment), not argv. |
| INF-014 | Fixed. RDS CPU and credit balance are computed per window. |
| INF-015 | Fixed. The probe-host lookup reads the container's own metadata document (no `/task`, no list position); ADR-016 updated. |
| INF-016 | Done as a command: `aws_capture.py cpu --variant ...` (SSM on A, a one-off task on B) saves the CPU model; `export` adds it to each run and the report prints it. Untested against real AWS. |

### Next step

Round 2: a fresh Opus 5.5 session reviews only the diff since `f36c663`, keeping the INF IDs.


## Round 2 (6 October 2026)

- **Diff reviewed:** `f36c663..6ab07ef` (26 files), with the fixes table above as the fixer's account of each INF ID.
- **Reviewer:** Claude Opus 5.5 (`claude-opus-5-5`). **The same session that wrote round 1**: it did not write the fixes
  and had no access to the fixing (Sonnet 5.5) conversation. Because it re-checked its own round 1 findings, it may
  share their blind spots; this is the same-session disclosure DEVELOPMENT.md asks for. Read-only for code: the only
  file written is this log.
- **Extra asks from the user:** (1) look for regressions the fixes introduced, especially the stack-validity rules in
  `analyze.py` and the new `aws_capture.py cpu` command; (2) challenge the fixer's disagreement on INF-012.

### Checks run

| Check | Result |
|---|---|
| `terraform validate` and `fmt -check -recursive` for `base`, `ec2`, `fargate`, `loadgen`; `fmt -check` for `modules/` | All pass (same local-tfvars warnings on `base/` as round 1). No new `init` was needed, so no files were created |
| `bash -n` on all scripts | Pass. shellcheck still not installed |
| `python3 tests/load/selftest.py` | 14 of 14 PASS |
| `git show f36c663:tests/load/selftest.py` | Checked what `test_analysis` asserted before the fix (INF-012) |
| Grep for the removed outputs and the removed metric across docs, scripts and harness | Two docs still name them (INF-017) |
| `base/storage.tf` | ECR `image_tag_mutability = "IMMUTABLE"` confirmed, so `tf.sh` comparing tags (not digests) is sound |

### Status of round 1 findings

No round 1 finding recurs, so the repeat-after-fix stop rule is not triggered.

| ID | Round 2 status | Notes |
|---|---|---|
| INF-001 | **Resolved** | `need_image` copies the other stack's `image.auto.tfvars` and builds only when neither stack has one; `tf.sh ec2\|fargate plan` stops on unequal tags. Equal tags mean equal bytes because ECR tags are immutable |
| INF-002 | **Resolved** (user decision: graceful on both) | Recorded in ADR-017, plan section 15 and the harness README. That the group drains before terminating is an AWS assumption; see "Not verifiable offline (round 2)" |
| INF-003 | **Resolved**, with new issues | Rules implemented as described. New weaknesses in the fix: INF-018, INF-019, INF-020 |
| INF-004 | **Resolved** | Window bounded to recovery + 30 s (to run end + 30 s if never recovered); `errors_later` reported; covered by `test_replace_error_window_is_bounded` |
| INF-005 | **Resolved** | Only ResourceNotFoundException becomes `{}`; any other error dies inside the command substitution, and `set -e` stops the caller. Observation, not a finding: `2>&1` also merges stderr into a *successful* read, so a CLI warning on stderr would corrupt the JSON. Unlikely with AWS CLI v2 |
| INF-006 | **Resolved** | `mode=blocking` on the EC2 web and job containers and on the ECS task; recorded in ADR-017 |
| INF-007 | **Resolved** | Prompt skipped only when the sorted, lower-cased, dot-stripped delegation equals this zone's four servers; without `dig`, the prompt always shows (safe) |
| INF-008 | **Resolved** | Both lookups tolerate failure and retry on the next round |
| INF-009 | **Resolved** | describe-tasks failure dies with a message; `bootstrap_cleanup` (a function, inherited by the subshell trap) prints the exact master-out command when it fails |
| INF-010 | **Resolved in code** | Outputs and the query removed; ADR-013 and ADR-015 corrected. Two other docs still list the removed outputs: INF-017 |
| INF-011 | **Resolved** | AWS_INFRASTRUCTURE.md synced, smoke.sh header correct, `LOAD_DOMAIN` with validation; `run.py` derives the variant from the same map |
| INF-012 | **Withdrawn: the fixer's disagreement is upheld** | At `f36c663`, `test_analysis` already asserted `detection_s`, `provisioning_s`, `scale_out_s`, `total_from_load_s` (scale-out) and `detected_s`, `replacement_s`, `error_window_s`, `errors_after_kill` (replacement). The round 1 statement "no test covers `scaleout_timings` or `replace_timings`" was wrong. The real gap was narrower: no case had an error after recovery, which is how INF-004 went unnoticed. The new bounded-window test closes it |
| INF-013 | **Resolved**, small residue | Password now reaches `put-secret-value` through a 0600 file and `$ENV`, not argv. Residue: INF-023 |
| INF-014 | **Resolved** | Per-window RDS CPU and credits (`in_window` uses minute-start timestamps correctly); covered by `test_database_figures_per_step` |
| INF-015 | **Resolved** | Reads the container's own metadata document (`Networks[0].IPv4Addresses[0]`); ADR-016 updated |
| INF-016 | **Addressed**, accuracy issue | A CPU model is now recorded and reported, but it may not be the hardware that served the load: INF-021 |

### New findings (round 2)

All **open**. None blocks an apply.

#### INF-017 — Low — area G — two docs still list the outputs INF-010 removed

- **Location:** `docs/plans/fargate-variant.md:40`; `docs/plans/load-harness.md:200`.
- **Evidence:** fargate-variant.md's outputs row still names `alb_arn_suffix` and `target_group_arn_suffix` as
  `fargate/` outputs. load-harness.md section 10 item 4 still asks for them and `db_instance_identifier`, and section 15
  (as built) does not record that they were dropped.
- **Impact:** a reader or an agent checking "plan vs code" finds outputs that do not exist.
- **Direction:** update the outputs row; add one line to load-harness.md section 15 saying they were not added (INF-010).

#### INF-018 — Low — area F — the campaign reference is a majority vote, not a stated value

- **Location:** `tests/load/analyze.py:142-150` (`campaign_reference`).
- **Evidence:** the reference digest, RDS class and WAF mode are whichever value most runs share; ties go to the
  value that sorts first.
- **Impact:** plan section 3 says that after an RDS resize the old runs are kept (marked superseded) and the affected
  runs rerun. Whichever set is larger then becomes "the campaign", so the current runs can be the ones marked invalid.
  On a tie (for example 3 A runs on one digest and 3 B runs on another), which variant is invalidated depends on the
  digest's spelling.
- **Direction:** take the reference as an explicit input (a flag or a small committed file), and list every distinct
  value found so a split is visible.

#### INF-019 — Low — area F — capacity, image and WAF are checked as they were at export, not during the run

- **Location:** `tests/load/aws_capture.py` `describe_stack` (called from `export`); `tests/load/analyze.py:167-173`.
- **Evidence:** `stack.json` is written by `export`, after the run. The capacity message itself says "at export".
- **Impact:** if pinning, image or WAF mode is changed between a run and its export (for example several runs
  exported at the end of a session after unpinning), a good run is marked invalid, or a bad run passes. The README asks
  for export "before any teardown", not "before any change".
- **Direction:** state in the harness README that `export` must run before any apply. Optionally cross-check pinned
  runs against data from the run itself (for example the maximum of `alb_healthy_hosts` over the measurement window
  must not exceed the pinned count).

#### INF-020 — Medium, might fail (unverified) — area F — healthy-at-start depends on HealthyHostCount aggregation

- **Location:** `tests/load/analyze.py:174-181`; `tests/load/aws_capture.py` query `alb_healthy_hosts`
  (`HealthyHostCount`, dimensions TargetGroup + LoadBalancer, statistic Average).
- **Evidence:** the check requires the last 1-minute Average before measurement start to equal exactly 1 (or 2 for
  `replace`, within 0.01). The value this aggregate reports when targets sit in two Availability Zones has not been
  observed. The reviewer is not certain the zone-less dimension reports the total rather than a per-zone or
  per-load-balancer-node figure.
- **Impact:** if the series reports per zone, every replacement run (two units, usually in two zones) reads 1 and is
  marked invalid. A minute with a target mid-transition averages to a fraction and fails the 0.01 tolerance even when
  the start itself was fine.
- **Direction:** for `replace` and `scaleout` use `targets.jsonl` (the watcher's exact, timestamped healthy count,
  already exported for those runs) instead of CloudWatch. Confirm the CloudWatch semantics on the first pilot before
  relying on it for the other run types.

#### INF-021 — Low — area C, F — the recorded CPU model may not be the hardware that served the load

- **Location:** `tests/load/aws_capture.py` (`record_cpu`, `run_in_task`; `export` copies `aws-out/cpu-<variant>.json`).
- **Evidence:** on B the model comes from a separate one-off task, which Fargate may place on different hardware from
  the service's tasks. On A it comes from the lexically first in-service instance. `export` copies whatever
  `cpu-<variant>.json` exists, with no check that it is from the same session (its `ts_utc` is not compared with the
  run's time).
- **Impact:** the report can name a processor that did not serve the run, for example a stale file from an earlier
  session, or a one-off task on newer hardware than the service task.
- **Direction:** have `export` flag a `cpu.json` older than the run's stack (or than a set age). Simpler and exact:
  have the serving containers log the model at start-up (one `grep` line in the Fargate `web_command` before `exec`,
  and in the EC2 user data), so each unit's hardware is in its own log stream.

#### INF-022 — Low — area F, G — `aws_capture.py cpu`: a false docstring and an unclear failure

- **Location:** `tests/load/aws_capture.py` module docstring (the `kill` paragraph), `run_in_task`.
- **Evidence:** the docstring still says "kill is the only command here that changes AWS". `cpu` now also starts a
  Fargate task (billed; creates a log stream) or sends an SSM command. `run_in_task` never checks the task's exit code
  or stop reason, so an image-pull or permission failure ends in a `ValueError` traceback from `parse_cpu`
  ("no 'model name' line") rather than a STOP message naming the cause.
- **Impact:** a misleading safety statement; an opaque error on the first real use (the command is untested against
  AWS).
- **Direction:** correct the sentence; read `stoppedReason` and the container exit code before parsing.

#### INF-023 — Low — area D — the operator password file can be left behind on failure

- **Location:** `src/infrastructure/scripts/jobs.sh` `job_operator` (the remote script, after the `umask 077` line).
- **Evidence:** `rm -f "$F"` runs only if `put-secret-value` succeeds. Under the remote script's `set -euo pipefail`,
  a failed put exits first and leaves the 0600 root-owned file holding the password in the instance's `/tmp`.
- **Impact:** small: root-only file on a single-purpose instance, gone when the instance is replaced. But it is the
  one place this flow persists the password outside Secrets Manager.
- **Direction:** remove the file in a `trap … EXIT` inside the remote script.

### Regression check on the areas the user named

- **Stack-validity rules (`analyze.py`):** logic is correct against its own tests (11 cases), and output stays
  deterministic (sorted inputs; ties resolved by sorted order). Weak points are INF-018, INF-019 and INF-020. The
  variant-mismatch rule, the per-type capacity table and the "flag, don't invalidate when data is missing" behaviour
  match plan section 15 item 12.
- **`aws_capture.py cpu`:** parameters pass botocore's stubbed models (`test_cpu_model_record`). `grep` and `nproc` exist
  in the Debian-based image, and user 10001 can read `/proc/cpuinfo`. Issues: INF-021 and INF-022.
- **Other fixed code checked for regressions, none found:**
  - the `tf.sh` image check (runs at plan only, skips when either file is missing, can be overridden);
  - `up.sh` `need_image` (copies in either direction, builds only when neither stack has an image);
  - `secrets.sh` `get` under `set -e`;
  - the `jobs.sh` `ecs_task` result read;
  - the trap function in the bootstrap subshell;
  - the Fargate metadata read;
  - the module and stack outputs (no remaining reference to a removed output in code; `terraform validate` passes).

### Verdict (round 2)

**Ready to apply.** Nothing blocks `up.sh ec2` or `up.sh fargate`.

**Before trusting load-run validity, address INF-020** (or confirm the HealthyHostCount semantics on the first
pilot). The other round 2 findings are Low.

### Not verifiable offline (round 2 additions)

These add to the round 1 list.

| Assumption | Observable that confirms it |
|---|---|
| `terminate-instance-in-auto-scaling-group` deregisters and drains (30 s) before terminating, as `StopTask` does on ECS (INF-002 fix) | During the first A replacement run, `targets.jsonl` shows the killed instance `draining` before it disappears, and the ASG activity for it starts at the kill time with termination about 30 s later |
| `HealthyHostCount` (TargetGroup + LoadBalancer, Average) reports the total healthy targets across zones (INF-020) | With two healthy targets in two zones, `aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB --metric-name HealthyHostCount --dimensions Name=TargetGroup,Value=… Name=LoadBalancer,Value=… --statistics Average --period 60 …` returns 2.0 |
| ECS accepts `mode = "blocking"` in the awslogs options, and Docker accepts `--log-opt mode=blocking` with awslogs | The task definition registers; on A, `docker inspect web --format '{{.HostConfig.LogConfig}}'` shows `mode:blocking` |
| The container metadata document on Fargate has `Networks[0].IPv4Addresses[0]` | The first task becomes healthy (same observable as round 1) |
| `aws_capture.py cpu` works end to end (SSM on A, one-off task and log on B) | `aws-out/cpu-ec2.json` and `cpu-fargate.json` are written on the first session |

### Next step

Hand the open findings the user approves (INF-017 to INF-023) to the fixer; the same reviewer tier reviews that diff
in round 3, keeping these IDs. INF-012 is closed (withdrawn).

## Fixes applied after round 2 (6 October 2026, before round 3)

Fixer: the writing session (Claude Sonnet 5.5). Offline checks: `terraform fmt -check` and `validate`, `bash -n`, `tests/load/selftest.py` 15 of 15 (was 14).

| ID | Disposition |
|---|---|
| INF-017 | Fixed. fargate-variant.md and load-harness.md section 10 list the outputs that exist and say the suffix outputs and `db_instance_identifier` were not added. |
| INF-018 | Fixed. `analyze.py --reference FILE` states the campaign's fixed values; without it the majority is used, and the report lists every distinct value found and warns when runs disagree. |
| INF-019 | Fixed in the README: `stack.json` describes the stack at export, so export before any apply, unpinning or WAF change. The optional cross-check was not added. |
| INF-020 | Fixed as the reviewer directed: scale-out and replacement runs read the healthy count from the watcher's `targets.jsonl` (exact); the CloudWatch average is used only for single-unit runs, where there is nothing to disagree about, and its semantics are still to be confirmed on the first pilot. A missing watcher record is flagged, not invalid. |
| INF-021 | Partly. `analyze.py` flags a CPU model recorded more than 12 h from the run. The start-up log line in the serving containers was not added: it would not be uniform (the EC2 container's start command cannot log it without changing the image or the Docker command), so the limitation (a one-off task may differ from the serving task) is left for the report to state. |
| INF-022 | Fixed. The docstring no longer claims `kill` is the only command that changes AWS; `run_in_task` reads the exit code and stop reason and stops with the cause. Tested with a task that fails to pull. |
| INF-023 | Fixed. The operator password file is removed by a trap in the remote script, so a failed put leaves nothing behind. |

### Next step

Round 3: re-check only the diff since `6ab07ef`, keeping the INF IDs.


## Round 3 (6 October 2026)

- **Diff reviewed:** `6ab07ef..41e6ed2` (8 files), with "Fixes applied after round 2" as the fixer's account.
- **Reviewer:** Claude Opus 5.5 (`claude-opus-5-5`), the same session as rounds 1 and 2. It did not write the fixes and
  had no access to the fixing conversation. The same-session disclosure from round 2 applies: it reviews its own earlier
  findings and may share their blind spots.
- **Where the user asked to look hardest:**
  - the `targets.jsonl` healthy-count rule;
  - `--reference` and the distinct-value warning;
  - the exit-code check in `run_in_task`;
  - challenge the decision to leave out the start-up CPU log line (INF-021).

### Checks run

| Check | Result |
|---|---|
| `python3 tests/load/selftest.py` | 15 of 15 PASS |
| `bash -n src/infrastructure/scripts/jobs.sh` (the only script changed) | Pass |
| Terraform | Not re-run: no `.tf` file changed in this diff |
| Probe: `analyze.campaign_reference(runs, {"rds-class": "db.t4g.medium"})` (a misspelled key) | The key is silently ignored and the majority value is used (INF-024) |
| Grep of README, plan, ADRs and `analyze.py` for the one-off-task CPU limitation | Not stated anywhere outside this log (INF-021) |

### Status of earlier findings

| ID | Round 3 status | Notes |
|---|---|---|
| INF-017 | **Resolved** | fargate-variant.md lists the outputs that exist; load-harness.md section 10 says the three outputs were not added and why |
| INF-018 | **Resolved**, with a new edge: INF-024 | `--reference` overrides the majority; every distinct value is listed with run counts in sorted order (output stays deterministic); a warning is printed when runs disagree. Tested, including the RDS-resize case |
| INF-019 | **Resolved** (documentation, as directed) | README says `stack.json` describes the stack at export time and to export before any apply, unpinning or WAF change. The optional cross-check was not added; that is acceptable |
| INF-020 | **Resolved for the two-unit runs**; residual stays in "Not verifiable offline" | `scaleout` and `replace` take the last watcher record at or before the measurement start. That is exact, because `watch` writes a record as soon as it starts and on every change; a missing record is flagged, not invalid. Tested (good, bad, no watcher). **Residual:** the fixer's reason for keeping CloudWatch on single-unit runs ("nothing to disagree about") overstates it. If the zone-less series averaged per-zone or per-node reports, one healthy target could read 0.5 and fail the 0.01 tolerance. That is still the round 2 not-verifiable item, now named in the README as "confirmed on the first pilot". A simpler way to remove it: run `watch` for every run type and use `targets.jsonl` everywhere. Not a new finding |
| INF-021 | **Partly resolved; part still open, and it is the user's call** | See "INF-021: challenge" below |
| INF-022 | **Resolved** | The docstring no longer claims `kill` is the only command that changes AWS, and says what `cpu` costs. `run_in_task` keeps the last `describe_tasks` result and stops on a non-zero or missing exit code, showing `stoppedReason`. Tested with a stubbed `CannotPullContainerError` |
| INF-023 | **Resolved** | `trap 'rm -f "$F"' EXIT` is set right after `mktemp`, after the early `exit 0` branch. The heredoc is quoted, so `$F` expands on the instance; `F` is defined before the trap can fire under `set -u` |

### INF-021: challenge of the fixer's decision

The fixer left out the start-up CPU line because it "would not be uniform": the EC2 container runs the image's own CMD,
so only Fargate could log the model at start-up without changing the image or the Docker command.

**The uniformity argument does not hold.** The goal is to record the hardware that served each run, not to collect it
the same way on both variants:

- **On A:** the CPU model is a property of the host, which the container shares. In the pinned single-unit runs, the
  SSM read in `aws_capture.py cpu` already lands on the serving instance, so A's figure is exact provided it is taken
  in the same session. That matters here because a `c5.large` can be either of two Xeon generations.
- **On B:** the figure comes from a separate one-off task, which Fargate may place on different hardware. B's figure
  is the only inexact one, and the start-up line would fix exactly that.

**The cost of adding it is small:**

- one line before `exec` in `fargate/ecs.tf`'s `web_command`, for example `grep -m1 'model name' /proc/cpuinfo || true`;
- `|| true` is needed because of `set -eu`;
- the `tf.sh` drift check is unaffected, because it matches only the `exec gunicorn …` line;
- each serving task's model would then be in its own log stream.

**What is still open either way:** the limitation is not written where a report author or marker will see it. The
README, plan section 15, ADR-015/017 and `analyze.py`'s "CPU model" line all present B's figure as the hardware,
without saying it comes from a one-off task that may not have served the load. It is mentioned only in this review log.

**Under DEVELOPMENT.md this is an unresolved finding after its remediation attempt**, so it goes to the user, not to
another fixer retry. The user picks one:

- **(a) Accept the limitation.** State it in the harness README and in `analyze.py`'s "CPU model" line (for example
  "fargate: from a one-off task; the serving task may differ").
- **(b) Add the start-up line** to the Fargate `web_command`.

**Reviewer's recommendation:** (b), which removes the limitation, keeping `aws_capture.py cpu` for A.

### New findings (round 3)

Both **open**. Neither blocks an apply or a load run.

#### INF-024 — Low — area F — `--reference` silently ignores unknown keys and over-claims in the report

- **Location:** `tests/load/analyze.py` `campaign_reference` (the `ref.update(...)` line) and the "Campaign reference"
  header in `main`.
- **Evidence:** keys not in `CAMPAIGN_KEYS` are dropped without a message. The probe above: `{"rds-class": …}` left the
  majority value in place. The header still reads "stated by the user in reference.json" whenever the file is given,
  even if it covers only some keys, or none because of a typo. A JSON file that is not an object (a list) raises an
  unhandled `AttributeError`.
- **Impact:** the user believes the reference is pinned while the majority decides, which is exactly the INF-018
  failure the option exists to prevent. The report then attributes it to the user.
- **Direction:** stop on an unknown key or a non-object file. In the header, say per setting whether the value was
  stated or taken from the majority.

#### INF-025 — Info — area F — two clocks meet in the replacement and healthy-start figures

- **Location:** `tests/load/analyze.py` `replace_timings` and `check_stack`; `aws_capture.py` (`kill.json`,
  `targets.jsonl`).
- **Evidence:** `kill.json` and `targets.jsonl` carry the laptop's clock. The request rows and `timing.json` carry the
  generator's clock, whose offset is checked (under 50 ms). The laptop's offset is never recorded.
- **Impact:** a laptop clock off by seconds would shift which errors fall inside the bounded error window (INF-004) and
  which watcher record counts as "at the start". Small with chrony on Fedora, but unmeasured, in a criterion weighted
  25. Not introduced by this diff; noted because the round 2 fixes made both rules depend on it.
- **Direction:** record the laptop's `chronyc tracking` offset in `kill.json` and at the start of `watch`, and apply the
  same 50 ms rule.

### Verdict (round 3)

**Ready to apply** (no change in this diff touches Terraform; the one script change passes `bash -n`).

- **For the load campaign:** decide INF-021 ((a) or (b)) before the first recorded Fargate run, because it decides
  whether B's hardware line in the report is true.
- **INF-024:** should be fixed before `--reference` is relied on.
- **INF-025:** information only.

### Next step

1. The user decides INF-021 (a) or (b).
2. INF-024 (and optionally INF-025) go to the fixer.
3. Round 4 reviews that diff, keeping these IDs.

## Decisions after round 3 and close-out (6 October 2026)

The user chose to wrap up: about 3 to 4 days remain before the deadline, so low-value work is skipped.

| ID | Decision | Done |
|---|---|---|
| INF-021 | **User chose (a): accept and state the limitation.** No start-up CPU line | The limitation is now stated in the harness README (the `aws_capture.py cpu` paragraph) and in `analyze.py`'s "CPU model" report line. This is a two-line documentation change, made by the reviewer session at the user's direction; `selftest.py` still passes 15 of 15. **Closed** |
| INF-024 | **Accepted, not fixed** (low value for the time left) | Procedure: check the "Campaign reference" line at the top of the report against the reference file. The distinct-value warning still appears whenever runs disagree. **Closed as a known limit** |
| INF-025 | **Accepted, not fixed** (Info) | Keep the laptop clock synced (chrony is on by default on Fedora). **Closed as a known limit** |

**Final state:**

- No finding is open.
- The round 2 and round 3 "Not verifiable offline" items stay as the checklist for the first apply and the first pilot.

**Role note:** the INF-021 documentation edit was written by the reviewing session, not a separate fixer, at the
user's request. It changes text only. No separate review round was run for it.
