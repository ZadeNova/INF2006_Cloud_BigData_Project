# RES-03-ec2-scaleout-r1_2026-10-08

**What this run was:** Scale-out: 10 users for 180 s, a step to 200 users for 900 s, then 10 users for 300 s (23 minutes), with the group allowed to grow from 1 to 2 instances.

| Item | Value |
|---|---|
| Run id | `RES-03-ec2-scaleout-r1_2026-10-08` |
| Variant | A (EC2 with an Auto Scaling group) |
| Type | `scaleout` |
| Started / ended (UTC) | 2026-10-08T16:48:08.322Z / 2026-10-08T17:11:09.994Z |
| Command | `run.py scaleout --variant ec2 --base-url https://shop-ec2.fourtytwofactors.me --repeat 1 --location us-east-1` |
| Image digest | `sha256:fa72e949b47de9cb5c6378608072cb3b376503de8dc11bbb34b98940ea8cb481` (see `stack.json`) |
| Headline numbers (from `analyze.py`) | 11,643 requests, 0 errors. Detection 299 s (load step to alarm), alarm to scaling action 64 s, alarm to second unit healthy 161 s, load step to healthy 460 s. Scale-in not observed in this folder. |

## The six key files

| # | File | What it holds |
|---|---|---|
| 1 | `run.json` | what was run: schedule, seed, commit, `git_dirty_harness`, exact command, generator, start and end |
| 2 | `stack.json` | what it ran on: image digest, database class, capacity (min, max, desired), WAF mode, export window |
| 3 | `timing.json` | the run's start and end times (epoch and UTC) |
| 4 | `targets.jsonl` | target health over time (initial, unhealthy, healthy states, one record per change) |
| 5 | `locust_stats.csv` | Locust's per-request-name summary (counts, failures, percentiles). The per-request log `requests-30556.csv, requests-30557.csv` is what `analyze.py` reads |
| 6 | `cloudwatch/` and `alarm_history.json`, `scaling_activities.json` | one-minute CloudWatch metrics (load balancer, CPU, RDS, WAF) as CSV; the alarm state changes; the Auto Scaling activity that launched the second instance, with its cause |

Everything else in the folder (`cpu.json`, `generator_cpu.csv`, `locust_failures.csv`, `locust_exceptions.csv`, `locust_stats_history.csv`, `report.html`) is supporting detail. No file in this folder was edited or renamed after export.

**Notes:** The `<ACCOUNT>` marker inside some averages of `locust_stats.csv`, `locust_stats_history.csv` and `report.html` is a redaction defect fixed afterwards; `requests-*.csv` is not affected.

**Reproduce the numbers:** from the repository root run `python tests/load/analyze.py --raw evidence/raw` (read-only; add `--out some-file.md` to write the tables to a file); the rows for `RES-03-ec2-scaleout-r1_2026-10-08` are the headline numbers above and match [evidence/load-summary.md](../../load-summary.md).
