# Monitoring / operational evidence

**Status:** PLANNED. The expected results below were written on 8 October 2026, before any cloud run. Every case runs identically on variant A (`ec2`) and variant B (`fargate`) through `src/infrastructure/scripts/evidence.sh`; procedure and order in [docs/plans/evidence-session.md](../docs/plans/evidence-session.md). Raw files are redacted (account IDs, public IPs, email addresses) when they are written.

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
| A | | `raw/MON-01_<date>_ec2_{sample,status-per-5min}.txt` | |
| B | | `raw/MON-01_<date>_fargate_{sample,status-per-5min}.txt` | |

- **Date:** —

## MON-02: Saved Logs Insights queries

- **Objective:** Show that the two saved queries an operator would use during an incident run and return results.
- **Command/steps:** `evidence.sh <variant> logs`, steps `MON-02 saved queries` (`<stack>/recent-errors-and-security-warnings`, `<stack>/errors-and-warnings-per-minute`), run over the session window.
- **Expected result:** `status: Complete` for both. The rows show the session's warnings, for example the failed logins of the SEC-17 burst if the app logs them; an empty result is valid when nothing matched, and is stated as such.
- **Actual result:**

| Variant | Result | Raw files | Status |
|---|---|---|---|
| A | | `raw/MON-02_<date>_ec2_*.txt` | |
| B | | `raw/MON-02_<date>_fargate_*.txt` | |

- **Date:** —

## MON-03: An alarm reaches the operator by email

- **Objective:** Show the path from a CloudWatch alarm to an operator's inbox, and back to OK.
- **Setup:** The SNS email subscription is confirmed (checked in the preflight, `raw/PRE_<date>_sns.txt`).
- **Command/steps:** `evidence.sh <variant> alarm`: forces `<stack>-target-5xx` to ALARM with `set-alarm-state`, waits for the next evaluation to return it to OK, saves the alarm history; then the two emails are saved as screenshots with the address, account number and unsubscribe link cropped out.
- **Expected result:** History: a `StateUpdate` OK to ALARM, an `Action` "Successfully executed action arn:aws:sns:…", a `StateUpdate` ALARM to OK within about 2 minutes, and a second `Action`. Two emails: "ALARM: …-target-5xx" and "OK: …-target-5xx".
- **Actual result:**

| Variant | Result | Raw files | Status |
|---|---|---|---|
| A | | `raw/MON-03_<date>_ec2_{force,return-to-ok,history}.txt`, `raw/MON-03_<date>_ec2_email-{alarm,ok}.png` | |
| B | | `raw/MON-03_<date>_fargate_{force,return-to-ok,history}.txt`, `raw/MON-03_<date>_fargate_email-{alarm,ok}.png` | |

- **Limitation:** A forced state tests the notification path, not detection. Detection under real load is MON-04.
- **Date:** —

## MON-04: Detection under real load (from the scale-out runs)

- **Objective:** Show that a real condition, rising load, is detected by an alarm and acted on without a person.
- **Command/steps:** No extra step: the RES-03a scale-out run's export saves `alarm_history.json` and the scaling activities (A) or ECS service events (B).
- **Expected result:** The target-tracking `AlarmHigh` alarm goes to ALARM a few minutes after the load step, followed by a scaling activity that raises the desired count from 1 to 2, and later the low alarm and a scale-in.
- **Actual result:**

| Variant | Alarm time | Scaling action | Raw files | Status |
|---|---|---|---|---|
| A | | | `raw/RES-03-ec2-scaleout-r1_<date>/{alarm_history,scaling_activities}.json` | |
| B | | | `raw/RES-03-fargate-scaleout-r1_<date>/{alarm_history,ecs_events}.json` | |

- **Date:** —

## Interpretation

To be written after the runs: what an operator sees, how fast, and what is not monitored (no tracing, no RDS alarm, email only).
