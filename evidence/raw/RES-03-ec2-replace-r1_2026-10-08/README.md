# RES-03-ec2-replace-r1_2026-10-08

**What this run was:** Replacement: 100 users for 20 minutes with two instances; one is removed gracefully (the Auto Scaling group is asked to terminate it) 300 s into the run, and the run continues until two healthy instances are back.

| Item | Value |
|---|---|
| Run id | `RES-03-ec2-replace-r1_2026-10-08` |
| Variant | A (EC2 with an Auto Scaling group) |
| Type | `replace` |
| Started / ended (UTC) | 2026-10-08T17:23:17.899Z / 2026-10-08T17:43:20.173Z |
| Command | `run.py replace --variant ec2 --base-url https://shop-ec2.fourtytwofactors.me --repeat 1 --location us-east-1` |
| Image digest | `sha256:fa72e949b47de9cb5c6378608072cb3b376503de8dc11bbb34b98940ea8cb481` (see `stack.json`) |
| Headline numbers (from `analyze.py`) | 7,474 requests, 0 errors. Kill to detected 2 s, replacement 114 s (removal to two healthy), error window 0 s, errors in the window 0, errors later in the run 0. |

## The six key files

| # | File | What it holds |
|---|---|---|
| 1 | `run.json` | what was run: schedule, seed, commit, `git_dirty_harness`, exact command, generator, start and end |
| 2 | `stack.json` | what it ran on: image digest, database class, capacity (min, max, desired), WAF mode, export window |
| 3 | `timing.json` | the run's start and end times (epoch and UTC) |
| 4 | `targets.jsonl` and `kill.json` | target health over time; `kill.json` is the removal itself (time, unit, graceful) |
| 5 | `locust_stats.csv` | Locust's per-request-name summary (counts, failures, percentiles). The per-request log `requests-31735.csv, requests-31736.csv` is what `analyze.py` reads |
| 6 | `cloudwatch/` and `alarm_history.json`, `scaling_activities.json` | one-minute CloudWatch metrics (load balancer, CPU, RDS, WAF) as CSV; the alarm state changes; the termination and the replacement launch |

Everything else in the folder (`cpu.json`, `generator_cpu.csv`, `locust_failures.csv`, `locust_exceptions.csv`, `locust_stats_history.csv`, `report.html`) is supporting detail. No file in this folder was edited or renamed after export.

**Notes:** The `<ACCOUNT>` marker inside some averages of the Locust summary files is a redaction defect fixed afterwards; `requests-*.csv` is not affected.

**Reproduce the numbers:** from the repository root run `python tests/load/analyze.py --raw evidence/raw` (read-only; add `--out some-file.md` to write the tables to a file); the rows for `RES-03-ec2-replace-r1_2026-10-08` are the headline numbers above and match [evidence/load-summary.md](../../load-summary.md).
