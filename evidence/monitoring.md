# Monitoring / operational evidence

**Status (9 October 2026):** variant A (`ec2`) was run on 8 October 2026 and variant B (`fargate`) on 9 October 2026 (UTC). The A and B columns use the same wording so they can be compared line by line. The expected results were written on 8 October 2026, before any cloud run, and are unchanged. Every case runs identically on both variants through `src/infrastructure/scripts/evidence.sh`; procedure and order in [docs/plans/evidence-session.md](../docs/plans/evidence-session.md). Raw files are redacted (account IDs, public IPs, email addresses) when they are written.

## Results at a glance

| Case | What it proves | Result on A (EC2) | Result on B (Fargate) | Date (UTC) | Key artefact A | Key artefact B |
|---|---|---|---|---|---|---|
| MON-01 structured logs | Request logs reach CloudWatch as JSON and can be counted by status | **PASS with one deviation**: JSON fields confirmed and status counts follow the load (15,291 `200` lines in one 5-minute window of the saturation run), but 16 of the 20 sample lines are plain-text job output, not JSON | **PASS with one deviation**: JSON fields confirmed and status counts follow the load (13,025 `200` lines in one 5-minute window of the saturation run), but 6 of the 20 sample lines are plain-text job output, not JSON | A 2026-10-08; B 2026-10-09 | `raw/MON-01_2026-10-08_ec2_status-per-5min_rerun.txt` | `raw/MON-01_2026-10-09_fargate_status-per-5min.txt` |
| MON-02 saved queries | The two saved queries an operator would use return results | **FAIL for one of two**: `recent-errors-and-security-warnings` Complete (152 matched, 50 shown, all `DisallowedHost` 400s); `errors-and-warnings-per-minute` rejected as `MalformedQueryException` | **FAIL for one of two**: `recent-errors-and-security-warnings` Complete (181 matched, 50 shown, all `DisallowedHost` 400s); `errors-and-warnings-per-minute` rejected as `MalformedQueryException` | A 2026-10-08; B 2026-10-09 | `raw/MON-02_2026-10-08_ec2_recent-errors-and-security-warnings_rerun.txt` | `raw/MON-02_2026-10-09_fargate_recent-errors-and-security-warnings.txt` |
| MON-03 alarm to email | An alarm notification reaches the operator and the alarm returns to OK | **PARTIAL**: history shows ALARM, SNS action, OK, SNS action; the ALARM email is recorded as a hand transcription; **no record of the OK email** | **PARTIAL**: history shows ALARM, SNS action, OK, SNS action; the OK email is recorded as a hand transcription (clipped by the mail client); **no record of the ALARM email** | A 2026-10-08; B 2026-10-09 | `raw/MON-03_2026-10-08_ec2_history.txt` | `raw/MON-03_2026-10-09_fargate_history.txt` |
| MON-04 detection under load | A real load increase trips an alarm and the service acts without a person | **PASS** for scale-out: `AlarmHigh` ALARM 299 s after the load step, scaling action 64 s later. Low alarm and scale-in not observed | **PASS** for scale-out: `AlarmHigh` ALARM 305 s after the load step, scaling action 67 s later. Scale-in observed after the run (task stopped 03:03:08 UTC) | A 2026-10-08; B 2026-10-09 | `raw/RES-03-ec2-scaleout-r1_2026-10-08/alarm_history.json` | `raw/RES-03-fargate-scaleout-r1_2026-10-09/alarm_history.json` |
| 400 entries in MON-02 | Whether the HTTP 400 entries are an attack, a fault or a leak | **Not a leak.** Unknown-Host requests rejected by design (details below); source not identifiable from the logs | **Not a leak.** Same entries, same reason; source not identifiable from the logs | A 2026-10-08; B 2026-10-09 | `raw/MON-02_2026-10-08_ec2_recent-errors-and-security-warnings_rerun.txt` | `raw/MON-02_2026-10-09_fargate_recent-errors-and-security-warnings.txt` |

Reruns: `MON-01_*`, `MON-02_*` and `SEC-18_*` were run twice on 8 October. The first set (17:52 UTC, commit `4e06901`) was taken before the saturation run and saw 15,891 log records; the `_rerun` set (18:51 UTC, commit `3c910b8`) saw 88,064, the whole session, so the `_rerun` files are cited. The first MON-02 per-minute attempt failed the same way as the rerun. Variant B was run once (77,326 log records scanned), so its files carry no `_rerun` suffix.

## What is monitored (both variants, from `src/infrastructure/modules/web-entry/`)

| Signal | Where | Action |
|---|---|---|
| `<stack>-unhealthy-hosts`: any unhealthy target | CloudWatch alarm on the target group | SNS email (ALARM and OK) |
| `<stack>-no-healthy-hosts`: no healthy target | CloudWatch alarm | SNS email |
| `<stack>-target-5xx`: more than 5 app 5xx responses a minute, twice | CloudWatch alarm | SNS email |
| Scaling: requests per target above 300 a minute | Target-tracking alarms made by the ASG (A) or Application Auto Scaling (B) | Scale out or in |
| Application logs: one JSON line per request (`ts, level, logger, message, status, request_id`) | Log group `/<stack>/app`, 7-day retention | Two saved Logs Insights queries |
| Edge: login rate rule | WAF metrics `CountedRequests`, `BlockedRequests` | Count or block (SEC-17) |

## MON-01: Structured logs reach CloudWatch

- **Objective:** Show that the application's request logs reach CloudWatch in the structured form the queries rely on, on both variants.
- **Setup:** After the session's traffic (smoke, FUNC-03, load runs), before `down`.
- **Command/steps:** `evidence.sh <variant> logs`, steps `MON-01 the latest 20 log lines` and `MON-01 requests by status per 5 minutes` (Logs Insights over the last 6 hours).
- **Expected result:** 20 JSON lines with `ts, level, logger, message, status, request_id`; the status table is mostly `200` and `302`, with request counts that rise during each load run.
- **Actual result:**

| Variant | Result | Raw files | Status |
|---|---|---|---|
| A | Sample: `recordsMatched` 88,064; the 20 newest lines include 4 JSON request or security lines with `ts, level, logger, message, request_id, status` (plus `method, path, duration_ms, user_id`, and `exception, frames` on the security line). The other 16 lines are plain text from the database-reset job (log stream `job-web-i-0375a1086e96bad06-…`, for example "APPLIED. Left: load orders 0 …"), because the reset ran a minute before the query. Status table: 87,995 lines carry a `status` field; per 5-minute window the counts follow the traffic, for example 6 `200` at 15:00 (idle), 1,671 `200` and 329 `302` at 16:55 (scale-out run), 15,291 `200` and 3,770 `302` at 18:25 (saturation run). Statuses seen: 200, 301, 302, 400, 404; no 5xx | `raw/MON-01_2026-10-08_ec2_sample_rerun.txt`, `raw/MON-01_2026-10-08_ec2_status-per-5min_rerun.txt` (first attempts `…_sample.txt`, `…_status-per-5min.txt` kept) | PASS with one deviation (the sample was not 20 JSON lines) |
| B | Sample: `recordsMatched` 77,329; 14 of the 20 newest lines are JSON request or security lines with the same fields as on A (`ts, level, logger, message, request_id, status, method, path, duration_ms, user_id`; `exception, frames` on the security line); the other 6 are plain text from the database-reset job (stream `web/web/…`, for example "APPLIED. Left: load orders 0 …"). Status table: 77,252 lines carry a `status` field; per 5-minute window the counts follow the traffic, for example 37 `200` at 02:00 (idle), 1,668 `200` and 406 `302` at 02:35 (scale-out run), 13,025 `200` and 3,209 `302` at 06:25 (saturation run). Statuses seen: 200, 302, 400, 404; no 5xx | `raw/MON-01_2026-10-09_fargate_sample.txt`, `raw/MON-01_2026-10-09_fargate_status-per-5min.txt` | PASS with one deviation (the sample was not 20 JSON lines) |

- **Date:** A 2026-10-08, 18:51 UTC (rerun); B 2026-10-09, 07:11 UTC

## MON-02: Saved Logs Insights queries

- **Objective:** Show that the two saved queries an operator would use during an incident run and return results.
- **Command/steps:** `evidence.sh <variant> logs`, steps `MON-02 saved queries` (`<stack>/recent-errors-and-security-warnings`, `<stack>/errors-and-warnings-per-minute`), run over the session window.
- **Expected result:** `status: Complete` for both. The rows show the session's warnings, for example the failed logins of the SEC-17 burst if the app logs them; an empty result is valid when nothing matched, and is stated as such.
- **Actual result:**

| Variant | Result | Raw files | Status |
|---|---|---|---|
| A | Query 1 `recent-errors-and-security-warnings`: `Complete`, 152 records matched, 50 returned (the query's `limit 50`); all 50 are `level ERROR`, `logger django.security.DisallowedHost`, `status 400`. Query 2 `errors-and-warnings-per-minute`: **did not run**, `MalformedQueryException: unexpected symbol found ( at line 3 and position 10`, exit 1. The first attempt at 17:52 failed identically | `raw/MON-02_2026-10-08_ec2_recent-errors-and-security-warnings_rerun.txt`, `raw/MON-02_2026-10-08_ec2_errors-and-warnings-per-minute_rerun.txt` (first attempts without `_rerun` kept) | Query 1 PASS; query 2 **FAIL** |
| B | Query 1 `recent-errors-and-security-warnings`: `Complete`, 181 records matched, 50 returned (`limit 50`); all 50 are `level ERROR`, `logger django.security.DisallowedHost`, `status 400`, dated 04:04:21 to 06:57:11 UTC. Query 2 `errors-and-warnings-per-minute`: **did not run**, the same `MalformedQueryException: unexpected symbol found ( at line 3 and position 10`, exit 1. The saved queries come from the shared `modules/web-entry`, so the failure is the same on both variants | `raw/MON-02_2026-10-09_fargate_recent-errors-and-security-warnings.txt`, `raw/MON-02_2026-10-09_fargate_errors-and-warnings-per-minute.txt` | Query 1 PASS; query 2 **FAIL** |

- **Why query 2 failed:** its text in `src/infrastructure/modules/web-entry/alarms.tf` (lines 79 to 80) is `stats count(*) as events by bin(1m), level | sort bin(1m) desc`. CloudWatch Logs Insights does not accept a function call in `sort`. The MON-01 query that completed in the same session names the bucket and sorts by the name (`bin(5m) as window | sort window asc`), so the same form is the likely fix (`bin(1m) as minute`, `sort minute desc`). The fix is in Terraform, outside this documentation pass, and was not applied or tested. The saved query is defined, but it cannot be run as saved. This is reported, not hidden.
- **Date:** A 2026-10-08, 18:51 UTC (rerun); B 2026-10-09, 07:11 UTC

## MON-03: An alarm reaches the operator by email

- **Objective:** Show the path from a CloudWatch alarm to an operator's inbox, and back to OK.
- **Setup:** The SNS email subscription is confirmed (checked in the preflight, `raw/PRE_<date>_sns.txt`).
- **Command/steps:** `evidence.sh <variant> alarm`: forces `<stack>-target-5xx` to ALARM with `set-alarm-state`, waits for the next evaluation to return it to OK, saves the alarm history; then the two emails are saved as screenshots with the address, account number and unsubscribe link cropped out.
- **Expected result:** History: a `StateUpdate` OK to ALARM, an `Action` "Successfully executed action arn:aws:sns:…", a `StateUpdate` ALARM to OK within about 2 minutes, and a second `Action`. Two emails: "ALARM: …-target-5xx" and "OK: …-target-5xx".
- **Actual result:**

| Variant | Result | Raw files | Status |
|---|---|---|---|
| A | `inf2006-grp21-ec2-target-5xx` forced to ALARM at 17:48:17.9 UTC; SNS action executed at 17:48:18.0; wait loop saw OK at 17:49:44; history records ALARM to OK at 17:49:36.4 and the second SNS action at 17:49:36.5 (the history file prints times as +08:00, 01:48 and 01:49 on 9 October). The ALARM email arrived (received 01:48 SGT) and is recorded as a **hand transcription** of the operator's screenshot with the account number, address and unsubscribe link removed. The screenshot file itself and any record of the OK email are **not in `raw/`** | `raw/MON-03_2026-10-08_ec2_history.txt`, `raw/MON-03_2026-10-08_ec2_force.txt`, `raw/MON-03_2026-10-08_ec2_return-to-ok.txt`, `raw/MON-03_2026-10-08_ec2_email-alarm.txt` | PARTIAL: ALARM leg complete, OK email not recorded |
| B | `inf2006-grp21-fargate-target-5xx` forced to ALARM at 04:11:17.0 UTC; SNS action executed at 04:11:17.1; wait loop saw OK at 04:13:01; history records ALARM to OK at 04:12:44.7 and the second SNS action at 04:12:44.7 (printed as +08:00, 12:11 and 12:12 on 9 October). The OK email arrived (received 12:12 SGT) and is recorded as a **hand transcription** of the operator's screenshot, clipped by the mail client; its reason reads "no datapoints were received for 2 periods" (the alarm treats missing data as not breaching). The ALARM email and the screenshots are **not in `raw/`** | `raw/MON-03_2026-10-09_fargate_history.txt`, `raw/MON-03_2026-10-09_fargate_force.txt`, `raw/MON-03_2026-10-09_fargate_return-to-ok.txt`, `raw/MON-03_2026-10-09_fargate_email-ok.txt` | PARTIAL: OK leg complete, ALARM email not recorded |

- **Limitation:** A forced state tests the notification path, not detection. Detection under real load is MON-04. The alarm and the SNS topic are the same shared module and topic on both variants; read together, the two variants show an ALARM email (A) and an OK email (B), but no single variant has both.
- **Date:** A 2026-10-08, 17:48 to 17:50 UTC; B 2026-10-09, 04:11 to 04:13 UTC

## MON-04: Detection under real load (from the scale-out runs)

- **Objective:** Show that a real condition, rising load, is detected by an alarm and acted on without a person.
- **Command/steps:** No extra step: the RES-03a scale-out run's export saves `alarm_history.json` and the scaling activities (A) or ECS service events (B).
- **Expected result:** The target-tracking `AlarmHigh` alarm goes to ALARM a few minutes after the load step, followed by a scaling activity that raises the desired count from 1 to 2, and later the low alarm and a scale-in.
- **Actual result:**

| Variant | Alarm time | Scaling action | Raw files | Status |
|---|---|---|---|---|
| A | `TargetTracking-…-AlarmHigh` OK to ALARM at 16:56:07 UTC, 299 s after the load step at 16:51:08 | Instance launched 16:57:11 (64 s after the alarm), desired capacity 1 to 2; second target healthy 16:58:48; `AlarmHigh` back to OK 17:02:07. No scale-in and no `AlarmLow` ALARM before the run ended (17:11:10) | `raw/RES-03-ec2-scaleout-r1_2026-10-08/{alarm_history,scaling_activities}.json` | PASS for scale-out; scale-in not observed |
| B | `TargetTracking-…-AlarmHigh` OK to ALARM at 02:35:20.7 UTC, 305 s after the load step at 02:30:15 | ECS started a task at 02:36:28 (67 s after the alarm), desired 1 to 2; second target healthy 02:37:01.9; `AlarmHigh` back to OK 02:41:20.7. The low alarm is not in the run's export; the task was stopped (scale-in) at 03:03:08 (service events, `raw/SESSION_2026-10-09_fargate_service-events.txt`) | `raw/RES-03-fargate-scaleout-r1_2026-10-09/{alarm_history,ecs_events}.json` | PASS for scale-out; scale-in observed after the run |

- **Date:** A 2026-10-08, 16:48 to 17:11 UTC; B 2026-10-09, 02:27 to 02:50 UTC

## HTTP 400 entries in MON-02

On both variants the 50 rows returned by the saved query are all `ERROR`, logger `django.security.DisallowedHost`, `status 400`, message "Django security rejection".

| Question | Answer | Evidence |
|---|---|---|
| What are they? | Django refused requests whose `Host` header is not in the allowed list (`DJANGO_ALLOWED_HOSTS`, `src/config/settings.py`). Only the stack's own hostname is allowed (`shop-ec2.fourtytwofactors.me` on A, `shop-fargate.fourtytwofactors.me` on B; `modules/web-entry/environment.tf`), plus the load balancer's own health probe by its exact private address. A request addressed to the load balancer's own DNS name, or to its IP address, gets a 400 | `exception: DisallowedHost`, frames `http/request.py get_host` in `raw/MON-01_2026-10-08_ec2_sample_rerun.txt` |
| How many? | The query matched 152 `ERROR` or `WARNING` records and showed 50. The status table counts 303 log lines with status 400, consistent with two lines per rejected request (one security `ERROR`, one request line); not exactly 2 x 152, and not reconciled further. **B:** 181 matched, 50 shown; the status table counts 360 status-400 lines (summed from its rows), about two per rejection | A: `raw/MON-02_…recent-errors…_rerun.txt` (`recordsMatched`), `raw/MON-01_…status-per-5min_rerun.txt`. B: `raw/MON-02_2026-10-09_fargate_recent-errors-and-security-warnings.txt`, `raw/MON-01_2026-10-09_fargate_status-per-5min.txt` |
| When? | A burst in the first minutes after the stack started (252 status-400 lines in the 14:50 window, 8 in the next, 24 of the 50 shown dated 14:51), then a few single requests spread over the day, including during load runs (6 in the 16:40 window, 5 at 17:30, 6 at 18:35). **B:** the large burst is not at start-up: 306 status-400 lines in the 04:00 UTC window, about two hours after the stack was up and during the idle gap between the replacement and saturation runs; otherwise single requests (6 in the 02:15 window, 8 at 02:50, 6 at 04:25). The request line of the newest B rejection is `GET /favicon.ico`, the kind of request a browser sends after loading a page from the load balancer's own address | `raw/MON-01_…status-per-5min_rerun.txt`, timestamps in the MON-02 rerun file |
| Did it affect the shop? | No. Every request of the load runs returned 200 or 302 and the harness counted 0 errors; the load balancer recorded 1 to 3 target 4xx responses in some minutes and no 5xx | `cloudwatch/alb_target_4xx.csv`, `alb_target_5xx.csv` in the run folders |
| Is any a secret leak? | **No.** The application replaces the message of every `django.security.*` record with a fixed text (`src/config/jsonlog.py`), so the offending `Host` value is not written. The rows hold only time, level, logger, status, request ID, exception class and three code locations. The SEC-18 search (password, csrftoken, csrfmiddlewaretoken, sessionid, secret_key) over the same 88,044 records found 0 matches; on B the same search over 77,326 records found 0 | A: `raw/SEC-18_2026-10-08_ec2_count_rerun.txt`. B: `raw/SEC-18_2026-10-09_fargate_count.txt` |
| Who sent them? | **Not known.** The log deliberately drops the `Host` value and the source address, and the load balancer's access logs and the WAF's sampled requests were not exported. The pattern (a burst on each variant, at start-up on A and two hours in on B, then sporadic single requests, none from the load generator) fits internet scanners probing the load balancer by address; a burst that is not tied to start-up on B weakens any idea that the 400s come from the stack's own start-up traffic. That is an inference, not a finding | — |

Operational consequence: the saved "recent errors" query is dominated by these rejections (50 of 50 rows here), so a real application error would be hidden behind them (the same on B). A filter excluding `django.security.DisallowedHost`, or a separate query for status 500 and above, would make the query useful. Not changed in this pass.

## Interpretation

What an operator saw, on variant A (8 October 2026) and variant B (9 October 2026); the findings are the same on both unless a line says otherwise.

- **Logs:** every request is one JSON line in CloudWatch Logs (`/inf2006-grp21-ec2/app`, `/inf2006-grp21-fargate/app`); counting by status over time works (MON-01). Security rejections are logged with a fixed message and no request data. Job output (database reset, migrations) lands in the same group as plain text.
- **Alarms:** the forced 5xx alarm reached the operator's inbox on each variant for one leg that was recorded (ALARM email on A, OK email on B; MON-03). Scaling alarms fired on load and the service acted within 64 s (A) and 67 s (B) (MON-04).
- **Saved queries:** one of the two cannot run as saved on either variant (MON-02, one defective query in the shared module); the other works but is swamped by scanner noise.
- **Not monitored:** no RDS alarm (CPU, connections or credits), no tracing, email only, no alarm on 4xx, and no alarm on slow responses. The RDS CPU credit balance was read from exported metrics after the fact (it stayed at 576 on both variants), not alarmed. Under the 512-user step the single unit failed health checks on both variants (see [test-performance.md](test-performance.md#load-03-saturation-capacity-of-one-unit)); whether the `unhealthy-hosts` alarm fired then was not exported or checked.
- **Cost of retention:** the log groups have 7-day retention and are deleted with the stack, so the raw files in `raw/` are the surviving record.
