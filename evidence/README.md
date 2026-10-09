# evidence/

The single current index of the evidence. **Start with the five test records** (`test-functional.md`, `test-security.md`, `test-data-ai.md`, `test-resilience.md` with `test-performance.md`, and `monitoring.md`): each opens with a "Results at a glance" table (case, what it proves, result, date, one key file) and gives the full objective, setup, command, expected, actual, date and artefact path below it. **`raw/` is supporting proof**: the unedited command output those records cite (447 files, 296 of them inside eight run folders). Nobody is expected to read it in bulk: [raw/INDEX.md](raw/INDEX.md) lists every case and run folder once, with its authoritative file and a note on every superseded or failed attempt, and each run folder has a short `README.md` naming its key files and how to reproduce its numbers.

New here? [docs/GUIDE.md](../docs/GUIDE.md) explains the file names, how to check a claim, and where AWS logs and metrics end up. The mapping from the marking criteria to these files is in [README.md](../README.md#rubric-to-evidence-map) and in `project_manifest.yaml` (`rubric_evidence_map`).

**State on 9 October 2026:** both variants were measured, one repeat each: variant A (EC2 behind an Auto Scaling group) on 8 October 2026 and variant B (ECS on Fargate) on 9 October 2026 (UTC), then both stacks were torn down. The A and B results sit side by side in the same tables. Evidence covers commits up to `e4bc928`.

## Read these limits first

| Limit | Where it matters |
|---|---|
| One repeat per condition: every A-versus-B difference is "indicative, n = 1" | all load, scale-out and replacement results |
| The replacement test is a graceful removal (ADR-017), not a crash | RES-03b |
| RDS CPU credits and cache cannot be reset between variants (credit balance stayed at 576 on both); shop data was reset at different points on A and B | LOAD-03, RES-03 |
| The two variants ran on different hardware as far as the files show (Xeon 8124M at 3.0 GHz on A, Xeon 8259CL at 2.5 GHz on B) | LOAD-03 |
| The 3D models (12 files, about 15 MB, served by the app) are not fetched by the load test | all load results |
| The ladder (10 and 100 users) was dropped for time; the saturation run (1 to 512 users) replaced it | LOAD-02, LOAD-03 |
| The WAF block test (SEC-17) is run on B only, because the WAF is one shared module | SEC-17 |
| FUNC-03 part 2 (browser steps) has no screenshots in `raw/` | FUNC-03 |
| The scaling target (300 requests per target per minute) was set before any data and is a small fraction of the measured ceiling | RES-03a |
| Prices in `tests/load/prices.json` are list prices (checked 9 October 2026), not the lab's billed amounts | any cost figure |

## Index

Status words: `PASS` (ran and matched the expectation written first), `FAIL` (ran, did not match; kept and explained), `PARTIAL` (some of the expectation met, the gap stated), `NOT RUN` (not run in a recorded session).

### Functional

| Case | Environment | Status | Key file | Date |
|---|---|---|---|---|
| FUNC-01 automated workflow suite (accounts, catalogue, cart, checkout, order history) | Local Docker | PASS (93 passed) | [raw/FUNC-01_2026-09-26.txt](raw/FUNC-01_2026-09-26.txt) | 2026-09-26 |
| FUNC-02 manual browser walkthrough (customer and operator) | Local Docker | PASS | [test-functional.md](test-functional.md#func-02-manual-browser-walkthrough) | 2026-09-26 |
| FUNC-03 part 1, variant A | AWS (EC2) | PASS, 2 orders, 0 errors | [raw/FUNC-03_2026-10-08_ec2_summary.txt](raw/FUNC-03_2026-10-08_ec2_summary.txt) | 2026-10-08 |
| FUNC-03 part 2, variants A and B (browser steps) | AWS (EC2, Fargate) | No screenshots in `raw/`; to be stated by the team | [test-functional.md](test-functional.md#func-03-purchase-flow-on-the-deployed-shop-variant-a-and-variant-b) | |
| FUNC-03 part 1, variant B | AWS (Fargate) | PASS, 2 orders, 0 errors | [raw/FUNC-03_2026-10-09_fargate_summary.txt](raw/FUNC-03_2026-10-09_fargate_summary.txt) | 2026-10-09 |

### Security

| Case | Environment | Status | Key file | Date |
|---|---|---|---|---|
| SEC-01 to SEC-08 (T1 to T8: access control, privilege escalation, CSRF, tampering, overselling, XSS, weak passwords, secrets in logs) | Local Docker | PASS (25 test IDs) | [raw/SEC-ALL_2026-09-26_rerun.txt](raw/SEC-ALL_2026-09-26_rerun.txt); per case `raw/SEC-0N_2026-09-26_rerun.txt` | 2026-09-26 |
| SEC-12 to SEC-16 (production settings, secret loader, health and Host handling, request logging, unusable imported passwords) | Local Docker | PASS | [raw/SEC-12_2026-10-01.txt](raw/SEC-12_2026-10-01.txt) to `SEC-16_2026-10-01.txt` | 2026-10-01 |
| SEC-ALL rerun (the 25 IDs on the current commit) | Local Docker | PASS | [raw/SEC-ALL-rerun_2026-10-01.txt](raw/SEC-ALL-rerun_2026-10-01.txt) | 2026-10-01 |
| SCAN-01 to SCAN-07 (gitleaks, bandit, pip-audit, `check --deploy`, hadolint, Trivy image and IaC) | Local Docker, not CI | Run; findings triaged, 4 open | [security-scan-triage.md](security-scan-triage.md) | 2026-10-01 |
| SEC-09 database and storage private, only the app tier reaches the database | AWS (EC2) | PASS | [raw/SEC-09_2026-10-08_ec2_security-groups.txt](raw/SEC-09_2026-10-08_ec2_security-groups.txt) | 2026-10-08 |
| SEC-10 HTTPS enforced, TLS 1.2+ policy | AWS (EC2) | PASS | [raw/SEC-10_2026-10-08_ec2_listeners.txt](raw/SEC-10_2026-10-08_ec2_listeners.txt) | 2026-10-08 |
| SEC-11 runtime secrets from Secrets Manager | AWS (EC2) | PASS (instance role is the broad `LabRole`) | [raw/SEC-11_2026-10-08_ec2_runtime.txt](raw/SEC-11_2026-10-08_ec2_runtime.txt) | 2026-10-08 |
| SEC-18 no secrets in the CloudWatch logs | AWS (EC2) | PASS, 0 matches in 88,044 records | [raw/SEC-18_2026-10-08_ec2_count_rerun.txt](raw/SEC-18_2026-10-08_ec2_count_rerun.txt) | 2026-10-08 |
| SEC-09 database and storage private, only the app tier reaches the database | AWS (Fargate) | PASS | [raw/SEC-09_2026-10-09_fargate_security-groups.txt](raw/SEC-09_2026-10-09_fargate_security-groups.txt) | 2026-10-09 |
| SEC-10 HTTPS enforced, TLS 1.2+ policy | AWS (Fargate) | PASS | [raw/SEC-10_2026-10-09_fargate_listeners.txt](raw/SEC-10_2026-10-09_fargate_listeners.txt) | 2026-10-09 |
| SEC-11 runtime secrets from Secrets Manager | AWS (Fargate) | PASS (task role is the broad `LabRole`) | [raw/SEC-11_2026-10-09_fargate_runtime.txt](raw/SEC-11_2026-10-09_fargate_runtime.txt) | 2026-10-09 |
| SEC-18 no secrets in the CloudWatch logs | AWS (Fargate) | PASS, 0 matches in 77,326 records | [raw/SEC-18_2026-10-09_fargate_count.txt](raw/SEC-18_2026-10-09_fargate_count.txt) | 2026-10-09 |
| SEC-17 WAF blocks a login burst | AWS (Fargate only) | PASS: attempts 1 to 24 allowed, 25 to 29 blocked by the load balancer's WAF, browsing unaffected; not run on A by decision (shared module) | [raw/SEC-17_2026-10-09_fargate_burst.txt](raw/SEC-17_2026-10-09_fargate_burst.txt) | 2026-10-09 |
| Threat map T1 to T19 to control, code and evidence | Local and AWS A and B | Filled; cloud rows updated for variants A and B | [threat-control-map.md](threat-control-map.md) | 2026-10-09 |

### Data and analytics

| Case | Environment | Status | Key file | Date |
|---|---|---|---|---|
| DATA-01 analytics refresh against an independent pandas check (original dataset) | Local Docker | PASS (earlier record) | [test-data-ai.md](test-data-ai.md) | 2026-09-22 |
| DATA-01 rerun on the shoe dataset the application imports | Local Docker | PASS, 0 mismatches | [raw/DATA-01_2026-09-26_verify.txt](raw/DATA-01_2026-09-26_verify.txt) | 2026-09-26 |
| DATA-01 refresh on the deployed database | AWS (EC2) | PASS against its expectation; not independently verified on AWS | [raw/DATA-01_2026-10-08_aws_refresh.txt](raw/DATA-01_2026-10-08_aws_refresh.txt) | 2026-10-08 |
| DATA-02 customer segmentation: tests, training, strict import, dashboard | Local Docker | PASS | [raw/DATA-02_2026-09-26_m03-train-load.txt](raw/DATA-02_2026-09-26_m03-train-load.txt) | 2026-09-26 |
| DATA-02 hold-out and 80% subsample stability | Local Docker | Ran; segments show no predictive difference on this synthetic data | [raw/DATA-02_2026-09-26_holdout.txt](raw/DATA-02_2026-09-26_holdout.txt), [ml-holdout-evaluation.json](ml-holdout-evaluation.json) | 2026-09-26 |
| DATA-02 on AWS | AWS | NOT RUN | — | |

### Scalability, resilience and load

| Case | Environment | Status | Key file | Date |
|---|---|---|---|---|
| RES-03a scale-out 1 to 2 units | AWS (EC2) | PASS for scale-out (alarm 299 s after the load step, healthy 161 s after the alarm); scale-in not observed | [raw/RES-03-ec2-scaleout-r1_2026-10-08/](raw/RES-03-ec2-scaleout-r1_2026-10-08/) | 2026-10-08 |
| RES-03b replacement of a removed unit under 100 users | AWS (EC2) | PASS (114 s to two healthy, 0 errors); graceful removal | [raw/RES-03-ec2-replace-r1_2026-10-08/](raw/RES-03-ec2-replace-r1_2026-10-08/) | 2026-10-08 |
| RES-04 session continuity across the removal | AWS (EC2) | Not analysed yet | same folder as RES-03b | |
| LOAD-03 saturation, 1 to 512 users | AWS (EC2) | Measured: practical capacity 16 users (46.54 page actions/s), maximum 118.8 requests/s, 0 errors; instance CPU is the limit | [raw/LOAD-ec2-saturation-r1_2026-10-08/](raw/LOAD-ec2-saturation-r1_2026-10-08/) | 2026-10-08 |
| RES-03a scale-out 1 to 2 units | AWS (Fargate) | PASS for scale-out (alarm 305 s after the load step, healthy 101 s after the alarm); scale-in observed after the run | [raw/RES-03-fargate-scaleout-r1_2026-10-09/](raw/RES-03-fargate-scaleout-r1_2026-10-09/) | 2026-10-09 |
| RES-03b replacement of a removed unit under 100 users | AWS (Fargate) | PASS (50 s to two healthy, 0 errors); graceful removal | [raw/RES-03-fargate-replace-r1_2026-10-09/](raw/RES-03-fargate-replace-r1_2026-10-09/) | 2026-10-09 |
| RES-04 session continuity across the removal | AWS (Fargate) | Not analysed yet | same folder as RES-03b | |
| LOAD-03 saturation, 1 to 512 users | AWS (Fargate) | Measured: practical capacity 8 users (44.01 page actions/s), maximum 105.5 requests/s, 0 errors; task CPU is the limit | [raw/LOAD-fargate-saturation-r1_2026-10-09/](raw/LOAD-fargate-saturation-r1_2026-10-09/) | 2026-10-09 |
| LOAD-01 RDS pilot, LOAD-02 ladder, LOAD-04 Singapore latency | AWS | NOT RUN (dropped for time) | — | |
| RES-01, RES-02 database outage, local | Local Docker | NOT RUN | — | |
| All run tables generated from the raw run folders | | Generated by `tests/load/analyze.py` | [load-summary.md](load-summary.md) | 2026-10-09 |

Records: [test-resilience.md](test-resilience.md) (index) and [test-performance.md](test-performance.md) (full case tables).

### Monitoring

| Case | Environment | Status | Key file | Date |
|---|---|---|---|---|
| MON-01 structured logs reach CloudWatch | AWS (EC2) | PASS with one deviation (sample was mostly job output) | [raw/MON-01_2026-10-08_ec2_status-per-5min_rerun.txt](raw/MON-01_2026-10-08_ec2_status-per-5min_rerun.txt) | 2026-10-08 |
| MON-02 saved Logs Insights queries | AWS (EC2) | One of two works; the other is rejected as malformed (open defect) | [raw/MON-02_2026-10-08_ec2_recent-errors-and-security-warnings_rerun.txt](raw/MON-02_2026-10-08_ec2_recent-errors-and-security-warnings_rerun.txt) | 2026-10-08 |
| MON-03 forced alarm to email | AWS (EC2) | PARTIAL: ALARM leg complete; no record of the OK email | [raw/MON-03_2026-10-08_ec2_history.txt](raw/MON-03_2026-10-08_ec2_history.txt) | 2026-10-08 |
| MON-04 detection under real load | AWS (EC2) | PASS for scale-out; scale-in not observed | [raw/RES-03-ec2-scaleout-r1_2026-10-08/alarm_history.json](raw/RES-03-ec2-scaleout-r1_2026-10-08/alarm_history.json) | 2026-10-08 |
| HTTP 400 entries in the saved query | AWS (EC2) | Investigated on both variants: unknown-Host rejections, not a leak | [monitoring.md](monitoring.md#http-400-entries-in-mon-02) | 2026-10-08 |
| MON-01 structured logs reach CloudWatch | AWS (Fargate) | PASS with one deviation (6 of 20 sample lines were job output) | [raw/MON-01_2026-10-09_fargate_status-per-5min.txt](raw/MON-01_2026-10-09_fargate_status-per-5min.txt) | 2026-10-09 |
| MON-02 saved Logs Insights queries | AWS (Fargate) | One of two works; the other is rejected as malformed (the same open defect) | [raw/MON-02_2026-10-09_fargate_recent-errors-and-security-warnings.txt](raw/MON-02_2026-10-09_fargate_recent-errors-and-security-warnings.txt) | 2026-10-09 |
| MON-03 forced alarm to email | AWS (Fargate) | PARTIAL: OK leg complete; no record of the ALARM email | [raw/MON-03_2026-10-09_fargate_history.txt](raw/MON-03_2026-10-09_fargate_history.txt) | 2026-10-09 |
| MON-04 detection under real load | AWS (Fargate) | PASS for scale-out; scale-in observed after the run | [raw/RES-03-fargate-scaleout-r1_2026-10-09/alarm_history.json](raw/RES-03-fargate-scaleout-r1_2026-10-09/alarm_history.json) | 2026-10-09 |

Record: [monitoring.md](monitoring.md).

### Build and operations

| Item | Status | Key file | Date |
|---|---|---|---|
| Build record, one dated entry per apply, with timings, defects and cost | Current to the 9 October session; lab balance at the end of both sessions recorded (USD 9.8 of 50 used) | [aws-build-runbook.md](aws-build-runbook.md) | 2026-10-08 |
| Preflight checks (`PRE_*`), timed up/down/pin/reset (`OPS_*`), resource IDs (`SESSION_*`) | Variants A and B recorded | `raw/PRE_2026-10-08_*.txt`, `raw/OPS_2026-10-08_ec2_*.txt`, `raw/OPS_2026-10-09_fargate_*.txt`, `raw/SESSION_*` | 2026-10-08, 2026-10-09 |
| `architecture.png` | **Missing**, to be supplied by the report lead | — | |
| `report.pdf` | **Missing**, to be supplied | — | |

## Evidence rules

- Every actual result comes from a command run in a recorded session and saved unchanged in `raw/`, except lines cut and marked `…` and redactions (`<ACCOUNT>`, `<PUBLIC-IP>`, `<EMAIL>`, `<REDACTED>`).
- The expected result is written before the run and is not changed afterwards.
- Raw files from AWS sessions start with the UTC date, commit and exact command and end with the exit code. Reruns carry a `_rerun` suffix and failed attempts are kept; the records cite the authoritative file and note that the others exist.
- Dates are UTC from the file headers; a few AWS history files print +08:00 (Singapore) times, which the record converts.
- Use `Local Docker` and `AWS` explicitly: local checks do not prove hosted behaviour.
- Prefer text exports to screenshots; a screenshot needs a text file beside it with the same fact.
- Re-runs add a new dated file; earlier results remain.
- The evidence writer does not run `aws` or `terraform`, does not edit `raw/`, and does not write "Verified by"; the human reviewer adds it.
