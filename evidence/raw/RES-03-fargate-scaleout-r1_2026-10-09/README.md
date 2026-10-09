# RES-03-fargate-scaleout-r1_2026-10-09

**What this run was:** Scale-out: 10 users for 180 s, a step to 200 users for 900 s, then 10 users for 300 s (23 minutes), with the service allowed to grow from 1 to 2 tasks.

| Item | Value |
|---|---|
| Run id | `RES-03-fargate-scaleout-r1_2026-10-09` |
| Variant | B (ECS on Fargate) |
| Type | `scaleout` |
| Started / ended (UTC) | 2026-10-09T02:27:15.319Z / 2026-10-09T02:50:16.918Z |
| Command | `run.py scaleout --variant fargate --base-url https://shop-fargate.fourtytwofactors.me --repeat 1 --location us-east-1` |
| Image digest | `sha256:fa72e949b47de9cb5c6378608072cb3b376503de8dc11bbb34b98940ea8cb481` (see `stack.json`) |
| Headline numbers (from `analyze.py`) | 11,627 requests, 0 errors. Detection 305 s, alarm to scaling action 67 s, alarm to second unit healthy 101 s, load step to healthy 407 s. Scale-in is not in this folder: the task was stopped at 03:03:08 UTC, after the export (see `../SESSION_2026-10-09_fargate_service-events.txt`). |

## The six key files

| # | File | What it holds |
|---|---|---|
| 1 | `run.json` | what was run: schedule, seed, commit, `git_dirty_harness`, exact command, generator, start and end |
| 2 | `stack.json` | what it ran on: image digest, database class, capacity (min, max, desired), WAF mode, export window |
| 3 | `timing.json` | the run's start and end times (epoch and UTC) |
| 4 | `targets.jsonl` | target health over time |
| 5 | `locust_stats.csv` | Locust's per-request-name summary (counts, failures, percentiles). The per-request log `requests-3728.csv, requests-3729.csv` is what `analyze.py` reads |
| 6 | `cloudwatch/` and `alarm_history.json`, `ecs_events.json` | one-minute CloudWatch metrics (load balancer, CPU, RDS, WAF) as CSV; the alarm state changes; the ECS service events (task started, registered, steady state) |

Everything else in the folder (`cpu.json`, `generator_cpu.csv`, `locust_failures.csv`, `locust_exceptions.csv`, `locust_stats_history.csv`, `report.html`) is supporting detail. No file in this folder was edited or renamed after export.

**Notes:** `run.json` records `git_dirty_harness: true`.

**Reproduce the numbers:** from the repository root run `python tests/load/analyze.py --raw evidence/raw` (read-only; add `--out some-file.md` to write the tables to a file); the rows for `RES-03-fargate-scaleout-r1_2026-10-09` are the headline numbers above and match [evidence/load-summary.md](../../load-summary.md).
