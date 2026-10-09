# evidence/raw/ index

`raw/` holds the unedited output behind every claim in the test records (438 files before this index and the eight run-folder READMEs; 288 of them inside the eight run folders). **Nobody needs to read it in bulk.** Start from a test record in [evidence/](../README.md); its "Results at a glance" table names one authoritative file per case; this page lists every case or run folder once (not every file), with its authoritative file and what the other files are.

Words used below:

- **authoritative**: the file the test records cite.
- **superseded by X**: an earlier attempt or output replaced by X; kept because nothing in `raw/` is deleted.
- **failed attempt, kept for honesty**: a command that failed; the failure is part of the record and is explained in the test record or the build runbook.

Dates are UTC. Variant A is EC2 with an Auto Scaling group (`ec2`), variant B is ECS on Fargate (`fargate`). File names are `<CASE>_<UTC date>_<variant>_<step>.txt`; a run folder is `<CASE>-<variant>-<type>-r<repeat>_<UTC date>/`. Every AWS file starts with its UTC date, git commit and exact command, and ends with the exit code. Redactions are `<ACCOUNT>`, `<PUBLIC-IP>` and `<EMAIL>`.

## Run folders (RES-03, LOAD): eight folders, each with its own `README.md`

| Run folder | What it is | Date | Variant | Authoritative file for the headline numbers |
|---|---|---|---|---|
| [RES-03-ec2-scaleout-r1_2026-10-08/](RES-03-ec2-scaleout-r1_2026-10-08/README.md) | Scale-out: 10, then 200, then 10 users, 23 minutes | 2026-10-08 | A | `alarm_history.json`, `scaling_activities.json`, `targets.jsonl` |
| [RES-03-ec2-replace-r1_2026-10-08/](RES-03-ec2-replace-r1_2026-10-08/README.md) | Replacement: 100 users, one of two instances removed gracefully at 300 s | 2026-10-08 | A | `kill.json`, `targets.jsonl` |
| [LOAD-ec2-saturation-r1_2026-10-08/](LOAD-ec2-saturation-r1_2026-10-08/README.md) | Saturation: 1 to 512 users in ten 120 s steps, no think time | 2026-10-08 | A | `locust_stats.csv`, `cloudwatch/` |
| [LOAD-ec2-smoke-r1_2026-10-08/](LOAD-ec2-smoke-r1_2026-10-08/README.md) | FUNC-03 smoke run: 2 users for 75 s from the laptop | 2026-10-08 | A | `run.json`, `locust_stats.csv` |
| [RES-03-fargate-scaleout-r1_2026-10-09/](RES-03-fargate-scaleout-r1_2026-10-09/README.md) | Scale-out, same schedule as A | 2026-10-09 | B | `alarm_history.json`, `ecs_events.json`, `targets.jsonl` |
| [RES-03-fargate-replace-r1_2026-10-09/](RES-03-fargate-replace-r1_2026-10-09/README.md) | Replacement, same schedule as A (one of two tasks stopped gracefully) | 2026-10-09 | B | `kill.json`, `ecs_events.json`, `targets.jsonl` |
| [LOAD-fargate-saturation-r1_2026-10-09/](LOAD-fargate-saturation-r1_2026-10-09/README.md) | Saturation, same steps as A | 2026-10-09 | B | `locust_stats.csv`, `cloudwatch/` |
| [LOAD-fargate-smoke-r1_2026-10-09/](LOAD-fargate-smoke-r1_2026-10-09/README.md) | FUNC-03 smoke run | 2026-10-09 | B | `run.json`, `locust_stats.csv` |

No run was rerun and none failed: each is the only attempt and [load-summary.md](../load-summary.md) marks all eight "valid". The three A folders exported before commit `0276f52` (smoke, scale-out, replacement) have `<ACCOUNT>` inside some averages of `locust_stats*.csv` and `report.html` (a redaction defect, fixed afterwards); their `requests-*.csv`, which the numbers come from, are not affected. Folder contents, key files and how to reproduce each folder's numbers are in its `README.md`.

## PRE: preflight before the AWS session (2026-10-08, both variants)

| Case | What it is | Authoritative file | Other files |
|---|---|---|---|
| Image | The pinned image (`release-c19d547`, digest `sha256:fa72e949…`) is in the registry | `PRE_2026-10-08_image.txt` | |
| Lab role | `LabRole` trusts `ecs-tasks.amazonaws.com` (variant B can run) | `PRE_2026-10-08_labrole.txt` | |
| Capacity pins | No pin file left from an earlier session | `PRE_2026-10-08_pins.txt` | |
| Fargate quota | The quota cannot be read in the lab (`AccessDenied`); a result, not an error | `PRE_2026-10-08_quota.txt` | |
| Service-linked roles | The two ECS roles were missing | `PRE_2026-10-08_slr.txt` | |
| Create the roles | Both roles created | `PRE_2026-10-08_slr-create.txt` | `PRE_2026-10-08_slr-create_rerun.txt`: failed attempt, kept for honesty (roles already existed; "already taken"); the first attempt succeeded |
| Alarm email | The SNS email subscription is confirmed | `PRE_2026-10-08_sns.txt` | |

## OPS: timed bring-up, capacity changes, resets and teardown

| Case | What it is | Date | Variant | Authoritative file | Other files |
|---|---|---|---|---|---|
| Bring up A | `up.sh ec2`: 25 resources applied, secrets checks `match`, then `db_bootstrap` failed on the existing database | 2026-10-08 | A | `OPS_2026-10-08_ec2_up_rerun.txt` | `OPS_2026-10-08_ec2_up.txt`: failed attempt, kept for honesty (`tf.sh` exited silently, status 2), superseded by `…_up_rerun.txt` |
| Jobs on A | `migrate`, `check` and `smoke.sh`, run by hand after the bootstrap failure; smoke 8 of 8 | 2026-10-08 | A | `OPS_2026-10-08_ec2_jobs.txt` | |
| Pin A to 2 / 2 / 2 | Capacity for the replacement run | 2026-10-08 | A | `OPS_2026-10-08_ec2_pin-2-2-2-count_apply.txt` | `…_plan.txt`: the plan applied |
| Pin A to 1 / 1 / 1 | Capacity for the saturation run | 2026-10-08 | A | `OPS_2026-10-08_ec2_pin-1-1-1-count_apply.txt` | `…_plan.txt`: the plan applied |
| Database reset 1 on A | Dry run then apply: 37 load orders removed, stock restored | 2026-10-08 | A | `OPS_2026-10-08_ec2_reset-apply.txt` | `OPS_2026-10-08_ec2_reset-dry.txt`: the dry run before it |
| Database reset 2 on A | After the saturation run: 274 load orders removed | 2026-10-08 | A | `OPS_2026-10-08_ec2_reset-apply2.txt` | `OPS_2026-10-08_ec2_reset-dry2.txt`: the dry run before it |
| Tear down A | `down.sh ec2`: 25 destroyed, leftover lists empty | 2026-10-08 | A | `OPS_2026-10-08_ec2_down.txt` | |
| Bring up B | `up.sh fargate`: 27 resources applied, `jobs fargate check` ok, smoke 8 of 8 | 2026-10-09 | B | `OPS_2026-10-09_fargate_up.txt` | |
| Pin B to 2 / 2 / 2 | Capacity for the replacement run | 2026-10-09 | B | `OPS_2026-10-09_fargate_pin-2-2-2-count_apply.txt` | `…_plan_rerun.txt`: the plan applied. `…_plan.txt`: failed attempt, kept for honesty (uncommitted change in `src/infrastructure`, exit 1), superseded by `…_plan_rerun.txt` |
| Pin B to 1 / 1 / 1 | Capacity for the saturation run | 2026-10-09 | B | `OPS_2026-10-09_fargate_pin-1-1-1-count_apply.txt` | `…_plan_rerun.txt`: the plan applied. `…_plan.txt`: failed attempt, kept for honesty (AccessDenied errors reading AWS resources, "explicit deny … voc-cancel-cred", exit 1), superseded by `…_plan_rerun.txt` |
| Pin B to block mode | WAF in block mode for SEC-17 | 2026-10-09 | B | `OPS_2026-10-09_fargate_pin-1-1-1-block_apply.txt` | `…_plan.txt`: the plan applied |
| Database reset 1 on B | After the saturation run: 299 load orders removed | 2026-10-09 | B | `OPS_2026-10-09_fargate_reset-apply.txt` | `OPS_2026-10-09_fargate_reset-dry.txt`: the dry run before it |
| Database reset 2 on B | Final check: nothing left (0 load orders) | 2026-10-09 | B | `OPS_2026-10-09_fargate_reset-apply_rerun.txt` | `OPS_2026-10-09_fargate_reset-dry_rerun.txt`: the dry run before it |
| Tear down B | `down.sh fargate`: 27 destroyed, leftover lists empty | 2026-10-09 | B | `OPS_2026-10-09_fargate_down.txt` | |

## SESSION: resource IDs and service events kept for later lookups

| Case | What it is | Date | Variant | Authoritative file |
|---|---|---|---|---|
| IDs | Terraform outputs and the target group, written before the stack is destroyed | 2026-10-08 | A | `SESSION_2026-10-08_ec2_ids.txt` |
| IDs | The same for B | 2026-10-09 | B | `SESSION_2026-10-09_fargate_ids.txt` |
| ECS service events | The service's event list, which shows the scale-in task stop at 03:03:08 UTC after the scale-out run | 2026-10-09 | B | `SESSION_2026-10-09_fargate_service-events.txt` |

## FUNC: functional workflow

| Case | What it is | Date | Variant | Authoritative file | Other files |
|---|---|---|---|---|---|
| FUNC-01 | Automated workflow suite, 93 passed | 2026-09-26 | local | `FUNC-01_2026-09-26.txt` | |
| FUNC-02 | Manual browser walkthrough, local: setup, generator, step checks | 2026-09-26 | local | `FUNC-02_2026-09-26_setup.txt`; step files `…_step6-deactivated-check-rerun2.txt`, `…_step6-reactivated-check-rerun2.txt`, `…_step7-current-crosscheck-rerun2.txt`, `…_step8-analytics-check.txt`; dataset rebuild `…_generator-fixed-clean.txt` | Superseded: `…_generator.txt` (failed attempt, kept for honesty: no Python installed, exit 103) and `…_generator-fixed.txt` by `…_generator-fixed-clean.txt`; `…_step6-deactivated-check.txt` and `…_step6-deactivated-check-rerun.txt` by `…_rerun2.txt`; `…_step7-current-crosscheck.txt` and `…_step7-current-crosscheck-rerun.txt` by `…_rerun2.txt` |
| FUNC-02 screenshots | Six browser screenshots of the local shop (`127.0.0.1`), among them the catalogue page and the 403 on `/analytics/`; they show the tester's browser tabs. [test-functional.md](../test-functional.md) says FUNC-02 screenshots were not saved as files and does not cite these | 2026-09-26 | local | `Screenshot 2026-09-26 153100.png` and the five others with the same prefix | |
| FUNC-03 on A | Per-action summary of the smoke run (`errors: 0`) | 2026-10-08 | A | `FUNC-03_2026-10-08_ec2_summary.txt` | the run folder `LOAD-ec2-smoke-r1_2026-10-08/` |
| FUNC-03 on B | The same on B | 2026-10-09 | B | `FUNC-03_2026-10-09_fargate_summary.txt` | the run folder `LOAD-fargate-smoke-r1_2026-10-09/` |

## SEC: security cases

| Case | What it is | Date | Variant | Authoritative file | Other files |
|---|---|---|---|---|---|
| SEC-01 to SEC-05 | Local access control, privilege, CSRF, tampering, concurrency | 2026-09-26 | local | `SEC-0N_2026-09-26_rerun.txt` | `SEC-0N_2026-09-26.txt` (N = 1 to 5): superseded by the `_rerun` file (first wrapper attempt; the SEC-05 file is a stub) |
| SEC-06 to SEC-08 | Local XSS, weak passwords, secrets in logs | 2026-09-26 | local | `SEC-0N_2026-09-26_rerun.txt` | no earlier file |
| SEC-ALL | The 25 local test IDs in one sequential run | 2026-09-26 | local | `SEC-ALL_2026-09-26_rerun.txt` | superseded for the current commit by `SEC-ALL-rerun_2026-10-01.txt` |
| SEC-12 to SEC-16 | Production settings, secret loader, health and Host handling, request logging, unusable imported passwords | 2026-10-01 | local | `SEC-12_2026-10-01.txt` to `SEC-16_2026-10-01.txt` | |
| SEC-ALL rerun | The 25 IDs again on the current commit | 2026-10-01 | local | `SEC-ALL-rerun_2026-10-01.txt` | |
| SEC-09 | Database and bucket private; security-group chain | 2026-10-08 | A | `SEC-09_2026-10-08_ec2_security-groups.txt` | `…_ec2_rds.txt`, `…_ec2_s3.txt` |
| SEC-09 | The same on B | 2026-10-09 | B | `SEC-09_2026-10-09_fargate_security-groups.txt` | `…_fargate_rds.txt`, `…_fargate_s3.txt` |
| SEC-10 | HTTPS enforced | 2026-10-08 | A | `SEC-10_2026-10-08_ec2_listeners.txt` | `…_ec2_smoke.txt` (smoke 8 of 8) |
| SEC-10 | The same on B | 2026-10-09 | B | `SEC-10_2026-10-09_fargate_listeners.txt` | `…_fargate_smoke.txt` |
| SEC-11 | Secrets from Secrets Manager | 2026-10-08 | A | `SEC-11_2026-10-08_ec2_runtime.txt` | `…_ec2_secrets-check.txt`, `…_ec2_app-check.txt` |
| SEC-11 | The same on B | 2026-10-09 | B | `SEC-11_2026-10-09_fargate_runtime.txt` | `…_fargate_secrets-check.txt`, `…_fargate_app-check.txt` |
| SEC-17 | WAF blocks a login burst (B only) | 2026-10-09 | B | `SEC-17_2026-10-09_fargate_burst.txt` | `…_fargate_metrics.txt` (BlockedRequests 5); `…_fargate_samples-burst.txt` (authoritative sample file: 5 `BLOCK` rows); `…_fargate_samples.txt`: superseded by `…_samples-burst.txt` (100 random sampled requests, mostly `COUNT` from the saturation run) |
| SEC-18 | No secrets in the logs | 2026-10-08 | A | `SEC-18_2026-10-08_ec2_count_rerun.txt` | `…_ec2_matches_rerun.txt` (authoritative, same run); `…_ec2_count.txt` and `…_ec2_matches.txt`: superseded by the `_rerun` files (taken at 17:52, before the saturation run; also 0 matches) |
| SEC-18 | The same on B | 2026-10-09 | B | `SEC-18_2026-10-09_fargate_count.txt` | `…_fargate_matches.txt` |

## SCAN: automated scans (local, 2026-10-01)

| Case | What it is | Authoritative file |
|---|---|---|
| SCAN-01 | gitleaks on git history and on the working tree (no secret; one false positive) | `SCAN-01_2026-10-01_gitleaks-history.json`, `SCAN-01_2026-10-01_gitleaks-tree.json` (the `.log` files are the tool output) |
| SCAN-02 | bandit static analysis | `SCAN-02_2026-10-01_bandit.json` |
| SCAN-03 | pip-audit on the application and analytics requirements | `SCAN-03_2026-10-01_pip-audit-src.json`, `SCAN-03_2026-10-01_pip-audit-analytics.json` |
| SCAN-04 | Django `check --deploy` | `SCAN-04_2026-10-01_check-deploy.txt` |
| SCAN-05 | hadolint on the Dockerfile | `SCAN-05_2026-10-01_hadolint.json` |
| SCAN-06 | Trivy image scan | `SCAN-06_2026-10-01_trivy-image.json` |
| SCAN-07 | Trivy infrastructure-code scan | `SCAN-07_2026-10-01_trivy-iac.json` |

Triage of all seven: [security-scan-triage.md](../security-scan-triage.md).

## DATA: analytics and machine learning

| Case | What it is | Date | Variant | Authoritative file | Other files |
|---|---|---|---|---|---|
| DATA-01 | Import, refresh and independent pandas check on the shoe dataset (0 mismatches) | 2026-09-26 | local | `DATA-01_2026-09-26_verify.txt` | `…_import.txt`, `…_refresh.txt` |
| DATA-01 on AWS | The refresh job on the deployed database | 2026-10-08 | A | `DATA-01_2026-10-08_aws_refresh.txt` | |
| DATA-02 (adopted recipe) | Segmentation tests, training, strict import and dashboard for the adopted `log_rfm_aov` recipe | 2026-09-26 | local | `DATA-02_2026-09-26_m03-train-load.txt` | `…_m03-tests.txt`, `…_m03-dashboard.txt`, `…_m03-comparison.txt` |
| DATA-02 hold-out | 90-day hold-out and 80% subsample stability | 2026-09-26 | local | `DATA-02_2026-09-26_holdout.txt` | |
| DATA-02 (first recipe) | The same steps for the earlier `log_frequency` recipe, kept as history | 2026-09-26 | local | superseded by the `…_m03-*` files for the adopted recipe | `DATA-02_2026-09-26_tests.txt`, `…_train.txt`, `…_load.txt`, `…_dashboard-run.txt`, `…_dashboard.txt` |

## MON: logs, saved queries and alarms

| Case | What it is | Date | Variant | Authoritative file | Other files |
|---|---|---|---|---|---|
| MON-01 | Log sample and requests by status per 5 minutes | 2026-10-08 | A | `MON-01_2026-10-08_ec2_status-per-5min_rerun.txt` | `…_ec2_sample_rerun.txt` (authoritative, same run); `…_ec2_sample.txt` and `…_ec2_status-per-5min.txt`: superseded by the `_rerun` files (17:52, before the saturation run) |
| MON-01 | The same on B | 2026-10-09 | B | `MON-01_2026-10-09_fargate_status-per-5min.txt` | `…_fargate_sample.txt` |
| MON-02 | The two saved Logs Insights queries | 2026-10-08 | A | `MON-02_2026-10-08_ec2_recent-errors-and-security-warnings_rerun.txt` | `…_ec2_errors-and-warnings-per-minute_rerun.txt` (authoritative: the query failed as malformed, a recorded result); the two files without `_rerun` are superseded by them |
| MON-02 | The same on B | 2026-10-09 | B | `MON-02_2026-10-09_fargate_recent-errors-and-security-warnings.txt` | `…_fargate_errors-and-warnings-per-minute.txt` (the same malformed-query failure) |
| MON-03 | Forced alarm, return to OK, history, ALARM email transcription | 2026-10-08 | A | `MON-03_2026-10-08_ec2_history.txt` | `…_ec2_force.txt`, `…_ec2_return-to-ok.txt`, `…_ec2_email-alarm.txt` (hand transcription) |
| MON-03 | The same on B; OK email transcription | 2026-10-09 | B | `MON-03_2026-10-09_fargate_history.txt` | `…_fargate_force.txt`, `…_fargate_return-to-ok.txt`, `…_fargate_email-ok.txt` (hand transcription, clipped) |

MON-04 (detection under real load) has no files of its own: it is `alarm_history.json` and `scaling_activities.json` (A) or `ecs_events.json` (B) inside the RES-03 scale-out folders.
