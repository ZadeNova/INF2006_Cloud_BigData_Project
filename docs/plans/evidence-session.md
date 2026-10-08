# Runbook: the AWS evidence session (variant A and variant B, 8 October 2026)

**Status (8 October 2026):** written after the readiness review ([evidence-session-readiness.md](../reviews/evidence-session-readiness.md)); not yet run. Follow it top to bottom. The user runs every command; nothing here needs Claude during the session. Times are a guide, the stop rules are not.

**What the session produces:** the cloud evidence for the brief's four tests, identical on both variants: functional (FUNC-03), security (SEC-09, 10, 11, 17, 18), scalability and resilience (RES-03a, RES-03b, saturation), monitoring (MON-01 to MON-04). Expected results are already written in the evidence files; you fill in "Actual" afterwards (or hand the raw files to Claude).

**Order:** A (EC2) completely, reset the database, then B (Fargate) completely, then reset again as the final cleanup; each variant has the same steps in the same order, on the same generator. The reset cannot cover CPU credits or cache of the database: state that in the report.

## 0. Before Start Lab (offline, about 20 minutes)

1. **Commit everything first.** `tf.sh` refuses to plan with uncommitted changes under `src/infrastructure/`, and an apply must come from the commit its plan was made on. Do not commit again during the session (evidence files under `evidence/` are fine to leave uncommitted until the end).
2. **Laptop harness** (once): `cd tests/load && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && cp .env.example .env`, then set `LOADTEST_PASSWORD` in `.env` (any strong password; it never leaves the laptop and the generator's shell).
3. **Session Manager plugin** installed (`session-manager-plugin --version`), needed to open a shell on the generator.
4. **Harness bundle for the generator** (EVD-013: the generator gets the code with its git history, never `.env`):
   ```bash
   mkdir -p ~/evidence-scratch && git bundle create ~/evidence-scratch/repo.bundle HEAD
   ```
5. Optional, 10 minutes: check `tests/load/prices.json` against the AWS price pages and set `"verified_by_user": true`. Otherwise every cost is flagged unverified.
6. Know where the lab timer and the lab balance are on the Learner Lab page.

## 1. Terminals

| Terminal | Where | Set up with |
|---|---|---|
| **T1 infra** | repository root, laptop (open a second tab, **T1b**, in the same place for things that run in parallel) | `labcreds` in each tab |
| **T2 harness** | `tests/load/`, laptop | `labcreds; . .venv/bin/activate; set -a; . ./.env; set +a` |
| **T3 generator** | Session Manager shell on the load generator, inside `tmux` | section 3 |

`E=src/infrastructure/scripts/evidence.sh` in T1 saves typing (`$E ec2 security`). Every `evidence.sh` step writes dated, redacted files to `evidence/raw/` and prints `>> saved ...`; a rerun gets `_rerun`, nothing is overwritten.

## 2. Stop rules (read before starting)

- **Timer:** never start a recorded run unless the lab timer shows the run length plus 25 minutes. At 30 minutes left, start nothing new: export, `logs`, `down`. Learner Lab lets you reset the timer by pressing Start Lab again (unverified; check it once early); then run `labcreds` again in T1 and T2.
- **Credentials:** run `labcreds` in T1 and T2 before every scale-out and replacement run. If `watch` dies with an expired token, restart it with the same `--run-id`; it appends.
- **A run marked invalid** is rerun at most once; a second failure is recorded with its diagnosis and you move on.
- **Variant A:** `up` plus smoke 8 of 8 not done within 45 minutes: no load runs; save the output, `down`, diagnose offline. RDS CPU above 80% in the saturation run: record it as a result, do not resize RDS. The kill does not show `draining` in `watch`: keep the run and note it.
- **Variant B:** preflight says LabRole does not trust `ecs-tasks.amazonaws.com`: do not apply B; the preflight file is the evidence ("designed, blocked by lab IAM"); spend the time on A repeats. No healthy task within 15 minutes of the apply, or `up` not finished in 30 minutes: Ctrl-C once, save `aws ecs describe-services` and the log group, `down`, record "B apply failed: <reason>". An "unable to place" / vCPU limit event when pinning to 2: skip B's scale-out and replacement, run the ladder only.

## 3. Window 1: variant A (about 3 hours)

| Clock | Terminal | Step |
|---|---|---|
| 0:00 | browser | Start Lab. Note the **lab balance** (for the runbook) |
| 0:02 | T1 | `labcreds`; `src/infrastructure/scripts/status.sh`; `$E preflight`. Read the VERDICT lines: they decide whether B runs later, and whether the alarm email is confirmed (if not, click the confirmation link in your inbox now) |
| 0:10 | T1 | `$E ec2 up` (plan, type `yes`, jobs, smoke). About 25 minutes |
| 0:10 | T1b | `src/infrastructure/scripts/up.sh loadgen`, then `B=$(terraform -chdir=src/infrastructure/base output -raw s3_bucket_name); echo $B; aws s3 cp ~/evidence-scratch/repo.bundle s3://$B/exports/tools/repo.bundle` |
| 0:15 | T3 | Generator setup, below |
| 0:35 | T1 | `$E ec2 security` (SEC-09, SEC-10, SEC-11, stack IDs) |
| 0:40 | T1 | `$E ec2 func` (FUNC-03 part 1; it reads `tests/load/.env` itself). Then FUNC-03 part 2 in the browser on `https://shop-ec2.fourtytwofactors.me`, screenshots saved as `evidence/raw/FUNC-03_<date>_ec2_step<N>.png` |
| 0:40 | T3 | `python accounts.py create --base-url $LOAD_BASE_URL` (about 10 minutes; once for both variants, they share the database) |
| 0:50 | T2 | `python aws_capture.py cpu --variant ec2` |
| 0:55 | | **RES-03a scale-out r1** (defaults 1/2/1 are the scale-out setting; no pin needed). Section 5 |
| 1:20 | T1 | `$E ec2 pin 2 2 2 count`; wait for "Healthy", then 3 minutes |
| 1:28 | | **RES-03b replace r1**, section 5. During its quiet 15 minutes after the kill, in T1: `$E ec2 alarm` (MON-03), then save the two emails as screenshots |
| 1:50 | T1 | `$E ec2 pin 1 1 1 count`; wait, 3 minutes |
| 1:57 | | **Saturation r1** (20 min, may stop early on its abort rule), section 5. Afterwards check `evidence/raw/LOAD-ec2-saturation-r1_<date>/cloudwatch/alb_healthy_hosts.csv` reads 1.0 and look at RDS CPU and the CPU credit balance |
| 2:25 | T1 | **Reset the database** (both variants share it; B must start from the same state): dry run `$E rec OPS_<date>_ec2_reset-dry bash -c 'cd tests/load && .venv/bin/python reset_state.py --target ec2'`, read the counts, then the same with `--apply` (name `..._reset-apply`). Every run must already be exported |
| 2:27 | | **WAF test (SEC-17) skipped on A** because of the lab window; the WAF is one shared module, so it is run on B only (decided 9 October). Say so in the SEC-17 record |
| 2:40 | T1 | `$E ec2 logs` (MON-01, MON-02, SEC-18). Check every run of today was exported. Then `$E ec2 down` (type `yes`; removes the pin file) |
| 2:50 | | Done with A. If more than 60 minutes remain, a replace r2 fits at the end; do the same on B later |

### Generator setup (T3, once per day)

```bash
aws ssm start-session --target <instance id printed by up.sh loadgen>
# on the generator:
ls /var/lib/loadgen-ready && tmux new -s load        # if the file is missing, wait a minute (tools still installing)
export AWS_DEFAULT_REGION=us-east-1
B=<the bucket name>                                  # same as on the laptop
cd ~ && aws s3 cp s3://$B/exports/tools/repo.bundle . && git clone repo.bundle inf2006 && cd inf2006/tests/load
aws s3 cp /etc/hostname s3://$B/exports/load/probe.txt   # S3 write test; if AccessDenied see the review section 5
python3.12 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
read -rs LOADTEST_PASSWORD && export LOADTEST_PASSWORD     # type the same password as in the laptop's .env
export LOAD_BASE_URL=https://shop-ec2.fourtytwofactors.me  # for B: https://shop-fargate.fourtytwofactors.me
chronyc tracking | grep 'System time'                      # offset well under 50 ms
```

If the Session Manager connection drops, reconnect and `tmux attach -t load`; the run keeps going.

## 4. Window 2: variant B (about 2.5 hours)

Same generator (if the lab stopped it, `aws ec2 start-instances --instance-ids <id>` and redo the `export` and `cd` lines of the setup). Same steps, same order:

| Step | Command |
|---|---|
| Timer, `labcreds` in T1 and T2 | Preflight already ran today; rerun `$E preflight` only if the lab was restarted |
| Up | `$E fargate up` (it copies A's image, checks the shared secrets, applies, runs `jobs fargate check` and smoke). Watch the stop rules. In a second tab, if it seems stuck: `aws ecs describe-services --cluster inf2006-grp21-fargate-cluster --services inf2006-grp21-fargate-service --query 'services[0].events[:5].message'` |
| Security | `$E fargate security` |
| Functional | `$E fargate func`, then the browser steps on `https://shop-fargate.fourtytwofactors.me` |
| CPU | `python aws_capture.py cpu --variant fargate` (before any pin to 2: it starts a one-off task) |
| Generator | `export LOAD_BASE_URL=https://shop-fargate.fourtytwofactors.me` (accounts already exist) |
| Scale-out r1 | defaults, section 5 |
| Replace r1 | `$E fargate pin 2 2 2 count`, section 5; `$E fargate alarm` after the kill |
| Saturation r1 | `$E fargate pin 1 1 1 count`, section 5 |
| WAF | `$E fargate pin 1 1 1 block`, `$E fargate waf` |
| Reset | Before `down` (it runs through B's stack): dry run, then `--apply`, with `--target fargate`: `$E rec OPS_<date>_fargate_reset-apply bash -c 'cd tests/load && .venv/bin/python reset_state.py --target fargate --apply'`. This is the final cleanup before the demo |
| Logs, down | `$E fargate logs`, then `$E fargate down` (budget 20 minutes: ENIs release slowly; rerun if it times out) |
| Generator down | `src/infrastructure/scripts/down.sh loadgen` (or `$E rec OPS_<date>_loadgen_down src/infrastructure/scripts/down.sh loadgen`) |

## 5. One recorded run (the same for every run type and both variants)

1. Run the **checklist** in [test-performance.md](../../evidence/test-performance.md#checklist-before-every-recorded-run-identical-on-both-variants-review-evd-010): pinned, 3 minutes settled, credentials fresh, timer, carts reset.
2. **T3:** start the run, but do not answer the prompt yet:
   - scale-out: `python run.py scaleout --variant ec2 --base-url $LOAD_BASE_URL --repeat 1 --location us-east-1`
   - replace: `python run.py replace --variant ec2 --base-url $LOAD_BASE_URL --repeat 1 --location us-east-1`
   - saturation: `python run.py saturation --variant ec2 --base-url $LOAD_BASE_URL --repeat 1 --location us-east-1`

   It prints the **run id** (for example `RES-03-ec2-scaleout-r1_2026-10-08`).
3. **T2:** `python aws_capture.py watch --variant ec2 --run-id <RUN-ID>` and leave it running.
4. **T3:** answer `y`.
5. **Replace only:** have `python aws_capture.py kill --variant ec2 --run-id <RUN-ID>` typed in another T2 tab; when T3 prints `NOW: kill one unit`, run it and type `kill`.
6. When the run ends: Ctrl-C the watch. **T3:** `aws s3 cp --recursive out/<RUN-ID> s3://$B/exports/load/<RUN-ID>/`. **T2:** `aws s3 cp --recursive s3://<bucket>/exports/load/<RUN-ID> out/<RUN-ID>` then `python aws_capture.py export --variant ec2 --run-id <RUN-ID> --run-dir out/<RUN-ID>`. Export **before** the next pin, apply or down.
7. **T3**, before the next run: `python accounts.py reset-carts --base-url $LOAD_BASE_URL --from-run out/<RUN-ID>`.

For B, replace `ec2` with `fargate` everywhere.

## 6. After the session (laptop, no lab needed)

1. Leak check on today's evidence (EVD-012); expect only `<ACCOUNT>`, `<PUBLIC-IP>`, `<EMAIL>` markers and no hits for the rest:
   ```bash
   grep -rnE '\b[0-9]{12}\b|@[a-z0-9-]+\.[a-z]|Cookie:|sessionid=|csrftoken=|BEGIN ' evidence/raw/*2026-10-08*
   ```
   Check the screenshots by eye (account number, email address).
2. Check `stack.json` `image_digest` in the first export equals the runbook's digest (EVD-014).
3. Copy the new `terraform.tfstate.*.bak` files off the laptop.
4. `python analyze.py --out ../../evidence/load-summary.md` in T2.
5. Note for the runbook entry: lab balance before and after, apply and destroy times (in `raw/OPS_*`), anything that failed or surprised you.
6. Hand Claude the list of files (or just say "done"): it fills the Actual columns, the runbook entry, RES-04 from the replacement request log, and the comparison write-up, labelled n = 1.

## 7. Not in this session

The 1,000-user RDS pilot, the ladder (u10, u100), Singapore latency, second repeats, a bad-image rollout and Multi-AZ failover. Each is added only if time allows on both variants; otherwise each is a stated limitation.
